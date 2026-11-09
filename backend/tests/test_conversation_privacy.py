from sqlalchemy import select

from backend.app.core.security import create_access_token
from backend.app.models import AIRequest, Conversation, ConversationMessage, User


def test_customer_can_delete_owned_conversation_and_erase_message_content(client, test_db):
    with test_db() as db:
        user = User(email="privacy-owner@example.com", password_hash="unused")
        db.add(user)
        db.flush()
        conversation = Conversation(user_id=user.id, title="Private topic")
        db.add(conversation)
        db.flush()
        request = AIRequest(
            user_id=user.id,
            idempotency_key="privacy-delete-request-001",
            request_hash="a" * 64,
            provider="openai",
            model="test-model",
            status="completed",
            conversation_id=conversation.id,
            response_text="Private assistant response",
        )
        db.add(request)
        db.flush()
        db.add_all([
            ConversationMessage(
                conversation_id=conversation.id,
                request_id=request.id,
                role="user",
                content="Private user prompt",
            ),
            ConversationMessage(
                conversation_id=conversation.id,
                request_id=request.id,
                role="assistant",
                content="Private assistant response",
            ),
        ])
        db.commit()
        user_id = user.id
        conversation_id = conversation.id

    token = create_access_token(str(user_id))
    response = client.delete(
        f"/api/v1/chat/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    with test_db() as db:
        assert db.get(Conversation, conversation_id) is None
        assert db.scalar(select(ConversationMessage).where(
            ConversationMessage.conversation_id == conversation_id
        )) is None
        request = db.scalar(select(AIRequest).where(
            AIRequest.idempotency_key == "privacy-delete-request-001"
        ))
        assert request.conversation_id is None
        assert request.response_text is None
        assert request.status == "completed"


def test_customer_cannot_delete_another_users_conversation(client, test_db):
    with test_db() as db:
        owner = User(email="privacy-owner-two@example.com", password_hash="unused")
        other = User(email="privacy-other@example.com", password_hash="unused")
        db.add_all([owner, other])
        db.flush()
        conversation = Conversation(user_id=owner.id, title="Not yours")
        db.add(conversation)
        db.commit()
        conversation_id = conversation.id
        other_id = other.id

    token = create_access_token(str(other_id))
    response = client.delete(
        f"/api/v1/chat/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
