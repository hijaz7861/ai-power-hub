import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base
from backend.app.models import CreditAccount, CreditLedger, CreditReservation, User
from backend.app.services.credits import (
    InsufficientCreditsError, get_balance, release_reservation,
    reserve_credits, settle_reservation,
)


def make_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = User(email="metered@example.com", password_hash="unused")
    user.credit_account = CreditAccount(balance=1000)
    db.add(user)
    db.commit()
    db.refresh(user)
    return engine, db, user


def test_reserve_settle_captures_actual_usage_and_releases_remainder():
    engine, db, user = make_db()
    try:
        hold = reserve_credits(db, user_id=user.id, amount=400, idempotency_key="chat-request-0001")
        assert hold.status == "reserved"
        assert get_balance(db, user.id) == 600
        settled = settle_reservation(db, user_id=user.id, reservation_id=hold.id, actual_amount=275)
        assert settled.status == "captured"
        assert settled.captured_amount == 275
        assert get_balance(db, user.id) == 725
        entries = list(db.scalars(select(CreditLedger).where(CreditLedger.user_id == user.id)))
        assert [(e.entry_type, e.amount) for e in entries] == [("reserve", -400), ("release", 125)]
        assert settle_reservation(db, user_id=user.id, reservation_id=hold.id, actual_amount=275).id == hold.id
        assert get_balance(db, user.id) == 725
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_reservation_is_idempotent_and_cannot_be_reused_for_other_amount():
    engine, db, user = make_db()
    try:
        first = reserve_credits(db, user_id=user.id, amount=300, idempotency_key="same-chat-key")
        again = reserve_credits(db, user_id=user.id, amount=300, idempotency_key="same-chat-key")
        assert first.id == again.id
        assert get_balance(db, user.id) == 700
        with pytest.raises(ValueError):
            reserve_credits(db, user_id=user.id, amount=301, idempotency_key="same-chat-key")
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_insufficient_balance_never_creates_a_reservation():
    engine, db, user = make_db()
    try:
        with pytest.raises(InsufficientCreditsError):
            reserve_credits(db, user_id=user.id, amount=1001, idempotency_key="too-large-request")
        assert db.scalar(select(CreditReservation)) is None
        assert get_balance(db, user.id) == 1000
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_release_refunds_full_hold_and_is_idempotent():
    engine, db, user = make_db()
    try:
        hold = reserve_credits(db, user_id=user.id, amount=250, idempotency_key="provider-failure-01")
        released = release_reservation(db, user_id=user.id, reservation_id=hold.id)
        assert released.status == "released"
        assert released.captured_amount == 0
        assert get_balance(db, user.id) == 1000
        release_reservation(db, user_id=user.id, reservation_id=hold.id)
        assert get_balance(db, user.id) == 1000
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_settlement_cannot_capture_more_than_reserved_or_change_afterwards():
    engine, db, user = make_db()
    try:
        hold = reserve_credits(db, user_id=user.id, amount=100, idempotency_key="cap-limit-request")
        with pytest.raises(ValueError):
            settle_reservation(db, user_id=user.id, reservation_id=hold.id, actual_amount=101)
        settled = settle_reservation(db, user_id=user.id, reservation_id=hold.id, actual_amount=80)
        with pytest.raises(ValueError):
            settle_reservation(db, user_id=user.id, reservation_id=hold.id, actual_amount=79)
        assert settled.captured_amount == 80
        assert get_balance(db, user.id) == 920
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
