"""add opencode and opencode_go provider types

Revision ID: c1f2e3a4b5d6
Revises: b7e2a4c9f1d3
Create Date: 2026-07-10 10:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'c1f2e3a4b5d6'
down_revision = 'b7e2a4c9f1d3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Postgres requires ALTER TYPE ... ADD VALUE to run outside a transaction
    # block; autocommit_block temporarily commits and switches to autocommit.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE providertype ADD VALUE IF NOT EXISTS 'opencode'")
        op.execute("ALTER TYPE providertype ADD VALUE IF NOT EXISTS 'opencode_go'")


def downgrade() -> None:
    # Postgres cannot drop a value from an enum type without recreating it and
    # rewriting every dependent column; since providers of these types may exist,
    # removal is unsafe. Leaving the values in place is a harmless no-op.
    pass
