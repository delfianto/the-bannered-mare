"""add_provider_allowed_models

Revision ID: 9a3d7c1e5b24
Revises: bd16d2b144ef
Create Date: 2026-07-05 02:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '9a3d7c1e5b24'
down_revision = 'bd16d2b144ef'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "providers",
        sa.Column(
            "allowed_models",
            sa.JSON().with_variant(postgresql.ARRAY(sa.String()), "postgresql"),
            nullable=False,
            # Empty array backfills existing rows; NOT NULL ADD COLUMN needs a
            # default. Dropped afterwards so the ORM's `default=list` governs
            # new rows, matching the other StringList columns.
            server_default="{}",
            comment="Curated allow-list of provider-native model identifiers; empty means show all",
        ),
    )
    op.alter_column("providers", "allowed_models", server_default=None)


def downgrade() -> None:
    op.drop_column("providers", "allowed_models")
