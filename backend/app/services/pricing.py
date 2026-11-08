"""Deterministic, integer-safe retail pricing for AI Power Hub.

All money values are integer minor units (for PKR, paisa). Rates are basis
points: 100 = 1%. No floating-point arithmetic is used for money.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR


@dataclass(frozen=True)
class PricingInputs:
    provider_cost: int
    contributor_payout: int = 0
    infrastructure_cost: int = 0
    support_cost: int = 0
    target_margin_bps: int = 1500
    payment_fee_bps: int = 0
    tax_bps: int = 0


@dataclass(frozen=True)
class PriceQuote:
    total_cost: int
    retail_price: int
    provider_cost: int
    contributor_payout: int
    infrastructure_cost: int
    support_cost: int
    payment_fee: int
    tax: int
    projected_profit: int
    projected_margin_bps: int


def _ceil_money(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_CEILING))


def calculate_retail_price(inputs: PricingInputs) -> PriceQuote:
    """Calculate a retail price that covers costs, fees, tax and target margin.

    The target margin, payment fee and tax are all calculated against retail
    revenue. Costs and the resulting price are integer minor currency units.
    """
    costs = (
        inputs.provider_cost,
        inputs.contributor_payout,
        inputs.infrastructure_cost,
        inputs.support_cost,
    )
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in costs):
        raise ValueError("all cost values must be non-negative integers")
    rates = (inputs.target_margin_bps, inputs.payment_fee_bps, inputs.tax_bps)
    if any(isinstance(rate, bool) or not isinstance(rate, int) or rate < 0 or rate > 10_000 for rate in rates):
        raise ValueError("rates must be integer basis points between 0 and 10000")
    retained_bps = 10_000 - sum(rates)
    if retained_bps <= 0:
        raise ValueError("target margin, payment fee and tax must total less than 10000 bps")

    total_cost = sum(costs)
    if total_cost == 0:
        raise ValueError("at least one cost component must be greater than zero")

    retail_price = _ceil_money(
        Decimal(total_cost) * Decimal(10_000) / Decimal(retained_bps)
    )
    # Fee/tax rounding can consume a minor unit. Raise the price until the
    # realised contribution margin (after those round-ups) meets the target.
    while True:
        payment_fee = _ceil_money(Decimal(retail_price * inputs.payment_fee_bps) / Decimal(10_000))
        tax = _ceil_money(Decimal(retail_price * inputs.tax_bps) / Decimal(10_000))
        projected_profit = retail_price - total_cost - payment_fee - tax
        required_profit = _ceil_money(
            Decimal(retail_price * inputs.target_margin_bps) / Decimal(10_000)
        )
        if projected_profit >= required_profit:
            break
        retail_price += 1
    margin_bps = int(
        (Decimal(projected_profit) * Decimal(10_000) / Decimal(retail_price))
        .quantize(Decimal("1"), rounding=ROUND_FLOOR)
    )
    return PriceQuote(
        total_cost=total_cost,
        retail_price=retail_price,
        provider_cost=inputs.provider_cost,
        contributor_payout=inputs.contributor_payout,
        infrastructure_cost=inputs.infrastructure_cost,
        support_cost=inputs.support_cost,
        payment_fee=payment_fee,
        tax=tax,
        projected_profit=projected_profit,
        projected_margin_bps=margin_bps,
    )
