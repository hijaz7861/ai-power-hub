def test_register_login_and_me(client):
    registered = client.post("/api/v1/auth/register", json={"email": "User@example.com", "password": "a-long-test-password"})
    assert registered.status_code == 201
    assert registered.json()["email"] == "user@example.com"
    assert "password_hash" not in registered.json()
    login = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "a-long-test-password"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"

def test_duplicate_registration_is_rejected(client):
    payload = {"email": "same@example.com", "password": "a-long-test-password"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409

def test_invalid_login_is_rejected(client):
    response = client.post("/api/v1/auth/login", json={"email": "missing@example.com", "password": "wrong-password"})
    assert response.status_code == 401

def test_me_requires_bearer_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
