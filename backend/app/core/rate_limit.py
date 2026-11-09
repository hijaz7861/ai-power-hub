"""Distributed, fail-closed rate limits for sensitive API operations."""

import asyncio
import hashlib
import ipaddress
import time
from collections.abc import Callable

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.app.core.security import decode_access_token

WINDOW_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('PEXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('PTTL', KEYS[1])
return {count, ttl}
"""

# Requests are keyed by the authenticated principal (where available) and the
# direct peer, or by X-Forwarded-For only when that peer is explicitly trusted.
LIMITS: dict[str, tuple[int, int]] = {
    "POST /api/v1/auth/login": (10, 900),
    "POST /api/v1/auth/register": (5, 3600),
    "POST /api/v1/chat/completions": (30, 60),
    "POST /api/v1/payments/topups": (5, 3600),
    "POST /api/v1/account/close": (3, 3600),
}


def _client_ip(request: Request, settings) -> str:
    peer = request.client.host if request.client else "unknown"
    try:
        peer_address = ipaddress.ip_address(peer)
    except ValueError:
        return peer

    trusted_ranges = []
    for item in (getattr(settings, "trusted_proxy_ips", "") or "").split(","):
        item = item.strip()
        if not item:
            continue
        try:
            trusted_ranges.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            continue
    if not any(peer_address in network for network in trusted_ranges):
        return peer

    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    try:
        return str(ipaddress.ip_address(forwarded))
    except ValueError:
        return peer


def _identity(request: Request, settings) -> str:
    peer = _client_ip(request, settings)
    subject = "anonymous"
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        decoded = decode_access_token(authorization[7:].strip())
        if decoded and decoded.isdigit():
            subject = f"user:{decoded}"
    raw = f"{request.method}:{request.url.path}:{peer}:{subject}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed fixed-window limiter; process-local fallback is development-only."""

    def __init__(self, app, clock: Callable[[], float] = time.monotonic):
        super().__init__(app)
        self._clock = clock
        self._memory: dict[str, tuple[float, int]] = {}
        self._lock = asyncio.Lock()

    async def _memory_hit(self, key: str, window_seconds: int) -> tuple[int, int]:
        now = self._clock()
        async with self._lock:
            started, count = self._memory.get(key, (now, 0))
            if now - started >= window_seconds:
                started, count = now, 0
            count += 1
            self._memory[key] = (started, count)
            if len(self._memory) > 10000:
                self._memory = {
                    item_key: item
                    for item_key, item in self._memory.items()
                    if now - item[0] < window_seconds
                }
            retry_after = max(1, int(window_seconds - (now - started)))
            return count, retry_after

    async def dispatch(self, request: Request, call_next) -> Response:
        rule = LIMITS.get(f"{request.method} {request.url.path}")
        if rule is None:
            return await call_next(request)

        limit, window_seconds = rule
        settings = getattr(request.app.state, "settings", None)
        identity = _identity(request, settings)
        key = f"aiph:ratelimit:{identity}"
        redis_client = getattr(request.app.state, "rate_limit_redis", None)

        if redis_client is not None:
            try:
                count, ttl_ms = await redis_client.eval(
                    WINDOW_SCRIPT, 1, key, window_seconds * 1000
                )
                retry_after = max(1, int((int(ttl_ms) + 999) / 1000))
            except Exception:
                if settings is not None and settings.app_env.lower() == "production":
                    return JSONResponse(
                        status_code=503,
                        content={"detail": "Rate-limit service unavailable; retry shortly"},
                        headers={"Retry-After": "5", "Cache-Control": "no-store"},
                    )
                count, retry_after = await self._memory_hit(key, window_seconds)
        else:
            if settings is not None and settings.app_env.lower() == "production":
                return JSONResponse(
                    status_code=503,
                    content={"detail": "Distributed rate limiting is not configured"},
                    headers={"Retry-After": "5", "Cache-Control": "no-store"},
                )
            count, retry_after = await self._memory_hit(key, window_seconds)

        if int(count) > limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests; retry after the rate-limit window"},
                headers={
                    "Retry-After": str(retry_after),
                    "Cache-Control": "no-store",
                },
            )
        response = await call_next(request)
        response.headers.setdefault("Cache-Control", "no-store")
        return response
