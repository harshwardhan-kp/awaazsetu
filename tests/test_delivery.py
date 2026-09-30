import asyncio
import httpx
from sqlalchemy import select
from backend.app.db import SessionLocal, Outbox, Contact
from backend.app.config import settings
from backend.app.m4.notifications import deliver
from backend.app.security import encrypt
from test_api import client


def test_transactional_delivery_and_concurrent_retry_are_safe(client, monkeypatch):
    monkeypatch.setattr(settings, "delivery_enabled", True)
    monkeypatch.setattr(settings, "sms_gateway_url", "https://test.invalid")
    monkeypatch.setattr(settings, "sms_gateway_user", "test")
    monkeypatch.setattr(settings, "sms_gateway_password", "test")
    with SessionLocal() as db:
        c = Contact(
            id="safe-contact",
            encrypted_address=encrypt("+919876543210"),
            channel="sms",
            language="mr",
            opted_in=False,
        )
        db.add(c)
        db.flush()
        db.add(
            Outbox(
                id="transactional-reply",
                contact_id=c.id,
                channel="sms",
                language="mr",
                message="STOP confirmation",
                kind="transactional",
            )
        )
        db.add(
            Outbox(
                id="unsubscribed-alert",
                contact_id=c.id,
                channel="sms",
                language="mr",
                message="Do not send",
                kind="area_alert",
            )
        )
        db.commit()
    calls = []

    async def post(self, url, **kwargs):
        calls.append(kwargs["json"]["id"])
        await asyncio.sleep(0.01)
        return httpx.Response(
            200, json={"state": "Pending"}, request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", post)

    async def concurrently():
        with SessionLocal() as a, SessionLocal() as b:
            return await asyncio.gather(deliver(a), deliver(b))

    asyncio.run(concurrently())
    assert calls == ["transactional-reply"]
    with SessionLocal() as db:
        assert db.get(Outbox, "transactional-reply").status == "gateway_accepted"
        assert db.get(Outbox, "unsubscribed-alert").status == "cancelled"
