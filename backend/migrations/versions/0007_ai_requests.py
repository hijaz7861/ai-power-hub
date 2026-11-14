"""Persist idempotent metered AI request outcomes."""
from alembic import op
import sqlalchemy as sa

revision = "0007_ai_requests"
down_revision = "0006_credit_reservations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="processing"),
        sa.Column("reservation_id", sa.Integer(), nullable=True),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("provider_request_id", sa.String(length=160), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("credits_charged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reservation_id"], ["credit_reservations.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_ai_request_user_key"),
        sa.CheckConstraint(
            "status IN ('processing', 'completed', 'failed', 'reconciliation_required')",
            name="ck_ai_request_status",
        ),
        sa.CheckConstraint("credits_charged >= 0", name="ck_ai_request_nonnegative_charge"),
    )
    op.create_index("ix_ai_requests_user_id", "ai_requests", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_requests_user_id", table_name="ai_requests")
    op.drop_table("ai_requests")
