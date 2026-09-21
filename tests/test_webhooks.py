import hashlib
import hmac
import json

from tests.test_auth import register_and_verify
from tests.test_service_keys import admin_headers


def test_webhook_delivery_signature(client, mail, monkeypatch):
    register_and_verify(client, mail, "hook@example.com")
    captured = {}

    class FakeResp:
        status_code = 200

    def fake_post(url, content=None, headers=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = content
        return FakeResp()

    import app.services.webhook_service as ws

    monkeypatch.setattr(ws.httpx, "post", fake_post)

    r = client.post(
        "/v1/webhooks/subscriptions",
        json={"url": "https://business.example/hooks/cas", "secret": "whsec_test", "events": ["user.verified"]},
        headers=admin_headers(),
    )
    assert r.status_code == 201

    # a new verification should trigger delivery
    register_and_verify(client, mail, "hook2@example.com")
    assert captured["url"] == "https://business.example/hooks/cas"
    expected = hmac.new(b"whsec_test", captured["body"], hashlib.sha256).hexdigest()
    assert captured["headers"]["X-CAS-Signature"] == expected
    payload = json.loads(captured["body"])
    assert payload["type"] == "user.verified"


def test_unknown_event_type_rejected(client):
    r = client.post(
        "/v1/webhooks/subscriptions",
        json={"url": "https://x.example", "secret": "whsec_test", "events": ["nope.nope"]},
        headers=admin_headers(),
    )
    assert r.status_code == 422
