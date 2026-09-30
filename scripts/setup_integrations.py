#!/usr/bin/env python3
"""Explicit operator setup only. Registers webhooks; sends no messages."""

import sys, asyncio, secrets
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from backend.app.config import settings


async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    origin = settings.public_base_url or "https://awaazsetu-hkp-2026.azurewebsites.net"
    async with httpx.AsyncClient(timeout=30) as client:
        if mode == "telegram":
            if not settings.telegram_bot_token or not settings.telegram_webhook_secret:
                raise SystemExit(
                    "Configure TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET privately first."
                )
            r = await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook",
                json={
                    "url": origin + "/api/webhooks/telegram",
                    "secret_token": settings.telegram_webhook_secret,
                    "allowed_updates": ["message"],
                },
            )
            if r.status_code != 200 or not r.json().get("ok"):
                raise SystemExit(
                    "Telegram registration failed. Check private credentials."
                )
            print("Telegram webhook registered.")
        elif mode == "sms":
            if not all(
                [
                    settings.sms_gateway_url,
                    settings.sms_gateway_user,
                    settings.sms_gateway_password,
                    settings.sms_webhook_secret,
                ]
            ):
                raise SystemExit(
                    "Configure SMS gateway credentials/signing key privately first."
                )
            for event in ["sms:received", "sms:sent", "sms:delivered", "sms:failed"]:
                r = await client.post(
                    settings.sms_gateway_url.rstrip("/") + "/webhooks",
                    auth=(settings.sms_gateway_user, settings.sms_gateway_password),
                    json={
                        "id": "awaazsetu-" + event.replace(":", "-"),
                        "event": event,
                        "url": origin + "/api/webhooks/sms",
                    },
                )
                if r.status_code not in {200, 201, 409}:
                    raise SystemExit(
                        "SMS webhook registration failed. Check private gateway settings."
                    )
            print(
                "SMS webhooks registered. Confirm the server signing key matches the phone app."
            )
        else:
            raise SystemExit(
                "Usage: .venv/bin/python scripts/setup_integrations.py sms|telegram"
            )


asyncio.run(main())
