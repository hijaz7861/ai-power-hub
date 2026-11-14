from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=12, max_length=128)

class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=1, max_length=128)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    is_active: bool
    role: str

class CreditBalanceResponse(BaseModel):
    balance: int
    unit: str = "credits"


from typing import Literal


class SupplierOfferCreate(BaseModel):
    supplier_name: str = Field(min_length=2, max_length=160)
    supplier_code: str = Field(min_length=2, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    service_type: Literal["ai_api", "gpu_compute", "cloud", "storage", "web_data"]
    provider_code: str = Field(min_length=2, max_length=40, pattern=r"^[a-zA-Z0-9_-]+$")
    model_code: str | None = Field(default=None, max_length=120)
    billing_unit: Literal["per_1k_input_tokens", "per_1k_output_tokens", "per_request", "per_gpu_second", "per_gb_month", "per_1k_results"]
    currency: Literal["PKR", "USD"] = "PKR"
    wholesale_cost_minor_units: int = Field(gt=0, le=10**12)
    contract_status: Literal["pending", "verified", "suspended"] = "pending"
    is_active: bool = False


class SupplierOfferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    supplier_name: str
    supplier_code: str
    service_type: str
    provider_code: str
    model_code: str | None
    billing_unit: str
    currency: str
    wholesale_cost_minor_units: int
    contract_status: str
    is_active: bool
    created_by: int


class SupplierOfferQuoteRequest(BaseModel):
    contributor_payout_minor_units: int = Field(default=0, ge=0, le=10**12)
    infrastructure_cost_minor_units: int = Field(default=0, ge=0, le=10**12)
    support_cost_minor_units: int = Field(default=0, ge=0, le=10**12)
    target_margin_bps: int = Field(default=1500, ge=0, le=9999)
    payment_fee_bps: int = Field(default=0, ge=0, le=9999)
    tax_bps: int = Field(default=0, ge=0, le=9999)


class SupplierOfferQuoteResponse(BaseModel):
    supplier_offer_id: int
    currency: str
    billing_unit: str
    wholesale_cost_minor_units: int
    total_cost_minor_units: int
    retail_price_minor_units: int
    payment_fee_minor_units: int
    tax_minor_units: int
    projected_profit_minor_units: int
    projected_margin_bps: int


class AdminCreditGrantRequest(BaseModel):
    user_id: int = Field(gt=0)
    amount: int = Field(gt=0, le=10**9)
    idempotency_key: str = Field(min_length=8, max_length=128)
    reason: str = Field(min_length=4, max_length=255)


class AdminCreditGrantResponse(BaseModel):
    user_id: int
    granted_credits: int
    balance: int
    entry_type: str = "grant"


class CreditLedgerEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    amount: int
    entry_type: str
    description: str
    created_at: datetime


class PaymentWebhookEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_token: str
    event_type: str
    tracker_token: str | None
    order_reference: str | None
    provider_state: str | None
    payment_order_id: int | None
    amount_minor_units: int | None
    currency: str | None
    payload_sha256: str
    processing_status: str
    received_at: datetime
    processed_at: datetime | None


class PaymentTopupCreate(BaseModel):
    amount_pkr: int = Field(ge=100, le=100000)
    idempotency_key: str = Field(min_length=8, max_length=128)


class PaymentTopupResponse(BaseModel):
    reference: str
    amount_pkr: int
    amount_minor_units: int
    credits_to_receive: int
    currency: str
    status: str
    checkout_url: str | None = None


class PaymentOrderStatusResponse(BaseModel):
    reference: str
    amount_pkr: int
    amount_minor_units: int
    currency: str
    status: str
    created_at: datetime
    paid_at: datetime | None


class ChatMessageInput(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=32768)


class ChatCompletionRequest(BaseModel):
    provider: Literal["openai", "mistral"]
    model: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9._:-]+$")
    messages: list[ChatMessageInput] = Field(min_length=1, max_length=32)
    max_tokens: int = Field(default=1024, ge=1, le=2048)
    idempotency_key: str = Field(min_length=8, max_length=128)
    conversation_id: int | None = Field(default=None, gt=0)


class ChatCompletionResponse(BaseModel):
    request_id: int
    conversation_id: int | None
    provider: str
    model: str
    content: str
    prompt_tokens: int
    completion_tokens: int
    credits_charged: int
    credits_refunded: int
    balance: int


class AIRequestAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    provider: str
    model: str
    status: str
    reservation_id: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    credits_charged: int
    input_rate_minor_units: int
    output_rate_minor_units: int
    target_margin_bps: int
    error_code: str | None
    reconciliation_evidence: str | None
    reconciled_by_user_id: int | None
    created_at: datetime
    completed_at: datetime | None


class AIRequestReconcileRequest(BaseModel):
    prompt_tokens: int = Field(ge=0, le=10**9)
    completion_tokens: int = Field(ge=0, le=10**9)
    evidence_reference: str = Field(min_length=8, max_length=255)


class AIRequestReleaseRequest(BaseModel):
    evidence_reference: str = Field(min_length=8, max_length=255)



class ConversationSummaryResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    content: str
    provider: str | None
    model: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    credits_charged: int
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    conversation: ConversationSummaryResponse
    messages: list[ConversationMessageResponse]


class PaymentOrderAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reference: str
    user_id: int
    amount_minor_units: int
    refunded_amount_minor_units: int
    currency: str
    status: str
    provider_tracker: str | None
    created_at: datetime
    paid_at: datetime | None


class AIRequestRecoveryRequest(BaseModel):
    evidence_reference: str = Field(min_length=8, max_length=255)


class CloseAccountRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class CloseAccountResponse(BaseModel):
    status: str
    message: str
