from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from backend.app.models import CreditAccount, CreditLedger

class InsufficientCreditsError(Exception):
    pass

def get_balance(db: Session, user_id: int) -> int:
    account = db.scalar(select(CreditAccount).where(CreditAccount.user_id == user_id))
    return account.balance if account else 0

def debit_credits(db: Session, *, user_id: int, amount: int, idempotency_key: str, description: str = "") -> int:
    """Debit integer credits atomically; repeat keys do not charge twice."""
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        raise ValueError("amount must be a positive integer")
    idempotency_key = idempotency_key.strip() if isinstance(idempotency_key, str) else ""
    if not idempotency_key or len(idempotency_key) > 128:
        raise ValueError("a valid idempotency_key is required")
    existing = db.scalar(select(CreditLedger).where(CreditLedger.idempotency_key == idempotency_key))
    if existing is not None:
        if existing.user_id != user_id or existing.amount != -amount or existing.entry_type != "debit":
            raise ValueError("idempotency_key was already used for a different operation")
        return get_balance(db, user_id)
    result = db.execute(
        update(CreditAccount)
        .where(CreditAccount.user_id == user_id, CreditAccount.balance >= amount)
        .values(balance=CreditAccount.balance - amount)
    )
    if result.rowcount != 1:
        db.rollback()
        raise InsufficientCreditsError("insufficient credits")
    db.add(CreditLedger(user_id=user_id, amount=-amount, entry_type="debit",
                        idempotency_key=idempotency_key, description=description[:255]))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(CreditLedger).where(CreditLedger.idempotency_key == idempotency_key))
        if existing is not None and existing.user_id == user_id and existing.amount == -amount and existing.entry_type == "debit":
            return get_balance(db, user_id)
        raise ValueError("idempotency_key was already used for a different operation") from None
    return get_balance(db, user_id)


def grant_credits(
    db: Session,
    *,
    user_id: int,
    amount: int,
    idempotency_key: str,
    description: str,
    actor_user_id: int,
) -> int:
    """Apply an audited administrative credit adjustment exactly once.

    This is not a payment confirmation mechanism. Only a privileged admin API
    may call it after an independently authorised manual adjustment decision.
    """
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        raise ValueError("amount must be a positive integer")
    idempotency_key = idempotency_key.strip() if isinstance(idempotency_key, str) else ""
    if not idempotency_key or len(idempotency_key) > 128:
        raise ValueError("a valid idempotency_key is required")
    reason = description.strip()
    if len(reason) < 4 or len(reason) > 255:
        raise ValueError("a reason between 4 and 255 characters is required")

    existing = db.scalar(
        select(CreditLedger).where(CreditLedger.idempotency_key == idempotency_key)
    )
    if existing is not None:
        if (
            existing.user_id != user_id
            or existing.amount != amount
            or existing.entry_type != "grant"
        ):
            raise ValueError("idempotency_key was already used for a different operation")
        return get_balance(db, user_id)

    result = db.execute(
        update(CreditAccount)
        .where(CreditAccount.user_id == user_id)
        .values(balance=CreditAccount.balance + amount)
    )
    if result.rowcount != 1:
        db.rollback()
        raise ValueError("credit account does not exist")
    db.add(CreditLedger(
        user_id=user_id,
        amount=amount,
        entry_type="grant",
        idempotency_key=idempotency_key,
        description=reason,
        actor_user_id=actor_user_id,
    ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(CreditLedger).where(CreditLedger.idempotency_key == idempotency_key))
        if existing is not None and existing.user_id == user_id and existing.amount == amount and existing.entry_type == "grant":
            return get_balance(db, user_id)
        raise ValueError("idempotency_key was already used for a different operation") from None
    return get_balance(db, user_id)
