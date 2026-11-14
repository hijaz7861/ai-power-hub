import hashlib
import hmac
import json
from types import SimpleNamespace

import backend.app.api.webhooks as webhook_module
from sqlalchemy import select

from backend.app.models import CreditAccount, CreditLedger, PaymentOrder, PaymentWebhookEvent, User


SECRET = "unit-test-safepay-webhook-secret"
MERCHANT_KEY = "test-safepay-api-key"


def signed_headers(body: bytes):
    signature = hmac.new(SECRET.encode("utf-8"), body, hashlib.sha512).hexdigest()
    return {"X-SFPY-SIGNATURE": signature, "content-type": "application/json"}


def configure_webhook(monkeypatch):
    monkeypatch.setattr(
        webhook_module,
        "get_settings",
        lambda: SimpleNamespace(safepay_webhook_secret=SECRET, safepay_api_key=MERCHANT_KEY),
    )


def test_safepay_webhook_rejects_when_secret_not_configured(client, monkeypatch):
    monkeypatch.setattr(
        webhook_module,
        "get_settings",
        lambda: SimpleNamespace(safepay_webhook_secret="", safepay_api_key=""),
    )
    response = client.post("/api/v1/webhooks/safepay", content=b"{}", headers={"X-SFPY-SIGNATURE": "0" * 128})
    assert response.status_code == 503


def test_safepay_webhook_verifies_raw_body_and_stores_minimal_event(client, test_db, monkeypatch):
    configure_webhook(monkeypatch)
    event = {
        "token": "evt_payment_001",
        "merchant_api_key": MERCHANT_KEY,
        "type": "payment.succeeded",
        "version": "2.0.0",
        "data": {
            "tracker": "track_order_001",
            "state": "TRACKER_ENDED",
            "amount": 15000,
            "currency": "pkr",
            "customer_email": "private@example.com",
        },
    }
    body = json.dumps(event, separators=(",", ":")).encode()
    response = client.post("/api/v1/webhooks/safepay", content=body, headers=signed_headers(body))
    assert response.status_code == 202
    assert response.json() == {"accepted": True, "duplicate": False}

    with test_db() as db:
        stored_event = db.scalar(select(PaymentWebhookEvent).where(PaymentWebhookEvent.event_token == "evt_payment_001"))
        assert stored_event is not None
        assert stored_event.event_type == "payment.succeeded"
        assert stored_event.tracker_token == "track_order_001"
        assert stored_event.amount_minor_units == 15000
        assert stored_event.currency == "PKR"
        assert stored_event.processing_status == "unmatched"
        assert "private@example.com" not in stored_event.payload_sha256


def test_safepay_webhook_duplicate_is_idempotent_and_collision_is_rejected(client, monkeypatch):
    configure_webhook(monkeypatch)
    event = {
        "token": "evt_duplicate_001",
        "merchant_api_key": MERCHANT_KEY,
        "type": "payment.failed",
        "data": {"tracker": "track_2"},
    }
    body = json.dumps(event).encode()
    first = client.post("/api/v1/webhooks/safepay", content=body, headers=signed_headers(body))
    duplicate = client.post("/api/v1/webhooks/safepay", content=body, headers=signed_headers(body))
    assert first.status_code == 202
    assert duplicate.status_code == 202
    assert duplicate.json()["duplicate"] is True

    changed = {
        "token": "evt_duplicate_001",
        "merchant_api_key": MERCHANT_KEY,
        "type": "payment.succeeded",
        "data": {"tracker": "track_2", "amount": 100, "state": "TRACKER_ENDED"},
    }
    changed_body = json.dumps(changed).encode()
    collision = client.post(
        "/api/v1/webhooks/safepay",
        content=changed_body,
        headers=signed_headers(changed_body),
    )
    assert collision.status_code == 409


def test_safepay_webhook_rejects_bad_signature_and_invalid_event(client, monkeypatch):
    configure_webhook(monkeypatch)
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
    configure_webhook(monkeypatch)
    event = {
        "token": "evt_bad_amount",
        "merchant_api_key": MERCHANT_KEY,
        "type": "payment.succeeded",
        "data": {"amount": 10.5},
    }
    body = json.dumps(event).encode()
    response = client.post("/api/v1/webhooks/safepay", content=body, headers=signed_headers(body))
    assert response.status_code == 422


def test_safepay_webhook_requires_matching_merchant(client, monkeypatch):
    configure_webhook(monkeypatch)
    event = {"token": "evt_other_merchant", "merchant_api_key": "other-key", "type": "payment.succeeded", "data": {}}
    body = json.dumps(event).encode()
    response = client.post("/api/v1/webhooks/safepay", content=body, headers=signed_headers(body))
    assert response.status_code == 403


def test_safepay_payment_success_credits_exact_order_once(client, test_db, monkeypatch):
    configure_webhook(monkeypatch)
    credentials = {"email": "topup-owner@example.com", "password": "a-long-test-password"}
    assert client.post("/api/v1/auth/register", json=credentials).status_code == 201

    with test_db() as db:
        user = db.scalar(select(User).where(User.email == credentials["email"]))
        order = PaymentOrder(
            reference="order-reference-001",
            user_id=user.id,
            amount_minor_units=15000,
            currency="PKR",
            provider="safepay",
            status="pending",
            idempotency_key="topup-order-key-001",
            provider_tracker="track_topup_001",
        )
        db.add(order)
        db.commit()
        user_id = user.id

    event = {
        "token": "evt_topup_success_001",
        "merchant_api_key": MERCHANT_KEY,
        "type": "payment.succeeded",
        "data": {
            "tracker": "track_topup_001",
            "state": "TRACKER_ENDED",
            "amount": 15000,
            "currency": "PKR",
            "metadata": {"order_id": "order-reference-001"},
        },
    }
    body = json.dumps(event, separators=(",", ":")).encode()
    first = client.post("/api/v1/webhooks/safepay", content=body, headers=signed_headers(body))
    duplicate = client.post("/api/v1/webhooks/safepay", content=body, headers=signed_headers(body))
    assert first.status_code == 202
    assert first.json()["duplicate"] is False
    assert duplicate.status_code == 202
    assert duplicate.json()["duplicate"] is True

    with test_db() as db:
        account = db.scalar(select(CreditAccount).where(CreditAccount.user_id == user_id))
        order = db.scalar(select(PaymentOrder).where(PaymentOrder.reference == "order-reference-001"))
        entries = list(db.scalars(select(CreditLedger).where(CreditLedger.user_id == user_id)).all())
        assert account.balance == 15000
        assert order.status == "succeeded"
        assert len(entries) == 1
        assert entries[0].entry_type == "payment"
        assert entries[0].amount == 15000


def test_safepay_payment_mismatch_never_credits_account(client, test_db, monkeypatch):
    configure_webhook(monkeypatch)
    credentials = {"email": "topup-mismatch@example.com", "password": "a-long-test-password"}
    client.post("/api/v1/auth/register", json=credentials)
    with test_db() as db:
        user = db.scalar(select(User).where(User.email == credentials["email"]))
        user_id = user.id
        db.add(PaymentOrder(
            reference="order-reference-002",
            user_id=user_id,
            amount_minor_units=15000,
            currency="PKR",
            provider="safepay",
            status="pending",
            idempotency_key="topup-order-key-002",
            provider_tracker="track_topup_002",
        ))
        db.commit()
    event = {
        "token": "evt_topup_mismatch_001",
        "merchant_api_key": MERCHANT_KEY,
        "type": "payment.succeeded",
        "data": {
            "tracker": "track_topup_002",
            "state": "TRACKER_ENDED",
            "amount": 14999,
            "currency": "PKR",
            "metadata": {"order_id": "order-reference-002"},
        },
    }
    body = json.dumps(event).encode()
    response = client.post("/api/v1/webhooks/safepay", content=body, headers=signed_headers(body))
    assert response.status_code == 202
    with test_db() as db:
        account = db.scalar(select(CreditAccount).where(CreditAccount.user_id == user_id))
        order = db.scalar(select(PaymentOrder).where(PaymentOrder.reference == "order-reference-002"))
        assert account.balance == 0
        assert order.status == "pending"


def test_safepay_partial_and_full_refunds_reverse_credits_once(client, test_db, monkeypatch):
    configure_webhook(monkeypatch)
    credentials = {"email": "refund-owner@example.com", "password": "a-long-test-password"}
    assert client.post("/api/v1/auth/register", json=credentials).status_code == 201

    with test_db() as db:
        user = db.scalar(select(User).where(User.email == credentials["email"]))
        user_id = user.id
        db.add(PaymentOrder(
            reference="refund-order-001",
            user_id=user_id,
            amount_minor_units=15000,
            currency="PKR",
            provider="safepay",
            status="pending",
            idempotency_key="refund-order-key-001",
            provider_tracker="track_refund_001",
        ))
        db.commit()

    def send(event):
        body = json.dumps(event, separators=(",", ":")).encode()
        return client.post(
            "/api/v1/webhooks/safepay",
            content=body,
            headers=signed_headers(body),
        )

    paid = {
        "token": "evt_refund_payment_success",
        "merchant_api_key": MERCHANT_KEY,
        "type": "payment.succeeded",
        "data": {
            "tracker": "track_refund_001",
            "state": "TRACKER_ENDED",
            "amount": 15000,
            "currency": "PKR",
            "metadata": {"order_id": "refund-order-001"},
        },
    }
    assert send(paid).status_code == 202

    partial = {
        "token": "evt_refund_partial_001",
        "merchant_api_key": MERCHANT_KEY,
        "type": "payment.refunded",
        "data": {
            "tracker": "track_refund_001",
            "state": "TRACKER_PARTIAL_REFUND",
            "refund_amount": 5000,
            "currency": "PKR",
            "metadata": {"order_id": "refund-order-001"},
        },
    }
    assert send(partial).status_code == 202
    assert send(partial).json()["duplicate"] is True

    full = {
        "token": "evt_refund_final_001",
        "merchant_api_key": MERCHANT_KEY,
        "type": "payment.refunded",
        "data": {
            "tracker": "track_refund_001",
            "state": "TRACKER_REFUNDED",
            "refund_amount": 10000,
            "currency": "PKR",
            "metadata": {"order_id": "refund-order-001"},
        },
    }
    assert send(full).status_code == 202

    # A later duplicate success event must never re-credit an already-paid order.
    paid_again = {**paid, "token": "evt_refund_payment_success_redelivery"}
    assert send(paid_again).status_code == 202

    with test_db() as db:
        account = db.scalar(select(CreditAccount).where(CreditAccount.user_id == user_id))
        order = db.scalar(select(PaymentOrder).where(PaymentOrder.reference == "refund-order-001"))
        entries = list(db.scalars(
            select(CreditLedger).where(CreditLedger.user_id == user_id).order_by(CreditLedger.id)
        ).all())
        assert account.balance == 0
        assert order.status == "refunded"
        assert order.refunded_amount_minor_units == 15000
        assert [entry.amount for entry in entries] == [15000, -5000, -10000]
        assert [entry.entry_type for entry in entries] == ["payment", "refund", "refund"]


def test_safepay_refund_with_wrong_reference_or_excess_amount_never_reverses(client, test_db, monkeypatch):
    configure_webhook(monkeypatch)
    credentials = {"email": "refund-mismatch@example.com", "password": "a-long-test-password"}
    client.post("/api/v1/auth/register", json=credentials)
    with test_db() as db:
        user = db.scalar(select(User).where(User.email == credentials["email"]))
        user_id = user.id
        db.add(PaymentOrder(
            reference="refund-order-002",
            user_id=user_id,
            amount_minor_units=15000,
            currency="PKR",
            provider="safepay",
            status="succeeded",
            idempotency_key="refund-order-key-002",
            provider_tracker="track_refund_002",
        ))
        db.commit()

    event = {
        "token": "evt_refund_bad_reference",
        "merchant_api_key": MERCHANT_KEY,
        "type": "payment.refunded",
        "data": {
            "tracker": "track_refund_002",
            "state": "TRACKER_REFUNDED",
            "refund_amount": 15001,
            "currency": "PKR",
            "metadata": {"order_id": "different-order"},
        },
    }
    body = json.dumps(event).encode()
    assert client.post(
        "/api/v1/webhooks/safepay",
        content=body,
        headers=signed_headers(body),
    ).status_code == 202
    with test_db() as db:
        account = db.scalar(select(CreditAccount).where(CreditAccount.user_id == user_id))
        order = db.scalar(select(PaymentOrder).where(PaymentOrder.reference == "refund-order-002"))
        event_record = db.scalar(select(PaymentWebhookEvent).where(
            PaymentWebhookEvent.event_token == "evt_refund_bad_reference"
        ))
        assert account.balance == 0
        assert order.refunded_amount_minor_units == 0
        assert order.status == "succeeded"
        assert event_record.processing_status == "refund_review"
