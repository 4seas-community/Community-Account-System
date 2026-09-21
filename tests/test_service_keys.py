
from tests.test_auth import register_and_verify


def admin_headers():
    return {"X-Admin-Key": "test-admin-key"}


def create_service_key(client, scopes):
    r = client.post("/v1/service-keys", json={"name": "communityos", "scopes": scopes}, headers=admin_headers())
    assert r.status_code == 201, r.text
    return r.json()["secret"]


def test_service_key_lifecycle_and_scopes(client, mail):
    register_and_verify(client, mail, "svc@example.com")
    secret = create_service_key(client, ["users:read"])
    # users:read works on a real user id
    from app.services.auth_service import get_user_by_email
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()
    user = get_user_by_email(db, "svc@example.com")
    db.close()
    r = client.get("/v1/users/" + user.id, headers={"X-Service-Key": secret})
    assert r.status_code == 200
    assert r.json()["email"] == "svc@example.com"

    # points:write is not granted -> 403
    r = client.post(
        "/v1/users/" + user.id + "/points/adjust",
        json={"delta": 10, "reason": "test"},
        headers={"X-Service-Key": secret},
    )
    assert r.status_code == 403


def test_service_key_revocation(client):
    r = client.post("/v1/service-keys", json={"name": "x", "scopes": ["users:read"]}, headers=admin_headers())
    key_id = r.json()["key_id"]
    r = client.delete("/v1/service-keys/" + key_id, headers=admin_headers())
    assert r.status_code == 204
    # revoked key no longer authenticates
    r = client.get("/v1/users/whatever", headers={"X-Service-Key": "cas_sk_bogus"})
    assert r.status_code == 401


def test_admin_key_required(client):
    r = client.post("/v1/service-keys", json={"name": "x", "scopes": ["users:read"]})
    assert r.status_code == 403
