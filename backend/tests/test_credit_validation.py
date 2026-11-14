import pytest
from sqlalchemy import select

from backend.app.models import CreditAccount, User
from backend.app.services.credits import debit_credits


@pytest.mark.parametrize("amount", [0, -1, 1.5, True])
def test_debit_rejects_non_positive_or_non_integer_amount(test_db, amount):
    with test_db() as db:
        user = User(email=f"bad-amount-{str(amount)}@example.com", password_hash="unused")
        user.credit_account = CreditAccount(balance=10)
        db.add(user)
        db.commit()
        user_id = user.id
        with pytest.raises(ValueError, match="positive integer"):
            debit_credits(
                db,
                user_id=user_id,
                amount=amount,
                idempotency_key="invalid-amount-key",
            )
