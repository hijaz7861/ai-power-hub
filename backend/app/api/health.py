from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict[str, str]:
    """Confirm that the API process is responding."""
    return {"status": "ok", "service": "ai-power-hub-api"}


@router.get("/ready", summary="Dependency readiness probe")
async def ready(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    """Check database and configured distributed rate-limit dependency."""
    checks: dict[str, str] = {}
    healthy = True
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"
        healthy = False

    settings = getattr(request.app.state, "settings", None)
    redis_client = getattr(request.app.state, "rate_limit_redis", None)
    if redis_client is None:
        if settings is not None and settings.app_env.lower() == "production":
            checks["redis"] = "unavailable"
            healthy = False
        else:
            checks["redis"] = "optional_in_development"
    else:
        try:
            await redis_client.ping()
            checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "unavailable"
            healthy = False

    return JSONResponse(
        status_code=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ready" if healthy else "not_ready", "checks": checks},
        headers={"Cache-Control": "no-store"},
    )
