"""Shared service-layer helpers.

`get_or_404` replaces the ``find_by_id`` → raise-404 block that was copy-pasted
into every service's ``get_by_id``. It raises ``NotFoundError`` (a domain
exception) so the service layer stays HTTP-agnostic — the global handler in
``main.py`` maps it to a 404. A free helper (rather than a base class) keeps it
usable by services that hold specialised or multiple repositories.
"""

from collections.abc import Awaitable, Callable

from src.core.exceptions import NotFoundError
from src.core.persistence.base_model import BaseModel
from src.core.persistence.base_repository import DefaultableRepository
from src.core.persistence.base_repository_async import AsyncBaseRepository
from src.core.persistence.ports import ReadPort
from src.core.persistence.unit_of_work import UnitOfWork


def get_or_404[T: BaseModel](repo: ReadPort[T], entity_id: str, resource_name: str) -> T:
    """Return the entity by id, or raise NotFoundError (→ HTTP 404).

    Args:
        repo: any read port / repository exposing ``find_by_id`` (BE-H2 — lets a
            cross-module caller pass a thin ``ReadPort`` instead of a foreign repo).
        entity_id: the id to look up.
        resource_name: human label for the 404 message (e.g. "Persona").
    """
    entity = repo.find_by_id(entity_id)
    if entity is None:
        raise NotFoundError(f"{resource_name} not found")
    return entity


async def async_get_or_404[T: BaseModel](
    repo: AsyncBaseRepository[T],
    entity_id: str,
    resource_name: str,
    finder: Callable[[str], Awaitable[T | None]] | None = None,
) -> T:
    """Async counterpart to ``get_or_404``.

    Pass ``finder`` to use a specialised lookup (e.g. a relations-eager variant);
    defaults to ``repo.find_by_id``.
    """
    lookup = finder or repo.find_by_id
    entity = await lookup(entity_id)
    if entity is None:
        raise NotFoundError(f"{resource_name} not found")
    return entity


def set_as_default[T: BaseModel](repo: DefaultableRepository[T], entity: T, uow: UnitOfWork) -> T:
    """Make ``entity`` the sole default row, commit, and return it reloaded.

    Collapses the identical ``set_default`` bodies across the persona / preset /
    profile / prompt-template services. Commits through the service's unit of
    work (BE-H1) — the single, explicit transaction boundary for the operation.
    """
    repo.set_default(entity.id)
    uow.commit()
    repo.refresh(entity)
    return entity
