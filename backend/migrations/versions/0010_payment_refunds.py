"""Track cumulative refund amounts for Safepay top-ups."""

from alembic import op
import sqlalchemy as sa

revision = "0010_payment_refunds"
down_revision = "0009_chat_conversations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payment_orders",
        sa.Column(
            "refunded_amount_minor_units",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    with op.batch_alter_table("payment_orders") as batch_op:
        batch_op.create_check_constraint(
            "ck_payment_order_refund_range",
            "refunded_amount_minor_units >= 0 AND refunded_amount_minor_units <= amount_minor_units",
        )


def downgrade() -> None:
    with op.batch_alter_table("payment_orders") as batch_op:
        batch_op.drop_constraint("ck_payment_order_refund_range", type_="check")
    op.drop_column("payment_orders", "refunded_amount_minor_units")
