import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import Account, AuditEvent, BrowserSession, RateBucket, Workspace
from app.db.session import get_db

password_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
DUMMY_HASH = password_hasher.hash(secrets.token_urlsafe(32))


def utcnow() -> datetime:
    return datetime.now(UTC)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def cipher(settings: Settings) -> Fernet:
    if not settings.app_secret:
        raise HTTPException(503, "service_not_configured")
    raw = hashlib.sha256(("encryption:" + settings.app_secret.get_secret_value()).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(raw))


def encrypt(settings: Settings, value: dict) -> str:
    return cipher(settings).encrypt(json.dumps(value, ensure_ascii=False).encode()).decode()


def decrypt(settings: Settings, value: str) -> dict:
    return json.loads(cipher(settings).decrypt(value.encode()))


def verify_password(hashed: str, value: str) -> bool:
    try:
        return password_hasher.verify(hashed, value)
    except (VerificationError, InvalidHashError):
        return False


def rate_limit(
    request: Request,
    db: Session,
    action: str,
    limit: int = 10,
    identity: str | None = None,
    seconds: int = 900,
) -> None:
    settings = request.app.state.settings
    secret = settings.app_secret.get_secret_value()
    identity = identity or (request.client.host if request.client else "unknown")
    bucket = int(utcnow().timestamp()) // seconds
    key = hmac.new(
        secret.encode(), f"{action}:{identity}:{bucket}".encode(), hashlib.sha256
    ).hexdigest()
    statement = (
        insert(RateBucket)
        .values(
            key=key,
            count=1,
            expires_at=utcnow() + timedelta(seconds=seconds * 2),
        )
        .on_conflict_do_update(
            index_elements=[RateBucket.key], set_={"count": RateBucket.count + 1}
        )
    )
    count = db.scalar(statement.returning(RateBucket.count))
    db.commit()
    if count > limit:
        raise HTTPException(429, "rate_limited", headers={"Retry-After": str(seconds)})


def browser_session(request: Request, db: Session = Depends(get_db)) -> BrowserSession | None:
    value = request.cookies.get(request.app.state.settings.cookie_name)
    if not value or len(value) > 128:
        return None
    session = db.get(BrowserSession, digest(value))
    now = utcnow()
    if not session or session.expires_at <= now or session.last_seen < now - timedelta(hours=12):
        return None
    if session.last_seen < now - timedelta(minutes=5):
        session.last_seen = now
        db.commit()
    return session


def csrf(
    request: Request, session: BrowserSession | None = Depends(browser_session)
) -> BrowserSession:
    if request.headers.get("origin") not in request.app.state.settings.origins:
        raise HTTPException(403, "invalid_origin")
    token = request.headers.get("x-csrf-token", "")
    if not session or not hmac.compare_digest(token, session.csrf_token):
        raise HTTPException(403, "invalid_csrf")
    return session


def account(
    request: Request,
    db: Session = Depends(get_db),
    session: BrowserSession | None = Depends(browser_session),
) -> Account:
    if not session or session.account_id is None:
        raise HTTPException(401, "authentication_required")
    result = db.get(Account, session.account_id)
    if not result or (
        request.app.state.settings.require_email_verification and not result.verified
    ):
        raise HTTPException(401, "authentication_required")
    return result


def new_session(
    request: Request, response: Response, db: Session, owner: Account | None
) -> BrowserSession:
    old = request.cookies.get(request.app.state.settings.cookie_name)
    if old:
        db.execute(delete(BrowserSession).where(BrowserSession.token_hash == digest(old)))
    token = secrets.token_urlsafe(32)
    lifetime = 7 * 24 * 3600 if owner else 1800
    now = utcnow()
    session = BrowserSession(
        token_hash=digest(token),
        account_id=owner.id if owner else None,
        csrf_token=secrets.token_urlsafe(32),
        expires_at=now + timedelta(seconds=lifetime),
        last_seen=now,
    )
    db.add(session)
    db.commit()
    response.set_cookie(
        request.app.state.settings.cookie_name,
        token,
        max_age=lifetime,
        secure=request.app.state.settings.app_env == "production",
        httponly=True,
        samesite="lax",
        path="/",
    )
    return session


def session_payload(db: Session, session: BrowserSession) -> dict:
    owner = db.get(Account, session.account_id) if session.account_id else None
    workspace = db.get(Workspace, owner.workspace_id) if owner else None
    return {
        "csrf_token": session.csrf_token,
        "account": {
            "email": owner.email,
            "workspace_name": workspace.name,
            "workspace_id": str(workspace.id),
            "verified": owner.verified,
        }
        if owner
        else None,
    }


def lock_workspace(db: Session, workspace_id) -> Workspace:
    return db.scalar(select(Workspace).where(Workspace.id == workspace_id).with_for_update())


def audit(db: Session, workspace_id, action: str, rows: int | None = None) -> None:
    db.add(AuditEvent(workspace_id=workspace_id, action=action, row_count=rows))
