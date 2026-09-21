from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_service
from ..schemas import UserOut
from ..services.auth_service import get_user
from ..services.points_service import get_balance

router = APIRouter(prefix="/v1/users", tags=["users"])


@router.get("/{user_id}")
def get_user_detail(
    user_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_service({"users:read"})),
):
    user = get_user(db, user_id)
    data = UserOut.model_validate(user).model_dump()
    data["points"] = {"balance": get_balance(db, user.id)}
    return data
