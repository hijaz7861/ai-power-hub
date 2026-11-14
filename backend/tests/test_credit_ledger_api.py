from sqlalchemy import select

from backend.app.models import CreditLedger, User


def test_credit_ledger_is_authenticated_and_scoped_to_current_user(client, test_db):
    first = {"email": "ledger-first@example.com", "password": "a-long-test-password"}
    second = {"email": "ledger-second@example.com", "password": "a-long-test-password"}
    client.post("/api/v1/auth/register", json=first)
    client.post("/api/v1/auth/register", json=second)
    first_token = client.post("/api/v1/auth/login", json=first).json()["access_token"]

    with test_db() as db:
        first_user = db.scalar(select(User).where(User.email == first["email"]))
        second_user = db.scalar(select(User).where(User.email == second["email"]))
        db.add_all([
            CreditLedger(user_id=first_user.id, amount=25, entry_type="grant",
                         idempotency_key="ledger-first-0001", description="test credit"),
            CreditLedger(user_id=second_user.id, amount=99, entry_type="grant",
                         idempotency_key="ledger-second-0001", description="other user's credit"),
        ])
        db.commit()

    assert client.get("/api/v1/credits/ledger").status_code == 401
    response = client.get(
        "/api/v1/credits/ledger?limit=10&offset=0",
        headers={"Authorization": f"Bearer {first_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["amount"] == 25
    assert response.json()[0]["description"] == "test credit"


def test_credit_ledger_rejects_out_of_range_pagination(client):
    user = {"email": "ledger-page@example.com", "password": "a-long-test-password"}
    client.post("/api/v1/auth/register", json=user)
    token = client.post("/api/v1/auth/login", json=user).json()["access_token"]
    response = client.get(
        "/api/v1/credits/ledger?limit=1000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
