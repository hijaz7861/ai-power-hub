import asyncio

import httpx
import pytest

from backend.app.services.provider_adapters import (
    ChatMessage,
    OpenAICompatibleChatAdapter,
    ProviderError,
)


def test_openai_compatible_adapter_parses_response_and_usage():
    seen = {}

    async def handler(request):
        seen["authorization"] = request.headers["authorization"]
        seen["payload"] = await request.aread()
        return httpx.Response(200, json={
            "id": "req_test_123",
            "choices": [{"message": {"role": "assistant", "content": "Hello from the provider"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 5},
        })

    adapter = OpenAICompatibleChatAdapter(
        provider="test-provider",
        base_url="https://api.example.test/v1",
        api_key="test-secret",
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(adapter.complete(
        model="test-model",
        messages=[ChatMessage(role="user", content="Hello")],
        max_tokens=50,
    ))
    assert result.content == "Hello from the provider"
    assert result.request_id == "req_test_123"
    assert result.prompt_tokens == 12
    assert result.completion_tokens == 5
    assert seen["authorization"] == "Bearer test-secret"
    assert b'"model":"test-model"' in seen["payload"]


def test_provider_http_error_is_sanitised():
    async def handler(request):
        return httpx.Response(401, json={"error": "secret provider diagnostic"})

    adapter = OpenAICompatibleChatAdapter(
        provider="test-provider",
        base_url="https://api.example.test/v1",
        api_key="test-secret",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderError, match="HTTP 401") as error:
        asyncio.run(adapter.complete(model="test-model", messages=[ChatMessage("user", "Hi")]))
    assert "secret provider diagnostic" not in str(error.value)
    assert "test-secret" not in str(error.value)


def test_provider_malformed_response_is_rejected():
    async def handler(request):
        return httpx.Response(200, json={"choices": []})

    adapter = OpenAICompatibleChatAdapter(
        provider="test-provider",
        base_url="https://api.example.test/v1",
        api_key="test-secret",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderError, match="unsupported response shape"):
        asyncio.run(adapter.complete(model="test-model", messages=[ChatMessage("user", "Hi")]))


@pytest.mark.parametrize("base_url", ["http://api.example.test/v1", ""])
def test_adapter_requires_https(base_url):
    with pytest.raises(ValueError, match="HTTPS"):
        OpenAICompatibleChatAdapter(
            provider="test-provider",
            base_url=base_url,
            api_key="test-secret",
        )


def test_invalid_request_is_rejected_before_network_call():
    adapter = OpenAICompatibleChatAdapter(
        provider="test-provider",
        base_url="https://api.example.test/v1",
        api_key="test-secret",
        transport=httpx.MockTransport(lambda request: httpx.Response(500)),
    )
    with pytest.raises(ValueError, match="max_tokens"):
        asyncio.run(adapter.complete(
            model="test-model",
            messages=[ChatMessage("user", "Hi")],
            max_tokens=0,
        ))


def test_provider_negative_token_usage_is_rejected():
    async def handler(request):
        return httpx.Response(200, json={
            "choices": [{"message": {"role": "assistant", "content": "Hi"}}],
            "usage": {"prompt_tokens": -1, "completion_tokens": 2},
        })

    adapter = OpenAICompatibleChatAdapter(
        provider="test-provider",
        base_url="https://api.example.test/v1",
        api_key="test-secret",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderError, match="unsupported response shape"):
        asyncio.run(adapter.complete(model="test-model", messages=[ChatMessage("user", "Hi")]))
