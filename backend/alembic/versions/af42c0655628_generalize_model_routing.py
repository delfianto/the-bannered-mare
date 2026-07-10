"""generalize model routing

Revision ID: af42c0655628
Revises: 5abc40a88101
Create Date: 2026-07-11 00:35:16.099377

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'af42c0655628'
down_revision = '5abc40a88101'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add the generic routing columns first (old OpenRouter pair still present).
    op.add_column('models', sa.Column('routing_provider_id', sa.String(length=12), nullable=True, comment='Optional provider to route through instead of the native one (aggregators like OpenRouter/OpenCode); NULL = use provider_id'))
    op.add_column('models', sa.Column('routing_identifier', sa.String(length=100), nullable=True, comment="Model identifier on the routing provider (e.g. 'deepseek/deepseek-v4' on OpenRouter, 'deepseek-v4-flash' on OpenCode Go)"))
    op.create_index(op.f('ix_models_routing_provider_id'), 'models', ['routing_provider_id'], unique=False)
    op.create_foreign_key(None, 'models', 'providers', ['routing_provider_id'], ['id'], ondelete='SET NULL')

    # Migrate existing OpenRouter-routed models to the generic override. Rows
    # whose native provider is already OpenRouter keep NULL (native == route), so
    # their active_identifier is unchanged.
    op.execute(
        """
        UPDATE models
        SET routing_provider_id = (SELECT id FROM providers WHERE provider_type = 'openrouter'),
            routing_identifier = openrouter_identifier
        WHERE use_openrouter = true
          AND provider_id <> (SELECT id FROM providers WHERE provider_type = 'openrouter')
        """
    )

    # Drop the OpenRouter-specific pair now that data is migrated.
    op.drop_index(op.f('ix_models_openrouter_identifier'), table_name='models')
    op.drop_index(op.f('ix_models_use_openrouter'), table_name='models')
    op.drop_column('models', 'openrouter_identifier')
    op.drop_column('models', 'use_openrouter')


def downgrade() -> None:
    # Re-add the OpenRouter pair (server_default so the NOT NULL add succeeds on
    # a populated table).
    op.add_column('models', sa.Column('use_openrouter', sa.BOOLEAN(), server_default=sa.false(), autoincrement=False, nullable=False, comment='If True, route through OpenRouter'))
    op.add_column('models', sa.Column('openrouter_identifier', sa.VARCHAR(length=100), autoincrement=False, nullable=True, comment="OpenRouter model identifier (e.g., 'openai/gpt-4o', 'sao10k/l3-euryale-70b')"))
    op.create_index(op.f('ix_models_use_openrouter'), 'models', ['use_openrouter'], unique=False)
    op.create_index(op.f('ix_models_openrouter_identifier'), 'models', ['openrouter_identifier'], unique=False)

    # Best-effort reverse: models with a routing override become OpenRouter-routed.
    op.execute(
        """
        UPDATE models
        SET use_openrouter = true, openrouter_identifier = routing_identifier
        WHERE routing_provider_id IS NOT NULL
        """
    )

    op.drop_constraint(None, 'models', type_='foreignkey')
    op.drop_index(op.f('ix_models_routing_provider_id'), table_name='models')
    op.drop_column('models', 'routing_identifier')
    op.drop_column('models', 'routing_provider_id')
