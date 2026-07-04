"""add_provider_last_synced_at

Revision ID: bd16d2b144ef
Revises: 71042953805b
Create Date: 2026-07-04 21:34:25.855660

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bd16d2b144ef'
down_revision = '71042953805b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "providers",
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when the provider's models were last synced",
        ),
    )


def downgrade() -> None:
    op.drop_column("providers", "last_synced_at")
