def test_new_user_starts_with_zero_credits(client):
    client.post("/api/v1/auth/register", json={"email": "credits@example.com", "password": "a-long-test-password"})
    token = client.post("/api/v1/auth/login", json={"email": "credits@example.com", "password": "a-long-test-password"}).json()["access_token"]
    response = client.get("/api/v1/credits/balance", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"balance": 0, "unit": "credits"}

def test_credit_balance_requires_authentication(client):
    assert client.get("/api/v1/credits/balance").status_code == 401
