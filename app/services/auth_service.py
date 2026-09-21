from datetime import timedelta

from sqlalchemy.orm import Session

from .. import audit as audit_mod
from ..config import get_settings
from ..email_backend import send_email
from ..errors import Conflict, Gone, NotFound, Unauthorized
from ..models import Token, User
from ..security import hash_secret, new_id, new_opaque_token, utcnow
from .webhook_service import emit

settings = get_settings()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.lower()).one_or_none()


def get_user(db: Session, user_id: str) -> User:
    user = db.get(User, user_id)
    if not user:
        raise NotFound("user not found")
    return user


def _issue_token(db: Session, user: User, purpose: str, ttl) -> str:
    raw = new_opaque_token()
    db.add(
        Token(
            id=new_id(),
            user_id=user.id,
            purpose=purpose,
            token_hash=hash_secret(raw),
            expires_at=utcnow() + ttl,
        )
    )
    return raw


def register(db: Session, email: str, display_name: str | None, timezone: str | None) -> User:
    email = email.lower()
    existing = get_user_by_email(db, email)
    if existing and existing.verified:
        raise Conflict("email already registered")
    user = existing or User(id=new_id(), email=email)
    user.display_name = display_name or user.display_name
    user.timezone = timezone or user.timezone
    db.add(user)
    db.flush()
    token = _issue_token(db, user, "verify_email", timedelta(hours=settings.verify_token_ttl_hours))
    send_email(email, "Verify your 4Seas account", "Verify: /v1/auth/verify-email token=" + token)
    audit_mod.audit(db, "system", None, "auth.register", {"user_id": user.id})
    db.commit()
    db.refresh(user)
    return user


def _consume_token(db: Session, raw: str, purpose: str) -> User:
    token = db.query(Token).filter(Token.token_hash == hash_secret(raw), Token.purpose == purpose).one_or_none()
    if not token:
        raise Unauthorized("invalid token")
    if token.consumed_at is not None:
        raise Unauthorized("token already used")
    if token.expires_at < utcnow():
        raise Gone("token expired")
    token.consumed_at = utcnow()
    user = db.get(User, token.user_id)
    db.flush()
    return user


def verify_email(db: Session, token: str) -> User:
    user = _consume_token(db, token, "verify_email")
    user.verified = True
    audit_mod.audit(db, "system", None, "auth.verify_email", {"user_id": user.id})
    db.commit()
    db.refresh(user)
    emit(db, "user.verified", {"user_id": user.id, "email": user.email})
    db.commit()
    return user


def request_login(db: Session, email: str) -> None:
    """Always succeeds from the caller's perspective (no account enumeration)."""
    email = email.lower()
    user = get_user_by_email(db, email)
    if user and user.verified:
        token = _issue_token(db, user, "login", timedelta(minutes=settings.login_token_ttl_minutes))
        send_email(email, "Your 4Seas login link", "Login: /v1/auth/login/verify token=" + token)
    db.commit()


def verify_login(db: Session, token: str) -> User:
    user = _consume_token(db, token, "login")
    if not user.verified:
        raise Unauthorized("email not verified")
    audit_mod.audit(db, "system", None, "auth.login", {"user_id": user.id})
    db.commit()
    db.refresh(user)
    return user
