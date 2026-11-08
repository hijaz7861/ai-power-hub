import pytest

from backend.app.services.pricing import PricingInputs, calculate_retail_price


def test_price_covers_all_costs_and_target_margin():
    quote = calculate_retail_price(PricingInputs(
        provider_cost=5000,
        contributor_payout=1000,
        infrastructure_cost=500,
        support_cost=500,
        target_margin_bps=2000,
        payment_fee_bps=200,
        tax_bps=0,
    ))
    assert quote.total_cost == 7000
    assert quote.retail_price == 8975
    assert quote.payment_fee == 180
    assert quote.projected_profit == 1795
    assert quote.projected_margin_bps >= 2000


def test_zero_fee_and_zero_margin_is_cost_price():
    quote = calculate_retail_price(PricingInputs(provider_cost=100))
    assert quote.retail_price == 100
    assert quote.projected_profit == 0


@pytest.mark.parametrize("value", [-1, 1.5, True])
def test_costs_must_be_non_negative_integers(value):
    with pytest.raises(ValueError):
        calculate_retail_price(PricingInputs(provider_cost=value))


@pytest.mark.parametrize("rates", [(10000, 0, 0), (5000, 3000, 2001)])
def test_revenue_allocations_must_leave_positive_revenue(rates):
    with pytest.raises(ValueError):
        calculate_retail_price(PricingInputs(
            provider_cost=100,
            target_margin_bps=rates[0],
            payment_fee_bps=rates[1],
            tax_bps=rates[2],
        ))


def test_all_zero_costs_are_rejected():
    with pytest.raises(ValueError):
        calculate_retail_price(PricingInputs(provider_cost=0))
