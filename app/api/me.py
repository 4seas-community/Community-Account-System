from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import audit as audit_mod
from ..db import get_db
from ..deps import current_user
from ..errors import Conflict
from ..models import User
from ..schemas import MeUpdate, TelegramBindIn, UserOut
from ..services import telegram as tg
from ..services.points_service import get_balance
from ..services.webhook_service import emit

router = APIRouter(prefix="/v1/me", tags=["me"])


def _out(user: User, balance: int) -> dict:
    data = UserOut.model_validate(user).model_dump()
    data["points"] = {"balance": balance, "updated_at": user.updated_at.isoformat()}
    return data


@router.get("")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _out(user, get_balance(db, user.id))


@router.patch("")
def update_me(body: MeUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.avatar_url is not None:
        user.avatar_url = body.avatar_url
    if body.timezone is not None:
        user.timezone = body.timezone
    audit_mod.audit(db, "user", user.id, "me.update", body.model_dump(exclude_none=True))
    db.commit()
    db.refresh(user)
    emit(db, "user.updated", {"user_id": user.id})
    db.commit()
    return _out(user, get_balance(db, user.id))


@router.post("/telegram")
def bind_telegram(body: TelegramBindIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    info = tg.verify_init_data(body.init_data)
    clash = db.query(User).filter(User.telegram_id == info["telegram_id"], User.id != user.id).one_or_none()
    if clash:
        raise Conflict("telegram account already bound to another user")
    user.telegram_id = info["telegram_id"]
    user.telegram_username = info["username"]
    audit_mod.audit(db, "user", user.id, "me.telegram.bind", {"telegram_id": info["telegram_id"]})
    db.commit()
    db.refresh(user)
    emit(db, "telegram.bound", {"user_id": user.id, "telegram_id": info["telegram_id"]})
    db.commit()
    return {"bound": True, "telegram_id": info["telegram_id"], "username": info["username"]}


@router.delete("/telegram", status_code=204)
def unbind_telegram(user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.telegram_id = None
    user.telegram_username = None
    audit_mod.audit(db, "user", user.id, "me.telegram.unbind", {})
    db.commit()
