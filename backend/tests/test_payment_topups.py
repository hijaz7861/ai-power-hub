from types import SimpleNamespace

import backend.app.api.payments as payments_module
from sqlalchemy import select

from backend.app.models import PaymentOrder, User


class FakeSafepayClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def create_checkout(self, **kwargs):
        return SimpleNamespace(tracker="track_fake_001", checkout_url="https://sandbox.api.getsafepay.com/checkout/pay?test=1")

    async def create_checkout_url(self, **kwargs):
        return "https://sandbox.api.getsafepay.com/checkout/pay?tracker=track_fake_001&renewed=1"


def configure_payments(monkeypatch):
    monkeypatch.setattr(
        payments_module,
        "get_settings",
        lambda: SimpleNamespace(
            safepay_api_key="sandbox-api-key",
            safepay_secret_key="sandbox-secret-key",
            safepay_webhook_secret="sandbox-webhook-secret",
            safepay_environment="sandbox",
            public_app_url="https://app.example.test",
        ),
    )
    monkeypatch.setattr(payments_module, "SafepayClient", FakeSafepayClient)


def register(client, email):
    credentials = {"email": email, "password": "a-long-test-password"}
    assert client.post("/api/v1/auth/register", json=credentials).status_code == 201
    token = client.post("/api/v1/auth/login", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_customer_can_create_idempotent_safepay_topup(client, test_db, monkeypatch):
    configure_payments(monkeypatch)
    headers = register(client, "topup-customer@example.com")
    payload = {"amount_pkr": 100, "idempotency_key": "topup-idempotency-001"}

    first = client.post("/api/v1/payments/topups", json=payload, headers=headers)
    second = client.post("/api/v1/payments/topups", json=payload, headers=headers)
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["amount_minor_units"] == 10000
    assert first.json()["credits_to_receive"] == 10000
    assert first.json()["checkout_url"].startswith("https://")
    assert second.json()["checkout_url"].endswith("renewed=1")

    with test_db() as db:
        orders = list(db.scalars(select(PaymentOrder)).all())
        assert len(orders) == 1
        assert orders[0].status == "pending"
        assert orders[0].provider_tracker == "track_fake_001"

    status_response = client.get(
        "/api/v1/payments/topups/" + first.json()["reference"],
        headers=headers,
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "pending"


def test_topup_requires_provider_credentials(client, monkeypatch):
    monkeypatch.setattr(
        payments_module,
        "get_settings",
        lambda: SimpleNamespace(
            safepay_api_key="",
            safepay_secret_key="",
            safepay_webhook_secret="",
            safepay_environment="sandbox",
            public_app_url="https://app.example.test",
        ),
    )
    headers = register(client, "topup-unconfigured@example.com")
    response = client.post(
        "/api/v1/payments/topups",
        json={"amount_pkr": 100, "idempotency_key": "topup-idempotency-002"},
        headers=headers,
    )
    assert response.status_code == 503


def test_topup_minimum_amount_is_enforced(client, monkeypatch):
    configure_payments(monkeypatch)
    headers = register(client, "topup-minimum@example.com")
    response = client.post(
        "/api/v1/payments/topups",
        json={"amount_pkr": 50, "idempotency_key": "topup-idempotency-003"},
        headers=headers,
    )
    assert response.status_code == 422


def test_payment_order_is_private_to_its_owner(client, test_db, monkeypatch):
    configure_payments(monkeypatch)
    first_headers = register(client, "topup-owner-one@example.com")
    second_headers = register(client, "topup-owner-two@example.com")
    created = client.post(
        "/api/v1/payments/topups",
        json={"amount_pkr": 100, "idempotency_key": "topup-idempotency-004"},
        headers=first_headers,
    )
    reference = created.json()["reference"]
    forbidden = client.get("/api/v1/payments/topups/" + reference, headers=second_headers)
    assert forbidden.status_code == 404
