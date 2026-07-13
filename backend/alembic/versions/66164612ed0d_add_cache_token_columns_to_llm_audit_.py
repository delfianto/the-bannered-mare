"""add cache token columns to llm_audit_logs

Revision ID: 66164612ed0d
Revises: a8c4f2e91d07
Create Date: 2026-07-13 18:59:05.725309

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '66164612ed0d'
down_revision = 'a8c4f2e91d07'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('llm_audit_logs', sa.Column('cache_read_tokens', sa.Integer(), nullable=False, server_default='0', comment='Prompt-cache read tokens (cached prefix served from cache)'))
    op.add_column('llm_audit_logs', sa.Column('cache_creation_tokens', sa.Integer(), nullable=False, server_default='0', comment='Prompt-cache write tokens (prefix written to ephemeral cache)'))


def downgrade() -> None:
    op.drop_column('llm_audit_logs', 'cache_creation_tokens')
    op.drop_column('llm_audit_logs', 'cache_read_tokens')
