"""Persist customer chat conversations and messages."""
from alembic import op
import sqlalchemy as sa

revision = "0009_chat_conversations"
down_revision = "0008_ai_request_reconciliation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False, server_default="New conversation"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    op.add_column("ai_requests", sa.Column("conversation_id", sa.Integer(), nullable=True))
    with op.batch_alter_table("ai_requests") as batch_op:
        batch_op.create_foreign_key(
            "fk_ai_request_conversation",
            "conversations",
            ["conversation_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_ai_requests_conversation_id", ["conversation_id"])

    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("credits_charged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["ai_requests.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("request_id", "role", name="uq_conversation_message_request_role"),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_conversation_message_role"),
        sa.CheckConstraint("credits_charged >= 0", name="ck_conversation_message_nonnegative_charge"),
    )
    op.create_index("ix_conversation_messages_conversation_id", "conversation_messages", ["conversation_id"])
    op.create_index("ix_conversation_messages_request_id", "conversation_messages", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_conversation_messages_request_id", table_name="conversation_messages")
    op.drop_index("ix_conversation_messages_conversation_id", table_name="conversation_messages")
    op.drop_table("conversation_messages")
    with op.batch_alter_table("ai_requests") as batch_op:
        batch_op.drop_index("ix_ai_requests_conversation_id")
        batch_op.drop_constraint("fk_ai_request_conversation", type_="foreignkey")
        batch_op.drop_column("conversation_id")
    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_table("conversations")
