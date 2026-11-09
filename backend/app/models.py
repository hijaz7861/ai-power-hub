from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
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


class PaymentWebhookEvent(Base):
    """Verified provider webhook inbox; business settlement is a separate step."""
    __tablename__ = "payment_webhook_events"
    __table_args__ = (
        UniqueConstraint("event_token", name="uq_payment_webhook_event_token"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_token: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    tracker_token: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    amount_minor_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    order_reference: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    provider_state: Mapped[str | None] = mapped_column(String(60), nullable=True)
    payment_order_id: Mapped[int | None] = mapped_column(ForeignKey("payment_orders.id", ondelete="SET NULL"), nullable=True)
    processing_status: Mapped[str] = mapped_column(String(24), default="received", nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PaymentOrder(Base):
    """A PKR credit top-up linked to one Safepay tracker."""
    __tablename__ = "payment_orders"
    __table_args__ = (
        UniqueConstraint("reference", name="uq_payment_order_reference"),
        UniqueConstraint("user_id", "idempotency_key", name="uq_payment_order_user_idempotency"),
        UniqueConstraint("provider_tracker", name="uq_payment_order_provider_tracker"),
        CheckConstraint("amount_minor_units > 0", name="ck_payment_order_positive_amount"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount_minor_units: Mapped[int] = mapped_column(Integer, nullable=False)
    refunded_amount_minor_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="PKR", nullable=False)
    provider: Mapped[str] = mapped_column(String(24), default="safepay", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_tracker: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CreditReservation(Base):
    """Funds reserved before a metered provider call and settled exactly once."""
    __tablename__ = "credit_reservations"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_credit_reservation_user_key"),
        CheckConstraint("reserved_amount > 0", name="ck_credit_reservation_positive"),
        CheckConstraint("captured_amount >= 0 AND captured_amount <= reserved_amount",
                        name="ck_credit_reservation_capture_range"),
        CheckConstraint("status IN ('reserved', 'captured', 'released')",
                        name="ck_credit_reservation_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"),
                                         nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    reserved_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    captured_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="reserved")
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AIRequest(Base):
    """Idempotent record of a metered AI request and its settled response."""
    __tablename__ = "ai_requests"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_ai_request_user_key"),
        CheckConstraint(
            "status IN ('processing', 'completed', 'failed', 'reconciliation_required')",
            name="ck_ai_request_status",
        ),
        CheckConstraint("credits_charged >= 0", name="ck_ai_request_nonnegative_charge"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"),
                                         nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="processing")
    reservation_id: Mapped[int | None] = mapped_column(
        ForeignKey("credit_reservations.id", ondelete="SET NULL"), nullable=True
    )
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_request_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    credits_charged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_rate_minor_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_rate_minor_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    target_margin_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=1500)
    reconciliation_evidence: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reconciled_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)



class Conversation(Base):
    """A customer-owned chat thread."""
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"),
                                         nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False, default="New conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ConversationMessage(Base):
    """User and assistant messages linked to a metered AI request."""
    __tablename__ = "conversation_messages"
    __table_args__ = (
        UniqueConstraint("request_id", "role", name="uq_conversation_message_request_role"),
        CheckConstraint("role IN ('user', 'assistant')", name="ck_conversation_message_role"),
        CheckConstraint("credits_charged >= 0", name="ck_conversation_message_nonnegative_charge"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    request_id: Mapped[int] = mapped_column(
        ForeignKey("ai_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    credits_charged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
