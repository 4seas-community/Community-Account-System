from app.services.auth_service import get_user_by_email
from tests.conftest import TestingSessionLocal
from tests.test_auth import register_and_verify
from tests.test_service_keys import create_service_key


def setup_user_and_key(client, mail, email="points@example.com"):
    register_and_verify(client, mail, email)
    secret = create_service_key(client, ["points:read", "points:write"])
    db = TestingSessionLocal()
    user = get_user_by_email(db, email)
    db.close()
    return user.id, {"X-Service-Key": secret}


def test_points_adjust_and_balance(client, mail):
    user_id, headers = setup_user_and_key(client, mail)
    r = client.post(f"/v1/users/{user_id}/points/adjust", json={"delta": 100, "reason": "quota_grant"}, headers=headers)
    assert r.status_code == 201
    assert r.json()["balance"] == 100
    r = client.post(
        f"/v1/users/{user_id}/points/adjust",
        json={"delta": -40, "reason": "booking_charge", "ref_type": "booking", "ref_id": "b1"},
        headers=headers,
    )
    assert r.status_code == 201
    assert r.json()["balance"] == 60
    r = client.get(f"/v1/users/{user_id}/points", headers=headers)
    assert r.json()["balance"] == 60


def test_points_insufficient_balance(client, mail):
    user_id, headers = setup_user_and_key(client, mail, "poor@example.com")
    r = client.post(f"/v1/users/{user_id}/points/adjust", json={"delta": -10, "reason": "booking_charge"}, headers=headers)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "unprocessable"


def test_points_zero_delta_rejected(client, mail):
    user_id, headers = setup_user_and_key(client, mail, "zero@example.com")
    r = client.post(f"/v1/users/{user_id}/points/adjust", json={"delta": 0, "reason": "x"}, headers=headers)
    assert r.status_code == 422


def test_ledger_pagination(client, mail):
    user_id, headers = setup_user_and_key(client, mail, "ledger@example.com")
    for i in range(3):
        client.post(f"/v1/users/{user_id}/points/adjust", json={"delta": 1, "reason": f"r{i}"}, headers=headers)
    base = "/v1/points/ledger?user_id=" + user_id
    r = client.get(base + "&limit=2", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body["entries"]) == 2
    assert body["next_cursor"] is not None
    r = client.get(base + "&limit=2&cursor=" + body["next_cursor"], headers=headers)
    assert len(r.json()["entries"]) == 1
    assert r.json()["next_cursor"] is None
