from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_root_returns_platform_identity() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "AI Power Hub"


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ai-power-hub-api"}


def test_readiness_endpoint_checks_database_and_marks_development_redis_optional() -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["checks"]["database"] == "ok"
    assert response.json()["checks"]["redis"] == "optional_in_development"
