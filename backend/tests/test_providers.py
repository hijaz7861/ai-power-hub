def test_provider_catalog_does_not_expose_secrets(client):
    response = client.get("/api/v1/providers")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 4
    assert {item["id"] for item in payload["items"]} == {"openai", "google", "anthropic", "mistral"}
    assert all(item["integration_status"] == "adapter_not_implemented" for item in payload["items"])
    assert "api_key" not in response.text.lower()
