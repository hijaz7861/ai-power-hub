from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.core.rate_limit import RateLimitMiddleware


def test_login_route_returns_429_after_ten_requests_and_sets_retry_after():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.post("/api/v1/auth/login")
    def login():
        return {"ok": True}

    with TestClient(app) as client:
        for _ in range(10):
            assert client.post("/api/v1/auth/login").status_code == 200
        limited = client.post("/api/v1/auth/login")
        assert limited.status_code == 429
        assert int(limited.headers["retry-after"]) > 0
        assert limited.headers["cache-control"] == "no-store"


def test_unlisted_health_route_is_not_rate_limited():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    with TestClient(app) as client:
        for _ in range(20):
            assert client.get("/health").status_code == 200


class _RedisLimitHit:
    async def eval(self, script, key_count, key, window_ms):
        return 31, window_ms


class _UnavailableRedis:
    async def eval(self, *args):
        raise ConnectionError("Redis is unavailable")


def _rate_limited_app():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.post("/api/v1/chat/completions")
    def chat():
        return {"ok": True}

    return app


def test_redis_rate_limit_backend_enforces_distributed_limit():
    from types import SimpleNamespace

    app = _rate_limited_app()
    app.state.rate_limit_redis = _RedisLimitHit()
    app.state.settings = SimpleNamespace(app_env="production")
    with TestClient(app) as client:
        response = client.post("/api/v1/chat/completions")
    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"


def test_production_rate_limit_fails_closed_when_redis_is_unavailable():
    from types import SimpleNamespace

    app = _rate_limited_app()
    app.state.rate_limit_redis = _UnavailableRedis()
    app.state.settings = SimpleNamespace(app_env="production")
    with TestClient(app) as client:
        response = client.post("/api/v1/chat/completions")
    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"
