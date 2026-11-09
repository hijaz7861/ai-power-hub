from sqlalchemy import select

from backend.app.core.security import create_access_token, hash_password
from backend.app.models import (
    AIRequest,
    CreditReservation,
    Conversation,
    ConversationMessage,
    CreditAccount,
    CreditLedger,
    PaymentOrder,
    User,
)


def _create_customer(test_db, *, balance=0, role="customer"):
    with test_db() as db:
        user = User(
            email=f"close-{role}-{balance}@example.com",
            password_hash=hash_password("a-long-test-password"),
            role=role,
        )
        user.credit_account = CreditAccount(balance=balance)
        db.add(user)
        db.flush()
        user_id = user.id
        db.commit()
    return user_id, create_access_token(str(user_id))


def test_account_closure_erases_chat_and_anonymizes_identity_but_keeps_financial_audit(client, test_db):
    with test_db() as db:
        user = User(
            email="closure-customer@example.com",
            password_hash=hash_password("a-long-test-password"),
        )
        user.credit_account = CreditAccount(balance=0)
        db.add(user)
        db.flush()
        conversation = Conversation(user_id=user.id, title="Private title")
        db.add(conversation)
        db.flush()
        request = AIRequest(
            user_id=user.id,
            idempotency_key="closure-request-001",
            request_hash="a" * 64,
            provider="openai",
            model="test-model",
            status="completed",
            conversation_id=conversation.id,
            response_text="Private assistant answer",
            credits_charged=0,
        )
        db.add(request)
        db.flush()
        db.add(ConversationMessage(
            conversation_id=conversation.id,
            request_id=request.id,
            role="user",
            content="Private customer prompt",
        ))
        db.add(CreditLedger(
            user_id=user.id,
            amount=0,
            entry_type="adjustment",
            idempotency_key="closure-audit-001",
            description="Retained financial audit record",
        ))
        db.commit()
        user_id = user.id
        request_id = request.id

    token = create_access_token(str(user_id))
    response = client.post(
        "/api/v1/account/close",
        json={"password": "a-long-test-password"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "closed"

    with test_db() as db:
        closed = db.get(User, user_id)
        assert closed is not None
        assert closed.email == f"closed+{user_id}@accounts.invalid"
        assert closed.is_active is False
        assert closed.closed_at is not None
        assert closed.role == "customer"
        assert db.scalar(select(Conversation).where(Conversation.user_id == user_id)) is None
        assert db.scalar(select(ConversationMessage).where(ConversationMessage.content == "Private customer prompt")) is None
        stored_request = db.get(AIRequest, request_id)
        assert stored_request.response_text is None
        assert stored_request.request_hash == "0" * 64
        assert stored_request.conversation_id is None
        assert db.scalar(select(CreditLedger).where(
            CreditLedger.user_id == user_id,
            CreditLedger.idempotency_key == "closure-audit-001",
        )) is not None

    assert client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 401


def test_account_closure_requires_correct_password(client, test_db):
    user_id, token = _create_customer(test_db)
    response = client.post(
        "/api/v1/account/close",
        json={"password": "incorrect-password"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    with test_db() as db:
        assert db.get(User, user_id).is_active is True


def test_account_closure_refuses_unsettled_credit_balance(client, test_db):
    user_id, token = _create_customer(test_db, balance=500)
    response = client.post(
        "/api/v1/account/close",
        json={"password": "a-long-test-password"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409
    assert "credit balance" in response.json()["detail"]
    with test_db() as db:
        assert db.get(User, user_id).is_active is True


def test_administrator_must_transfer_role_before_closing_account(client, test_db):
    user_id, token = _create_customer(test_db, role="admin")
    response = client.post(
        "/api/v1/account/close",
        json={"password": "a-long-test-password"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409
    with test_db() as db:
        assert db.get(User, user_id).is_active is True



def test_account_closure_refuses_unsettled_ai_reconciliation(client, test_db):
    with test_db() as db:
        user = User(
            email="close-reconcile@example.com",
            password_hash=hash_password("a-long-test-password"),
        )
        user.credit_account = CreditAccount(balance=0)
        db.add(user)
        db.flush()
        db.add(AIRequest(
            user_id=user.id,
            idempotency_key="close-reconcile-001",
            request_hash="b" * 64,
            provider="openai",
            model="test-model",
            status="reconciliation_required",
        ))
        user_id = user.id
        db.commit()
    token = create_access_token(str(user_id))
    response = client.post(
        "/api/v1/account/close",
        json={"password": "a-long-test-password"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409
    assert "AI request" in response.json()["detail"]
    with test_db() as db:
        assert db.get(User, user_id).is_active is True


def test_account_closure_refuses_pending_payment(client, test_db):
    with test_db() as db:
        user = User(
            email="close-payment@example.com",
            password_hash=hash_password("a-long-test-password"),
        )
        user.credit_account = CreditAccount(balance=0)
        db.add(user)
        db.flush()
        db.add(PaymentOrder(
            reference="close-payment-reference",
            user_id=user.id,
            amount_minor_units=10000,
            currency="PKR",
            provider="safepay",
            status="pending",
            idempotency_key="close-payment-001",
        ))
        user_id = user.id
        db.commit()
    token = create_access_token(str(user_id))
    response = client.post(
        "/api/v1/account/close",
        json={"password": "a-long-test-password"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409
    assert "payment is still pending" in response.json()["detail"]
    with test_db() as db:
        assert db.get(User, user_id).is_active is True


def test_account_closure_refuses_reserved_credit_hold(client, test_db):
    with test_db() as db:
        user = User(
            email="close-reservation@example.com",
            password_hash=hash_password("a-long-test-password"),
        )
        user.credit_account = CreditAccount(balance=0)
        db.add(user)
        db.flush()
        db.add(CreditReservation(
            user_id=user.id,
            idempotency_key="close-reservation-001",
            reserved_amount=100,
            captured_amount=0,
            status="reserved",
            description="Unsettled test hold",
        ))
        user_id = user.id
        db.commit()
    token = create_access_token(str(user_id))
    response = client.post(
        "/api/v1/account/close",
        json={"password": "a-long-test-password"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409
    assert "AI request or credit reservation" in response.json()["detail"]
    with test_db() as db:
        assert db.get(User, user_id).is_active is True
