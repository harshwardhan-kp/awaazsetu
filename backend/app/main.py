import asyncio, csv, io, secrets, hmac, json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Request,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
)
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .config import settings, ROOT
from .db import (
    Base,
    engine,
    get_db,
    SessionLocal,
    Incident,
    Report,
    History,
    Contact,
    Outbox,
    Alert,
    IntakeKey,
    now,
    ensure_schema,
)
from .security import admin, make_token, digest, rate_limit
from .schemas import ReportIn, LoginIn, UpdateIn, MergeIn, ClarifyIn, AlertIn
from .service import intake, incident_json, rescore, budget, save_contact
from .m3.location import resolve_location, get_gazetteer
from .m4.notifications import acknowledgement, status_message, CLARIFY, queue, deliver
from .m4.coverage import coverage, BASELINE_NOTE
from .m1.voice import transcribe


async def delivery_loop():
    ticks = 0
    while True:
        await asyncio.sleep(15)
        try:
            with SessionLocal() as db:
                await deliver(db)
                ticks += 1
                if ticks % 5760 == 0:
                    from .maintenance import purge

                    purge(db)
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app):
    if not all(
        [
            settings.admin_password,
            settings.jwt_secret,
            settings.contact_hash_secret,
            settings.contact_encryption_key,
        ]
    ):
        raise RuntimeError(
            "Missing required secrets. Run scripts/init_env.py before starting."
        )
    ensure_schema()
    from .maintenance import purge

    with SessionLocal() as db:
        purge(db)
    worker = asyncio.create_task(delivery_loop())
    yield
    worker.cancel()
    try:
        await worker
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="AwaazSetu",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
from .middleware import BodyLimitMiddleware

app.add_middleware(BodyLimitMiddleware, max_bytes=settings.voice_max_bytes + 100000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Webhook-Secret"],
)


@app.middleware("http")
async def secure_headers(request, call_next):
    length = request.headers.get("content-length", "0")
    try:
        if int(length) > settings.voice_max_bytes + 100000:
            return Response("Request too large", status_code=413)
    except ValueError:
        return Response("Invalid content length", status_code=400)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(self), geolocation=(self)"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://tile.openstreetmap.org https://*.tile.openstreetmap.org; connect-src 'self' https://tile.openstreetmap.org https://*.tile.openstreetmap.org; font-src 'self' data:; media-src 'self' blob:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "mode": "drill" if settings.demo_mode else "pilot",
        "demo": settings.demo_mode,
        "capabilities": {
            "ai_extraction": bool(settings.openai_api_key and settings.ai_enabled),
            "voice": bool(settings.openai_api_key and settings.ai_enabled),
            "sms": bool(settings.sms_gateway_url and settings.delivery_enabled),
            "telegram": bool(settings.telegram_bot_token and settings.delivery_enabled),
        },
    }


@app.post("/api/auth/login")
def login(payload: LoginIn, request: Request):
    rate_limit(request, "login", 5, 60)
    if not hmac.compare_digest(
        payload.password.encode(), settings.admin_password.encode()
    ):
        raise HTTPException(401, "Incorrect coordinator password")
    return {"token": make_token(), "expires_in": 43200}


@app.post("/api/reports")
async def create_report(
    payload: ReportIn, request: Request, db: Session = Depends(get_db)
):
    rate_limit(request)
    # Only trusted webhooks can assert SMS/Telegram source identities.
    if payload.channel not in {"web", "voice"}:
        raise HTTPException(
            422,
            "SMS and Telegram reports must arrive through their authenticated gateways",
        )
    return await intake(db, payload)


@app.post("/api/transcriptions")
async def voice_preview(
    request: Request,
    audio: UploadFile = File(...),
    language: str | None = Form(None),
    consent: bool = Form(False),
    db: Session = Depends(get_db),
):
    rate_limit(request, "voice", 5, 60)
    if not consent:
        raise HTTPException(422, "Consent is required")
    if language not in {None, "", "en", "hi", "mr"}:
        raise HTTPException(422, "Unsupported language")
    if not budget(db):
        raise HTTPException(
            503,
            "Voice service is unavailable or daily usage limit reached. Please send text.",
        )
    data = await audio.read(settings.voice_max_bytes + 1)
    if len(data) > settings.voice_max_bytes:
        raise HTTPException(413, "Audio must be under 10 MB")
    text = await transcribe(data, audio.filename or "recording.webm", language or None)
    return {"text": text, "language": language or None}


@app.post("/api/reports/voice")
async def create_voice(
    request: Request,
    audio: UploadFile = File(...),
    language: str | None = Form(None),
    contact: str | None = Form(None),
    consent: bool = Form(False),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    db: Session = Depends(get_db),
):
    rate_limit(request, "voice", 5, 60)
    if not consent:
        raise HTTPException(422, "Consent is required")
    if language not in {None, "", "en", "hi", "mr"}:
        raise HTTPException(422, "Unsupported language")
    if not budget(db):
        raise HTTPException(
            503,
            "Voice service is unavailable or daily usage limit reached. Please send text.",
        )
    data = await audio.read(settings.voice_max_bytes + 1)
    if len(data) > settings.voice_max_bytes:
        raise HTTPException(413, "Audio must be under 10 MB")
    db.commit()
    text = await transcribe(data, audio.filename or "recording.webm", language or None)
    return await intake(
        db,
        ReportIn(
            text=text,
            language=language or None,
            contact=contact,
            channel="voice",
            consent=True,
            latitude=latitude,
            longitude=longitude,
        ),
        use_ai=budget(db),
    )


def tracked(db, ticket, token):
    r = db.scalar(select(Report).where(Report.ticket_id == ticket))
    if not r or not hmac.compare_digest(r.tracking_hash, digest(token)):
        raise HTTPException(404, "Ticket not found or tracking token invalid")
    return r


def tracking_json(db, r):
    i = db.get(Incident, r.incident_id)
    updates = [
        {
            "status": h.status,
            "message": status_message(r.ticket_id, h.status, r.language),
            "created_at": h.created_at,
        }
        for h in db.scalars(
            select(History)
            .where(History.incident_id == i.id)
            .order_by(History.created_at)
        )
    ]
    return {
        "ticket_id": r.ticket_id,
        "status": i.status,
        "language": r.language,
        "acknowledgement": acknowledgement(r.ticket_id, r.language),
        "updates": updates,
        "needs_clarification": i.needs_clarification,
        "clarification_prompt": CLARIFY[r.language] if i.needs_clarification else None,
    }


@app.get("/api/track/{ticket_id}")
def track(ticket_id: str, token: str, request: Request, db: Session = Depends(get_db)):
    rate_limit(request, "tracking", 60, 60)
    return tracking_json(db, tracked(db, ticket_id, token))


@app.post("/api/track/{ticket_id}/clarify")
def clarify(
    ticket_id: str, payload: ClarifyIn, request: Request, db: Session = Depends(get_db)
):
    rate_limit(request, "clarify", 10, 60)
    r = tracked(db, ticket_id, payload.token)
    i = db.get(Incident, r.incident_id)
    loc = resolve_location(payload.text)
    if loc["needs_clarification"]:
        raise HTTPException(
            422, "Landmark is unclear. Please provide a nearby named place in Pune."
        )
    if i.status in {"resolved", "dismissed"}:
        raise HTTPException(409, "This incident is closed; submit a new report")
    if not i.needs_clarification:
        raise HTTPException(409, "Location already set. A coordinator can correct it.")
    r.location = loc
    for key in ["latitude", "longitude", "location_name", "ward"]:
        setattr(i, key, loc.get(key))
    i.location_method = loc["method"]
    i.location_confidence = loc["confidence"]
    i.needs_clarification = False
    i.updated_at = now()
    db.add(
        History(
            incident_id=i.id,
            status=i.status,
            notes="Reporter provided a landmark",
            actor="reporter",
        )
    )
    queue(db, r, status_message(r.ticket_id, i.status, r.language))
    db.commit()
    return tracking_json(db, r)


@app.get("/api/incidents", dependencies=[Depends(admin)])
def incidents(
    status: str | None = None,
    band: str | None = None,
    language: str | None = None,
    channel: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    statement = select(Incident)
    if status:
        statement = statement.where(Incident.status == status)
    if band:
        statement = statement.where(Incident.severity_band == band)
    rows = [
        incident_json(db, i)
        for i in db.scalars(
            statement.order_by(
                Incident.severity_score.desc(), Incident.updated_at.desc()
            ).limit(500)
        )
    ]
    if language:
        rows = [r for r in rows if language in r["languages"]]
    if channel:
        rows = [r for r in rows if channel in r["channels"]]
    if q:
        rows = [r for r in rows if q.casefold() in str(r).casefold()]
    return {"items": rows, "total": len(rows)}


def find_incident(db, id):
    i = db.get(Incident, id)
    if not i:
        raise HTTPException(404, "Incident not found")
    return i


@app.get("/api/incidents/{id}", dependencies=[Depends(admin)])
def get_incident(id: str, db: Session = Depends(get_db)):
    return incident_json(db, find_incident(db, id), True)


@app.patch("/api/incidents/{id}", dependencies=[Depends(admin)])
def update_incident(id: str, payload: UpdateIn, db: Session = Depends(get_db)):
    i = find_incident(db, id)
    if payload.status:
        i.status = payload.status
    i.updated_at = now()
    db.add(
        History(
            incident_id=id, status=i.status, notes=payload.notes, actor="coordinator"
        )
    )
    for r in db.scalars(select(Report).where(Report.incident_id == id)):
        queue(db, r, status_message(r.ticket_id, i.status, r.language))
    db.commit()
    return incident_json(db, i, True)


@app.post("/api/incidents/{id}/merge", dependencies=[Depends(admin)])
def merge(id: str, payload: MergeIn, db: Session = Depends(get_db)):
    target = find_incident(db, id)
    source = find_incident(db, payload.source_id)
    if target.id == source.id:
        raise HTTPException(422, "Choose two different incidents")
    if len(payload.reason.strip()) < 5:
        raise HTTPException(
            422,
            "Add a review note explaining why these reports describe the same incident",
        )
    if target.status in {"resolved", "dismissed"}:
        raise HTTPException(409, "Cannot merge into a closed incident")
    for r in db.scalars(select(Report).where(Report.incident_id == source.id)):
        r.incident_id = target.id
        queue(db, r, status_message(r.ticket_id, target.status, r.language))
    for h in db.scalars(select(History).where(History.incident_id == source.id)):
        h.incident_id = target.id
    db.add(
        History(
            incident_id=target.id,
            status=target.status,
            notes=f"Coordinator merged incident {source.ticket_id}. Reason: {payload.reason.strip()}",
            actor="coordinator",
        )
    )
    db.flush()
    db.delete(source)
    rescore(db, target)
    db.commit()
    return incident_json(db, target, True)


@app.get("/api/coverage", dependencies=[Depends(admin)])
def get_coverage(db: Session = Depends(get_db)):
    return coverage(db)


@app.get("/api/outbox", dependencies=[Depends(admin)])
def outbox(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Outbox).order_by(Outbox.created_at.desc()).limit(500)
    ).all()
    return {
        "items": [
            {
                c: getattr(r, c)
                for c in [
                    "id",
                    "channel",
                    "ticket_id",
                    "language",
                    "message",
                    "status",
                    "created_at",
                    "attempts",
                    "last_error",
                ]
            }
            for r in rows
        ],
        "total": len(rows),
    }


@app.post("/api/outbox/retry", dependencies=[Depends(admin)])
async def retry(db: Session = Depends(get_db)):
    return await deliver(db)


@app.post("/api/alerts", dependencies=[Depends(admin)])
def alert(payload: AlertIn, db: Session = Depends(get_db)):
    a = Alert(ward=payload.ward, message=payload.message)
    db.add(a)
    db.flush()
    contacts = db.scalars(
        select(Contact).where(Contact.opted_in == True, Contact.ward == payload.ward)
    ).all()
    count = 0
    for c in contacts:
        if payload.language and c.language != payload.language:
            continue
        # Use only matching-language alerts rather than pretending an arbitrary message was translated.
        if not payload.language:
            continue
        db.add(
            Outbox(
                contact_id=c.id,
                channel=c.channel,
                language=c.language,
                message=f"[Drill / सराव / अभ्यास] {payload.message}",
                status="queued",
                kind="area_alert",
            )
        )
        count += 1
    db.commit()
    return {
        "queued": count,
        "alert_id": a.id,
        "note": "Only opted-in contacts with the selected language receive alerts.",
    }


@app.get("/api/settings", dependencies=[Depends(admin)])
def get_settings():
    return {
        "demo": settings.demo_mode,
        "integrations": [
            {
                "name": "OpenAI extraction and speech",
                "configured": bool(settings.openai_api_key and settings.ai_enabled),
                "description": "Schema extraction with keyword fallback; audio sent to OpenAI only with consent.",
            },
            {
                "name": "Android SMS gateway",
                "configured": bool(
                    settings.sms_gateway_url
                    and settings.sms_gateway_user
                    and settings.delivery_enabled
                ),
                "description": "Connect the Android phone/SIM and authenticated gateway after the product review.",
            },
            {
                "name": "Telegram bot",
                "configured": bool(
                    settings.telegram_bot_token and settings.delivery_enabled
                ),
                "description": "Configure a bot token and webhook secret.",
            },
        ],
        "gazetteer_count": len(get_gazetteer()),
        "baseline_note": BASELINE_NOTE,
        "daily_ai_limit": settings.daily_ai_limit,
        "retention_days": settings.retention_days,
        "delivery_enabled": settings.delivery_enabled,
    }


@app.get("/api/export/reports.csv", dependencies=[Depends(admin)])
def export(db: Session = Depends(get_db)):
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(
        [
            "ticket_id",
            "language",
            "channel",
            "text",
            "incident_type",
            "created_at",
            "synthetic",
        ]
    )

    def safe(v):
        s = str(v)
        return "'" + s if s.startswith(("=", "+", "-", "@", "\t", "\r")) else s

    for r in db.scalars(select(Report).order_by(Report.created_at)):
        writer.writerow(
            [
                safe(v)
                for v in [
                    r.ticket_id,
                    r.language,
                    r.channel,
                    r.text,
                    r.fields["incident_type"],
                    r.created_at,
                    r.synthetic,
                ]
            ]
        )
    return Response(
        stream.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="awaazsetu-reports.csv"'},
    )


@app.post("/api/demo/seed", dependencies=[Depends(admin)])
async def seed(db: Session = Depends(get_db)):
    if not settings.demo_mode:
        raise HTTPException(403, "Demo mode disabled")
    examples = [
        ("mr", "एकता नगरमध्ये घरात पाणी शिरलं आहे, कमरेइतकं पाणी, आजी अडकल्या आहेत.", "sms"),
        ("hi", "Warje में सड़क पर घुटने तक पानी है।", "web"),
        (
            "en",
            "Medical emergency in Dattawadi. A sick elderly person needs medicine.",
            "telegram",
        ),
        ("mr", "कर्वेनगर येथे घरात छातीपर्यंत पाणी आहे. दोन लहान मुले अडकली आहेत.", "voice"),
        (
            "en",
            "Water is entering homes in Erandwane. Five people need food and clean drinking water.",
            "web",
        ),
        ("hi", "वडगाव बुद्रुक में सड़क पर पानी भर गया है।", "sms"),
        (
            "en",
            "A family is trapped near an unknown unnamed bridge. Need rescue.",
            "web",
        ),
        ("hi", "एकता नगर में घर में कमर तक पानी है और बुजुर्ग फँसे हैं।", "telegram"),
        ("en", "Road flooded in Warje, knee deep water.", "sms"),
    ]
    added = 0
    for n, (lang, text, channel) in enumerate(examples):
        result = await intake(
            db,
            ReportIn(
                text=text,
                language=lang,
                channel=channel,
                consent=True,
                idempotency_key=f"demo-v1-{n}",
            ),
            synthetic=True,
            use_ai=False,
        )
        if not result.get("duplicate"):
            added += 1
        else:
            # Refresh only synthetic single-report fixtures after policy/resolver changes.
            old = db.scalar(
                select(Report).where(Report.idempotency_key == f"demo-v1-{n}")
            )
            if old and old.synthetic:
                i = db.get(Incident, old.incident_id)
                from .m2.triage import extract_report

                old.fields = await extract_report(text, lang, use_ai=False)
                old.location = resolve_location(text)
                count = db.scalar(
                    select(func.count())
                    .select_from(Report)
                    .where(Report.incident_id == i.id)
                )
                if count == 1:
                    i.incident_type = old.fields["incident_type"]
                    i.summary = old.fields["summary"]
                    for field in ["latitude", "longitude", "location_name", "ward"]:
                        setattr(i, field, old.location.get(field))
                    i.location_method = old.location["method"]
                    i.location_confidence = old.location["confidence"]
                    i.needs_clarification = old.location["needs_clarification"]
                rescore(db, i)
                db.commit()
    return {
        "reports": added,
        "incidents": db.scalar(select(func.count()).select_from(Incident)),
    }


@app.post("/api/maintenance/purge", dependencies=[Depends(admin)])
def purge_reports(db: Session = Depends(get_db)):
    from .maintenance import purge

    return purge(db)


# Integration routes are imported after the common app/service are defined.
from .m1.webhooks import router

app.include_router(router)

DIST = ROOT / "frontend/dist"


@app.get("/{path:path}")
def frontend(path: str):
    if path.startswith("api/"):
        raise HTTPException(404, "Endpoint not found")
    target = (DIST / path).resolve()
    if target.is_relative_to(DIST.resolve()) and target.is_file():
        return FileResponse(target)
    if (DIST / "index.html").is_file():
        return FileResponse(DIST / "index.html")
    return {
        "message": "Frontend not built. Run npm install && npm run build in frontend/."
    }
