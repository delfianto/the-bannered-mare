"""move rag_context after chat_history in stored component_order

Prompt-cache correctness: rag_context is rebuilt every turn from a semantic
query, so when it sits before chat_history it severs the cacheable prefix and
forces the entire conversation to be reprocessed at full price. The builder now
emits rag_context authoritatively after chat_history regardless of stored order;
this migration aligns the stored ``component_order`` rows so they match reality.

Revision ID: a8c4f2e91d07
Revises: 4b09e82135f5
Create Date: 2026-07-13 14:00:00.000000

"""

import json

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a8c4f2e91d07"
down_revision = "4b09e82135f5"
branch_labels = None
depends_on = None


def _reorder(order: list[str], *, after: bool) -> list[str]:
    """Move ``rag_context`` relative to ``chat_history``.

    ``after=True`` places it immediately after chat_history (upgrade);
    ``after=False`` places it immediately before (downgrade).
    """
    order = list(order)
    if "rag_context" not in order or "chat_history" not in order:
        return order
    order.remove("rag_context")
    idx = order.index("chat_history")
    order.insert(idx + 1 if after else idx, "rag_context")
    return order


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, component_order FROM prompt_templates")).fetchall()
    for row in rows:
        new_order = _reorder(list(row[1]), after=True)
        conn.execute(
            sa.text("UPDATE prompt_templates SET component_order = CAST(:order AS json) WHERE id = :id"),
            {"order": json.dumps(new_order), "id": row[0]},
        )


def downgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, component_order FROM prompt_templates")).fetchall()
    for row in rows:
        old_order = _reorder(list(row[1]), after=False)
        conn.execute(
            sa.text("UPDATE prompt_templates SET component_order = CAST(:order AS json) WHERE id = :id"),
            {"order": json.dumps(old_order), "id": row[0]},
        )
