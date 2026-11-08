"""Record the administrator responsible for manual credit grants."""
from alembic import op
import sqlalchemy as sa

revision = "0003_credit_grant_actor"
down_revision = "0002_supplier_offers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("credit_ledger") as batch_op:
        batch_op.add_column(sa.Column("actor_user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_credit_ledger_actor_user",
            "users",
            ["actor_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_credit_ledger_actor_user_id", ["actor_user_id"])


def downgrade() -> None:
    with op.batch_alter_table("credit_ledger") as batch_op:
        batch_op.drop_index("ix_credit_ledger_actor_user_id")
        batch_op.drop_constraint("fk_credit_ledger_actor_user", type_="foreignkey")
        batch_op.drop_column("actor_user_id")
