import io, wave, asyncio
import pytest, httpx
from sqlalchemy import select, func
from fastapi import HTTPException
from backend.app.config import settings
from backend.app.db import Report, SessionLocal
from backend.app.m1.voice import normalize_audio
from test_api import client


def wav(seconds=1):
    b = io.BytesIO()
    with wave.open(b, "wb") as a:
        a.setnchannels(1)
        a.setsampwidth(2)
        a.setframerate(16000)
        a.writeframes(b"\0" * (32000 * seconds))
    return b.getvalue()


def test_voice_preview_requires_consent_and_does_not_create_ticket(client, monkeypatch):
    monkeypatch.setattr(settings, "ai_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    async def fake_post(self, url, **kwargs):
        assert url == "https://api.openai.com/v1/audio/transcriptions"
        return httpx.Response(
            200,
            json={"text": "Water on road at Warje"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    assert (
        client.post(
            "/api/transcriptions",
            files={"audio": ("clip.wav", wav())},
            data={"consent": "false"},
        ).status_code
        == 422
    )
    response = client.post(
        "/api/transcriptions",
        files={"audio": ("clip.wav", wav())},
        data={"consent": "true", "language": "mr"},
    )
    assert (
        response.status_code == 200
        and response.json()["text"] == "Water on road at Warje"
    )
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Report)) == 0
    sent = client.post(
        "/api/reports",
        json={
            "text": "Reviewed: water on road at Warje",
            "channel": "voice",
            "language": "en",
            "consent": True,
        },
    )
    assert sent.status_code == 200 and sent.json()["report"]["channel"] == "voice"


def test_audio_duration_limit_and_invalid_decoder():
    async def run():
        with pytest.raises(HTTPException) as long:
            await normalize_audio(wav(121), "clip.wav")
        assert long.value.status_code == 422 and "2 minutes" in long.value.detail
        with pytest.raises(HTTPException) as invalid:
            await normalize_audio(b"not audio", "clip.wav")
        assert invalid.value.status_code == 422
        with pytest.raises(HTTPException):
            await normalize_audio(wav(), "clip.exe")

    asyncio.run(run())
