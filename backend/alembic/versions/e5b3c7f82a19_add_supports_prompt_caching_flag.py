"""add supports_prompt_caching to model family extra_metadata

Flags each model family's extra_metadata JSON with supports_prompt_caching
(true for cloud-routed models that report cache_read_tokens, false for
local-only families where KV reuse is implicit but not reported in usage).

Revision ID: e5b3c7f82a19
Revises: d7e2a1b93c41
Create Date: 2026-07-13 20:30:00.000000

"""

import json

import sqlalchemy as sa
from alembic import op

revision = "e5b3c7f82a19"
down_revision = "d7e2a1b93c41"
branch_labels = None
depends_on = None

_LOCAL_ONLY_LINEAGES = frozenset({"gemma", "llama", "mistral"})


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, extra_metadata FROM model_families")).fetchall()
    for row in rows:
        meta = row[1]
        if meta is None:
            meta = {}
        if "supports_prompt_caching" in meta:
            continue
        lineage = meta.get("lineage", "")
        is_local = any(loc == lineage for loc in _LOCAL_ONLY_LINEAGES)
        meta["supports_prompt_caching"] = not is_local
        conn.execute(
            sa.text("UPDATE model_families SET extra_metadata = CAST(:meta AS json) WHERE id = :id"),
            {"meta": json.dumps(meta), "id": row[0]},
        )


def downgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, extra_metadata FROM model_families")).fetchall()
    for row in rows:
        meta = row[1]
        if meta is None:
            continue
        meta.pop("supports_prompt_caching", None)
        conn.execute(
            sa.text("UPDATE model_families SET extra_metadata = CAST(:meta AS json) WHERE id = :id"),
            {"meta": json.dumps(meta), "id": row[0]},
        )
