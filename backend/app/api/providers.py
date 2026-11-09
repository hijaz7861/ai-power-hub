from fastapi import APIRouter
from backend.app.core.config import get_settings

router = APIRouter(prefix="/api/v1/providers", tags=["AI providers"])
PROVIDERS = (
    ("openai", "OpenAI", "openai_api_key"),
    ("google", "Google Gemini", "gemini_api_key"),
    ("anthropic", "Anthropic", "anthropic_api_key"),
    ("mistral", "Mistral", "mistral_api_key"),
)

@router.get("")
def list_providers() -> dict:
    """Return provider metadata without exposing credentials or implying model support."""
    settings = get_settings()
    items = []
    for provider_id, name, key_attribute in PROVIDERS:
        items.append({
            "id": provider_id,
            "name": name,
            "credential_configured": bool(getattr(settings, key_attribute)),
            "capabilities_status": "requires_live_model_discovery",
            "integration_status": (
                "adapter_available_model_rate_required"
                if provider_id in {"openai", "mistral"}
                else "adapter_not_implemented"
            ),
        })
    return {"items": items, "count": len(items)}
