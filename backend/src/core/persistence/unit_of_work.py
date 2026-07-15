"""Explicit transaction boundary for the service layer (BE-H1).

A service holds one ``UnitOfWork`` — a thin wrapper over the request-scoped
session its repositories share — and commits its work ONCE per operation.
Repositories keep only ``flush()``; they no longer own ``commit``/``rollback``,
so the transaction boundary is **explicit and singular** instead of an implicit
side effect of ``some_repo.commit()`` (which committed the whole shared session,
including every other repository's pending writes).

Construct one per request over the same session the repositories receive (the
service ``dependencies.py`` factories do this). A raised exception before
``commit()`` leaves the work pending; the request-scoped session is rolled back
when ``get_db`` closes it, so a failed operation persists nothing.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session


class UnitOfWork:
    """Owns the request-scoped transaction boundary for a service operation."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def commit(self) -> None:
        """Persist every pending change in this unit of work."""
        self._session.commit()

    def rollback(self) -> None:
        """Discard every pending change in this unit of work."""
        self._session.rollback()


class AsyncUnitOfWork:
    """Async counterpart of ``UnitOfWork`` (the ``chat_message`` streaming path).

    Wraps the request-scoped ``AsyncSession`` the async repositories share; the
    service commits its work via ``await uow.commit()``. Same rationale as the
    sync version — the boundary is explicit and singular, not a per-repo side
    effect.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        """Persist every pending change in this unit of work."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Discard every pending change in this unit of work."""
        await self._session.rollback()
