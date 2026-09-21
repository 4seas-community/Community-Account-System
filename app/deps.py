import json

import jwt
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from .db import get_db
from .errors import Forbidden, Unauthorized
from .models import ServiceKey, User
from .security import decode_access_token, hash_secret
from .services.auth_service import get_user


def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise Unauthorized("missing bearer token")
    try:
        user_id = decode_access_token(authorization.removeprefix("Bearer "))
    except jwt.InvalidTokenError:
        raise Unauthorized("invalid token")
    return get_user(db, user_id)


def require_service(scopes: set[str]):
    def checker(
        x_service_key: str = Header(default=""),
        db: Session = Depends(get_db),
    ) -> str:
        if not x_service_key:
            raise Unauthorized("missing service key")
        key = (
            db.query(ServiceKey)
            .filter(ServiceKey.key_hash == hash_secret(x_service_key), ServiceKey.revoked_at.is_(None))
            .one_or_none()
        )
        if not key:
            raise Unauthorized("invalid service key")
        if not scopes.issubset(set(json.loads(key.scopes))):
            raise Forbidden("insufficient scope")
        return key.id

    return checker


def require_admin(x_admin_key: str = Header(default="")) -> None:
    from .config import get_settings

    if not x_admin_key or x_admin_key != get_settings().admin_key:
        raise Forbidden("admin key required")
