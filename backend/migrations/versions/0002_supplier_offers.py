"""Add administrator roles and supplier wholesale offers."""
from alembic import op
import sqlalchemy as sa

revision = "0002_supplier_offers"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(length=24), nullable=False, server_default="customer"))
    op.create_table(
        "supplier_offers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supplier_name", sa.String(length=160), nullable=False),
        sa.Column("supplier_code", sa.String(length=80), nullable=False),
        sa.Column("service_type", sa.String(length=40), nullable=False),
        sa.Column("provider_code", sa.String(length=40), nullable=False),
        sa.Column("model_code", sa.String(length=120), nullable=True),
        sa.Column("billing_unit", sa.String(length=40), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="PKR"),
        sa.Column("wholesale_cost_minor_units", sa.Integer(), nullable=False),
        sa.Column("contract_status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.UniqueConstraint("supplier_code", "provider_code", "model_code", "billing_unit",
                            name="uq_supplier_offer_identity"),
        sa.CheckConstraint("wholesale_cost_minor_units > 0", name="ck_supplier_offer_positive_cost"),
    )
    op.create_index("ix_supplier_offers_supplier_code", "supplier_offers", ["supplier_code"])
    op.create_index("ix_supplier_offers_service_type", "supplier_offers", ["service_type"])
    op.create_index("ix_supplier_offers_provider_code", "supplier_offers", ["provider_code"])


def downgrade() -> None:
    op.drop_index("ix_supplier_offers_provider_code", table_name="supplier_offers")
    op.drop_index("ix_supplier_offers_service_type", table_name="supplier_offers")
    op.drop_index("ix_supplier_offers_supplier_code", table_name="supplier_offers")
    op.drop_table("supplier_offers")
    op.drop_column("users", "role")
