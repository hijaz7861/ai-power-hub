from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Runtime configuration; secrets are read only from the environment."""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    app_name: str = "AI Power Hub"
    app_env: str = "development"
    debug: bool = False
    database_url: str = "sqlite:///./ai_power_hub.db"
    secret_key: str = "development-only-change-this-secret"
    access_token_minutes: int = 30
    openai_api_key: str = ""
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    mistral_api_key: str = ""
    safepay_webhook_secret: str = ""
    safepay_api_key: str = ""
    safepay_secret_key: str = ""
    safepay_environment: str = "sandbox"
    public_app_url: str = ""

    def validate_runtime(self) -> None:
        if self.app_env.lower() == "production":
            if self.secret_key == "development-only-change-this-secret" or len(self.secret_key) < 32:
                raise RuntimeError("A production SECRET_KEY of at least 32 characters is required")
            if self.debug:
                raise RuntimeError("DEBUG must be false in production")

@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime()
    return settings
