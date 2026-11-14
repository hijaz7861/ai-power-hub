"""Add Safepay top-up orders and webhook reconciliation fields."""
from alembic import op
import sqlalchemy as sa

revision = "0005_payment_orders"
down_revision = "0004_payment_webhook_inbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reference", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount_minor_units", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="PKR"),
        sa.Column("provider", sa.String(length=24), nullable=False, server_default="safepay"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("provider_tracker", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("reference", name="uq_payment_order_reference"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_payment_order_user_idempotency"),
        sa.UniqueConstraint("provider_tracker", name="uq_payment_order_provider_tracker"),
        sa.CheckConstraint("amount_minor_units > 0", name="ck_payment_order_positive_amount"),
    )
    op.create_index("ix_payment_orders_user_id", "payment_orders", ["user_id"])
    op.create_index("ix_payment_orders_provider_tracker", "payment_orders", ["provider_tracker"])

    with op.batch_alter_table("payment_webhook_events") as batch_op:
        batch_op.add_column(sa.Column("order_reference", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("provider_state", sa.String(length=60), nullable=True))
        batch_op.add_column(sa.Column("payment_order_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_payment_webhook_order",
            "payment_orders",
            ["payment_order_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_payment_webhook_events_order_reference", ["order_reference"])


def downgrade() -> None:
    with op.batch_alter_table("payment_webhook_events") as batch_op:
        batch_op.drop_index("ix_payment_webhook_events_order_reference")
        batch_op.drop_constraint("fk_payment_webhook_order", type_="foreignkey")
        batch_op.drop_column("payment_order_id")
        batch_op.drop_column("provider_state")
        batch_op.drop_column("order_reference")
    op.drop_index("ix_payment_orders_provider_tracker", table_name="payment_orders")
    op.drop_index("ix_payment_orders_user_id", table_name="payment_orders")
    op.drop_table("payment_orders")
