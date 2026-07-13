"""Persona business logic service"""

from typing import Any

from fastapi import UploadFile

from src.core.base_service import get_or_404, set_as_default
from src.core.persistence import gen_id
from src.core.utils.storage import delete_persona_files, save_persona_avatar
from src.persona.models import Persona
from src.persona.repository import PersonaRepository


class PersonaService:
    """Service for persona-related business logic"""

    def __init__(self, persona_repo: PersonaRepository):
        self.persona_repo = persona_repo

    def list_all(self) -> list[Persona]:
        """List all personas"""
        return self.persona_repo.find_all_ordered()

    def list_paginated(
        self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
    ) -> tuple[list[Persona], int]:
        """List personas with pagination and filtering"""
        return self.persona_repo.find_paginated_ordered(limit, offset, filters)

    def get_by_id(self, persona_id: str) -> Persona:
        """Get persona by ID, raise 404 if not found"""
        return get_or_404(self.persona_repo, persona_id, "Persona")

    async def create(
        self,
        name: str,
        description: str | None = None,
        is_default: bool = False,
        avatar: UploadFile | None = None,
    ) -> Persona:
        """Create new persona with optional avatar upload"""
        # If setting as default, unset other defaults
        if is_default:
            self.persona_repo.unset_all_defaults()

        persona = Persona(
            id=gen_id(),
            name=name,
            description=description,
            is_default=is_default,
        )
        created = self.persona_repo.create(persona)

        if avatar:
            original_path, large_path, thumbnail_path = await save_persona_avatar(
                created.id, avatar
            )
            created.avatar = original_path
            created.avatar_large = large_path
            created.avatar_thumbnail = thumbnail_path
            _ = self.persona_repo.update(created)

        self.persona_repo.commit()
        return created

    async def update(
        self,
        persona_id: str,
        name: str | None = None,
        description: str | None = None,
        is_default: bool | None = None,
        avatar: UploadFile | None = None,
    ) -> Persona:
        """Update persona"""
        persona = self.get_by_id(persona_id)

        # If setting as default, unset other defaults
        if is_default:
            self.persona_repo.unset_all_defaults(exclude_id=persona_id)

        if name is not None:
            persona.name = name
        if description is not None:
            persona.description = description
        if is_default is not None:
            persona.is_default = is_default

        # Update avatar if provided
        if avatar:
            original_path, large_path, thumbnail_path = await save_persona_avatar(
                persona.id, avatar
            )
            persona.avatar = original_path
            persona.avatar_large = large_path
            persona.avatar_thumbnail = thumbnail_path
        updated = self.persona_repo.update(persona)
        self.persona_repo.commit()

        return updated

    def delete(self, persona_id: str) -> None:
        """Delete persona and associated files"""
        persona = self.get_by_id(persona_id)

        # Delete persona files
        delete_persona_files(persona_id)

        self.persona_repo.delete(persona)
        self.persona_repo.commit()

    def set_default(self, persona_id: str) -> Persona:
        """Set persona as default"""
        return set_as_default(self.persona_repo, self.get_by_id(persona_id))
