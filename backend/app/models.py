from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    is_active: Mapped[bool] = mapped_column(default=True)
    role: Mapped[str] = mapped_column(String(24), default="customer", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    credit_account: Mapped["CreditAccount"] = relationship(back_populates="user", cascade="all, delete-orphan", uselist=False)

class CreditAccount(Base):
    __tablename__ = "credit_accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    balance: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    user: Mapped[User] = relationship(back_populates="credit_account")

class CreditLedger(Base):
    __tablename__ = "credit_ledger"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_credit_ledger_idempotency"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    entry_type: Mapped[str] = mapped_column(String(16))
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str] = mapped_column(String(255), default="")
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SupplierOffer(Base):
    """Admin-managed wholesale offer; not proof of a signed resale agreement."""
    __tablename__ = "supplier_offers"
    __table_args__ = (
        UniqueConstraint("supplier_code", "provider_code", "model_code", "billing_unit",
                         name="uq_supplier_offer_identity"),
        CheckConstraint("wholesale_cost_minor_units > 0", name="ck_supplier_offer_positive_cost"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_name: Mapped[str] = mapped_column(String(160), nullable=False)
    supplier_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    service_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    provider_code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    model_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    billing_unit: Mapped[str] = mapped_column(String(40), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PKR")
    wholesale_cost_minor_units: Mapped[int] = mapped_column(Integer, nullable=False)
    contract_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    is_active: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
