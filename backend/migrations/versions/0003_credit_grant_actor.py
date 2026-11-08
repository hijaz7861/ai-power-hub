"""Record the administrator responsible for manual credit grants."""
from alembic import op
import sqlalchemy as sa

revision = "0003_credit_grant_actor"
down_revision = "0002_supplier_offers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "credit_ledger",
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_credit_ledger_actor_user",
        "credit_ledger",
        "users",
        ["actor_user_id"],
        ["id"],
    )
    op.create_index(
        "ix_credit_ledger_actor_user_id",
        "credit_ledger",
        ["actor_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_credit_ledger_actor_user_id", table_name="credit_ledger")
    op.drop_constraint("fk_credit_ledger_actor_user", "credit_ledger", type_="foreignkey")
    op.drop_column("credit_ledger", "actor_user_id")
