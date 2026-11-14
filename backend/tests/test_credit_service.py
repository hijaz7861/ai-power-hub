import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from backend.app.core.database import Base
from backend.app.models import CreditAccount, CreditLedger, User
from backend.app.services.credits import InsufficientCreditsError, debit_credits, get_balance

def test_debit_is_idempotent_and_cannot_overdraw():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email="ledger@example.com", password_hash="unused")
        user.credit_account = CreditAccount(balance=50)
        db.add(user)
        db.commit()
        db.refresh(user)
        assert debit_credits(db, user_id=user.id, amount=15, idempotency_key="request-1") == 35
        assert debit_credits(db, user_id=user.id, amount=15, idempotency_key="request-1") == 35
        assert db.query(CreditLedger).count() == 1
        with pytest.raises(InsufficientCreditsError):
            debit_credits(db, user_id=user.id, amount=100, idempotency_key="request-2")
        assert get_balance(db, user.id) == 35
    Base.metadata.drop_all(engine)
    engine.dispose()

def test_idempotency_key_cannot_be_reused_for_different_charge():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email="keyreuse@example.com", password_hash="unused")
        user.credit_account = CreditAccount(balance=50)
        db.add(user)
        db.commit()
        db.refresh(user)
        debit_credits(db, user_id=user.id, amount=10, idempotency_key="same-key")
        with pytest.raises(ValueError):
            debit_credits(db, user_id=user.id, amount=20, idempotency_key="same-key")
    Base.metadata.drop_all(engine)
    engine.dispose()
