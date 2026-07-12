"""Shared service-layer helpers.

`get_or_404` replaces the ``find_by_id`` → raise-404 block that was copy-pasted
into every service's ``get_by_id``. It raises ``NotFoundError`` (a domain
exception) so the service layer stays HTTP-agnostic — the global handler in
``main.py`` maps it to a 404. A free helper (rather than a base class) keeps it
usable by services that hold specialised or multiple repositories.
"""

from src.core.exceptions import NotFoundError
from src.core.persistence.base_model import BaseModel
from src.core.persistence.base_repository import BaseRepository


def get_or_404[T: BaseModel](repo: BaseRepository[T], entity_id: str, resource_name: str) -> T:
    """Return the entity by id, or raise NotFoundError (→ HTTP 404).

    Args:
        repo: any repository exposing ``find_by_id``.
        entity_id: the id to look up.
        resource_name: human label for the 404 message (e.g. "Persona").
    """
    entity = repo.find_by_id(entity_id)
    if entity is None:
        raise NotFoundError(f"{resource_name} not found")
    return entity
