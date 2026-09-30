import asyncio
import httpx

delivery_lock = asyncio.Lock()
from sqlalchemy import select
from ..config import settings
from ..db import Outbox, Contact
from ..security import decrypt

ACK = {
    "en": "Report received ({ticket}). A coordinator will review it. This is a drill system; help has not been dispatched.",
    "mr": "संदेश मिळाला ({ticket}). समन्वयक तपासतील. ही सराव प्रणाली आहे; मदत रवाना झालेली नाही.",
    "hi": "रिपोर्ट मिली ({ticket})। समन्वयक जाँच करेंगे। यह अभ्यास प्रणाली है; सहायता रवाना नहीं हुई है।",
}
STATUSES = {
    "en": {
        "new": "Awaiting review",
        "verified": "Verified by a coordinator",
        "responding": "Coordinator is following up",
        "resolved": "Marked resolved",
        "dismissed": "Closed after review",
    },
    "mr": {
        "new": "तपासणीची प्रतीक्षा",
        "verified": "समन्वयकांनी तपासले",
        "responding": "समन्वयक पाठपुरावा करत आहेत",
        "resolved": "समस्या सुटली म्हणून नोंद",
        "dismissed": "तपासणीनंतर बंद",
    },
    "hi": {
        "new": "जाँच की प्रतीक्षा",
        "verified": "समन्वयक ने जाँच की",
        "responding": "समन्वयक आगे की कार्रवाई कर रहे हैं",
        "resolved": "समस्या हल होने की सूचना",
        "dismissed": "जाँच के बाद बंद",
    },
}
CLARIFY = {
    "en": "Which nearby landmark or area are you at? Reply with its name.",
    "mr": "तुमच्या जवळ कोणती खूण किंवा परिसर आहे? नाव पाठवा.",
    "hi": "आपके पास कौन सा स्थान या पहचान की जगह है? उसका नाम भेजें।",
}


def acknowledgement(ticket, lang):
    return ACK.get(lang, ACK["en"]).format(ticket=ticket)


def status_message(ticket, status, lang):
    return f"{ticket}: {STATUSES.get(lang, STATUSES['en']).get(status, status)}."


def queue(db, report, message):
    contact = db.get(Contact, report.contact_id) if report.contact_id else None
    obj = Outbox(
        report_id=report.id,
        contact_id=report.contact_id,
        ticket_id=report.ticket_id,
        channel=contact.channel if contact else "web",
        language=report.language,
        message=message,
        status=(
            "queued"
            if report.channel in {"sms", "telegram"}
            else "awaiting_contact_verification"
        )
        if contact
        else "available_in_ticket",
    )
    db.add(obj)
    return obj


async def deliver(db, limit=50):
    async with delivery_lock:
        return await _deliver(db, limit)


async def _deliver(db, limit=50):
    items = db.scalars(
        select(Outbox)
        .where(Outbox.status.in_(["queued", "failed"]), Outbox.attempts < 3)
        .order_by(Outbox.created_at)
        .limit(limit)
    ).all()
    sent = failed = 0
    if not settings.delivery_enabled:
        return {
            "processed": 0,
            "sent": 0,
            "failed": 0,
            "note": "Delivery disabled; messages retained in outbox.",
        }
    async with httpx.AsyncClient(timeout=15) as client:
        for item in items:
            contact = db.get(Contact, item.contact_id) if item.contact_id else None
            if not contact:
                continue
            if item.kind == "area_alert" and not contact.opted_in:
                item.status = "cancelled"
                continue
            if contact.channel == "sms" and not (
                settings.sms_gateway_url
                and settings.sms_gateway_user
                and settings.sms_gateway_password
            ):
                continue
            if contact.channel == "telegram" and not settings.telegram_bot_token:
                continue
            item.attempts += 1
            try:
                address = decrypt(contact.encrypted_address)
                if contact.channel == "sms":
                    response = await client.post(
                        settings.sms_gateway_url.rstrip("/") + "/messages",
                        auth=(settings.sms_gateway_user, settings.sms_gateway_password),
                        json={
                            "id": item.id,
                            "textMessage": {"text": item.message},
                            "phoneNumbers": [address],
                        },
                    )
                    response.raise_for_status()
                    item.status = (
                        "gateway_accepted"  # accepted is not proof of handset delivery
                    )
                elif contact.channel == "telegram":
                    response = await client.post(
                        f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                        json={"chat_id": address, "text": item.message},
                    )
                    response.raise_for_status()
                    if not response.json().get("ok"):
                        raise ValueError("Provider rejected message")
                    item.status = "sent"
                else:
                    continue
                item.last_error = None
                sent += 1
            except Exception:
                item.status = "failed"
                item.last_error = "Delivery failed; inspect gateway configuration"
                failed += 1
        db.commit()
    return {"processed": sent + failed, "sent": sent, "failed": failed}
