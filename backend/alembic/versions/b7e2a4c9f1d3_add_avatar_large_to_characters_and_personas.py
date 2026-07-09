"""add avatar_large to characters and personas

Revision ID: b7e2a4c9f1d3
Revises: d6b575f2458a
Create Date: 2026-07-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7e2a4c9f1d3'
down_revision = 'd6b575f2458a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'characters',
        sa.Column(
            'avatar_large',
            sa.String(length=255),
            nullable=True,
            comment='Path to the large (<=512px) full-portrait avatar',
        ),
    )
    op.add_column(
        'personas',
        sa.Column(
            'avatar_large',
            sa.String(length=255),
            nullable=True,
            comment='Path to the large (<=512px) full-portrait avatar',
        ),
    )


def downgrade() -> None:
    op.drop_column('personas', 'avatar_large')
    op.drop_column('characters', 'avatar_large')
