"""add audit log tables

Revision ID: d39bb8a9cb5c
Revises: 3e8d44254c65
Create Date: 2026-06-03 21:44:05.955109

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "d39bb8a9cb5c"
down_revision = "3e8d44254c65"
branch_labels = None
depends_on = None

# JSONB on Postgres (matches the JsonDict column variant used by the models)
_JSONB = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "error_logs",
        sa.Column("error_type", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("stack_trace", sa.Text(), nullable=True),
        sa.Column("context", _JSONB, nullable=False),
        sa.Column(
            "id",
            sa.String(length=12),
            nullable=False,
            comment="Unique short identifier (12 characters)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Timestamp when the record was created (UTC)",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Timestamp when the record was last updated (UTC)",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_error_logs_type_created", "error_logs", ["error_type", "created_at"], unique=False
    )

    op.create_table(
        "http_logs",
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("path", sa.String(length=2048), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("client_ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("request_body", _JSONB, nullable=True),
        sa.Column("response_body", _JSONB, nullable=True),
        sa.Column(
            "id",
            sa.String(length=12),
            nullable=False,
            comment="Unique short identifier (12 characters)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Timestamp when the record was created (UTC)",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Timestamp when the record was last updated (UTC)",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_http_logs_created", "http_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_http_logs_request_id"), "http_logs", ["request_id"], unique=False)

    op.create_table(
        "llm_audit_logs",
        sa.Column(
            "chat_id",
            sa.String(length=12),
            nullable=True,
            comment="Chat this call belongs to (null if the chat was deleted)",
        ),
        sa.Column(
            "provider",
            sa.String(length=50),
            nullable=False,
            comment="Provider type (e.g. openai, anthropic)",
        ),
        sa.Column(
            "model",
            sa.String(length=255),
            nullable=False,
            comment="Model identifier sent to the provider",
        ),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            comment="success or an error classification",
        ),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "request_payload",
            _JSONB,
            nullable=False,
            comment="Raw request messages sent to the provider",
        ),
        sa.Column(
            "response_payload",
            _JSONB,
            nullable=True,
            comment="Raw response (content, reasoning, finish_reason, usage)",
        ),
        sa.Column(
            "id",
            sa.String(length=12),
            nullable=False,
            comment="Unique short identifier (12 characters)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Timestamp when the record was created (UTC)",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Timestamp when the record was last updated (UTC)",
        ),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_llm_audit_logs_chat_created",
        "llm_audit_logs",
        ["chat_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_llm_audit_logs_chat_id"), "llm_audit_logs", ["chat_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_llm_audit_logs_chat_id"), table_name="llm_audit_logs")
    op.drop_index("ix_llm_audit_logs_chat_created", table_name="llm_audit_logs")
    op.drop_table("llm_audit_logs")

    op.drop_index(op.f("ix_http_logs_request_id"), table_name="http_logs")
    op.drop_index("ix_http_logs_created", table_name="http_logs")
    op.drop_table("http_logs")

    op.drop_index("ix_error_logs_type_created", table_name="error_logs")
    op.drop_table("error_logs")
