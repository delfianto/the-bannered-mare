"""remove temporal macros from template system_template strings

{{time}}/{{date}} in system_template re-render every minute/day, busting the
prompt cache from token 0 and forcing full reprocessing of the entire prompt
every turn. The builder now emits rag_context after chat_history and uses
block-chunked history eviction; temporal macros were the last cache-busting
holdout in the scaffolding. They're removed from the seed fixtures and scrubbed
from existing rows here. If wall-clock context is wanted, put it in a
post_history fragment (after the cached prefix) instead.

Revision ID: d7e2a1b93c41
Revises: 66164612ed0d
Create Date: 2026-07-13 19:30:00.000000

"""

import re

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d7e2a1b93c41"
down_revision = "66164612ed0d"
branch_labels = None
depends_on = None

# Matches lines that are just temporal-macro references (with optional label):
#   "Current date and time: {{date}} {{time}}"
#   "Current session: {{date}} at {{time}}"
#   "Current date: {{date}}"
#   "Current time: {{time}}"
_TEMPORAL_LINE = re.compile(
    r"^\s*(?:Current\s+(?:date(?:\s+and\s+time)?|time|session)\s*[:]?\s*)?"
    r"\{\{\s*(?:date|time)\s*\}\}"
    r"(?:\s+(?:at\s+)?\{\{\s*(?:date|time)\s*\}\})?"
    r"\s*$",
    re.MULTILINE,
)


def _scrub(template: str) -> str:
    """Remove temporal-macro lines and any trailing blank lines they leave behind."""
    cleaned = _TEMPORAL_LINE.sub("", template)
    return cleaned.rstrip() + "\n" if cleaned != template else template


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, system_template FROM prompt_templates")).fetchall()
    for row in rows:
        cleaned = _scrub(row[1])
        if cleaned != row[1]:
            conn.execute(
                sa.text("UPDATE prompt_templates SET system_template = :tpl WHERE id = :id"),
                {"tpl": cleaned, "id": row[0]},
            )


def downgrade() -> None:
    # Temporal macros were removed intentionally; no backward value in restoring them.
    pass
