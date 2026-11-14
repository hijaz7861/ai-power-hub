"""Customer data export and privacy-safe account closure endpoints."""

from datetime import datetime, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from backend.app.api.auth import get_current_user
from backend.app.core.database import get_db
from backend.app.core.security import hash_password, verify_password
from backend.app.models import (
    AIRequest,
    Conversation,
    ConversationMessage,
    CreditLedger,
    CreditReservation,
    PaymentOrder,
    User,
)
from backend.app.schemas import CloseAccountRequest, CloseAccountResponse
from backend.app.services.credits import get_balance

router = APIRouter(prefix="/api/v1/account", tags=["account privacy"])


@router.get("/export")
def export_account_data(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Export the authenticated customer's profile, billing and stored chat data."""
    conversations = list(db.scalars(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.asc())
    ).all())
    conversation_ids = [item.id for item in conversations]
    messages = []
    if conversation_ids:
        messages = list(db.scalars(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id.in_(conversation_ids))
            .order_by(ConversationMessage.id.asc())
        ).all())

    ledger = list(db.scalars(
        select(CreditLedger)
        .where(CreditLedger.user_id == user.id)
        .order_by(CreditLedger.id.asc())
    ).all())
    orders = list(db.scalars(
        select(PaymentOrder)
        .where(PaymentOrder.user_id == user.id)
        .order_by(PaymentOrder.id.asc())
    ).all())
    requests = list(db.scalars(
        select(AIRequest)
        .where(AIRequest.user_id == user.id)
        .order_by(AIRequest.id.asc())
    ).all())

    payload = {
        "export_version": 1,
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at,
        },
        "credits": {"balance": get_balance(db, user.id), "unit": "credits"},
        "credit_ledger": [
            {
                "id": row.id,
                "amount": row.amount,
                "entry_type": row.entry_type,
                "description": row.description,
                "created_at": row.created_at,
            }
            for row in ledger
        ],
        "payment_orders": [
            {
                "reference": row.reference,
                "amount_minor_units": row.amount_minor_units,
                "refunded_amount_minor_units": row.refunded_amount_minor_units,
                "currency": row.currency,
                "status": row.status,
                "created_at": row.created_at,
                "paid_at": row.paid_at,
            }
            for row in orders
        ],
        "ai_usage": [
            {
                "id": row.id,
                "provider": row.provider,
                "model": row.model,
                "status": row.status,
                "prompt_tokens": row.prompt_tokens,
                "completion_tokens": row.completion_tokens,
                "credits_charged": row.credits_charged,
                "created_at": row.created_at,
                "completed_at": row.completed_at,
            }
            for row in requests
        ],
        "conversations": [
            {
                "id": conversation.id,
                "title": conversation.title,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at,
                "messages": [
                    {
                        "id": message.id,
                        "role": message.role,
                        "content": message.content,
                        "provider": message.provider,
                        "model": message.model,
                        "prompt_tokens": message.prompt_tokens,
                        "completion_tokens": message.completion_tokens,
                        "credits_charged": message.credits_charged,
                        "created_at": message.created_at,
                    }
                    for message in messages
                    if message.conversation_id == conversation.id
                ],
            }
            for conversation in conversations
        ],
    }
    return JSONResponse(
        content=jsonable_encoder(payload),
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": 'attachment; filename="ai-power-hub-account-export.json"',
        },
    )


@router.post("/close", response_model=CloseAccountResponse)
def close_account(
    payload: CloseAccountRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CloseAccountResponse:
    """Deactivate a customer account and erase stored chat content.

    Financial ledger and payment reconciliation records are retained. Closure
    is blocked while money, a payment, or a provider request remains unsettled.
    """
    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transfer administrator duties to another account before closing this account",
        )
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Password confirmation failed")

    if get_balance(db, user.id) != 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Settle your remaining credit balance with support before closing this account",
        )

    pending_payment = db.scalar(select(PaymentOrder.id).where(
        PaymentOrder.user_id == user.id,
        PaymentOrder.status == "pending",
    ).limit(1))
    if pending_payment is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A payment is still pending; wait for its final provider status before closing this account",
        )

    unsettled_reservation = db.scalar(select(CreditReservation.id).where(
        CreditReservation.user_id == user.id,
        CreditReservation.status == "reserved",
    ).limit(1))
    unsettled_request = db.scalar(select(AIRequest.id).where(
        AIRequest.user_id == user.id,
        AIRequest.status.in_(("processing", "reconciliation_required")),
    ).limit(1))
    if unsettled_reservation is not None or unsettled_request is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An AI request or credit reservation is unsettled; resolve it before closing this account",
        )

    conversations = list(db.scalars(
        select(Conversation.id).where(Conversation.user_id == user.id)
    ).all())
    if conversations:
        db.execute(update(AIRequest).where(
            AIRequest.user_id == user.id
        ).values(conversation_id=None, response_text=None, request_hash="0" * 64))
        db.execute(delete(ConversationMessage).where(
            ConversationMessage.conversation_id.in_(conversations)
        ))
        db.execute(delete(Conversation).where(
            Conversation.id.in_(conversations)
        ))

    # Keep accounting rows for statutory/merchant reconciliation. Remove the
    # account's login identity and stored conversational content.
    user.email = f"closed+{user.id}@accounts.invalid"
    user.password_hash = hash_password(secrets.token_urlsafe(48))
    user.is_active = False
    user.role = "customer"
    user.closed_at = datetime.now(timezone.utc)
    db.commit()

    return CloseAccountResponse(
        status="closed",
        message="Account access disabled and stored conversation content erased. Financial records are retained for reconciliation.",
    )
