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
