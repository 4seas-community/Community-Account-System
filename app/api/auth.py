from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import User
from ..schemas import (
    LoginRequestIn,
    LoginVerifyIn,
    RegisterIn,
    UserOut,
    VerifyEmailIn,
)
from ..security import create_access_token
from ..services import auth_service

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    user = auth_service.register(db, body.email, body.display_name, body.timezone)
    return {"user_id": user.id, "email": user.email, "status": "unverified"}


@router.post("/verify-email")
def verify_email(body: VerifyEmailIn, db: Session = Depends(get_db)):
    user = auth_service.verify_email(db, body.token)
    return {"user_id": user.id, "verified": True}


@router.post("/login/request", status_code=202)
def login_request(body: LoginRequestIn, db: Session = Depends(get_db)):
    auth_service.request_login(db, body.email)
    return {"status": "sent"}


@router.post("/login/verify")
def login_verify(body: LoginVerifyIn, db: Session = Depends(get_db)):
    user = auth_service.verify_login(db, body.token)
    return {"access_token": create_access_token(user.id), "user": UserOut.model_validate(user)}


@router.post("/logout", status_code=204)
def logout(_: User = Depends(current_user)):
    return None
