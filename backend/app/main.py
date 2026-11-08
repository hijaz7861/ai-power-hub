from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.app import models  # noqa: F401
from backend.app.api.auth import router as auth_router
from backend.app.api.admin import router as admin_router
from backend.app.api.credits import router as credits_router
from backend.app.api.health import router as health_router
from backend.app.api.providers import router as providers_router
from backend.app.api.webhooks import router as webhooks_router
from backend.app.api.payments import router as payments_router
from backend.app.core.config import get_settings
from backend.app.core.database import Base, engine

@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if settings.app_env.lower() != "production":
        Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="AI Power Hub API",
    description="Unified API foundation for the AI Power Hub platform.",
    version="0.2.0",
    lifespan=lifespan,
)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(credits_router)
app.include_router(providers_router)
app.include_router(admin_router)
app.include_router(webhooks_router)
app.include_router(payments_router)

@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {"name": "AI Power Hub", "status": "foundation", "docs": "/docs"}
