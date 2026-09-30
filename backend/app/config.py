from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    database_url: str = "sqlite:///./work/awaazsetu.db"
    admin_password: str = ""
    jwt_secret: str = ""
    contact_hash_secret: str = ""
    contact_encryption_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_transcription_model: str = "gpt-4o-mini-transcribe"
    ai_enabled: bool = True
    demo_mode: bool = True
    delivery_enabled: bool = False
    sms_gateway_url: str = ""
    sms_gateway_user: str = ""
    sms_gateway_password: str = ""
    sms_webhook_secret: str = ""
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    public_base_url: str = ""
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    voice_max_bytes: int = 10_000_000
    daily_ai_limit: int = 200
    retention_days: int = 90


settings = Settings()
# M2 provider reads environment; expose only in process, never in API responses.
import os

for name in ("openai_api_key", "openai_model"):
    if getattr(settings, name):
        os.environ.setdefault(name.upper(), getattr(settings, name))
