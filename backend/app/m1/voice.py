"""Bounded speech intake. Normalize locally; never pretend a failed ASR produced text."""

import asyncio
import io
import shutil
import tempfile
import wave
from pathlib import Path
import httpx
from fastapi import HTTPException
from ..config import settings

ALLOWED = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg", ".oga"}


async def normalize_audio(data: bytes, filename: str):
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(
            422, "Unsupported audio format. Use MP3, WAV, M4A, OGG or WebM."
        )
    if not data:
        raise HTTPException(422, "Audio file is empty")
    if len(data) > settings.voice_max_bytes:
        raise HTTPException(413, "Audio must be under 10 MB")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        try:
            import imageio_ffmpeg

            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            raise HTTPException(503, "Audio conversion unavailable; please send text.")
    with tempfile.TemporaryDirectory() as temp:
        source = Path(temp) / ("audio" + suffix)
        dest = Path(temp) / "audio.wav"
        source.write_bytes(data)
        proc = await asyncio.create_subprocess_exec(
            ffmpeg,
            "-nostdin",
            "-v",
            "error",
            "-protocol_whitelist",
            "file,pipe",
            "-i",
            str(source),
            "-t",
            "121",
            "-vn",
            "-sn",
            "-dn",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(dest),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            await asyncio.wait_for(proc.wait(), 20)
        except TimeoutError:
            proc.kill()
            await proc.wait()
            raise HTTPException(422, "Audio conversion timed out")
        if proc.returncode or not dest.exists():
            raise HTTPException(422, "Audio could not be decoded")
        normalized = dest.read_bytes()
        try:
            with wave.open(io.BytesIO(normalized)) as audio:
                duration = audio.getnframes() / audio.getframerate()
        except (wave.Error, ZeroDivisionError):
            raise HTTPException(422, "Audio could not be decoded")
        if duration > 120:
            raise HTTPException(
                422,
                "Voice messages must be 2 minutes or shorter. Please record a shorter message.",
            )
        if duration <= 0:
            raise HTTPException(422, "Audio file is empty")
        return normalized


async def transcribe(data: bytes, filename: str, language: str | None = None):
    if not settings.openai_api_key or not settings.ai_enabled:
        raise HTTPException(
            503, "Voice transcription is unavailable. Please send a text report."
        )
    data = await normalize_audio(data, filename)
    payload = {
        "model": settings.openai_transcription_model,
        "response_format": "json",
        "prompt": "Flood report in Pune. Marathi, Hindi or English. Places: Ekta Nagar, Sinhagad Road, Warje, Dattawadi, Mutha river.",
    }
    if language:
        payload["language"] = language
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                data=payload,
                files={"file": ("audio.wav", data, "audio/wav")},
            )
            response.raise_for_status()
            text = response.json().get("text", "").strip()
        if not text:
            raise HTTPException(
                422, "No speech detected. Please try again or send text."
            )
        if len(text) > 4000:
            raise HTTPException(
                422, "Transcript is too long. Please record a shorter message."
            )
        return text
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            503, "Speech service is unavailable. Please retry or send a text report."
        )
