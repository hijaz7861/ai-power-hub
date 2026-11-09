from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.api.auth import require_admin
from backend.app.core.database import get_db
from backend.app.models import AIRequest, ConversationMessage, CreditReservation, PaymentOrder, PaymentWebhookEvent, SupplierOffer, User
from backend.app.schemas import (
    SupplierOfferCreate,
    SupplierOfferResponse,
    SupplierOfferQuoteRequest,
    SupplierOfferQuoteResponse,
    AdminCreditGrantRequest,
    AdminCreditGrantResponse,
    PaymentWebhookEventResponse,
    PaymentOrderAdminResponse,
    AIRequestAdminResponse,
    AIRequestReconcileRequest,
    AIRequestReleaseRequest,
)
from backend.app.services.pricing import PricingInputs, calculate_retail_price
from backend.app.services.credits import grant_credits, release_reservation, settle_reservation
from backend.app.services.pricing import calculate_token_retail_charge

router = APIRouter(prefix="/api/v1/admin", tags=["administration"])


@router.get("/supplier-offers", response_model=list[SupplierOfferResponse])
def list_supplier_offers(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[SupplierOffer]:
    return list(db.scalars(select(SupplierOffer).order_by(SupplierOffer.id.desc())).all())


@router.post(
    "/supplier-offers",
    response_model=SupplierOfferResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_supplier_offer(
    payload: SupplierOfferCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SupplierOffer:
    if payload.is_active and payload.contract_status != "verified":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="An offer cannot be activated before its commercial contract is verified",
        )
    offer = SupplierOffer(**payload.model_dump(), created_by=admin.id)
    db.add(offer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A supplier offer with this identity already exists",
        ) from None
    db.refresh(offer)
    return offer


@router.post(
    "/supplier-offers/{offer_id}/quote",
    response_model=SupplierOfferQuoteResponse,
)
def quote_supplier_offer(
    offer_id: int,
    payload: SupplierOfferQuoteRequest,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SupplierOfferQuoteResponse:
    offer = db.get(SupplierOffer, offer_id)
    if offer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier offer not found")
    try:
        quote = calculate_retail_price(PricingInputs(
            provider_cost=offer.wholesale_cost_minor_units,
            contributor_payout=payload.contributor_payout_minor_units,
            infrastructure_cost=payload.infrastructure_cost_minor_units,
            support_cost=payload.support_cost_minor_units,
            target_margin_bps=payload.target_margin_bps,
            payment_fee_bps=payload.payment_fee_bps,
            tax_bps=payload.tax_bps,
        ))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from None
    return SupplierOfferQuoteResponse(
        supplier_offer_id=offer.id,
        currency=offer.currency,
        billing_unit=offer.billing_unit,
        wholesale_cost_minor_units=quote.provider_cost,
        total_cost_minor_units=quote.total_cost,
        retail_price_minor_units=quote.retail_price,
        payment_fee_minor_units=quote.payment_fee,
        tax_minor_units=quote.tax,
        projected_profit_minor_units=quote.projected_profit,
        projected_margin_bps=quote.projected_margin_bps,
    )


@router.post(
    "/credits/grant",
    response_model=AdminCreditGrantResponse,
)
def admin_grant_credits(
    payload: AdminCreditGrantRequest,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminCreditGrantResponse:
    target = db.get(User, payload.user_id)
    if target is None or not target.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active user not found")
    try:
        balance = grant_credits(
            db,
            user_id=payload.user_id,
            amount=payload.amount,
            idempotency_key=payload.idempotency_key,
            description=payload.reason,
            actor_user_id=_.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    return AdminCreditGrantResponse(
        user_id=payload.user_id,
        granted_credits=payload.amount,
        balance=balance,
    )


@router.get("/payment-events", response_model=list[PaymentWebhookEventResponse])
def list_payment_events(
    limit: int = 50,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[PaymentWebhookEvent]:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="limit must be between 1 and 100")
    return list(db.scalars(
        select(PaymentWebhookEvent).order_by(PaymentWebhookEvent.id.desc()).limit(limit)
    ).all())



@router.get("/payment-orders", response_model=list[PaymentOrderAdminResponse])
def list_payment_orders(
    limit: int = 50,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[PaymentOrder]:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    return list(db.scalars(
        select(PaymentOrder).order_by(PaymentOrder.id.desc()).limit(limit)
    ).all())


@router.get("/ai-requests", response_model=list[AIRequestAdminResponse])
def list_ai_requests(
    request_status: str = "reconciliation_required",
    limit: int = 50,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AIRequest]:
    allowed = {"processing", "completed", "failed", "reconciliation_required"}
    if request_status not in allowed:
        raise HTTPException(status_code=422, detail="Unsupported AI request status")
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    return list(db.scalars(
        select(AIRequest)
        .where(AIRequest.status == request_status)
        .order_by(AIRequest.id.desc())
        .limit(limit)
    ).all())


@router.post(
    "/ai-requests/{request_id}/reconcile",
    response_model=AIRequestAdminResponse,
)
def reconcile_ai_request(
    request_id: int,
    payload: AIRequestReconcileRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AIRequest:
    ai_request = db.scalar(
        select(AIRequest).where(AIRequest.id == request_id).with_for_update()
    )
    if ai_request is None:
        raise HTTPException(status_code=404, detail="AI request not found")
    if ai_request.status != "reconciliation_required" or ai_request.reservation_id is None:
        raise HTTPException(status_code=409, detail="AI request is not awaiting reconciliation")
    if ai_request.prompt_tokens is not None and ai_request.prompt_tokens != payload.prompt_tokens:
        raise HTTPException(status_code=409, detail="Prompt token count conflicts with provider record")
    if ai_request.completion_tokens is not None and ai_request.completion_tokens != payload.completion_tokens:
        raise HTTPException(status_code=409, detail="Completion token count conflicts with provider record")

    reservation = db.get(CreditReservation, ai_request.reservation_id)
    if reservation is None or reservation.status != "reserved":
        raise HTTPException(status_code=409, detail="Credit reservation is not available for settlement")
    try:
        actual_charge = calculate_token_retail_charge(
            input_rate_minor_units=ai_request.input_rate_minor_units,
            output_rate_minor_units=ai_request.output_rate_minor_units,
            prompt_tokens=payload.prompt_tokens,
            completion_tokens=payload.completion_tokens,
            target_margin_bps=ai_request.target_margin_bps,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    if actual_charge > reservation.reserved_amount:
        raise HTTPException(
            status_code=422,
            detail="Verified usage exceeds the original authorization; obtain a new customer authorization before charging",
        )

    try:
        settle_reservation(
            db,
            user_id=ai_request.user_id,
            reservation_id=reservation.id,
            actual_amount=actual_charge,
            actor_user_id=admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None

    ai_request.prompt_tokens = payload.prompt_tokens
    ai_request.completion_tokens = payload.completion_tokens
    ai_request.credits_charged = actual_charge
    ai_request.status = "completed"
    ai_request.reconciliation_evidence = payload.evidence_reference.strip()
    ai_request.reconciled_by_user_id = admin.id
    ai_request.completed_at = datetime.now(timezone.utc)
    assistant_message = db.scalar(select(ConversationMessage).where(
        ConversationMessage.request_id == ai_request.id,
        ConversationMessage.role == "assistant",
    ))
    if assistant_message is not None:
        assistant_message.prompt_tokens = payload.prompt_tokens
        assistant_message.completion_tokens = payload.completion_tokens
        assistant_message.credits_charged = actual_charge
    db.commit()
    db.refresh(ai_request)
    return ai_request



@router.post(
    "/ai-requests/{request_id}/release",
    response_model=AIRequestAdminResponse,
)
def release_ai_request_hold(
    request_id: int,
    payload: AIRequestReleaseRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AIRequest:
    ai_request = db.scalar(
        select(AIRequest).where(AIRequest.id == request_id).with_for_update()
    )
    if ai_request is None:
        raise HTTPException(status_code=404, detail="AI request not found")
    if ai_request.status != "reconciliation_required" or ai_request.reservation_id is None:
        raise HTTPException(status_code=409, detail="AI request is not awaiting reconciliation")
    reservation = db.get(CreditReservation, ai_request.reservation_id)
    if reservation is None or reservation.status != "reserved":
        raise HTTPException(status_code=409, detail="Credit reservation is not available for release")
    try:
        release_reservation(
            db,
            user_id=ai_request.user_id,
            reservation_id=reservation.id,
            actor_user_id=admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None

    ai_request.status = "failed"
    ai_request.error_code = "admin_released_hold"
    ai_request.reconciliation_evidence = payload.evidence_reference.strip()
    ai_request.reconciled_by_user_id = admin.id
    ai_request.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ai_request)
    return ai_request
