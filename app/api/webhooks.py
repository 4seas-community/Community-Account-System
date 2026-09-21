from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import audit as audit_mod
from ..db import get_db
from ..deps import require_admin
from ..models import WebhookSubscription
from ..schemas import WebhookSubscriptionIn
from ..security import new_id
from ..services.webhook_service import EVENT_TYPES

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])


@router.post("/subscriptions", status_code=201)
def create_subscription(
    body: WebhookSubscriptionIn,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    unknown = set(body.events) - EVENT_TYPES
    if unknown:
        from ..errors import Unprocessable

        raise Unprocessable("unknown event types: " + ", ".join(sorted(unknown)))
    sub = WebhookSubscription(id=new_id(), url=body.url, secret=body.secret, events=__import__("json").dumps(body.events))
    db.add(sub)
    audit_mod.audit(db, "system", None, "webhook.subscription.create", {"url": body.url})
    db.commit()
    return {"subscription_id": sub.id, "events": body.events}
