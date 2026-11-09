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


from datetime import datetime, timezone
from backend.app.models import CreditReservation


def reserve_credits(
    db: Session, *, user_id: int, amount: int, idempotency_key: str,
    description: str = "Metered AI request",
) -> CreditReservation:
    """Atomically hold a maximum charge before any paid provider call."""
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        raise ValueError("reservation amount must be a positive integer")
    key = idempotency_key.strip() if isinstance(idempotency_key, str) else ""
    if not key or len(key) > 128:
        raise ValueError("a valid idempotency_key is required")
    existing = db.scalar(select(CreditReservation).where(
        CreditReservation.user_id == user_id,
        CreditReservation.idempotency_key == key,
    ))
    if existing is not None:
        if existing.reserved_amount != amount:
            raise ValueError("idempotency_key was already used for a different reservation")
        return existing

    result = db.execute(
        update(CreditAccount)
        .where(CreditAccount.user_id == user_id, CreditAccount.balance >= amount)
        .values(balance=CreditAccount.balance - amount)
    )
    if result.rowcount != 1:
        db.rollback()
        raise InsufficientCreditsError("insufficient credits for reservation")

    reservation = CreditReservation(
        user_id=user_id, idempotency_key=key, reserved_amount=amount,
        captured_amount=0, status="reserved", description=description[:255],
    )
    db.add(reservation)
    try:
        db.flush()
        db.add(CreditLedger(
            user_id=user_id, amount=-amount, entry_type="reserve",
            idempotency_key=f"reservation:{reservation.id}:hold",
            description=f"Reserved: {description}"[:255],
        ))
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(CreditReservation).where(
            CreditReservation.user_id == user_id,
            CreditReservation.idempotency_key == key,
        ))
        if existing is not None and existing.reserved_amount == amount:
            return existing
        raise ValueError("reservation idempotency key conflict") from None
    db.refresh(reservation)
    return reservation


def settle_reservation(
    db: Session, *, user_id: int, reservation_id: int, actual_amount: int,
) -> CreditReservation:
    """Capture actual usage and return the unused hold; safe to retry."""
    if isinstance(actual_amount, bool) or not isinstance(actual_amount, int) or actual_amount < 0:
        raise ValueError("actual_amount must be a non-negative integer")
    reservation = db.scalar(
        select(CreditReservation)
        .where(CreditReservation.id == reservation_id,
               CreditReservation.user_id == user_id)
        .with_for_update()
    )
    if reservation is None:
        raise ValueError("reservation not found")
    if reservation.status in {"captured", "released"}:
        if reservation.captured_amount != actual_amount:
            raise ValueError("reservation was already settled with a different amount")
        return reservation
    if actual_amount > reservation.reserved_amount:
        raise ValueError("actual usage exceeds reserved credits; additional authorization is required")

    refund = reservation.reserved_amount - actual_amount
    if refund:
        result = db.execute(
            update(CreditAccount)
            .where(CreditAccount.user_id == user_id)
            .values(balance=CreditAccount.balance + refund)
        )
        if result.rowcount != 1:
            db.rollback()
            raise ValueError("credit account does not exist")
        db.add(CreditLedger(
            user_id=user_id, amount=refund, entry_type="release",
            idempotency_key=f"reservation:{reservation.id}:release",
            description=f"Unused reservation released: {reservation.description}"[:255],
        ))
    reservation.captured_amount = actual_amount
    reservation.status = "captured" if actual_amount else "released"
    reservation.settled_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("reservation settlement conflict; reload and retry") from None
    db.refresh(reservation)
    return reservation


def release_reservation(db: Session, *, user_id: int, reservation_id: int) -> CreditReservation:
    """Release the complete hold after a provider failure or cancelled request."""
    return settle_reservation(
        db, user_id=user_id, reservation_id=reservation_id, actual_amount=0,
    )
