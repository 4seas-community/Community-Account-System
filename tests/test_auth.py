import time
import uuid

from tests.conftest import make_init_data


def unique_email(prefix="user"):
    return prefix + "-" + uuid.uuid4().hex[:8] + "@example.com"


def register_and_verify(client, mail, email=None):
    email = email or unique_email()
    r = client.post("/v1/auth/register", json={"email": email, "display_name": "Alice"})
    assert r.status_code == 201, r.text
    token = mail.last_token(email)
    r = client.post("/v1/auth/verify-email", json={"token": token})
    assert r.status_code == 200, r.text
    assert r.json()["verified"] is True
    return email


def login(client, mail, email):
    r = client.post("/v1/auth/login/request", json={"email": email})
    assert r.status_code == 202
    token = mail.last_token(email)
    r = client.post("/v1/auth/login/verify", json={"token": token})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_register_verify_login_flow(client, mail):
    email = unique_email()
    register_and_verify(client, mail, email)
    token = login(client, mail, email)
    r = client.get("/v1/me", headers={"Authorization": "Bearer " + token})
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == email
    assert body["verified"] is True
    assert body["points"]["balance"] == 0


def test_duplicate_register_rejected(client, mail):
    email = unique_email()
    register_and_verify(client, mail, email)
    r = client.post("/v1/auth/register", json={"email": email})
    assert r.status_code == 409


def test_verify_token_single_use(client, mail):
    email = unique_email("bob")
    client.post("/v1/auth/register", json={"email": email})
    token = mail.last_token(email)
    assert client.post("/v1/auth/verify-email", json={"token": token}).status_code == 200
    r = client.post("/v1/auth/verify-email", json={"token": token})
    assert r.status_code == 401


def test_login_requires_verification(client, mail):
    email = unique_email("carol")
    client.post("/v1/auth/register", json={"email": email})
    token = mail.last_token(email)
    r = client.post("/v1/auth/login/verify", json={"token": token})
    assert r.status_code == 401


def test_login_token_expired(client, mail, db):
    from datetime import timedelta

    from app.models import Token
    from app.security import hash_secret, new_id, new_opaque_token, utcnow
    from app.services.auth_service import get_user_by_email

    email = register_and_verify(client, mail)
    user = get_user_by_email(db, email)
    raw = new_opaque_token()
    db.add(
        Token(
            id=new_id(),
            user_id=user.id,
            purpose="login",
            token_hash=hash_secret(raw),
            expires_at=utcnow() - timedelta(minutes=1),
        )
    )
    db.commit()
    r = client.post("/v1/auth/login/verify", json={"token": raw})
    assert r.status_code == 410


def test_me_patch(client, mail):
    email = unique_email()
    register_and_verify(client, mail, email)
    token = login(client, mail, email)
    headers = {"Authorization": "Bearer " + token}
    r = client.patch("/v1/me", json={"display_name": "Alice2", "timezone": "Asia/Bangkok"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["display_name"] == "Alice2"
    r = client.get("/v1/me", headers=headers)
    assert r.json()["timezone"] == "Asia/Bangkok"


def test_telegram_bind_valid_and_tampered(client, mail):
    email = unique_email()
    register_and_verify(client, mail, email)
    token = login(client, mail, email)
    headers = {"Authorization": "Bearer " + token}
    tg_id = abs(hash(email)) % 10**8
    good = make_init_data("test-bot-token", {"id": tg_id, "username": "alice_tg"})
    r = client.post("/v1/me/telegram", json={"init_data": good}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["telegram_id"] == str(tg_id)
    bad = make_init_data("test-bot-token", {"id": tg_id}, tamper=True)
    r = client.post("/v1/me/telegram", json={"init_data": bad}, headers=headers)
    assert r.status_code == 401


def test_telegram_stale_rejected(client, mail):
    email = unique_email()
    register_and_verify(client, mail, email)
    token = login(client, mail, email)
    headers = {"Authorization": "Bearer " + token}
    stale = make_init_data("test-bot-token", {"id": 777001}, auth_date=int(time.time()) - 48 * 3600)
    r = client.post("/v1/me/telegram", json={"init_data": stale}, headers=headers)
    assert r.status_code == 401
