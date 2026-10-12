import logging
import secrets
import smtplib
import ssl
from datetime import timedelta
from email.message import EmailMessage

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, EmailStr, Field, StrictBool, StrictStr
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import POLICY_VERSION, Settings
from app.db.models import Account, ActionToken, BrowserSession, Workspace
from app.db.session import get_db
from app.security import (
    DUMMY_HASH,
    account,
    audit,
    browser_session,
    csrf,
    digest,
    new_session,
    password_hasher,
    rate_limit,
    session_payload,
    utcnow,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["identity"])


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: StrictStr = Field(min_length=1, max_length=128)


class Registration(Credentials):
    password: StrictStr = Field(min_length=12, max_length=128)
    workspace_name: StrictStr = Field(min_length=1, max_length=120)
    accepted_policy: StrictBool
    policy_version: StrictStr


class EmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr


class ResetPassword(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: StrictStr = Field(min_length=30, max_length=128)
    password: StrictStr = Field(min_length=12, max_length=128)


class TokenInput(ResetPassword):
    accepted_policy: StrictBool
    policy_version: StrictStr


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: StrictStr = Field(max_length=128)
    password: StrictStr = Field(min_length=12, max_length=128)


def send_token_email(settings: Settings, recipient: str, token: str, purpose: str) -> None:
    if not settings.smtp_host or not settings.smtp_from:
        return
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = recipient
    message["Subject"] = (
        "تأیید ایمیل دستیار انبار" if purpose == "verify" else "بازیابی رمز دستیار انبار"
    )
    message.set_content(
        "این پیوند تا ۳۰ دقیقه اعتبار دارد. اگر شما درخواست نکرده‌اید، آن را نادیده بگیرید.\n"
        f"{settings.public_origin}/#{purpose}={token}\n"
    )
    try:
        context = ssl.create_default_context()
        if settings.smtp_port == 465:
            server = smtplib.SMTP_SSL(
                settings.smtp_host, settings.smtp_port, timeout=10, context=context
            )
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
            server.starttls(context=context)
        with server:
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password.get_secret_value())
            server.send_message(message)
    except (OSError, smtplib.SMTPException):
        logging.getLogger("anbar").warning("mail_delivery_failed")


def issue_token(
    db: Session, owner: Account, purpose: str, tasks: BackgroundTasks, settings: Settings
) -> None:
    db.execute(
        delete(ActionToken).where(
            ActionToken.account_id == owner.id, ActionToken.purpose == purpose
        )
    )
    token = secrets.token_urlsafe(32)
    db.add(
        ActionToken(
            token_hash=digest(token),
            account_id=owner.id,
            purpose=purpose,
            expires_at=utcnow() + timedelta(minutes=30),
        )
    )
    db.commit()
    tasks.add_task(send_token_email, settings, owner.email, token, purpose)


@router.get("/session")
def session_status(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    existing: BrowserSession | None = Depends(browser_session),
):
    if existing is None:
        rate_limit(request, db, "bootstrap", 120)
        existing = new_session(request, response, db, None)
    return session_payload(db, existing)


@router.post("/register", dependencies=[Depends(csrf)])
def register(
    body: Registration,
    request: Request,
    response: Response,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    settings = request.app.state.settings
    rate_limit(request, db, "register", 10)
    email = str(body.email).casefold()
    rate_limit(request, db, "register-address", 3, identity=email)
    if body.accepted_policy is not True or body.policy_version != POLICY_VERSION:
        raise HTTPException(400, "policy_acceptance_required")
    if not body.workspace_name.strip():
        raise HTTPException(400, "workspace_name_required")
    hashed_password = password_hasher.hash(body.password)
    existing = db.scalar(select(Account).where(Account.email == email))
    if existing:
        if settings.require_email_verification and not existing.verified:
            issue_token(db, existing, "verify", tasks, settings)
        return {"verification_required": True, "message": "registration_received"}
    workspace = Workspace(name=body.workspace_name.strip())
    db.add(workspace)
    db.flush()
    owner = Account(
        workspace_id=workspace.id,
        email=email,
        password_hash=hashed_password,
        verified=False,
        policy_version=POLICY_VERSION,
    )
    db.add(owner)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"verification_required": True, "message": "registration_received"}
    audit(db, owner.workspace_id, "account_registered")
    db.commit()
    if settings.require_email_verification:
        issue_token(db, owner, "verify", tasks, settings)
        return {"verification_required": True, "message": "registration_received"}
    return session_payload(db, new_session(request, response, db, owner))


@router.post("/login", dependencies=[Depends(csrf)])
def login(body: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    rate_limit(request, db, "login", 10)
    email = str(body.email).casefold()
    rate_limit(request, db, "login-address", 10, identity=email)
    owner = db.scalar(select(Account).where(Account.email == email))
    valid = verify_password(owner.password_hash if owner else DUMMY_HASH, body.password)
    if (
        not owner
        or not valid
        or (request.app.state.settings.require_email_verification and not owner.verified)
    ):
        raise HTTPException(401, "invalid_credentials")
    if password_hasher.check_needs_rehash(owner.password_hash):
        owner.password_hash = password_hasher.hash(body.password)
    audit(db, owner.workspace_id, "login")
    db.commit()
    return session_payload(db, new_session(request, response, db, owner))


@router.post("/logout", dependencies=[Depends(csrf)])
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    existing: BrowserSession = Depends(browser_session),
):
    db.delete(existing)
    db.commit()
    response.delete_cookie(
        request.app.state.settings.cookie_name,
        path="/",
        secure=request.app.state.settings.app_env == "production",
        httponly=True,
        samesite="lax",
    )
    return {"ok": True}


@router.post("/password/request", dependencies=[Depends(csrf)])
def request_reset(
    body: EmailRequest, request: Request, tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    rate_limit(request, db, "password-request", 5)
    email = str(body.email).casefold()
    rate_limit(request, db, "password-request-address", 3, identity=email)
    owner = db.scalar(select(Account).where(Account.email == email))
    if owner and request.app.state.settings.smtp_host:
        issue_token(db, owner, "reset", tasks, request.app.state.settings)
    return {"message": "request_received"}


def consume_token(db: Session, token: str, purpose: str) -> Account:
    row = db.scalar(
        select(ActionToken)
        .where(
            ActionToken.token_hash == digest(token),
            ActionToken.purpose == purpose,
            ActionToken.expires_at > utcnow(),
        )
        .with_for_update()
    )
    if not row:
        raise HTTPException(400, "invalid_or_expired_link")
    owner = db.get(Account, row.account_id)
    db.delete(row)
    return owner


@router.post("/password/reset", dependencies=[Depends(csrf)])
def reset_password(
    body: ResetPassword, request: Request, response: Response, db: Session = Depends(get_db)
):
    rate_limit(request, db, "reset", 10)
    owner = consume_token(db, body.token, "reset")
    owner.password_hash = password_hasher.hash(body.password)
    db.execute(delete(BrowserSession).where(BrowserSession.account_id == owner.id))
    audit(db, owner.workspace_id, "password_reset")
    db.commit()
    return session_payload(db, new_session(request, response, db, None))


@router.post("/verify", dependencies=[Depends(csrf)])
def verify_email(
    body: TokenInput, request: Request, response: Response, db: Session = Depends(get_db)
):
    rate_limit(request, db, "verify", 10)
    owner = consume_token(db, body.token, "verify")
    owner.verified = True
    if not body.accepted_policy or body.policy_version != POLICY_VERSION:
        raise HTTPException(400, "policy_acceptance_required")
    owner.password_hash = password_hasher.hash(body.password)
    owner.policy_version = POLICY_VERSION
    db.execute(delete(BrowserSession).where(BrowserSession.account_id == owner.id))
    audit(db, owner.workspace_id, "email_verified")
    db.commit()
    return session_payload(db, new_session(request, response, db, owner))


@router.post("/password/change", dependencies=[Depends(csrf)])
def change_password(
    body: PasswordChange,
    request: Request,
    response: Response,
    owner: Account = Depends(account),
    db: Session = Depends(get_db),
):
    rate_limit(request, db, "password-change", 5)
    if not verify_password(owner.password_hash, body.current_password):
        raise HTTPException(401, "invalid_credentials")
    owner.password_hash = password_hasher.hash(body.password)
    db.execute(delete(BrowserSession).where(BrowserSession.account_id == owner.id))
    audit(db, owner.workspace_id, "password_changed")
    db.commit()
    return session_payload(db, new_session(request, response, db, owner))
