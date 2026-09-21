import hashlib
import hmac
import json
import time

import httpx
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import WebhookDelivery, WebhookSubscription

EVENT_TYPES = {"user.verified", "user.updated", "points.changed", "telegram.bound"}


def sign_payload(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def emit(db: Session, event_type: str, payload: dict) -> None:
    """Deliver an event to all active subscriptions. Best-effort with retries;
    failures are recorded on the delivery row for operators to inspect."""
    settings = get_settings()
    subs = db.query(WebhookSubscription).filter(WebhookSubscription.active.is_(True)).all()
    body = json.dumps({"type": event_type, "payload": payload}, ensure_ascii=False).encode()
    for sub in subs:
        if event_type not in json.loads(sub.events):
            continue
        delivery = WebhookDelivery(
            subscription_id=sub.id,
            event_type=event_type,
            payload=body.decode(),
        )
        db.add(delivery)
        db.flush()
        signature = sign_payload(sub.secret, body)
        headers = {"Content-Type": "application/json", "X-CAS-Signature": signature}
        last_error = None
        for attempt in range(1, settings.webhook_max_attempts + 1):
            delivery.attempts = attempt
            try:
                resp = httpx.post(sub.url, content=body, headers=headers, timeout=settings.webhook_timeout_seconds)
                if resp.status_code < 300:
                    delivery.status = "delivered"
                    last_error = None
                    break
                last_error = "HTTP " + str(resp.status_code)
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
            if attempt < settings.webhook_max_attempts:
                time.sleep(min(2 ** (attempt - 1), 4))
        if last_error:
            delivery.status = "failed"
            delivery.last_error = last_error
