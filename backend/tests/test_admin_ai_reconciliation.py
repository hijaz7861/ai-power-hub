from sqlalchemy import select

from backend.app.core.security import create_access_token
from backend.app.models import AIRequest, CreditAccount, CreditLedger, CreditReservation, User
from backend.app.services.credits import reserve_credits


def create_admin_and_held_request(test_db):
    with test_db() as db:
        admin = User(email="reconcile-admin@example.com", password_hash="unused", role="admin")
        customer = User(email="reconcile-customer@example.com", password_hash="unused")
        customer.credit_account = CreditAccount(balance=10000)
        db.add_all([admin, customer])
        db.commit()
        db.refresh(admin)
        db.refresh(customer)
        admin_token = create_access_token(str(admin.id))
        customer_token = create_access_token(str(customer.id))
        customer_id = customer.id
        admin_id = admin.id

    with test_db() as db:
        hold = reserve_credits(
            db, user_id=customer_id, amount=500,
            idempotency_key="held-reconciliation-001",
            description="held AI request",
        )
        request = AIRequest(
            user_id=customer_id,
            idempotency_key="ai-reconcile-001",
            request_hash="a" * 64,
            provider="openai",
            model="test-model",
            status="reconciliation_required",
            reservation_id=hold.id,
            response_text="Stored response awaiting verified usage",
            provider_request_id="provider-log-123",
            input_rate_minor_units=1000,
            output_rate_minor_units=2000,
            target_margin_bps=1500,
            error_code="provider_usage_missing",
        )
        db.add(request)
        db.commit()
        db.refresh(request)
        request_id = request.id
    return admin_id, customer_id, request_id, admin_token, customer_token


def test_admin_can_reconcile_held_usage_with_evidence_and_actor_audit(client, test_db):
    admin_id, customer_id, request_id, admin_token, _ = create_admin_and_held_request(test_db)
    headers = {"Authorization": f"Bearer {admin_token}"}

    inbox = client.get("/api/v1/admin/ai-requests", headers=headers)
    assert inbox.status_code == 200
    assert len(inbox.json()) == 1
    assert inbox.json()[0]["status"] == "reconciliation_required"

    response = client.post(
        f"/api/v1/admin/ai-requests/{request_id}/reconcile",
        json={
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "evidence_reference": "verified-provider-log-123",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"
    assert response.json()["credits_charged"] == 236
    assert response.json()["reconciled_by_user_id"] == admin_id
    assert response.json()["reconciliation_evidence"] == "verified-provider-log-123"

    with test_db() as db:
        account = db.scalar(select(CreditAccount).where(CreditAccount.user_id == customer_id))
        assert account.balance == 9764
        release = db.scalar(select(CreditLedger).where(
            CreditLedger.user_id == customer_id,
            CreditLedger.entry_type == "release",
        ))
        actor = db.get(User, admin_id)
        assert release.actor_user_id == actor.id
        reservation = db.scalar(select(CreditReservation).where(
            CreditReservation.user_id == customer_id
        ))
        assert reservation.status == "captured"
        assert reservation.captured_amount == 236


def test_non_admin_cannot_read_ai_reconciliation_inbox(client, test_db):
    _, _, _, _, customer_token = create_admin_and_held_request(test_db)
    response = client.get(
        "/api/v1/admin/ai-requests",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 403


def test_reconciliation_rejects_charge_above_authorized_hold(client, test_db):
    _, _, request_id, admin_token, _ = create_admin_and_held_request(test_db)
    response = client.post(
        f"/api/v1/admin/ai-requests/{request_id}/reconcile",
        json={
            "prompt_tokens": 1000,
            "completion_tokens": 1000,
            "evidence_reference": "verified-provider-log-456",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422
    assert "exceeds the original authorization" in response.json()["detail"]


def test_admin_can_release_exceptional_hold_with_audit_evidence(client, test_db):
    admin_id, customer_id, request_id, admin_token, _ = create_admin_and_held_request(test_db)
    response = client.post(
        f"/api/v1/admin/ai-requests/{request_id}/release",
        json={"evidence_reference": "provider-support-case-9981"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "failed"
    assert response.json()["error_code"] == "admin_released_hold"
    assert response.json()["reconciled_by_user_id"] == admin_id

    with test_db() as db:
        account = db.scalar(select(CreditAccount).where(CreditAccount.user_id == customer_id))
        assert account.balance == 10000
        release = db.scalar(select(CreditLedger).where(
            CreditLedger.user_id == customer_id,
            CreditLedger.entry_type == "release",
        ))
        assert release.amount == 500
        assert release.actor_user_id == admin_id


from datetime import datetime, timedelta, timezone


def test_admin_recovers_stale_processing_request_and_keeps_reservation_held(client, test_db):
    with test_db() as db:
        admin = User(email="recovery-admin@example.com", password_hash="unused", role="admin")
        customer = User(email="recovery-customer@example.com", password_hash="unused")
        customer.credit_account = CreditAccount(balance=10000)
        db.add_all([admin, customer])
        db.commit()
        admin_token = create_access_token(str(admin.id))
        customer_id = customer.id
        admin_id = admin.id

    with test_db() as db:
        request = AIRequest(
            user_id=customer_id,
            idempotency_key="recovery-request-001",
            request_hash="b" * 64,
            provider="openai",
            model="test-model",
            status="processing",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        )
        db.add(request)
        db.commit()
        request_id = request.id
        hold = reserve_credits(
            db,
            user_id=customer_id,
            amount=500,
            idempotency_key=f"ai-request-{request_id}",
            description="interrupted request hold",
        )
        assert hold.status == "reserved"
        assert db.get(AIRequest, request_id).reservation_id is None

    response = client.post(
        f"/api/v1/admin/ai-requests/{request_id}/recover",
        json={"evidence_reference": "worker-crash-investigation-001"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "reconciliation_required"
    assert response.json()["error_code"] == "interrupted_after_reservation"
    assert response.json()["reconciled_by_user_id"] == admin_id
    assert response.json()["completed_at"] is None

    with test_db() as db:
        recovered = db.get(AIRequest, request_id)
        reservation = db.scalar(select(CreditReservation).where(
            CreditReservation.idempotency_key == f"ai-request-{request_id}"
        ))
        account = db.scalar(select(CreditAccount).where(CreditAccount.user_id == customer_id))
        assert recovered.reservation_id == reservation.id
        assert reservation.status == "reserved"
        assert account.balance == 9500


def test_admin_recovers_stale_request_without_reservation_as_failed(client, test_db):
    with test_db() as db:
        admin = User(email="recovery-admin-nohold@example.com", password_hash="unused", role="admin")
        customer = User(email="recovery-customer-nohold@example.com", password_hash="unused")
        db.add_all([admin, customer])
        db.commit()
        token = create_access_token(str(admin.id))
        request = AIRequest(
            user_id=customer.id,
            idempotency_key="recovery-request-nohold",
            request_hash="c" * 64,
            provider="openai",
            model="test-model",
            status="processing",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        )
        db.add(request)
        db.commit()
        request_id = request.id

    response = client.post(
        f"/api/v1/admin/ai-requests/{request_id}/recover",
        json={"evidence_reference": "worker-crash-investigation-002"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["error_code"] == "interrupted_before_reservation"


def test_admin_cannot_recover_recent_processing_request(client, test_db):
    with test_db() as db:
        admin = User(email="recovery-admin-recent@example.com", password_hash="unused", role="admin")
        customer = User(email="recovery-customer-recent@example.com", password_hash="unused")
        db.add_all([admin, customer])
        db.commit()
        token = create_access_token(str(admin.id))
        request = AIRequest(
            user_id=customer.id,
            idempotency_key="recovery-request-recent",
            request_hash="d" * 64,
            provider="openai",
            model="test-model",
            status="processing",
        )
        db.add(request)
        db.commit()
        request_id = request.id

    response = client.post(
        f"/api/v1/admin/ai-requests/{request_id}/recover",
        json={"evidence_reference": "not-stale-yet-003"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409
