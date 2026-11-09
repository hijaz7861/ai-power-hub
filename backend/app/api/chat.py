"""Authenticated, prepaid AI chat with customer-owned conversation history."""
from datetime import datetime, timezone
import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.api.auth import get_current_user
from backend.app.core.config import get_settings
from backend.app.core.database import get_db
from backend.app.models import (
    AIRequest,
    Conversation,
    ConversationMessage,
    CreditReservation,
    SupplierOffer,
    User,
)
from backend.app.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ConversationDetailResponse,
    ConversationMessageResponse,
    ConversationSummaryResponse,
)
from backend.app.services.credits import (
    InsufficientCreditsError,
    get_balance,
    release_reservation,
    reserve_credits,
    settle_reservation,
)
from backend.app.services.pricing import calculate_token_retail_charge
from backend.app.services.provider_adapters import (
    ChatMessage,
    OpenAICompatibleChatAdapter,
    ProviderError,
)

router = APIRouter(prefix="/api/v1/chat", tags=["AI chat"])

PROVIDER_ENDPOINTS = {
    "openai": "https://api.openai.com/v1/",
    "mistral": "https://api.mistral.ai/v1/",
}


def _retail_charge(input_rate: int, output_rate: int, prompt_tokens: int,
                   completion_tokens: int, target_margin_bps: int = 1500) -> int:
    return calculate_token_retail_charge(
        input_rate_minor_units=input_rate,
        output_rate_minor_units=output_rate,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        target_margin_bps=target_margin_bps,
    )


def _find_verified_rate_pair(db: Session, provider: str, model: str) -> tuple[int, int] | None:
    offers = list(db.scalars(
        select(SupplierOffer).where(
            SupplierOffer.service_type == "ai_api",
            SupplierOffer.provider_code == provider,
            SupplierOffer.model_code == model,
            SupplierOffer.currency == "PKR",
            SupplierOffer.contract_status == "verified",
            SupplierOffer.is_active.is_(True),
        )
    ).all())
    by_supplier: dict[str, dict[str, int]] = {}
    for offer in offers:
        by_supplier.setdefault(offer.supplier_code, {})[offer.billing_unit] = offer.wholesale_cost_minor_units
    pairs = [
        (rates["per_1k_input_tokens"], rates["per_1k_output_tokens"])
        for rates in by_supplier.values()
        if "per_1k_input_tokens" in rates and "per_1k_output_tokens" in rates
    ]
    return min(pairs, key=lambda pair: sum(pair)) if pairs else None


def _completed_response(request: AIRequest, db: Session) -> ChatCompletionResponse:
    if request.status != "completed" or request.prompt_tokens is None or request.completion_tokens is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This idempotent request is not complete; check its status before retrying",
        )
    reserved = 0
    if request.reservation_id is not None:
        reservation = db.get(CreditReservation, request.reservation_id)
        reserved = reservation.reserved_amount if reservation else request.credits_charged
    return ChatCompletionResponse(
        request_id=request.id,
        conversation_id=request.conversation_id,
        provider=request.provider,
        model=request.model,
        content=request.response_text or "",
        prompt_tokens=request.prompt_tokens,
        completion_tokens=request.completion_tokens,
        credits_charged=request.credits_charged,
        credits_refunded=max(0, reserved - request.credits_charged),
        balance=get_balance(db, request.user_id),
    )


@router.post("/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(
    payload: ChatCompletionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatCompletionResponse:
    settings = get_settings()
    api_key = getattr(settings, f"{payload.provider}_api_key", "")
    if not api_key:
        raise HTTPException(status_code=503, detail=f"{payload.provider} credentials are not configured")
    if len(payload.messages) != 1 or payload.messages[0].role != "user":
        raise HTTPException(status_code=422, detail="Send one new user message per chat request")

    rates = _find_verified_rate_pair(db, payload.provider, payload.model)
    if rates is None:
        raise HTTPException(
            status_code=404,
            detail="This model has no active, contract-verified PKR input/output rate pair",
        )
    input_rate, output_rate = rates

    request_data = payload.model_dump(exclude={"idempotency_key"})
    request_hash = hashlib.sha256(
        json.dumps(request_data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    existing = db.scalar(select(AIRequest).where(
        AIRequest.user_id == user.id,
        AIRequest.idempotency_key == payload.idempotency_key,
    ))
    if existing is not None:
        if existing.request_hash != request_hash:
            raise HTTPException(status_code=409, detail="Idempotency key belongs to a different request")
        return _completed_response(existing, db)

    if payload.conversation_id is None:
        title = payload.messages[0].content.strip()[:157] or "New conversation"
        conversation = Conversation(user_id=user.id, title=title)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    else:
        conversation = db.scalar(select(Conversation).where(
            Conversation.id == payload.conversation_id,
            Conversation.user_id == user.id,
        ))
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

    history = list(db.scalars(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation.id)
        .order_by(ConversationMessage.id.desc())
        .limit(30)
    ).all())
    history.reverse()
    provider_messages = [
        ChatMessage(role=message.role, content=message.content)
        for message in history
    ]
    provider_messages.append(ChatMessage(role="user", content=payload.messages[0].content))

    message_bytes = sum(len(item.content.encode("utf-8")) for item in provider_messages)
    if message_bytes > 32768:
        raise HTTPException(status_code=413, detail="Conversation context exceeds 32 KiB")
    # Reserve against a byte-derived input upper estimate and the full output cap.
    max_input_tokens = max(1, (message_bytes * 5 + 3) // 4)
    reserve_amount = _retail_charge(
        input_rate, output_rate, max_input_tokens, payload.max_tokens
    )

    ai_request = AIRequest(
        user_id=user.id,
        idempotency_key=payload.idempotency_key,
        request_hash=request_hash,
        provider=payload.provider,
        model=payload.model,
        status="processing",
        conversation_id=conversation.id,
        input_rate_minor_units=input_rate,
        output_rate_minor_units=output_rate,
        target_margin_bps=1500,
    )
    db.add(ai_request)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(AIRequest).where(
            AIRequest.user_id == user.id,
            AIRequest.idempotency_key == payload.idempotency_key,
        ))
        if existing is None or existing.request_hash != request_hash:
            raise HTTPException(status_code=409, detail="Idempotency key conflict") from None
        return _completed_response(existing, db)
    db.refresh(ai_request)

    try:
        reservation = reserve_credits(
            db,
            user_id=user.id,
            amount=reserve_amount,
            idempotency_key=f"ai-request-{ai_request.id}",
            description=f"{payload.provider}/{payload.model} chat request",
        )
    except InsufficientCreditsError:
        ai_request.status = "failed"
        ai_request.error_code = "insufficient_credits"
        db.commit()
        raise HTTPException(status_code=402, detail="Insufficient credits for the maximum estimated request cost") from None

    ai_request.reservation_id = reservation.id
    db.add(ConversationMessage(
        conversation_id=conversation.id,
        request_id=ai_request.id,
        role="user",
        content=payload.messages[0].content,
    ))
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()

    adapter = OpenAICompatibleChatAdapter(
        provider=payload.provider,
        base_url=PROVIDER_ENDPOINTS[payload.provider],
        api_key=api_key,
        timeout_seconds=30,
    )
    try:
        result = await adapter.complete(
            model=payload.model,
            messages=provider_messages,
            max_tokens=payload.max_tokens,
        )
    except ProviderError:
        release_reservation(db, user_id=user.id, reservation_id=reservation.id)
        ai_request.status = "failed"
        ai_request.error_code = "provider_unavailable"
        db.commit()
        raise HTTPException(status_code=502, detail="AI provider request failed; reserved credits were released") from None

    assistant_message = ConversationMessage(
        conversation_id=conversation.id,
        request_id=ai_request.id,
        role="assistant",
        content=result.content,
        provider=payload.provider,
        model=payload.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        credits_charged=0,
    )
    db.add(assistant_message)
    conversation.updated_at = datetime.now(timezone.utc)

    if result.prompt_tokens is None or result.completion_tokens is None:
        ai_request.status = "reconciliation_required"
        ai_request.error_code = "provider_usage_missing"
        ai_request.provider_request_id = result.request_id
        ai_request.response_text = result.content
        db.commit()
        raise HTTPException(
            status_code=502,
            detail="Provider response did not include billable token usage; reserved credits remain held for reconciliation",
        )

    actual_charge = _retail_charge(
        input_rate, output_rate, result.prompt_tokens, result.completion_tokens
    )
    if actual_charge > reservation.reserved_amount:
        ai_request.status = "reconciliation_required"
        ai_request.error_code = "usage_exceeded_reservation"
        ai_request.provider_request_id = result.request_id
        ai_request.response_text = result.content
        ai_request.prompt_tokens = result.prompt_tokens
        ai_request.completion_tokens = result.completion_tokens
        db.commit()
        raise HTTPException(
            status_code=502,
            detail="Reported usage exceeded the authorized reservation; manual reconciliation is required",
        )

    settle_reservation(
        db, user_id=user.id, reservation_id=reservation.id, actual_amount=actual_charge
    )
    ai_request.status = "completed"
    ai_request.response_text = result.content
    ai_request.provider_request_id = result.request_id
    ai_request.prompt_tokens = result.prompt_tokens
    ai_request.completion_tokens = result.completion_tokens
    ai_request.credits_charged = actual_charge
    ai_request.completed_at = datetime.now(timezone.utc)
    ai_request.error_code = None
    assistant_message.credits_charged = actual_charge
    db.commit()
    db.refresh(ai_request)

    return ChatCompletionResponse(
        request_id=ai_request.id,
        conversation_id=conversation.id,
        provider=payload.provider,
        model=payload.model,
        content=result.content,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        credits_charged=actual_charge,
        credits_refunded=reservation.reserved_amount - actual_charge,
        balance=get_balance(db, user.id),
    )


@router.get("/conversations", response_model=list[ConversationSummaryResponse])
def list_conversations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    conversations = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
    ).all()
    return [
        {"id": item.id, "title": item.title, "created_at": item.created_at, "updated_at": item.updated_at}
        for item in conversations
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    conversation = db.scalar(select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id,
    ))
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = list(db.scalars(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation.id)
        .order_by(ConversationMessage.id.asc())
    ).all())
    return {
        "conversation": {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
        },
        "messages": messages,
    }


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    conversation = db.scalar(select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id,
    ))
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    active_request = db.scalar(select(AIRequest.id).where(
        AIRequest.conversation_id == conversation.id,
        AIRequest.status == "processing",
    ).limit(1))
    if active_request is not None:
        raise HTTPException(
            status_code=409,
            detail="This conversation has an AI request in progress; try again after it finishes",
        )

    # Keep financial/audit request rows, but erase the conversation text.
    db.execute(update(AIRequest).where(
        AIRequest.conversation_id == conversation.id
    ).values(conversation_id=None, response_text=None, request_hash="0" * 64))
    db.execute(delete(ConversationMessage).where(
        ConversationMessage.conversation_id == conversation.id
    ))
    db.delete(conversation)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/models")
def list_available_chat_models(db: Session = Depends(get_db)) -> dict:
    """Expose only models with both active, verified PKR token-rate offers."""
    offers = list(db.scalars(
        select(SupplierOffer).where(
            SupplierOffer.service_type == "ai_api",
            SupplierOffer.provider_code.in_(tuple(PROVIDER_ENDPOINTS)),
            SupplierOffer.model_code.is_not(None),
            SupplierOffer.currency == "PKR",
            SupplierOffer.contract_status == "verified",
            SupplierOffer.is_active.is_(True),
        )
    ).all())
    grouped: dict[tuple[str, str, str], set[str]] = {}
    for offer in offers:
        key = (offer.supplier_code, offer.provider_code, offer.model_code or "")
        grouped.setdefault(key, set()).add(offer.billing_unit)
    settings = get_settings()
    items = set()
    for (_, provider, model), units in grouped.items():
        if {"per_1k_input_tokens", "per_1k_output_tokens"}.issubset(units):
            credential_configured = bool(getattr(settings, f"{provider}_api_key", ""))
            if credential_configured:
                items.add((provider, model, True))
    return {
        "items": [
            {"provider": provider, "model": model, "credential_configured": configured}
            for provider, model, configured in sorted(items)
        ],
        "count": len(items),
    }
