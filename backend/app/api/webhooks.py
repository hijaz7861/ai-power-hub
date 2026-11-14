import hashlib
import hmac
import json
import re

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.database import get_db
from backend.app.models import CreditAccount, CreditLedger, PaymentOrder, PaymentWebhookEvent
from backend.app.models import utc_now

router = APIRouter(prefix="/api/v1/webhooks", tags=["payment webhooks"])
MAX_WEBHOOK_BYTES = 1024 * 1024
SIGNATURE_PATTERN = re.compile(r"^[0-9a-fA-F]{128}$")


@router.post("/safepay", status_code=status.HTTP_202_ACCEPTED)
async def receive_safepay_webhook(
    request: Request,
    signature: str | None = Header(default=None, alias="X-SFPY-SIGNATURE"),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    settings = get_settings()
    secret = settings.safepay_webhook_secret
    if not secret or not settings.safepay_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Safepay webhook is not configured",
        )

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_WEBHOOK_BYTES:
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Webhook body too large")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Content-Length") from None

    body_buffer = bytearray()
    async for chunk in request.stream():
        if len(body_buffer) + len(chunk) > MAX_WEBHOOK_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Webhook body too large")
        body_buffer.extend(chunk)
    raw_body = bytes(body_buffer)
    if signature is None or not SIGNATURE_PATTERN.fullmatch(signature.strip()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
    if not hmac.compare_digest(expected, signature.strip().lower()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    try:
        event = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook JSON") from None

    if not isinstance(event, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook event must be an object")

    if event.get("merchant_api_key") != settings.safepay_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Webhook merchant mismatch")

    event_token = event.get("token")
    event_type = event.get("type")
    data = event.get("data", {})
    if (
        not isinstance(event_token, str)
        or not event_token.strip()
        or len(event_token) > 128
        or not isinstance(event_type, str)
        or not event_type.strip()
        or len(event_type) > 120
        or not isinstance(data, dict)
    ):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid webhook event shape")

    tracker = data.get("tracker")
    if tracker is not None and (not isinstance(tracker, str) or len(tracker) > 128):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid tracker token")

    amount = data.get("refund_amount") if event_type == "payment.refunded" else data.get("amount")
    if amount is None and event_type == "payment.refunded":
        amount = data.get("amount")
    if amount is not None and (isinstance(amount, bool) or not isinstance(amount, int) or amount < 0):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid payment amount")

    currency = data.get("currency")
    if currency is not None and (
        not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha()
    ):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid currency")
    currency = currency.upper() if currency else None
    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid payment metadata")
    order_reference = metadata.get("order_id")
    if order_reference is not None and (not isinstance(order_reference, str) or len(order_reference) > 64):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid order reference")
    provider_state = data.get("state")
    if provider_state is not None and (not isinstance(provider_state, str) or len(provider_state) > 60):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid provider state")

    payload_hash = hashlib.sha256(raw_body).hexdigest()
    existing = db.scalar(
        select(PaymentWebhookEvent).where(PaymentWebhookEvent.event_token == event_token)
    )
    if existing is not None:
        if existing.payload_sha256 != payload_hash:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Webhook event token collision")
        return {"accepted": True, "duplicate": True}

    record = PaymentWebhookEvent(
        event_token=event_token,
        event_type=event_type,
        tracker_token=tracker,
        amount_minor_units=amount,
        currency=currency,
        payload_sha256=payload_hash,
        order_reference=order_reference,
        provider_state=provider_state,
        processing_status="received",
    )
    db.add(record)

    matched_order = None
    if event_type in {"payment.succeeded", "payment.failed", "payment.refunded"}:
        if tracker:
            matched_order = db.scalar(
                select(PaymentOrder).where(PaymentOrder.provider_tracker == tracker).with_for_update()
            )
        if matched_order is None and order_reference:
            matched_order = db.scalar(
                select(PaymentOrder).where(PaymentOrder.reference == order_reference).with_for_update()
            )
        if matched_order is not None:
            record.payment_order_id = matched_order.id
            if event_type == "payment.succeeded":
                tracker_matches = bool(tracker) and matched_order.provider_tracker in (None, tracker)
                amount_matches = amount == matched_order.amount_minor_units
                currency_matches = currency == matched_order.currency
                state_matches = provider_state == "TRACKER_ENDED"
                reference_matches = order_reference in (None, matched_order.reference)
                if not (tracker_matches and amount_matches and currency_matches and state_matches and reference_matches):
                    record.processing_status = "mismatch"
                elif matched_order.paid_at is not None or matched_order.status in {"succeeded", "partially_refunded", "refunded"}:
                    record.processing_status = "duplicate_payment_event"
                else:
                    account = db.scalar(
                        select(CreditAccount)
                        .where(CreditAccount.user_id == matched_order.user_id)
                        .with_for_update()
                    )
                    if account is None:
                        db.rollback()
                        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment account is unavailable")
                    account.balance += matched_order.amount_minor_units
                    db.add(CreditLedger(
                        user_id=matched_order.user_id,
                        amount=matched_order.amount_minor_units,
                        entry_type="payment",
                        idempotency_key="safepay-order:" + matched_order.reference,
                        description="Verified Safepay credit top-up",
                    ))
                    matched_order.provider_tracker = tracker or matched_order.provider_tracker
                    matched_order.status = "succeeded"
                    matched_order.paid_at = utc_now()
                    record.processing_status = "processed"
            elif event_type == "payment.failed":
                record.processing_status = "failed_attempt"
            elif event_type == "payment.refunded":
                # Safepay's payment.refunded payload reports refund_amount in PKR
                # minor units and the tracker state distinguishes partial/full refunds.
                # Require both identifiers and exact currency before touching credits.
                refund_state_valid = provider_state in {"TRACKER_PARTIAL_REFUND", "TRACKER_REFUNDED"}
                identifiers_match = (
                    bool(tracker)
                    and tracker == matched_order.provider_tracker
                    and order_reference == matched_order.reference
                )
                amount_valid = amount is not None and amount > 0
                currency_matches = currency == matched_order.currency
                order_is_paid = matched_order.paid_at is not None
                cumulative_refund = matched_order.refunded_amount_minor_units + (amount or 0)
                within_original_payment = cumulative_refund <= matched_order.amount_minor_units
                state_matches_cumulative = (
                    provider_state == "TRACKER_REFUNDED"
                    and cumulative_refund == matched_order.amount_minor_units
                ) or (
                    provider_state == "TRACKER_PARTIAL_REFUND"
                    and cumulative_refund < matched_order.amount_minor_units
                )
                if not (
                    identifiers_match
                    and amount_valid
                    and currency_matches
                    and refund_state_valid
                    and state_matches_cumulative
                    and order_is_paid
                    and within_original_payment
                ):
                    record.processing_status = "refund_review"
                else:
                    account = db.scalar(
                        select(CreditAccount)
                        .where(CreditAccount.user_id == matched_order.user_id)
                        .with_for_update()
                    )
                    if account is None:
                        db.rollback()
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Payment account is unavailable",
                        )
                    # A refund reverses the purchased credits. If the customer
                    # already spent them, the balance can become negative; further
                    # paid usage remains blocked until the balance is replenished.
                    account.balance -= amount
                    matched_order.refunded_amount_minor_units += amount
                    matched_order.status = (
                        "refunded"
                        if matched_order.refunded_amount_minor_units == matched_order.amount_minor_units
                        else "partially_refunded"
                    )
                    db.add(CreditLedger(
                        user_id=matched_order.user_id,
                        amount=-amount,
                        entry_type="refund",
                        idempotency_key="safepay-refund-event:" + event_token,
                        description="Verified Safepay refund credit reversal",
                    ))
                    record.processing_status = "processed_refund"
        else:
            record.processing_status = "unmatched"

    record.processed_at = utc_now()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(PaymentWebhookEvent).where(PaymentWebhookEvent.event_token == event_token)
        )
        if existing is not None and existing.payload_sha256 == payload_hash:
            return {"accepted": True, "duplicate": True}
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Webhook event conflict") from None

    return {"accepted": True, "duplicate": False}
