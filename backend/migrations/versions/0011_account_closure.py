"""Record account closure timestamp for privacy-safe deactivation."""

from alembic import op
import sqlalchemy as sa

revision = "0011_account_closure"
down_revision = "0010_payment_refunds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "closed_at")
