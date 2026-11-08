"""Add verified Safepay webhook event inbox."""
from alembic import op
import sqlalchemy as sa

revision = "0004_payment_webhook_inbox"
down_revision = "0003_credit_grant_actor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_token", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("tracker_token", sa.String(length=128), nullable=True),
        sa.Column("amount_minor_units", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("processing_status", sa.String(length=24), nullable=False, server_default="received"),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("event_token", name="uq_payment_webhook_event_token"),
    )
    op.create_index("ix_payment_webhook_events_tracker_token", "payment_webhook_events", ["tracker_token"])


def downgrade() -> None:
    op.drop_index("ix_payment_webhook_events_tracker_token", table_name="payment_webhook_events")
    op.drop_table("payment_webhook_events")
