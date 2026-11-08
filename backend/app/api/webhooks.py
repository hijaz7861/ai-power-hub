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
from backend.app.models import PaymentWebhookEvent

router = APIRouter(prefix="/api/v1/webhooks", tags=["payment webhooks"])
MAX_WEBHOOK_BYTES = 1024 * 1024
SIGNATURE_PATTERN = re.compile(r"^[0-9a-fA-F]{128}$")


@router.post("/safepay", status_code=status.HTTP_202_ACCEPTED)
async def receive_safepay_webhook(
    request: Request,
    signature: str | None = Header(default=None, alias="X-SFPY-SIGNATURE"),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    secret = get_settings().safepay_webhook_secret
    if not secret:
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

    amount = data.get("amount")
    if amount is None and event_type == "payment.refunded":
        amount = data.get("refund_amount")
    if amount is not None and (isinstance(amount, bool) or not isinstance(amount, int) or amount < 0):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid payment amount")

    currency = data.get("currency")
    if currency is not None and (
        not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha()
    ):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid currency")
    currency = currency.upper() if currency else None

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
        processing_status="received",
    )
    db.add(record)
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
