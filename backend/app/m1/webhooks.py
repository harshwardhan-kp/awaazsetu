"""Authenticated SMSGate and Telegram adapters. No gateway required for web MVP."""

import hashlib, hmac, time, re, asyncio

webhook_lock = asyncio.Lock()
import httpx
from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..config import settings
from ..db import get_db, Contact, IntakeKey, Report, Outbox
from ..service import intake, save_contact, budget
from ..schemas import ReportIn
from ..security import contact_hash
from ..m4.notifications import deliver
from .voice import transcribe

router = APIRouter(prefix="/api/webhooks")


async def command(db, text, sender, channel, key):
    parts = text.strip().split(maxsplit=1)
    action = parts[0].upper() if parts else ""
    if action not in {"JOIN", "STOP", "START", "/START", "STATUS", "LOCATION"}:
        return None
    from ..service import address

    normalized = address(channel, sender)
    existing = db.get(Contact, contact_hash(channel, normalized))
    c = existing or save_contact(db, channel, sender, "en")
    db.flush()
    if action == "STOP":
        c.opted_in = False
        # Cancel already queued area alerts immediately; status replies remain transactional.
        for item in db.scalars(
            select(Outbox).where(
                Outbox.contact_id == c.id,
                Outbox.kind == "area_alert",
                Outbox.status.in_(["queued", "failed"]),
            )
        ):
            item.status = "cancelled"
        message = "Area alerts stopped. Report status replies remain available. क्षेत्र सूचना बंद. परिसर सूचना बंद."
    elif action == "JOIN":
        args = (parts[1] if len(parts) > 1 else "").split(maxsplit=1)
        lang = args[0] if args and args[0] in {"en", "hi", "mr"} else None
        from ..m3.location import resolve_location

        loc = resolve_location(args[1] if len(args) > 1 else "")
        if not lang or loc["needs_clarification"]:
            message = "To consent to drill area alerts, send JOIN en|hi|mr followed by your Pune area, e.g. JOIN mr Ekta Nagar. STOP cancels alerts."
        else:
            c.opted_in = True
            c.language = lang
            c.ward = loc.get("ward")
            message = "Joined drill area alerts / सराव सूचना सुरू / अभ्यास सूचनाएँ चालू. STOP to unsubscribe."
    elif action == "STATUS":
        ticket = parts[1].strip() if len(parts) > 1 else ""
        r = db.scalar(
            select(Report).where(Report.ticket_id == ticket, Report.contact_id == c.id)
        )
        if r:
            from ..db import Incident
            from ..m4.notifications import status_message

            message = status_message(
                r.ticket_id, db.get(Incident, r.incident_id).status, r.language
            )
        else:
            message = "Ticket not found for this sender. Send STATUS PN-..."
    elif action == "LOCATION":
        args = (parts[1] if len(parts) > 1 else "").split(maxsplit=1)
        r = (
            db.scalar(
                select(Report).where(
                    Report.ticket_id == args[0], Report.contact_id == c.id
                )
            )
            if args
            else None
        )
        from ..db import Incident, History, now
        from ..m3.location import resolve_location

        loc = resolve_location(args[1] if len(args) > 1 else "")
        i = db.get(Incident, r.incident_id) if r else None
        if (
            i
            and i.needs_clarification
            and i.status not in {"resolved", "dismissed"}
            and not loc["needs_clarification"]
        ):
            r.location = loc
            for field in ["latitude", "longitude", "location_name", "ward"]:
                setattr(i, field, loc.get(field))
            i.location_method = loc["method"]
            i.location_confidence = loc["confidence"]
            i.needs_clarification = False
            i.updated_at = now()
            db.add(
                History(
                    incident_id=i.id,
                    status=i.status,
                    notes="Reporter clarified location through gateway",
                    actor="reporter",
                )
            )
            message = f"{r.ticket_id}: Location updated."
        else:
            message = "Send LOCATION PN-... nearby landmark for your unresolved ticket."
    else:
        message = "AwaazSetu is a flood-reporting drill. Sending a report consents to processing and replies; text and voice may be sent to an AI provider. Do not include names or identity documents. Send JOIN mr Ekta Nagar for area alerts, STOP to unsubscribe."
    db.add(
        Outbox(
            contact_id=c.id,
            channel=channel,
            language=c.language,
            message=message,
            status="queued",
        )
    )
    db.add(IntakeKey(id=key))
    db.commit()
    return {"ok": True, "command": action}


@router.post("/sms")
async def sms(request: Request, db: Session = Depends(get_db)):
    async with webhook_lock:
        return await _sms(request, db)


async def _sms(request, db):
    if not settings.sms_webhook_secret:
        raise HTTPException(503, "SMS gateway not configured")
    raw = await request.body()
    if len(raw) > 20000:
        raise HTTPException(413, "Webhook too large")
    # SMSGate v1 signs original JSON payload concatenated with timestamp.
    supplied = request.headers.get("x-webhook-secret", "")
    signature = request.headers.get("x-signature", "")
    timestamp = request.headers.get("x-timestamp", "")
    valid = bool(
        supplied and hmac.compare_digest(supplied, settings.sms_webhook_secret)
    )
    if not valid and timestamp:
        try:
            fresh = abs(time.time() - int(timestamp)) <= 300
            expected = hmac.new(
                settings.sms_webhook_secret.encode(),
                raw + timestamp.encode(),
                hashlib.sha256,
            ).hexdigest()
            valid = fresh and hmac.compare_digest(signature, expected)
        except ValueError:
            pass
    if not valid:
        raise HTTPException(401, "Invalid webhook authentication")
    try:
        body = __import__("json").loads(raw)
    except Exception:
        raise HTTPException(422, "Invalid JSON")
    if body.get("event") in {"sms:delivered", "sms:failed", "sms:sent"}:
        data = body.get("payload", {})
        item = db.get(Outbox, data.get("messageId", ""))
        if item and item.channel == "sms":
            item.status = {
                "sms:delivered": "delivered",
                "sms:failed": "failed",
                "sms:sent": "sent",
            }[body["event"]]
            if item.status == "failed":
                item.last_error = "Gateway reported delivery failure"
            db.commit()
        return {"ok": True}
    if body.get("event") != "sms:received":
        return {"ok": True, "ignored": True}
    p = body.get("payload", {})
    sender = p.get("sender")
    text = p.get("message")
    message_id = p.get("messageId") or body.get("id")
    if not all(isinstance(v, str) and v for v in [sender, text, message_id]):
        raise HTTPException(422, "Missing sender, message or messageId")
    key = "sms:" + str(body.get("deviceId", "default")) + ":" + message_id
    if db.get(IntakeKey, key):
        return {"ok": True, "duplicate": True}
    result = await command(db, text, sender, "sms", key)
    if result:
        return result
    try:
        payload = ReportIn(
            text=text, channel="sms", contact=sender, consent=True, idempotency_key=key
        )
    except ValidationError:
        raise HTTPException(422, "Invalid SMS report")
    result = await intake(db, payload)
    db.add(IntakeKey(id=key))
    db.commit()
    return {"ok": True, "ticket_id": result["ticket_id"]}


@router.post("/telegram")
async def telegram(request: Request, db: Session = Depends(get_db)):
    async with webhook_lock:
        return await _telegram(request, db)


async def _telegram(request, db):
    if not settings.telegram_bot_token or not settings.telegram_webhook_secret:
        raise HTTPException(503, "Telegram not configured")
    if not hmac.compare_digest(
        request.headers.get("x-telegram-bot-api-secret-token", ""),
        settings.telegram_webhook_secret,
    ):
        raise HTTPException(401, "Invalid webhook authentication")
    raw = await request.body()
    if len(raw) > 20000:
        raise HTTPException(413, "Webhook too large")
    try:
        body = __import__("json").loads(raw)
    except Exception:
        raise HTTPException(422, "Invalid JSON")
    message = body.get("message", {})
    update_id = body.get("update_id")
    if update_id is None:
        return {"ok": True, "ignored": True}
    key = "telegram:" + str(update_id)
    if db.get(IntakeKey, key):
        return {"ok": True, "duplicate": True}
    chat = message.get("chat", {})
    if chat.get("type") != "private":
        return {"ok": True, "ignored": True}
    sender = str(chat.get("id", ""))
    text = message.get("text", "")
    if text:
        result = await command(db, text, sender, "telegram", key)
        if result:
            return result
    elif message.get("voice"):
        if not budget(db):
            raise HTTPException(503, "Daily voice usage limit reached")
        db.commit()
        voice = message["voice"]
        if (
            voice.get("file_size", 0) > settings.voice_max_bytes
            or voice.get("duration", 0) > 120
        ):
            raise HTTPException(413, "Voice note too long; maximum 2 minutes / 10 MB")
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                meta = await client.get(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/getFile",
                    params={"file_id": voice["file_id"]},
                )
                meta.raise_for_status()
                path = meta.json()["result"]["file_path"]
                if ".." in path or not re.fullmatch(r"[A-Za-z0-9_./-]+", path):
                    raise ValueError()
                data = await client.get(
                    f"https://api.telegram.org/file/bot{settings.telegram_bot_token}/{path}"
                )
                data.raise_for_status()
            if len(data.content) > settings.voice_max_bytes:
                raise HTTPException(413, "Voice note too large")
            text = await transcribe(data.content, "voice.ogg")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(503, "Unable to retrieve voice note")
    else:
        return {"ok": True, "ignored": True}
    try:
        payload = ReportIn(
            text=text,
            channel="telegram",
            contact=sender,
            consent=True,
            idempotency_key=key,
        )
    except ValidationError:
        raise HTTPException(422, "Invalid Telegram report")
    result = await intake(db, payload)
    db.add(IntakeKey(id=key))
    db.commit()
    return {"ok": True, "ticket_id": result["ticket_id"]}
