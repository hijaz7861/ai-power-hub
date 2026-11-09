"""Customer-owned data export endpoint."""

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.auth import get_current_user
from backend.app.core.database import get_db
from backend.app.models import (
    AIRequest,
    Conversation,
    ConversationMessage,
    CreditLedger,
    PaymentOrder,
    User,
)
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
