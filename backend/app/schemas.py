from typing import Literal
from pydantic import BaseModel, Field, model_validator

Language = Literal["en", "mr", "hi"]


class ReportIn(BaseModel):
    text: str = Field(min_length=3, max_length=4000)
    language: Language | None = None
    channel: Literal["web", "sms", "telegram", "voice"] = "web"
    contact: str | None = Field(default=None, max_length=100)
    consent: bool = False
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    idempotency_key: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def validate_report(self):
        self.text = self.text.strip()
        if len(self.text) < 3:
            raise ValueError("Please describe the incident")
        if not self.consent:
            raise ValueError("Consent is required to process this report")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Provide both coordinates")
        return self


class LoginIn(BaseModel):
    password: str = Field(max_length=200)


class UpdateIn(BaseModel):
    status: Literal["new", "verified", "responding", "resolved", "dismissed"] | None = (
        None
    )
    notes: str = Field(default="", max_length=2000)


class MergeIn(BaseModel):
    source_id: str
    reason: str = Field(default="", max_length=2000)


class ClarifyIn(BaseModel):
    token: str = Field(max_length=100)
    text: str = Field(min_length=3, max_length=1000)


class AlertIn(BaseModel):
    ward: str = Field(min_length=1, max_length=100)
    language: Language | None = None
    message: str = Field(min_length=3, max_length=1000)


class SubscribeIn(BaseModel):
    contact: str = Field(min_length=3, max_length=100)
    channel: Literal["sms", "telegram"] = "sms"
    language: Language = "en"
    ward: str = Field(min_length=1, max_length=100)
    consent: bool = False
    action: Literal["JOIN", "STOP"] = "JOIN"
