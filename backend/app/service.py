import math, secrets, re
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func
from fastapi import HTTPException
from .db import Incident, Report, Contact, History, Usage, now
from .config import settings
from .security import digest, contact_hash, encrypt
from .schemas import ReportIn
from .m2.triage import extract_report, score_report, similarity
from .m3.location import resolve_location
from .m4.notifications import queue, acknowledgement, CLARIFY

# Serialize intake through the API process; run one worker for SQLite. Postgres deployment may use row/advisory locking.
import asyncio

intake_lock = asyncio.Lock()


def budget(db):
    if not settings.ai_enabled or not settings.openai_api_key:
        return False
    key = datetime.now(timezone.utc).date().isoformat()
    row = db.get(Usage, key)
    if not row:
        row = Usage(id=key, count=0)
        db.add(row)
    if row.count >= settings.daily_ai_limit:
        return False
    row.count += 1
    db.commit()
    return True


def address(channel, value):
    value = value.strip()
    if channel == "telegram":
        if not re.fullmatch(r"-?\d{1,20}", value):
            raise HTTPException(422, "Invalid Telegram chat ID")
        return value
    value = re.sub(r"[\s()-]", "", value)
    if re.fullmatch(r"[6-9]\d{9}", value):
        value = "+91" + value
    if not re.fullmatch(r"\+[1-9]\d{7,14}", value):
        raise HTTPException(422, "Use a valid phone number, including country code")
    return value


def save_contact(db, channel, value, lang, ward=None):
    value = address(channel, value)
    key = contact_hash(channel, value)
    row = db.get(Contact, key)
    if not row:
        row = Contact(
            id=key,
            encrypted_address=encrypt(value),
            channel=channel,
            language=lang,
            ward=ward,
            opted_in=False,
        )
        db.add(row)
    else:
        if not row.opted_in:
            row.language = lang
            if ward:
                row.ward = ward
    return row


def distance(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 6371000 * 2 * math.atan2(math.sqrt(h), math.sqrt(max(0, 1 - h)))


def report_json(r):
    return {
        "id": r.id,
        "ticket_id": r.ticket_id,
        "text": r.text,
        "language": r.language,
        "channel": r.channel,
        "fields": r.fields,
        "location": r.location,
        "consent": r.consent,
        "created_at": r.created_at,
        "extraction_method": r.fields.get("extraction_method", "rules"),
        "synthetic": r.synthetic,
    }


def incident_json(db, i, detail=False):
    reports = db.scalars(
        select(Report).where(Report.incident_id == i.id).order_by(Report.created_at)
    ).all()
    result = {c.name: getattr(i, c.name) for c in Incident.__table__.columns}
    result.update(
        report_count=len(reports),
        unique_reporters=len(
            {
                r.contact_id
                for r in reports
                if r.contact_id and r.channel in {"sms", "telegram"}
            }
        ),
        anonymous_reports=sum(r.contact_id is None for r in reports),
        languages=sorted({r.language for r in reports}),
        channels=sorted({r.channel for r in reports}),
    )
    if detail:
        result["reports"] = [report_json(r) for r in reports]
        result["history"] = [
            {
                "status": h.status,
                "notes": h.notes,
                "created_at": h.created_at,
                "actor": h.actor,
            }
            for h in db.scalars(
                select(History)
                .where(History.incident_id == i.id)
                .order_by(History.created_at)
            ).all()
        ]
    return result


def rescore(db, i):
    reports = db.scalars(select(Report).where(Report.incident_id == i.id)).all()
    count = len(
        {
            r.contact_id
            for r in reports
            if r.contact_id and r.channel in {"sms", "telegram"}
        }
    )
    from zoneinfo import ZoneInfo

    def is_night(r):
        hour = (
            datetime.fromisoformat(r.created_at)
            .astimezone(ZoneInfo("Asia/Kolkata"))
            .hour
        )
        return hour >= 19 or hour < 6

    scored = [
        score_report(r.fields, corroborations=count, night=is_night(r)) for r in reports
    ]
    if scored:
        strongest = max(scored, key=lambda s: s["score"])
        i.severity_score = strongest["score"]
        i.severity_band = strongest["band"]
        i.severity_reasons = strongest["reasons"]
    i.updated_at = now()


async def intake(db, payload: ReportIn, synthetic=False, use_ai=None):
    async with intake_lock:
        if payload.idempotency_key:
            existing = db.scalar(
                select(Report).where(Report.idempotency_key == payload.idempotency_key)
            )
            if existing:
                return {"duplicate": True, "ticket_id": existing.ticket_id}
        enabled = budget(db) if use_ai is None else use_ai
        fields = await extract_report(payload.text, payload.language, use_ai=enabled)
        lang = fields.get("language") or payload.language or "en"
        location = resolve_location(
            fields.get("location_text") or payload.text,
            payload.latitude,
            payload.longitude,
        )
        # If AI extracts a bad place phrase, retry the original text before asking.
        if location.get("needs_clarification") and fields.get("location_text"):
            original = resolve_location(
                payload.text, payload.latitude, payload.longitude
            )
            if not original.get("needs_clarification"):
                location = original
        contact = None
        if payload.contact:
            contact = save_contact(
                db,
                "telegram" if payload.channel == "telegram" else "sms",
                payload.contact,
                lang,
                location.get("ward"),
            )
            db.flush()
        ticket = "PN-" + secrets.token_hex(4).upper()
        token = secrets.token_urlsafe(32)
        match = None
        if (
            location.get("latitude") is not None
            and location.get("confidence", 0) >= 0.8
            and fields["incident_type"] != "other"
        ):
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
            candidates = db.scalars(
                select(Incident)
                .where(
                    Incident.created_at >= cutoff,
                    Incident.incident_type == fields["incident_type"],
                    Incident.status.in_(["new", "verified", "responding"]),
                    Incident.latitude.is_not(None),
                )
                .order_by(Incident.created_at.desc())
                .limit(10)
            ).all()
            for candidate in candidates:
                if candidate.location_confidence < 0.8:
                    continue
                if (
                    distance(
                        (location["latitude"], location["longitude"]),
                        (candidate.latitude, candidate.longitude),
                    )
                    > 500
                ):
                    continue
                previous = db.scalar(
                    select(Report)
                    .where(Report.incident_id == candidate.id)
                    .order_by(Report.created_at.desc())
                )
                sim = await similarity(
                    fields["summary"]
                    if fields.get("extraction_method") == "openai"
                    else payload.text,
                    previous.fields["summary"]
                    if previous.fields.get("extraction_method") == "openai"
                    else previous.text,
                    use_ai=enabled and budget(db),
                )
                threshold = 0.75 if sim["method"] == "openai_embeddings" else 0.90
                if sim["value"] >= threshold:
                    match = candidate
                    break
        score = score_report(fields)
        if not match:
            match = Incident(
                ticket_id=ticket,
                summary=fields["summary"],
                incident_type=fields["incident_type"],
                severity_score=score["score"],
                severity_band=score["band"],
                severity_reasons=score["reasons"],
                latitude=location.get("latitude"),
                longitude=location.get("longitude"),
                location_name=location.get("location_name"),
                location_method=location["method"],
                location_confidence=location["confidence"],
                ward=location.get("ward"),
                needs_clarification=location["needs_clarification"],
            )
            db.add(match)
            db.flush()
            db.add(
                History(
                    incident_id=match.id,
                    status="new",
                    notes="Report received; awaiting human review",
                    actor="system",
                )
            )
        report = Report(
            ticket_id=ticket,
            tracking_hash=digest(token),
            incident_id=match.id,
            contact_id=contact.id if contact else None,
            text=payload.text,
            language=lang,
            channel=payload.channel,
            fields=fields,
            location=location,
            consent=True,
            idempotency_key=payload.idempotency_key,
            synthetic=synthetic,
        )
        db.add(report)
        db.flush()
        rescore(db, match)
        ack = acknowledgement(ticket, lang)
        queue(db, report, ack)
        if location["needs_clarification"]:
            queue(db, report, CLARIFY[lang] + f" LOCATION {ticket} <landmark>")
        db.commit()
        return {
            "report": report_json(report),
            "incident": {
                "id": match.id,
                "ticket_id": ticket,
                "status": match.status,
                "needs_clarification": report.location["needs_clarification"],
                "latitude": report.location.get("latitude"),
                "longitude": report.location.get("longitude"),
                "location_name": report.location.get("location_name"),
                "summary": fields["summary"],
                "severity_score": score["score"],
                "severity_band": score["band"],
                "severity_reasons": score["reasons"],
            },
            "acknowledgement": ack,
            "ticket_id": ticket,
            "tracking_token": token,
            "tracking_url": f"/track/{ticket}?token={token}",
        }
