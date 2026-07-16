"""Cross-module read ports.

A service that needs to READ another slice's data (existence checks, lookups)
depends on one of these structural ``Protocol`` ports — NOT the foreign
``Repository`` class. The target slice's repository already satisfies them
structurally, so DI passes the concrete repo unchanged and the caller is
decoupled from the foreign data layer. Cross-module WRITES go through the target
slice's published service instead.
"""

from typing import Protocol

from src.core.persistence.base_model import BaseModel


class ExistsPort(Protocol):
    """Read port: does an entity with this id exist in the target slice?"""

    def exists(self, entity_id: str) -> bool: ...


class ReadPort[T: BaseModel](ExistsPort, Protocol):
    """Read port: existence check plus a typed lookup by id."""

    def find_by_id(self, entity_id: str) -> T | None: ...
