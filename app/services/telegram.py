import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from ..config import get_settings
from ..errors import Unauthorized

# initData older than this is rejected (replay protection at the app layer).
MAX_AUTH_AGE_SECONDS = 24 * 3600


def verify_init_data(init_data: str, bot_token: str | None = None, max_age_seconds: int = MAX_AUTH_AGE_SECONDS) -> dict:
    """Verify Telegram WebApp initData per the official algorithm.

    secret_key = HMAC_SHA256(key=b"WebAppData", msg=bot_token)
    check_hash = HMAC_SHA256(key=secret_key, msg=data_check_string).hexdigest()
    where data_check_string is the sorted key=value pairs excluding 'hash'.

    Dev fallback: when no bot token is configured, verification runs against the
    empty token so local runs work; production deployments must set a real token.
    """
    settings = get_settings()
    token = bot_token if bot_token is not None else settings.telegram_bot_token

    pairs = dict(parse_qsl(init_data, strict_parsing=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise Unauthorized("missing hash in init_data")

    data_check_string = chr(10).join(k + "=" + pairs[k] for k in sorted(pairs))
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise Unauthorized("init_data signature mismatch")

    auth_date = pairs.get("auth_date")
    if auth_date is not None:
        age = time.time() - int(auth_date)
        if age > max_age_seconds:
            raise Unauthorized("init_data is stale")

    user = json.loads(pairs.get("user", "{}"))
    if not user.get("id"):
        raise Unauthorized("init_data has no user")
    return {"telegram_id": str(user["id"]), "username": user.get("username")}
