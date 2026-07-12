"""Shared Chat query builders for the sync + async chat repositories.

Both repos need the identical ordered/cursor SELECTs (they differ only in
execution — ``execute`` vs ``await execute``); building the statements here keeps
the two in lockstep. ``find_by_id_with_relations`` stays async-only in its repo.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import joinedload

from src.chat_session.models import Chat
from src.core.persistence.statements import apply_filters


def _with_character() -> Select[tuple[Chat]]:
    return select(Chat).options(joinedload(Chat.character))


def all_ordered_stmt() -> Select[tuple[Chat]]:
    """All chats, newest first, with the character eager-loaded."""
    return _with_character().order_by(Chat.created_at.desc())


def by_id_with_character_stmt(chat_id: str) -> Select[tuple[Chat]]:
    return _with_character().where(Chat.id == chat_id)


def by_character_stmt(character_id: str) -> Select[tuple[Chat]]:
    return select(Chat).where(Chat.character_id == character_id)


def bookmarked_stmt() -> Select[tuple[Chat]]:
    """Bookmarked chats, newest first, with the character eager-loaded."""
    return _with_character().where(Chat.is_bookmarked.is_(True)).order_by(Chat.created_at.desc())


def ordered_page_stmts(
    limit: int, offset: int, filters: dict[str, Any] | None
) -> tuple[Select[Any], Select[tuple[Chat]]]:
    """(count_stmt, page_stmt) for offset pagination ordered by created_at desc."""
    base = apply_filters(Chat, _with_character(), filters)
    count_stmt = select(func.count()).select_from(base.subquery())
    page_stmt = base.order_by(Chat.created_at.desc()).limit(limit).offset(offset)
    return count_stmt, page_stmt


def cursor_page_stmt(
    limit: int, cursor: datetime | None, filters: dict[str, Any] | None
) -> Select[tuple[Chat]]:
    """updated_at-desc cursor page; fetches limit+1 so callers can detect more."""
    stmt = apply_filters(Chat, _with_character(), filters)
    if cursor:
        stmt = stmt.where(Chat.updated_at < cursor)
    return stmt.order_by(Chat.updated_at.desc()).limit(limit + 1)


def split_cursor_page(items: list[Chat], limit: int) -> tuple[list[Chat], bool]:
    """Trim the limit+1 fetch to `limit` and report whether more remain."""
    if len(items) > limit:
        return items[:limit], True
    return items, False
