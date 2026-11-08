from fastapi import FastAPI

from backend.app.api.health import router as health_router

app = FastAPI(
    title="AI Power Hub API",
    description="Unified API foundation for the AI Power Hub platform.",
    version="0.1.0",
)

app.include_router(health_router)


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {"name": "AI Power Hub", "status": "foundation", "docs": "/docs"}
