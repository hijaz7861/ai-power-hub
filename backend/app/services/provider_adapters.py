"""Safe async adapter for OpenAI-compatible chat-completions APIs.

The adapter is deliberately provider-agnostic: a provider is enabled only when
its base URL, server-side API key and permitted model are configured by the
application. It does not perform retries or billing; orchestration must make
those decisions explicitly to avoid duplicate billable requests.
"""
from dataclasses import dataclass
from typing import Any, Sequence

import httpx


class ProviderError(RuntimeError):
    """Sanitised provider failure safe to return to an API caller."""


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    model: str
    content: str
    request_id: str | None
    prompt_tokens: int | None
    completion_tokens: int | None


class OpenAICompatibleChatAdapter:
    ALLOWED_ROLES = frozenset({"system", "user", "assistant"})

    def __init__(
        self,
        *,
        provider: str,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not provider.strip():
            raise ValueError("provider is required")
        if not base_url.startswith("https://"):
            raise ValueError("provider base_url must use HTTPS")
        if not api_key.strip():
            raise ValueError("provider API key is required")
        if not 1 <= timeout_seconds <= 120:
            raise ValueError("timeout_seconds must be between 1 and 120")
        self.provider = provider
        self.base_url = base_url.rstrip("/") + "/"
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def complete(
        self,
        *,
        model: str,
        messages: Sequence[ChatMessage],
        max_tokens: int = 1024,
    ) -> ProviderResult:
        if not model.strip():
            raise ValueError("model is required")
        if not 1 <= max_tokens <= 8192:
            raise ValueError("max_tokens must be between 1 and 8192")
        if not messages:
            raise ValueError("at least one message is required")
        if any(message.role not in self.ALLOWED_ROLES or not isinstance(message.content, str)
               for message in messages):
            raise ValueError("messages contain an unsupported role or content type")

        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": item.role, "content": item.content} for item in messages],
            "max_tokens": max_tokens,
        }
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    "chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"{self.provider} returned HTTP {exc.response.status_code}"
            ) from None
        except (httpx.TimeoutException, httpx.TransportError):
            raise ProviderError(f"{self.provider} is temporarily unavailable") from None
        except ValueError:
            raise ProviderError(f"{self.provider} returned an invalid response") from None

        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
            if not isinstance(content, str):
                raise TypeError
            usage = data.get("usage") or {}
            prompt_tokens = usage.get("prompt_tokens")
            completion_tokens = usage.get("completion_tokens")
            if prompt_tokens is not None and (isinstance(prompt_tokens, bool) or not isinstance(prompt_tokens, int) or prompt_tokens < 0):
                raise TypeError
            if completion_tokens is not None and (isinstance(completion_tokens, bool) or not isinstance(completion_tokens, int) or completion_tokens < 0):
                raise TypeError
            request_id = data.get("id")
            if request_id is not None and not isinstance(request_id, str):
                raise TypeError
        except (KeyError, IndexError, TypeError):
            raise ProviderError(f"{self.provider} returned an unsupported response shape") from None

        return ProviderResult(
            provider=self.provider,
            model=model,
            content=content,
            request_id=request_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
