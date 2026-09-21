from tests.test_service_keys import create_service_key


def issue_token(client, event_id="evt1", reg_id="reg1", event_url="https://4seas.example/events/evt1", ttl=3600, max_uses=1):
    secret = create_service_key(client, ["checkin:issue"])
    r = client.post(
        "/v1/checkin/tokens",
        json={
            "event_id": event_id,
            "registration_id": reg_id,
            "event_url": event_url,
            "ttl_seconds": ttl,
            "max_uses": max_uses,
        },
        headers={"X-Service-Key": secret},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return body["token_id"], body["claim_url"]


def test_claim_url_roundtrip_and_single_use(client):
    token_id, claim_url = issue_token(client)
    assert "ck=" + token_id in claim_url
    assert "sig=" in claim_url
    from urllib.parse import parse_qs, urlparse

    qs = parse_qs(urlparse(claim_url).query)
    r = client.post("/v1/checkin/claim", json={"token_id": qs["ck"][0], "sig": qs["sig"][0]})
    assert r.status_code == 200, r.text
    assert r.json()["valid"] is True
    # replay -> 409
    r = client.post("/v1/checkin/claim", json={"token_id": qs["ck"][0], "sig": qs["sig"][0]})
    assert r.status_code == 409


def test_claim_bad_signature(client):
    token_id, _ = issue_token(client)
    r = client.post("/v1/checkin/claim", json={"token_id": token_id, "sig": "0" * 64})
    assert r.status_code == 401


def test_claim_expired(client):
    token_id, claim_url = issue_token(client, ttl=60)
    # force expiry by patching the stored row
    from datetime import timedelta

    from app.models import CheckinToken
    from app.security import utcnow
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()
    token = db.get(CheckinToken, token_id)
    token.exp = utcnow() - timedelta(seconds=1)
    db.commit()
    db.close()
    from urllib.parse import parse_qs, urlparse

    qs = parse_qs(urlparse(claim_url).query)
    r = client.post("/v1/checkin/claim", json={"token_id": qs["ck"][0], "sig": qs["sig"][0]})
    assert r.status_code == 410


def test_claim_unknown_token(client):
    r = client.post("/v1/checkin/claim", json={"token_id": "nope", "sig": "x"})
    assert r.status_code == 404


def test_token_status_and_nft_claim(client):
    token_id, _ = issue_token(client)
    secret = create_service_key(client, ["checkin:issue"])
    r = client.get("/v1/checkin/tokens/" + token_id, headers={"X-Service-Key": secret})
    assert r.status_code == 200
    assert r.json()["status"] == "pending"
    r = client.post(
        "/v1/checkin/tokens/" + token_id + "/nft-claim",
        json={"nft_contract": "0xabc", "token_id": "7", "tx_hash": "0xdef"},
        headers={"X-Service-Key": secret},
    )
    assert r.status_code == 201
    r = client.get("/v1/checkin/tokens/" + token_id, headers={"X-Service-Key": secret})
    assert r.json()["nft_claim_id"] is not None


def test_multi_use_token(client):
    _token_id, claim_url = issue_token(client, max_uses=3)
    from urllib.parse import parse_qs, urlparse

    qs = parse_qs(urlparse(claim_url).query)
    for _ in range(3):
        r = client.post("/v1/checkin/claim", json={"token_id": qs["ck"][0], "sig": qs["sig"][0]})
        assert r.status_code == 200
    r = client.post("/v1/checkin/claim", json={"token_id": qs["ck"][0], "sig": qs["sig"][0]})
    assert r.status_code == 409
