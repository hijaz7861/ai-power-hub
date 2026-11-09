import pytest

from backend.app.core.config import Settings

def test_production_config_requires_trusted_proxy_cidr():
    settings = Settings(
        app_env="production",
        debug=False,
        secret_key="a" * 64,
        database_url="postgresql+psycopg://user:pass@db.example.test:5432/aiph",
        public_app_url="https://ai.example.test",
        redis_url="rediss://cache.example.test:6379/0",
    )
    with pytest.raises(RuntimeError, match="TRUSTED_PROXY_IPS"):
        settings.validate_runtime()


def test_production_config_rejects_invalid_trusted_proxy_cidr():
    settings = Settings(
        app_env="production",
        debug=False,
        secret_key="a" * 64,
        database_url="postgresql+psycopg://user:pass@db.example.test:5432/aiph",
        public_app_url="https://ai.example.test",
        redis_url="rediss://cache.example.test:6379/0",
        trusted_proxy_ips="not-a-network",
    )
    with pytest.raises(RuntimeError, match="invalid IP or CIDR"):
        settings.validate_runtime()
