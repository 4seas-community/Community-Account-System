from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_service
from ..schemas import LedgerEntryOut, PointsAdjustIn
from ..services import points_service
from ..services.auth_service import get_user

router = APIRouter(tags=["points"])


@router.get("/v1/users/{user_id}/points")
def points_balance(
    user_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_service({"points:read"})),
):
    get_user(db, user_id)
    return {"user_id": user_id, "balance": points_service.get_balance(db, user_id)}


@router.post("/v1/users/{user_id}/points/adjust", status_code=201)
def points_adjust(
    user_id: str,
    body: PointsAdjustIn,
    db: Session = Depends(get_db),
    actor: str = Depends(require_service({"points:write"})),
):
    entry = points_service.adjust(db, user_id, body.delta, body.reason, body.ref_type, body.ref_id, actor)
    return {
        "id": entry.id,
        "user_id": entry.user_id,
        "delta": entry.delta,
        "reason": entry.reason,
        "balance": points_service.get_balance(db, user_id),
    }


@router.get("/v1/points/ledger")
def points_ledger(
    user_id: str | None = Query(default=None),
    since: datetime | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    _: str = Depends(require_service({"points:read"})),
):
    rows, next_cursor = points_service.ledger(db, user_id, since, cursor, limit)
    return {"entries": [LedgerEntryOut.model_validate(r) for r in rows], "next_cursor": next_cursor}
