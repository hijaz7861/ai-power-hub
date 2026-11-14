from sqlalchemy import select

from backend.app.core.security import create_access_token
from backend.app.models import AIRequest, Conversation, ConversationMessage, CreditAccount, CreditLedger, User


def test_customer_can_export_owned_profile_billing_and_conversation_data(client, test_db):
    with test_db() as db:
        user = User(
            email="export-customer@example.com",
            password_hash="never-export-this-hash",
        )
        user.credit_account = CreditAccount(balance=12345)
        db.add(user)
        db.flush()
        db.add(CreditLedger(
            user_id=user.id,
            amount=12345,
            entry_type="grant",
            idempotency_key="export-ledger-001",
            description="Initial test grant",
        ))
        conversation = Conversation(user_id=user.id, title="Export this chat")
        db.add(conversation)
        db.flush()
        request = AIRequest(
            user_id=user.id,
            idempotency_key="export-request-001",
            request_hash="e" * 64,
            provider="openai",
            model="test-model",
            status="completed",
            conversation_id=conversation.id,
            response_text="Exported assistant answer",
        )
        db.add(request)
        db.flush()
        db.add(ConversationMessage(
            conversation_id=conversation.id,
            request_id=request.id,
            role="user",
            content="My private exportable prompt",
        ))
        db.commit()
        user_id = user.id

    token = create_access_token(str(user_id))
    response = client.get(
        "/api/v1/account/export",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "attachment" in response.headers["content-disposition"]
    payload = response.json()
    assert payload["user"]["email"] == "export-customer@example.com"
    assert payload["credits"]["balance"] == 12345
    assert payload["credit_ledger"][0]["description"] == "Initial test grant"
    assert payload["conversations"][0]["messages"][0]["content"] == "My private exportable prompt"
    assert "password_hash" not in payload["user"]
    assert "never-export-this-hash" not in response.text


def test_account_export_requires_authentication(client):
    response = client.get("/api/v1/account/export")
    assert response.status_code == 401
