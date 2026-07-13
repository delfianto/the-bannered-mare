"""add embeddings.chat_id scope for message retrieval

Revision ID: b180e88fbb19
Revises: fc4ea3fcd13f
Create Date: 2026-07-14 00:46:07.703586

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b180e88fbb19'
down_revision = 'fc4ea3fcd13f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'embeddings',
        sa.Column(
            'chat_id',
            sa.String(length=12),
            nullable=True,
            comment='Chat scope for message embeddings (null for data_bank); retrieval matches message embeddings on this, and chat deletion cascades',
        ),
    )
    op.create_index(op.f('ix_embeddings_chat_id'), 'embeddings', ['chat_id'], unique=False)
    op.create_foreign_key(
        'embeddings_chat_id_fkey', 'embeddings', 'chats', ['chat_id'], ['id'], ondelete='CASCADE'
    )

    # Data migration: existing message embeddings pre-date this column and were
    # unretrievable (retrieval scopes messages by chat_id). Backfill chat_id from
    # the owning message where it still exists, then drop the rows whose message
    # was already deleted (previously un-cascaded leaks). Data-bank embeddings keep
    # chat_id NULL.
    op.execute(
        """
        UPDATE embeddings AS e
        SET chat_id = m.chat_id
        FROM messages AS m
        WHERE e.source_type = 'message' AND e.source_id = m.id
        """
    )
    op.execute("DELETE FROM embeddings WHERE source_type = 'message' AND chat_id IS NULL")


def downgrade() -> None:
    op.drop_constraint('embeddings_chat_id_fkey', 'embeddings', type_='foreignkey')
    op.drop_index(op.f('ix_embeddings_chat_id'), table_name='embeddings')
    op.drop_column('embeddings', 'chat_id')
