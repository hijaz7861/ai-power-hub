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
