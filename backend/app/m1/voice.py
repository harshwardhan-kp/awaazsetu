import httpx
from fastapi import HTTPException
from ..config import settings

ALLOWED = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg", ".oga"}


async def transcribe(data: bytes, filename: str, language: str | None = None):
    if not settings.openai_api_key or not settings.ai_enabled:
        raise HTTPException(
            503, "Voice transcription is unavailable. Please send a text report."
        )
    if not data:
        raise HTTPException(422, "Audio file is empty")
    # Telegram sends OGG/Opus; convert it to an API-supported WAV when ffmpeg is available.
    from pathlib import Path

    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(
            422, "Unsupported audio format. Use MP3, WAV, M4A, OGG or WebM."
        )
    if suffix in {".ogg", ".oga"}:
        import asyncio, tempfile, shutil

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            try:
                import imageio_ffmpeg

                ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            except Exception:
                raise HTTPException(
                    503, "OGG conversion unavailable; upload WAV, MP3 or WebM."
                )
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "audio.ogg"
            dest = Path(temp) / "audio.wav"
            source.write_bytes(data)
            proc = await asyncio.create_subprocess_exec(
                ffmpeg,
                "-nostdin",
                "-v",
                "error",
                "-i",
                str(source),
                "-t",
                "120",
                "-ar",
                "16000",
                "-ac",
                "1",
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
            if proc.returncode:
                raise HTTPException(422, "Audio could not be decoded")
            data = dest.read_bytes()
            filename = "audio.wav"
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
                files={"file": (filename, data, "application/octet-stream")},
            )
            response.raise_for_status()
            result = response.json()
        text = result.get("text", "").strip()
        if not text:
            raise HTTPException(
                422, "No speech detected. Please try again or send text."
            )
        return text
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            503, "Speech service is unavailable. Please retry or send a text report."
        )
