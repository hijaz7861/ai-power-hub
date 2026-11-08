from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.api.auth import get_current_user
from backend.app.core.config import get_settings
from backend.app.core.database import get_db
from backend.app.models import PaymentOrder, User
from backend.app.schemas import PaymentOrderStatusResponse, PaymentTopupCreate, PaymentTopupResponse
from backend.app.services.safepay import SafepayClient, SafepayError

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


def _client() -> SafepayClient:
    settings = get_settings()
    if not settings.safepay_api_key or not settings.safepay_secret_key or not settings.safepay_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Safepay sandbox credentials and webhook secret are not configured",
        )
    if not settings.public_app_url.startswith("https://"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PUBLIC_APP_URL must be configured as a public HTTPS URL",
        )
    try:
        return SafepayClient(
            api_key=settings.safepay_api_key,
            secret_key=settings.safepay_secret_key,
            environment=settings.safepay_environment,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Safepay configuration is invalid") from None


def _response(order: PaymentOrder, checkout_url: str | None) -> PaymentTopupResponse:
    return PaymentTopupResponse(
        reference=order.reference,
        amount_pkr=order.amount_minor_units // 100,
        amount_minor_units=order.amount_minor_units,
        credits_to_receive=order.amount_minor_units,
        currency=order.currency,
        status=order.status,
        checkout_url=checkout_url,
    )


@router.post("/topups", response_model=PaymentTopupResponse, status_code=status.HTTP_201_CREATED)
async def create_credit_topup(
    payload: PaymentTopupCreate,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentTopupResponse:
    settings = get_settings()
    key = payload.idempotency_key.strip()
    if len(key) < 8:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="idempotency_key is invalid")

    order = db.scalar(
        select(PaymentOrder).where(
            PaymentOrder.user_id == user.id,
            PaymentOrder.idempotency_key == key,
        )
    )
    if order is not None:
        if order.amount_minor_units != payload.amount_pkr * 100:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Idempotency key was used with a different amount")
        response.status_code = status.HTTP_200_OK
        if order.status == "succeeded":
            return _response(order, None)
        if order.status != "pending":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This payment order cannot be retried")
        client = _client()
        if order.provider_tracker:
            try:
                checkout_url = await client.create_checkout_url(
                    tracker=order.provider_tracker,
                    order_reference=order.reference,
                    public_app_url=settings.public_app_url,
                )
            except SafepayError as exc:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from None
            return _response(order, checkout_url)
    else:
        order = PaymentOrder(
            reference=uuid4().hex,
            user_id=user.id,
            amount_minor_units=payload.amount_pkr * 100,
            currency="PKR",
            provider="safepay",
            status="pending",
            idempotency_key=key,
        )
        db.add(order)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            order = db.scalar(
                select(PaymentOrder).where(
                    PaymentOrder.user_id == user.id,
                    PaymentOrder.idempotency_key == key,
                )
            )
            if order is None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment order conflict") from None
            response.status_code = status.HTTP_200_OK
            if order.amount_minor_units != payload.amount_pkr * 100:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Idempotency key was used with a different amount")
            if order.status != "pending" or not order.provider_tracker:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment order is not ready for retry")
            try:
                checkout_url = await client.create_checkout_url(
                    tracker=order.provider_tracker,
                    order_reference=order.reference,
                    public_app_url=settings.public_app_url,
                )
            except SafepayError as exc:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from None
            return _response(order, checkout_url)
        db.refresh(order)

    client = _client()
    try:
        checkout = await client.create_checkout(
            amount_minor_units=order.amount_minor_units,
            currency=order.currency,
            order_reference=order.reference,
            public_app_url=settings.public_app_url,
        )
    except SafepayError as exc:
        order.status = "initiation_failed"
        db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from None

    order.provider_tracker = checkout.tracker
    db.commit()
    db.refresh(order)
    return _response(order, checkout.checkout_url)


@router.get("/topups/{reference}", response_model=PaymentOrderStatusResponse)
def get_credit_topup(
    reference: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentOrderStatusResponse:
    order = db.scalar(
        select(PaymentOrder).where(
            PaymentOrder.reference == reference,
            PaymentOrder.user_id == user.id,
        )
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment order not found")
    return PaymentOrderStatusResponse(
        reference=order.reference,
        amount_pkr=order.amount_minor_units // 100,
        amount_minor_units=order.amount_minor_units,
        currency=order.currency,
        status=order.status,
        created_at=order.created_at,
        paid_at=order.paid_at,
    )
