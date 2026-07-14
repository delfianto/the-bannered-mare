"""add data_bank_entry_id fk to embeddings

Gives data_bank embeddings a real FK to their owning entry (ON DELETE CASCADE),
so deleting an entry — directly or when its chat/character cascades — also removes
its embeddings instead of orphaning them (the polymorphic source_id has no FK).
Backfills existing data_bank embeddings and purges pre-existing orphans.

Revision ID: 33655fb747cf
Revises: a901608705cb
Create Date: 2026-07-14 13:54:59.270994

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '33655fb747cf'
down_revision = 'a901608705cb'
branch_labels = None
depends_on = None

_FK_NAME = "fk_embeddings_data_bank_entry_id"


def upgrade() -> None:
    op.add_column(
        'embeddings',
        sa.Column(
            'data_bank_entry_id',
            sa.String(length=12),
            nullable=True,
            comment=(
                'Owning entry for data_bank embeddings (null for messages); the FK '
                'cascades so deleting an entry — directly or when its chat/character '
                'is removed — also removes its embeddings instead of orphaning them'
            ),
        ),
    )

    # Backfill existing data_bank embeddings from their polymorphic source_id, then
    # drop any that are already orphaned (their entry no longer exists) so the FK
    # can be enforced without violation.
    op.execute(
        """
        UPDATE embeddings
        SET data_bank_entry_id = source_id
        WHERE source_type = 'data_bank'
          AND source_id IN (SELECT id FROM data_bank_entries)
        """
    )
    op.execute(
        """
        DELETE FROM embeddings
        WHERE source_type = 'data_bank'
          AND source_id NOT IN (SELECT id FROM data_bank_entries)
        """
    )

    op.create_index(
        op.f('ix_embeddings_data_bank_entry_id'),
        'embeddings',
        ['data_bank_entry_id'],
        unique=False,
    )
    op.create_foreign_key(
        _FK_NAME,
        'embeddings',
        'data_bank_entries',
        ['data_bank_entry_id'],
        ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint(_FK_NAME, 'embeddings', type_='foreignkey')
    op.drop_index(op.f('ix_embeddings_data_bank_entry_id'), table_name='embeddings')
    op.drop_column('embeddings', 'data_bank_entry_id')
