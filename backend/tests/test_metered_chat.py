from types import SimpleNamespace

import pytest
from backend.app.core.security import create_access_token
from backend.app.models import CreditAccount, CreditLedger, SupplierOffer, User
from backend.app.services.provider_adapters import ProviderError, ProviderResult


def setup_chat_account(test_db, balance=10000):
    db = test_db()
    user = User(email="chat-metering@example.com", password_hash="unused")
    user.credit_account = CreditAccount(balance=balance)
    db.add(user)
    db.commit()
    db.refresh(user)
    for unit, cost in (("per_1k_input_tokens", 1000), ("per_1k_output_tokens", 2000)):
        db.add(SupplierOffer(
            supplier_name="Verified Test Supplier",
            supplier_code="verified-test",
            service_type="ai_api",
            provider_code="openai",
            model_code="test-model",
            billing_unit=unit,
            currency="PKR",
            wholesale_cost_minor_units=cost,
            contract_status="verified",
            is_active=True,
            created_by=user.id,
        ))
    db.commit()
    token = create_access_token(str(user.id))
    user_id = user.id
    db.close()
    return user_id, {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def chat_settings(monkeypatch):
    monkeypatch.setattr(
        "backend.app.api.chat.get_settings",
        lambda: SimpleNamespace(openai_api_key="test-key", mistral_api_key=""),
    )


def test_chat_reserves_then_charges_actual_usage_and_replays_idempotently(
    client, test_db, monkeypatch, chat_settings
):
    user_id, headers = setup_chat_account(test_db)
    calls = {"count": 0}

    async def fake_complete(self, *, model, messages, max_tokens):
        calls["count"] += 1
        return ProviderResult(
            provider="openai", model=model, content="Metered response",
            request_id="provider-request-1", prompt_tokens=100, completion_tokens=50,
        )

    monkeypatch.setattr(
        "backend.app.api.chat.OpenAICompatibleChatAdapter.complete", fake_complete
    )
    payload = {
        "provider": "openai",
        "model": "test-model",
        "messages": [{"role": "user", "content": "Hello AI"}],
        "max_tokens": 100,
        "idempotency_key": "chat-idempotency-0001",
    }
    first = client.post("/api/v1/chat/completions", json=payload, headers=headers)
    assert first.status_code == 200, first.text
    result = first.json()
    assert result["content"] == "Metered response"
    assert result["prompt_tokens"] == 100
    assert result["completion_tokens"] == 50
    assert result["credits_charged"] == 236
    assert result["balance"] == 9764
    assert result["credits_refunded"] > 0

    replay = client.post("/api/v1/chat/completions", json=payload, headers=headers)
    assert replay.status_code == 200
    assert replay.json() == result
    assert calls["count"] == 1

    db = test_db()
    try:
        account = db.query(CreditAccount).filter(CreditAccount.user_id == user_id).one()
        assert account.balance == 9764
        entries = db.query(CreditLedger).filter(CreditLedger.user_id == user_id).all()
        assert sorted(entry.entry_type for entry in entries) == ["release", "reserve"]
    finally:
        db.close()


def test_chat_does_not_call_provider_when_reservation_is_unaffordable(
    client, test_db, monkeypatch, chat_settings
):
    _, headers = setup_chat_account(test_db, balance=1)

    async def should_not_run(self, **kwargs):
        pytest.fail("provider must not be called without an authorized credit reservation")

    monkeypatch.setattr(
        "backend.app.api.chat.OpenAICompatibleChatAdapter.complete", should_not_run
    )
    response = client.post("/api/v1/chat/completions", json={
        "provider": "openai", "model": "test-model",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 100, "idempotency_key": "chat-insufficient-001",
    }, headers=headers)
    assert response.status_code == 402


def test_provider_failure_releases_the_entire_reservation(
    client, test_db, monkeypatch, chat_settings
):
    user_id, headers = setup_chat_account(test_db)

    async def fail_provider(self, **kwargs):
        raise ProviderError("sanitised failure")

    monkeypatch.setattr(
        "backend.app.api.chat.OpenAICompatibleChatAdapter.complete", fail_provider
    )
    response = client.post("/api/v1/chat/completions", json={
        "provider": "openai", "model": "test-model",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 100, "idempotency_key": "chat-provider-fail-001",
    }, headers=headers)
    assert response.status_code == 502

    db = test_db()
    try:
        account = db.query(CreditAccount).filter(CreditAccount.user_id == user_id).one()
        assert account.balance == 10000
        assert sorted(e.entry_type for e in db.query(CreditLedger).filter(
            CreditLedger.user_id == user_id
        ).all()) == ["release", "reserve"]
    finally:
        db.close()


def test_missing_provider_usage_keeps_reservation_for_reconciliation(
    client, test_db, monkeypatch, chat_settings
):
    user_id, headers = setup_chat_account(test_db)

    async def missing_usage(self, *, model, messages, max_tokens):
        return ProviderResult(
            provider="openai", model=model, content="response",
            request_id="request-no-usage", prompt_tokens=None, completion_tokens=None,
        )

    monkeypatch.setattr(
        "backend.app.api.chat.OpenAICompatibleChatAdapter.complete", missing_usage
    )
    response = client.post("/api/v1/chat/completions", json={
        "provider": "openai", "model": "test-model",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 100, "idempotency_key": "chat-missing-usage-001",
    }, headers=headers)
    assert response.status_code == 502

    db = test_db()
    try:
        account = db.query(CreditAccount).filter(CreditAccount.user_id == user_id).one()
        assert account.balance < 10000
        from backend.app.models import AIRequest
        request = db.query(AIRequest).filter(AIRequest.user_id == user_id).one()
        assert request.status == "reconciliation_required"
        assert request.error_code == "provider_usage_missing"
    finally:
        db.close()


def test_public_model_catalogue_only_lists_complete_verified_rate_pairs(
    client, test_db, chat_settings
):
    setup_chat_account(test_db)
    response = client.get("/api/v1/chat/models")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["items"] == [{
        "provider": "openai",
        "model": "test-model",
        "credential_configured": True,
    }]
