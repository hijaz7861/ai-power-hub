import asyncio
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from backend.app.services.safepay import SafepayClient, SafepayError


def test_safepay_checkout_creates_tracker_and_short_lived_token():
    seen = []

    async def handler(request):
        seen.append(request)
        if request.url.path == "/order/payments/v3/":
            return httpx.Response(200, json={"data": {"tracker": {"token": "track_test_001"}}})
        if request.url.path == "/client/passport/v1/token":
            return httpx.Response(200, json={"data": "tbt_test_token"})
        return httpx.Response(404)

    client = SafepayClient(
        api_key="test-public-api-key",
        secret_key="test-secret-key",
        environment="sandbox",
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(client.create_checkout(
        amount_minor_units=10000,
        currency="PKR",
        order_reference="order-test-001",
        public_app_url="https://app.example.test",
    ))
    assert result.tracker == "track_test_001"
    parsed = urlparse(result.checkout_url)
    query = parse_qs(parsed.query)
    assert parsed.scheme == "https"
    assert parsed.netloc == "sandbox.api.getsafepay.com"
    assert query["tracker"] == ["track_test_001"]
    assert query["tbt"] == ["tbt_test_token"]
    assert query["environment"] == ["sandbox"]
    assert query["redirect_url"] == ["https://app.example.test/payments/return?reference=order-test-001"]
    assert query["cancel_url"] == ["https://app.example.test/payments/cancel?reference=order-test-001"]
    setup = next(request for request in seen if request.url.path == "/order/payments/v3/")
    assert setup.headers["x-sfpy-merchant-secret"] == "test-secret-key"
    assert b'"amount":10000' in setup.content
    assert b'"order_id":"order-test-001"' in setup.content


def test_safepay_checkout_rejects_non_https_redirect_url():
    client = SafepayClient(api_key="key", secret_key="secret")
    with pytest.raises(ValueError, match="HTTPS"):
        asyncio.run(client.create_checkout(
            amount_minor_units=10000,
            currency="PKR",
            order_reference="order-test-002",
            public_app_url="http://localhost:3000",
        ))


def test_safepay_adapter_sanitises_http_errors():
    async def handler(request):
        return httpx.Response(401, json={"error": "secret merchant detail"})

    client = SafepayClient(
        api_key="test-key",
        secret_key="test-secret",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(SafepayError, match="HTTP 401") as error:
        asyncio.run(client.create_checkout(
            amount_minor_units=10000,
            currency="PKR",
            order_reference="order-test-003",
            public_app_url="https://app.example.test",
        ))
    assert "secret merchant detail" not in str(error.value)
    assert "test-secret" not in str(error.value)
