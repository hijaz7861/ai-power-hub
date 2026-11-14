"""Add idempotent credit reservations for metered usage."""
from alembic import op
import sqlalchemy as sa

revision = "0006_credit_reservations"
down_revision = "0005_payment_orders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "credit_reservations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("reserved_amount", sa.Integer(), nullable=False),
        sa.Column("captured_amount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="reserved"),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_credit_reservation_user_key"),
        sa.CheckConstraint("reserved_amount > 0", name="ck_credit_reservation_positive"),
        sa.CheckConstraint("captured_amount >= 0 AND captured_amount <= reserved_amount",
                           name="ck_credit_reservation_capture_range"),
        sa.CheckConstraint("status IN ('reserved', 'captured', 'released')",
                           name="ck_credit_reservation_status"),
    )
    op.create_index("ix_credit_reservations_user_id", "credit_reservations", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_credit_reservations_user_id", table_name="credit_reservations")
    op.drop_table("credit_reservations")
