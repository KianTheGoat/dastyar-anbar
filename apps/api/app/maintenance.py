from datetime import timedelta

from sqlalchemy import delete

from app.db.models import (
    ActionToken,
    AuditEvent,
    BrowserSession,
    DeletionMarker,
    ImportBatch,
    RateBucket,
)
from app.security import utcnow


def cleanup(factory) -> None:
    now = utcnow()
    with factory() as db:
        for model in [ActionToken, BrowserSession, ImportBatch, RateBucket, DeletionMarker]:
            db.execute(delete(model).where(model.expires_at <= now))
        db.execute(delete(AuditEvent).where(AuditEvent.created_at < now - timedelta(days=90)))
        db.commit()
