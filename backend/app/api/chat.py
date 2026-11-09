"""Authenticated, prepaid and idempotent AI chat execution."""
from datetime import datetime, timezone
import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.api.auth import get_current_user
from backend.app.core.config import get_settings
from backend.app.core.database import get_db
from backend.app.models import AIRequest, SupplierOffer, User
from backend.app.schemas import ChatCompletionRequest, ChatCompletionResponse
from backend.app.services.credits import (
    InsufficientCreditsError,
    get_balance,
    release_reservation,
    reserve_credits,
    settle_reservation,
)
from backend.app.services.pricing import PricingInputs, calculate_retail_price
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


def _ceil_rate(rate_per_1k: int, tokens: int) -> int:
    return (rate_per_1k * tokens + 999) // 1000


def _retail_charge(input_rate: int, output_rate: int, prompt_tokens: int,
                   completion_tokens: int) -> int:
    wholesale = _ceil_rate(input_rate, prompt_tokens) + _ceil_rate(output_rate, completion_tokens)
    if wholesale == 0:
        return 0
    return calculate_retail_price(PricingInputs(provider_cost=wholesale)).retail_price


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
        from backend.app.models import CreditReservation
        reservation = db.get(CreditReservation, request.reservation_id)
        reserved = reservation.reserved_amount if reservation else request.credits_charged
    return ChatCompletionResponse(
        request_id=request.id,
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

    rates = _find_verified_rate_pair(db, payload.provider, payload.model)
    if rates is None:
        raise HTTPException(
            status_code=404,
            detail="This model has no active, contract-verified PKR input/output rate pair",
        )
    input_rate, output_rate = rates

    message_bytes = sum(len(item.content.encode("utf-8")) for item in payload.messages)
    if message_bytes > 32768:
        raise HTTPException(status_code=413, detail="Combined message content exceeds 32 KiB")
    # Reserve against a byte-derived upper estimate plus the full requested output cap.
    # If reported usage exceeds this ceiling, funds remain held for reconciliation.
    max_input_tokens = max(1, (message_bytes * 5 + 3) // 4)
    reserve_amount = _retail_charge(
        input_rate, output_rate, max_input_tokens, payload.max_tokens
    )
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

    ai_request = AIRequest(
        user_id=user.id,
        idempotency_key=payload.idempotency_key,
        request_hash=request_hash,
        provider=payload.provider,
        model=payload.model,
        status="processing",
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
            messages=[ChatMessage(role=item.role, content=item.content) for item in payload.messages],
            max_tokens=payload.max_tokens,
        )
    except ProviderError:
        release_reservation(db, user_id=user.id, reservation_id=reservation.id)
        ai_request.status = "failed"
        ai_request.error_code = "provider_unavailable"
        db.commit()
        raise HTTPException(status_code=502, detail="AI provider request failed; reserved credits were released") from None

    if result.prompt_tokens is None or result.completion_tokens is None:
        ai_request.status = "reconciliation_required"
        ai_request.error_code = "provider_usage_missing"
        ai_request.provider_request_id = result.request_id
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
    db.commit()
    db.refresh(ai_request)

    return ChatCompletionResponse(
        request_id=ai_request.id,
        provider=payload.provider,
        model=payload.model,
        content=result.content,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        credits_charged=actual_charge,
        credits_refunded=reservation.reserved_amount - actual_charge,
        balance=get_balance(db, user.id),
    )
