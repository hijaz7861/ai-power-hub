from fastapi import APIRouter
from backend.app.core.config import get_settings

router = APIRouter(prefix="/api/v1/providers", tags=["AI providers"])
PROVIDERS = (
    ("openai", "OpenAI", "openai_api_key", ["text", "image", "audio"]),
    ("google", "Google Gemini", "gemini_api_key", ["text", "image"]),
    ("anthropic", "Anthropic", "anthropic_api_key", ["text"]),
    ("mistral", "Mistral", "mistral_api_key", ["text", "coding"]),
)

@router.get("")
def list_providers() -> dict:
    """Return metadata without exposing credentials or claiming integrations work."""
    settings = get_settings()
    items = []
    for provider_id, name, key_attribute, capabilities in PROVIDERS:
        items.append({
            "id": provider_id,
            "name": name,
            "capabilities": capabilities,
            "credential_configured": bool(getattr(settings, key_attribute)),
            "integration_status": "adapter_not_implemented",
        })
    return {"items": items, "count": len(items)}
