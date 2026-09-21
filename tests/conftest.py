import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("CHECKIN_SECRET", "test-checkin-secret")
os.environ.setdefault("ADMIN_KEY", "test-admin-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-bot-token")
os.environ.setdefault("EMAIL_BACKEND", "console")

from app.db import Base, get_db
from app.main import app

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


class MailCapture:
    """Stands in for the console email backend: records the last message per address."""

    def __init__(self):
        self.messages = []

    def send(self, to, subject, body):
        self.messages.append({"to": to, "subject": subject, "body": body})

    def last_token(self, to):
        for msg in reversed(self.messages):
            if msg["to"] == to:
                for part in msg["body"].split():
                    if part.startswith("token="):
                        return part[len("token="):]
        raise AssertionError("no token email for " + to)


@pytest.fixture()
def mail(monkeypatch):
    from app.services import auth_service

    capture = MailCapture()
    monkeypatch.setattr(auth_service, "send_email", capture.send)
    return capture


def make_init_data(bot_token: str, user: dict, auth_date: int | None = None, tamper: bool = False) -> str:
    fields = {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps(user, separators=(",", ":")),
    }
    data_check_string = chr(10).join(k + "=" + fields[k] for k in sorted(fields))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if tamper:
        h = "0" * 64
    fields["hash"] = h
    return urlencode(fields)
