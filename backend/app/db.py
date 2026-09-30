from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path
from sqlalchemy import (
    create_engine,
    event,
    String,
    Text,
    Float,
    Integer,
    Boolean,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import settings


def now():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Contact(Base):
    __tablename__ = "contacts"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    encrypted_address: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(20))
    language: Mapped[str] = mapped_column(String(3), default="en")
    ward: Mapped[str | None] = mapped_column(String(100), nullable=True)
    opted_in: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(String(40), default=now)


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    ticket_id: Mapped[str] = mapped_column(String(24), unique=True)
    summary: Mapped[str] = mapped_column(Text)
    incident_type: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    severity_score: Mapped[int] = mapped_column(Integer)
    severity_band: Mapped[str] = mapped_column(String(20), index=True)
    severity_reasons: Mapped[list] = mapped_column(JSON)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    location_method: Mapped[str] = mapped_column(String(100))
    location_confidence: Mapped[float] = mapped_column(Float, default=0)
    ward: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    needs_clarification: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(String(40), default=now, index=True)
    updated_at: Mapped[str] = mapped_column(String(40), default=now)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    ticket_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    tracking_hash: Mapped[str] = mapped_column(String(64))
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    contact_id: Mapped[str | None] = mapped_column(
        ForeignKey("contacts.id"), nullable=True
    )
    text: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(3))
    channel: Mapped[str] = mapped_column(String(20))
    fields: Mapped[dict] = mapped_column(JSON)
    location: Mapped[dict] = mapped_column(JSON)
    consent: Mapped[bool] = mapped_column(Boolean, default=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(200), unique=True, nullable=True
    )
    created_at: Mapped[str] = mapped_column(String(40), default=now)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)


class History(Base):
    __tablename__ = "history"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    notes: Mapped[str] = mapped_column(Text, default="")
    actor: Mapped[str] = mapped_column(String(30), default="coordinator")
    created_at: Mapped[str] = mapped_column(String(40), default=now)


class Outbox(Base):
    __tablename__ = "outbox"
    kind: Mapped[str] = mapped_column(
        String(30), default="transactional", server_default="transactional"
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    report_id: Mapped[str | None] = mapped_column(
        ForeignKey("reports.id"), nullable=True
    )
    contact_id: Mapped[str | None] = mapped_column(
        ForeignKey("contacts.id"), nullable=True
    )
    ticket_id: Mapped[str | None] = mapped_column(String(24), nullable=True)
    channel: Mapped[str] = mapped_column(String(20))
    language: Mapped[str] = mapped_column(String(3))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now)


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    ward: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40), default=now)


class Usage(Base):
    __tablename__ = "usage"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)


class IntakeKey(Base):
    __tablename__ = "intake_keys"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now)


if settings.database_url.startswith("sqlite:///"):
    path = settings.database_url.removeprefix("sqlite:///")
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False, "timeout": 30}
    if settings.database_url.startswith("sqlite")
    else {},
    pool_pre_ping=True,
)
if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def pragmas(conn, record):
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        yield db


def ensure_schema():
    """Idempotent additive migration for the initial drill release."""
    from sqlalchemy import inspect, text

    Base.metadata.create_all(engine)
    columns = {c["name"] for c in inspect(engine).get_columns("outbox")}
    if "kind" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE outbox ADD COLUMN kind VARCHAR(30) NOT NULL DEFAULT 'transactional'"
                )
            )
