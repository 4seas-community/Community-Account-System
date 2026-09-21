from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import audit as audit_mod
from ..errors import Unprocessable
from ..models import PointsEntry, User
from ..security import new_id
from .auth_service import get_user
from .webhook_service import emit


def get_balance(db: Session, user_id: str) -> int:
    total = (
        db.query(func.coalesce(func.sum(PointsEntry.delta), 0))
        .filter(PointsEntry.user_id == user_id)
        .scalar()
    )
    return int(total)


def adjust(db: Session, user_id: str, delta: int, reason: str, ref_type: str | None, ref_id: str | None, actor: str) -> PointsEntry:
    user: User = get_user(db, user_id)
    if delta == 0:
        raise Unprocessable("delta must be non-zero")
    if delta < 0 and get_balance(db, user_id) + delta < 0:
        raise Unprocessable("insufficient points balance")
    entry = PointsEntry(
        id=new_id(),
        user_id=user.id,
        delta=delta,
        reason=reason,
        ref_type=ref_type,
        ref_id=ref_id,
    )
    db.add(entry)
    db.flush()
    audit_mod.audit(db, "service", actor, "points.adjust", {"user_id": user_id, "delta": delta, "reason": reason})
    db.commit()
    db.refresh(entry)
    emit(db, "points.changed", {"user_id": user_id, "delta": delta, "reason": reason, "balance": get_balance(db, user_id)})
    db.commit()
    return entry


def ledger(db: Session, user_id: str | None = None, since=None, cursor: str | None = None, limit: int = 100):
    q = db.query(PointsEntry)
    if user_id:
        q = q.filter(PointsEntry.user_id == user_id)
    if since is not None:
        q = q.filter(PointsEntry.created_at > since)
    if cursor:
        q = q.filter(PointsEntry.seq > int(cursor))
    rows = q.order_by(PointsEntry.seq).limit(min(limit, 500)).all()
    next_cursor = str(rows[-1].seq) if len(rows) == min(limit, 500) else None
    return rows, next_cursor
