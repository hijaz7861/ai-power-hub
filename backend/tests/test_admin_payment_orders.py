from sqlalchemy import select

from backend.app.models import PaymentOrder, User


def test_payment_order_inbox_is_admin_only(client):
    credentials = {
        "email": "payment-order-customer@example.com",
        "password": "a-long-test-password",
    }
    assert client.post("/api/v1/auth/register", json=credentials).status_code == 201
    token = client.post("/api/v1/auth/login", json=credentials).json()["access_token"]
    response = client.get(
        "/api/v1/admin/payment-orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_admin_payment_order_inbox_exposes_refund_totals(client, test_db):
    credentials = {
        "email": "payment-order-admin@example.com",
        "password": "a-long-test-password",
    }
    assert client.post("/api/v1/auth/register", json=credentials).status_code == 201
    with test_db() as db:
        user = db.scalar(select(User).where(User.email == credentials["email"]))
        user.role = "admin"
        db.add(PaymentOrder(
            reference="admin-payment-order-001",
            user_id=user.id,
            amount_minor_units=12000,
            refunded_amount_minor_units=3000,
            currency="PKR",
            provider="safepay",
            status="partially_refunded",
            idempotency_key="admin-payment-order-key-001",
            provider_tracker="track_admin_order_001",
        ))
        db.commit()
    token = client.post("/api/v1/auth/login", json=credentials).json()["access_token"]
    response = client.get(
        "/api/v1/admin/payment-orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()[0]["refunded_amount_minor_units"] == 3000
    assert response.json()[0]["status"] == "partially_refunded"
