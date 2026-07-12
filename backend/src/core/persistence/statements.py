"""Session-agnostic SQLAlchemy query helpers shared by the base repositories.

The sync and async base repositories differ only in *execution* (``execute`` vs
``await execute``); the dynamic filter construction is identical, so it lives
here (written once) and both delegate to it.
"""

from typing import Any

from sqlalchemy import Select

from src.core.persistence.base_model import BaseModel

# op suffix -> callable building the SQLAlchemy comparison for a column/value.
_OPERATORS = {
    "eq": lambda col, val: col == val,
    "ne": lambda col, val: col != val,
    "gt": lambda col, val: col > val,
    "ge": lambda col, val: col >= val,
    "lt": lambda col, val: col < val,
    "le": lambda col, val: col <= val,
    "in": lambda col, val: col.in_(val),
    "like": lambda col, val: col.like(f"%{val}%"),
    "ilike": lambda col, val: col.ilike(f"%{val}%"),
}


def apply_filters[T: BaseModel](
    model: type[T], stmt: Select[Any], filters: dict[str, Any] | None
) -> Select[Any]:
    """Add WHERE clauses from a ``{"field__op": value}`` dict.

    Supported ops: eq (default), ne, gt, lt, ge, le, in, like, ilike. Unknown
    fields and None values are skipped.
    """
    if not filters:
        return stmt
    for key, value in filters.items():
        if value is None:
            continue
        field_name, _, op = key.partition("__")
        op = op or "eq"
        if not hasattr(model, field_name) or op not in _OPERATORS:
            continue
        stmt = stmt.where(_OPERATORS[op](getattr(model, field_name), value))
    return stmt
