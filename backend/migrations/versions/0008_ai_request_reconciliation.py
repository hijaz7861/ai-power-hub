"""Snapshot metered AI rates and add admin reconciliation audit fields."""
from alembic import op
import sqlalchemy as sa

revision = "0008_ai_request_reconciliation"
down_revision = "0007_ai_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_requests", sa.Column(
        "input_rate_minor_units", sa.Integer(), nullable=False, server_default="0"
    ))
    op.add_column("ai_requests", sa.Column(
        "output_rate_minor_units", sa.Integer(), nullable=False, server_default="0"
    ))
    op.add_column("ai_requests", sa.Column(
        "target_margin_bps", sa.Integer(), nullable=False, server_default="1500"
    ))
    op.add_column("ai_requests", sa.Column(
        "reconciliation_evidence", sa.String(length=255), nullable=True
    ))
    op.add_column("ai_requests", sa.Column(
        "reconciled_by_user_id", sa.Integer(), nullable=True
    ))
    op.create_foreign_key(
        "fk_ai_request_reconciled_by",
        "ai_requests",
        "users",
        ["reconciled_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_ai_request_reconciled_by", "ai_requests", type_="foreignkey")
    op.drop_column("ai_requests", "reconciled_by_user_id")
    op.drop_column("ai_requests", "reconciliation_evidence")
    op.drop_column("ai_requests", "target_margin_bps")
    op.drop_column("ai_requests", "output_rate_minor_units")
    op.drop_column("ai_requests", "input_rate_minor_units")
