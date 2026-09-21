import json
from typing import Any

from sqlalchemy.orm import Session

from .models import AuditLog


def audit(db: Session, actor_type: str, actor_id: str | None, action: str, detail: Any = None) -> None:
    entry = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        detail=json.dumps(detail, ensure_ascii=False) if detail is not None else None,
    )
    db.add(entry)
