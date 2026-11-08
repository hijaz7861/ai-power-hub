from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict[str, str]:
    """Confirm that the API process is responding."""
    return {"status": "ok", "service": "ai-power-hub-api"}


@router.get("/ready", summary="Readiness probe")
async def ready() -> dict[str, str]:
    """Initial readiness probe; dependency checks will be added with integrations."""
    return {"status": "ready", "checks": "not_yet_configured"}
