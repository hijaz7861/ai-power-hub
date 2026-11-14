from functools import lru_cache
import ipaddress
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
    redis_url: str = ""
    trusted_proxy_ips: str = ""

    def validate_runtime(self) -> None:
        if self.safepay_environment not in {"sandbox", "production"}:
            raise RuntimeError("SAFEPAY_ENVIRONMENT must be sandbox or production")
        if self.app_env.lower() == "production":
            if self.secret_key == "development-only-change-this-secret" or len(self.secret_key) < 32:
                raise RuntimeError("A production SECRET_KEY of at least 32 characters is required")
            if self.debug:
                raise RuntimeError("DEBUG must be false in production")
            if not self.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
                raise RuntimeError("A PostgreSQL DATABASE_URL is required in production")
            if not self.public_app_url.startswith("https://"):
                raise RuntimeError("PUBLIC_APP_URL must be a public HTTPS URL in production")
            if not self.redis_url.startswith(("redis://", "rediss://")):
                raise RuntimeError("A Redis REDIS_URL is required for distributed rate limiting in production")
            if not self.trusted_proxy_ips.strip():
                raise RuntimeError("TRUSTED_PROXY_IPS must identify the frontend proxy in production")
            for proxy_range in self.trusted_proxy_ips.split(","):
                try:
                    ipaddress.ip_network(proxy_range.strip(), strict=False)
                except ValueError:
                    raise RuntimeError("TRUSTED_PROXY_IPS contains an invalid IP or CIDR") from None

@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime()
    return settings
