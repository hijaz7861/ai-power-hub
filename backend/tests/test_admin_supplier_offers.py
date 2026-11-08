from sqlalchemy import select

from backend.app.models import User


def register_and_login(client, email="admin-test@example.com"):
    payload = {"email": email, "password": "a-long-test-password"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    token = client.post("/api/v1/auth/login", json=payload).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_supplier_registry_requires_admin(client):
    headers = register_and_login(client, "customer@example.com")
    response = client.get("/api/v1/admin/supplier-offers", headers=headers)
    assert response.status_code == 403


def test_admin_can_create_and_list_pending_supplier_offer(client, test_db):
    headers = register_and_login(client)
    with test_db() as db:
        user = db.scalar(select(User).where(User.email == "admin-test@example.com"))
        user.role = "admin"
        db.commit()

    payload = {
        "supplier_name": "Example GPU Cloud",
        "supplier_code": "example-cloud",
        "service_type": "gpu_compute",
        "provider_code": "example",
        "model_code": "gpu-standard",
        "billing_unit": "per_gpu_second",
        "currency": "PKR",
        "wholesale_cost_minor_units": 250,
        "contract_status": "pending",
        "is_active": False,
    }
    created = client.post("/api/v1/admin/supplier-offers", json=payload, headers=headers)
    assert created.status_code == 201
    assert created.json()["contract_status"] == "pending"
    assert created.json()["is_active"] is False
    listed = client.get("/api/v1/admin/supplier-offers", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["wholesale_cost_minor_units"] == 250


def test_supplier_offer_cannot_be_activated_without_verified_contract(client, test_db):
    headers = register_and_login(client)
    with test_db() as db:
        user = db.scalar(select(User).where(User.email == "admin-test@example.com"))
        user.role = "admin"
        db.commit()
    payload = {
        "supplier_name": "Unverified Provider",
        "supplier_code": "unverified",
        "service_type": "ai_api",
        "provider_code": "example",
        "billing_unit": "per_request",
        "wholesale_cost_minor_units": 100,
        "contract_status": "pending",
        "is_active": True,
    }
    response = client.post("/api/v1/admin/supplier-offers", json=payload, headers=headers)
    assert response.status_code == 422


def test_admin_can_preview_retail_price_from_wholesale_offer(client, test_db):
    headers = register_and_login(client)
    with test_db() as db:
        user = db.scalar(select(User).where(User.email == "admin-test@example.com"))
        user.role = "admin"
        db.commit()
    offer_payload = {
        "supplier_name": "Wholesale AI",
        "supplier_code": "wholesale-ai",
        "service_type": "ai_api",
        "provider_code": "openai",
        "model_code": "sample-model",
        "billing_unit": "per_1k_input_tokens",
        "currency": "PKR",
        "wholesale_cost_minor_units": 1000,
        "contract_status": "verified",
        "is_active": True,
    }
    created = client.post("/api/v1/admin/supplier-offers", json=offer_payload, headers=headers)
    assert created.status_code == 201
    offer_id = created.json()["id"]
    quote = client.post(
        f"/api/v1/admin/supplier-offers/{offer_id}/quote",
        json={"target_margin_bps": 2000, "payment_fee_bps": 200},
        headers=headers,
    )
    assert quote.status_code == 200
    result = quote.json()
    assert result["wholesale_cost_minor_units"] == 1000
    assert result["retail_price_minor_units"] > result["wholesale_cost_minor_units"]
    assert result["projected_margin_bps"] >= 2000
    assert result["currency"] == "PKR"
