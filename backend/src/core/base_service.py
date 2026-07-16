"""Shared service-layer helpers.

`get_or_404` replaces the ``find_by_id`` → raise-404 block that was copy-pasted
into every service's ``get_by_id``. It raises ``NotFoundError`` (a domain
exception) so the service layer stays HTTP-agnostic — the global handler in
``main.py`` maps it to a 404. A free helper (rather than a base class) keeps it
usable by services that hold specialised or multiple repositories.
"""

from typing import Any

from src.core.exceptions import NotFoundError
from src.core.persistence.base_model import BaseModel
from src.core.persistence.base_repository import BaseRepository, DefaultableRepository
from src.core.persistence.ports import ReadPort
from src.core.persistence.unit_of_work import UnitOfWork


def get_or_404[T: BaseModel](repo: ReadPort[T], entity_id: str, resource_name: str) -> T:
    """Return the entity by id, or raise NotFoundError (→ HTTP 404).

    Args:
        repo: any read port / repository exposing ``find_by_id`` (lets a
            cross-module caller pass a thin ``ReadPort`` instead of a foreign repo).
        entity_id: the id to look up.
        resource_name: human label for the 404 message (e.g. "Persona").
    """
    entity = repo.find_by_id(entity_id)
    if entity is None:
        raise NotFoundError(f"{resource_name} not found")
    return entity


def set_as_default[T: BaseModel](repo: DefaultableRepository[T], entity: T, uow: UnitOfWork) -> T:
    """Make ``entity`` the sole default row, commit, and return it reloaded.

    Collapses the identical ``set_default`` bodies across the persona / preset /
    profile / prompt-template services. Commits through the service's unit of
    work — the single, explicit transaction boundary for the operation.
    """
    repo.set_default(entity.id)
    uow.commit()
    repo.refresh(entity)
    return entity


def apply_update(entity: BaseModel, patch: dict[str, Any], editable: set[str]) -> None:
    """Apply a partial-update ``patch`` to ``entity`` — the one update mechanism.

    Sets each ``patch`` key that is in ``editable`` (an explicit ``None`` clears that
    field). Keys outside ``editable`` are ignored, so an over-posted payload can't
    write unintended columns. The CALLER decides what goes in ``patch`` — that is the
    endpoint's null policy in one place: a "skip-on-None" update omits the None keys;
    a "clearable" update includes them.
    """
    for key, value in patch.items():
        if key in editable:
            setattr(entity, key, value)


class BaseCrudService[T: BaseModel, R: BaseRepository[Any]]:
    """Generic CRUD over a single primary repository + unit of work.

    Subclasses pass their concrete repository, the request-scoped unit of work, and a
    human resource name, then inherit ``list_all`` / ``get_by_id`` / ``delete`` and use
    ``apply_update`` for partial updates. ``self.repo`` keeps the subclass's concrete
    repository type, so slice-specific queries stay available. Non-generic behavior
    (extra collaborators, file side effects, custom list/delete) stays in the subclass,
    which overrides these methods where it must.
    """

    def __init__(self, repo: R, uow: UnitOfWork, resource_name: str):
        self.repo: R = repo
        self.uow = uow
        self._resource_name = resource_name

    def list_all(self) -> list[T]:
        """List all rows, name-ordered. Override for a different order/query."""
        return self.repo.find_all_ordered()

    def get_by_id(self, entity_id: str) -> T:
        """Return the row by id, or raise NotFoundError (→ HTTP 404)."""
        return get_or_404(self.repo, entity_id, self._resource_name)

    def delete(self, entity_id: str, /) -> None:
        """Delete the row (plain). Override when deletion has side effects."""
        entity = self.get_by_id(entity_id)
        self.repo.delete(entity)
        self.uow.commit()
