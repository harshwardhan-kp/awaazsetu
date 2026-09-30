from datetime import datetime, timezone, timedelta
from sqlalchemy import select, delete
from .db import Report, Incident, Outbox, Contact, History, IntakeKey, Usage
from .config import settings


def purge(db):
    """Retain report contents for configured days; active opt-in contacts remain until STOP."""
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=settings.retention_days)
    ).isoformat()
    old = list(db.scalars(select(Report.id).where(Report.created_at < cutoff)))
    if old:
        db.execute(delete(Outbox).where(Outbox.report_id.in_(old)))
        db.execute(delete(Report).where(Report.id.in_(old)))
    db.execute(delete(Outbox).where(Outbox.created_at < cutoff))
    db.execute(delete(History).where(History.created_at < cutoff))
    db.execute(delete(IntakeKey).where(IntakeKey.created_at < cutoff))
    db.execute(delete(Usage).where(Usage.id < cutoff[:10]))
    empty = list(
        db.scalars(
            select(Incident.id).where(~Incident.id.in_(select(Report.incident_id)))
        )
    )
    if empty:
        db.execute(delete(History).where(History.incident_id.in_(empty)))
        db.execute(delete(Incident).where(Incident.id.in_(empty)))
    stale = list(
        db.scalars(
            select(Contact.id).where(
                Contact.opted_in == False,
                Contact.created_at < cutoff,
                ~Contact.id.in_(
                    select(Report.contact_id).where(Report.contact_id.is_not(None))
                ),
                ~Contact.id.in_(
                    select(Outbox.contact_id).where(Outbox.contact_id.is_not(None))
                ),
            )
        )
    )
    if stale:
        db.execute(delete(Contact).where(Contact.id.in_(stale)))
    db.commit()
    return {
        "removed_reports": len(old),
        "removed_incidents": len(empty),
        "removed_contacts": len(stale),
        "retention_days": settings.retention_days,
    }
