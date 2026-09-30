#!/usr/bin/env python3
"""Initialize private local settings without overwriting existing credentials."""

from pathlib import Path
import secrets, os
from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / ".env"
if path.exists():
    print("Existing .env preserved.")
else:
    values = {
        "ADMIN_PASSWORD": secrets.token_urlsafe(24),
        "JWT_SECRET": secrets.token_urlsafe(48),
        "CONTACT_HASH_SECRET": secrets.token_urlsafe(48),
        "CONTACT_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "DATABASE_URL": "sqlite:///./work/awaazsetu.db",
        "DEMO_MODE": "true",
        "DELIVERY_ENABLED": "false",
        "AI_ENABLED": "true",
        "DAILY_AI_LIMIT": "200",
        "OPENAI_API_KEY": "",
        "OPENAI_MODEL": "gpt-4o-mini",
        "OPENAI_TRANSCRIPTION_MODEL": "gpt-4o-mini-transcribe",
    }
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(f"{k}={v}" for k, v in values.items()) + "\n")
    print("Created private .env (mode 600). Coordinator password is stored there.")
