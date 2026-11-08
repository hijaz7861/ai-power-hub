from sqlalchemy import select

from backend.app.models import CreditLedger, User


def register(client, email):
    payload = {"email": email, "password": "a-long-test-password"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    return client.post("/api/v1/auth/login", json=payload).json()["access_token"]


def test_credit_grant_requires_admin(client):
    token = register(client, "ordinary-user@example.com")
    response = client.post(
        "/api/v1/admin/credits/grant",
        json={"user_id": 1, "amount": 100, "idempotency_key": "manual-grant-1", "reason": "support adjustment"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_admin_credit_grant_is_audited_and_idempotent(client, test_db):
    admin_token = register(client, "credit-admin@example.com")
    target_token = register(client, "credit-target@example.com")
    with test_db() as db:
        admin = db.scalar(select(User).where(User.email == "credit-admin@example.com"))
        admin.role = "admin"
        target = db.scalar(select(User).where(User.email == "credit-target@example.com"))
        target_id = target.id
        db.commit()

    payload = {
        "user_id": target_id,
        "amount": 500,
        "idempotency_key": "manual-credit-0001",
        "reason": "approved support adjustment",
    }
    headers = {"Authorization": f"Bearer {admin_token}"}
    first = client.post("/api/v1/admin/credits/grant", json=payload, headers=headers)
    second = client.post("/api/v1/admin/credits/grant", json=payload, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["balance"] == 500
    assert second.json()["balance"] == 500
    with test_db() as db:
        entries = list(db.scalars(select(CreditLedger).where(CreditLedger.user_id == target_id)).all())
        assert len(entries) == 1
        assert entries[0].entry_type == "grant"
        assert entries[0].amount == 500
        actor = db.scalar(select(User).where(User.email == "credit-admin@example.com"))
        assert entries[0].actor_user_id == actor.id


def test_credit_grant_idempotency_key_cannot_be_reused(client, test_db):
    admin_token = register(client, "grant-admin@example.com")
    target_token = register(client, "grant-target@example.com")
    with test_db() as db:
        admin = db.scalar(select(User).where(User.email == "grant-admin@example.com"))
        admin.role = "admin"
        target = db.scalar(select(User).where(User.email == "grant-target@example.com"))
        target_id = target.id
        db.commit()
    headers = {"Authorization": f"Bearer {admin_token}"}
    base = {"user_id": target_id, "amount": 100, "idempotency_key": "manual-credit-0002", "reason": "approved grant"}
    assert client.post("/api/v1/admin/credits/grant", json=base, headers=headers).status_code == 200
    changed = dict(base, amount=200)
    assert client.post("/api/v1/admin/credits/grant", json=changed, headers=headers).status_code == 409
