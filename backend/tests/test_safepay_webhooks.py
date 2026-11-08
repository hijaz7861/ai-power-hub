import hashlib
import hmac
import json
from types import SimpleNamespace

import backend.app.api.webhooks as webhook_module


SECRET = "unit-test-safepay-webhook-secret"


def signed_headers(body: bytes):
    signature = hmac.new(SECRET.encode("utf-8"), body, hashlib.sha512).hexdigest()
    return {"X-SFPY-SIGNATURE": signature, "content-type": "application/json"}


def test_safepay_webhook_rejects_when_secret_not_configured(client, monkeypatch):
    monkeypatch.setattr(
        webhook_module,
        "get_settings",
        lambda: SimpleNamespace(safepay_webhook_secret=""),
    )
    response = client.post("/api/v1/webhooks/safepay", content=b"{}", headers={"X-SFPY-SIGNATURE": "0" * 128})
    assert response.status_code == 503


def test_safepay_webhook_verifies_raw_body_and_stores_minimal_event(client, test_db, monkeypatch):
    monkeypatch.setattr(
        webhook_module,
        "get_settings",
        lambda: SimpleNamespace(safepay_webhook_secret=SECRET),
    )
    event = {
        "token": "evt_payment_001",
        "type": "payment.succeeded",
        "version": "2.0.0",
        "data": {
            "tracker": "track_order_001",
            "amount": 15000,
            "currency": "pkr",
            "customer_email": "private@example.com",
        },
    }
    body = json.dumps(event, separators=(",", ":")).encode()
    response = client.post("/api/v1/webhooks/safepay", content=body, headers=signed_headers(body))
    assert response.status_code == 202
    assert response.json() == {"accepted": True, "duplicate": False}

    from backend.app.models import PaymentWebhookEvent
    from sqlalchemy import select

    with test_db() as db:
        stored = db.scalar(select(PaymentWebhookEvent).where(PaymentWebhookEvent.event_token == "evt_payment_001"))
        assert stored is not None
        assert stored.event_type == "payment.succeeded"
        assert stored.tracker_token == "track_order_001"
        assert stored.amount_minor_units == 15000
        assert stored.currency == "PKR"
        assert stored.processing_status == "received"
        assert "private@example.com" not in stored.payload_sha256


def test_safepay_webhook_duplicate_is_idempotent_and_collision_is_rejected(client, test_db, monkeypatch):
    monkeypatch.setattr(
        webhook_module,
        "get_settings",
        lambda: SimpleNamespace(safepay_webhook_secret=SECRET),
    )
    event = {"token": "evt_duplicate_001", "type": "payment.failed", "data": {"tracker": "track_2"}}
    body = json.dumps(event).encode()
    first = client.post("/api/v1/webhooks/safepay", content=body, headers=signed_headers(body))
    duplicate = client.post("/api/v1/webhooks/safepay", content=body, headers=signed_headers(body))
    assert first.status_code == 202
    assert duplicate.status_code == 202
    assert duplicate.json()["duplicate"] is True

    changed = {"token": "evt_duplicate_001", "type": "payment.succeeded", "data": {"tracker": "track_2", "amount": 100}}
    changed_body = json.dumps(changed).encode()
    collision = client.post(
        "/api/v1/webhooks/safepay",
        content=changed_body,
        headers=signed_headers(changed_body),
    )
    assert collision.status_code == 409


def test_safepay_webhook_rejects_bad_signature_and_invalid_event(client, monkeypatch):
    monkeypatch.setattr(
        webhook_module,
        "get_settings",
        lambda: SimpleNamespace(safepay_webhook_secret=SECRET),
    )
    assert client.post(
        "/api/v1/webhooks/safepay",
        content=b"{}",
        headers={"X-SFPY-SIGNATURE": "0" * 128},
    ).status_code == 401

    invalid = b"not-json"
    response = client.post(
        "/api/v1/webhooks/safepay",
        content=invalid,
        headers=signed_headers(invalid),
    )
    assert response.status_code == 400


def test_safepay_webhook_rejects_invalid_amount(client, monkeypatch):
    monkeypatch.setattr(
        webhook_module,
        "get_settings",
        lambda: SimpleNamespace(safepay_webhook_secret=SECRET),
    )
    event = {"token": "evt_bad_amount", "type": "payment.succeeded", "data": {"amount": 10.5}}
    body = json.dumps(event).encode()
    response = client.post("/api/v1/webhooks/safepay", content=body, headers=signed_headers(body))
    assert response.status_code == 422
