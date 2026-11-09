import pytest

from backend.app.core.config import Settings


def test_production_config_requires_postgresql_and_public_https_url():
    settings = Settings(
        app_env="production",
        debug=False,
        secret_key="a" * 64,
        database_url="postgresql+psycopg://user:pass@db.example.test:5432/aiph",
        public_app_url="https://ai.example.test",
        redis_url="rediss://cache.example.test:6379/0",
    )
    settings.validate_runtime()


def test_production_config_rejects_sqlite():
    settings = Settings(
        app_env="production",
        debug=False,
        secret_key="a" * 64,
        database_url="sqlite:///./ai_power_hub.db",
        public_app_url="https://ai.example.test",
    )
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        settings.validate_runtime()


def test_production_config_requires_public_https_url():
    settings = Settings(
        app_env="production",
        debug=False,
        secret_key="a" * 64,
        database_url="postgresql+psycopg://user:pass@db.example.test:5432/aiph",
        public_app_url="",
    )
    with pytest.raises(RuntimeError, match="PUBLIC_APP_URL"):
        settings.validate_runtime()


def test_production_config_rejects_development_secret_and_debug():
    settings = Settings(
        app_env="production",
        debug=True,
        secret_key="development-only-change-this-secret",
        database_url="postgresql+psycopg://user:pass@db.example.test:5432/aiph",
        public_app_url="https://ai.example.test",
    )
    with pytest.raises(RuntimeError):
        settings.validate_runtime()


def test_production_config_requires_redis():
    settings = Settings(
        app_env="production",
        debug=False,
        secret_key="a" * 64,
        database_url="postgresql+psycopg://user:pass@db.example.test:5432/aiph",
        public_app_url="https://ai.example.test",
    )
    with pytest.raises(RuntimeError, match="Redis"):
        settings.validate_runtime()
