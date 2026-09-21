import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from .config import get_settings

settings = get_settings()


def new_id() -> str:
    return uuid4().hex


def hash_secret(value: str) -> str:
    """SHA-256 for high-entropy secrets (tokens, service keys). Not for passwords."""
    return hashlib.sha256(value.encode()).hexdigest()


def new_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def sign_hmac(message: str) -> str:
    return hmac.new(settings.checkin_secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def verify_hmac(message: str, signature: str) -> bool:
    return hmac.compare_digest(sign_hmac(message), signature)


def create_access_token(user_id: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
        "jti": new_id(),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    """Returns user_id or raises jwt.InvalidTokenError."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return payload["sub"]


def utcnow() -> datetime:
    # Naive UTC: SQLite columns are timezone-naive, so all timestamps are stored
    # and compared as naive UTC for consistency across backends.
    return datetime.now(UTC).replace(tzinfo=None)
