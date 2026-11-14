def test_payment_event_inbox_is_admin_only(client):
    payload = {"email": "payment-event-customer@example.com", "password": "a-long-test-password"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    token = client.post("/api/v1/auth/login", json=payload).json()["access_token"]
    response = client.get(
        "/api/v1/admin/payment-events",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
