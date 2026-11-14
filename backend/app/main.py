from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from backend.app import models  # noqa: F401
from backend.app.api.auth import router as auth_router
from backend.app.api.account import router as account_router
from backend.app.api.chat import router as chat_router
from backend.app.api.admin import router as admin_router
from backend.app.api.credits import router as credits_router
from backend.app.api.health import router as health_router
from backend.app.api.providers import router as providers_router
from backend.app.api.webhooks import router as webhooks_router
from backend.app.api.payments import router as payments_router
from backend.app.core.config import get_settings
from backend.app.core.database import Base, engine
from backend.app.core.rate_limit import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    redis_client = None
    if settings.redis_url:
        redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            await redis_client.ping()
        except Exception:
            await redis_client.aclose()
            redis_client = None
            if settings.app_env.lower() == "production":
                raise RuntimeError("Redis must be reachable before production startup")
    elif settings.app_env.lower() == "production":
        raise RuntimeError("REDIS_URL is required for production rate limiting")

    app.state.rate_limit_redis = redis_client
    if settings.app_env.lower() != "production":
        Base.metadata.create_all(bind=engine)
    try:
        yield
    finally:
        if redis_client is not None:
            await redis_client.aclose()


app = FastAPI(
    title="AI Power Hub API",
    description="Unified API foundation for the AI Power Hub platform.",
    version="0.3.0",
    lifespan=lifespan,
)
app.add_middleware(RateLimitMiddleware)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(account_router)
app.include_router(chat_router)
app.include_router(credits_router)
app.include_router(providers_router)
app.include_router(admin_router)
app.include_router(webhooks_router)
app.include_router(payments_router)


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {"name": "AI Power Hub", "status": "foundation", "docs": "/docs"}
