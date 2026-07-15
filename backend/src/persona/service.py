"""Persona business logic service"""

from typing import Any

from src.core.base_service import BaseCrudService, apply_update, set_as_default
from src.core.pagination import DEFAULT_PAGE_SIZE
from src.core.persistence import UnitOfWork, gen_id
from src.core.utils.storage import delete_persona_files, save_persona_avatar
from src.core.utils.upload import UploadedFile
from src.persona.models import Persona
from src.persona.repository import PersonaRepository

_EDITABLE = {"name", "description", "is_default"}


class PersonaService(BaseCrudService[Persona, PersonaRepository]):
    """Service for persona-related business logic (inherits list_all/get_by_id)."""

    def __init__(self, persona_repo: PersonaRepository, uow: UnitOfWork | None = None):
        super().__init__(persona_repo, uow or UnitOfWork(persona_repo.db), "Persona")

    def list_paginated(
        self, limit: int = DEFAULT_PAGE_SIZE, offset: int = 0, filters: dict[str, Any] | None = None
    ) -> tuple[list[Persona], int]:
        """List personas with pagination and filtering"""
        return self.repo.find_paginated_ordered(limit, offset, filters)

    async def create(
        self,
        name: str,
        description: str | None = None,
        is_default: bool = False,
        avatar: UploadedFile | None = None,
    ) -> Persona:
        """Create new persona with optional avatar upload"""
        if is_default:
            self.repo.unset_all_defaults()

        persona = Persona(
            id=gen_id(),
            name=name,
            description=description,
            is_default=is_default,
        )
        created = self.repo.create(persona)

        if avatar:
            original_path, large_path, thumbnail_path = await save_persona_avatar(
                created.id, avatar
            )
            created.avatar = original_path
            created.avatar_large = large_path
            created.avatar_thumbnail = thumbnail_path
            _ = self.repo.update(created)

        self.uow.commit()
        return created

    async def update(
        self,
        persona_id: str,
        name: str | None = None,
        description: str | None = None,
        is_default: bool | None = None,
        avatar: UploadedFile | None = None,
    ) -> Persona:
        """Update persona (skip-on-None: only provided fields change)."""
        persona = self.get_by_id(persona_id)

        if is_default:
            self.repo.unset_all_defaults(exclude_id=persona_id)

        patch = {"name": name, "description": description, "is_default": is_default}
        apply_update(persona, {k: v for k, v in patch.items() if v is not None}, _EDITABLE)

        if avatar:
            original_path, large_path, thumbnail_path = await save_persona_avatar(
                persona.id, avatar
            )
            persona.avatar = original_path
            persona.avatar_large = large_path
            persona.avatar_thumbnail = thumbnail_path

        updated = self.repo.update(persona)
        self.uow.commit()
        return updated

    def delete(self, persona_id: str) -> None:
        """Delete persona and associated files"""
        persona = self.get_by_id(persona_id)

        delete_persona_files(persona_id)

        self.repo.delete(persona)
        self.uow.commit()

    def set_default(self, persona_id: str) -> Persona:
        """Set persona as default"""
        return set_as_default(self.repo, self.get_by_id(persona_id), self.uow)
