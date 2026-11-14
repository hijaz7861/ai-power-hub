def test_provider_catalog_does_not_expose_secrets(client):
    response = client.get("/api/v1/providers")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 4
    assert {item["id"] for item in payload["items"]} == {"openai", "google", "anthropic", "mistral"}
    states = {item["id"]: item["integration_status"] for item in payload["items"]}
    assert states["openai"] == "adapter_available_model_rate_required"
    assert states["mistral"] == "adapter_available_model_rate_required"
    assert states["google"] == "adapter_not_implemented"
    assert states["anthropic"] == "adapter_not_implemented"
    assert "api_key" not in response.text.lower()
