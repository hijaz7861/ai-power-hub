from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.api.auth import require_admin
from backend.app.core.database import get_db
from backend.app.models import PaymentWebhookEvent, SupplierOffer, User
from backend.app.schemas import (
    SupplierOfferCreate,
    SupplierOfferResponse,
    SupplierOfferQuoteRequest,
    SupplierOfferQuoteResponse,
    AdminCreditGrantRequest,
    AdminCreditGrantResponse,
    PaymentWebhookEventResponse,
)
from backend.app.services.pricing import PricingInputs, calculate_retail_price
from backend.app.services.credits import grant_credits

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
