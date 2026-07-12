"""Profile business logic service"""

from typing import Any

from fastapi import HTTPException, status

from src.core.base_service import get_or_404
from src.core.persistence import gen_id
from src.model.repository import ModelRepository
from src.persona.repository import PersonaRepository
from src.preset.repository import PresetRepository
from src.profile.models import Profile
from src.profile.repository import ProfileRepository
from src.prompt_template.repository import PromptTemplateRepository


class ProfileService:
    """Service for profile-related business logic"""

    def __init__(
        self,
        profile_repo: ProfileRepository,
        template_repo: PromptTemplateRepository,
        preset_repo: PresetRepository,
        persona_repo: PersonaRepository,
        model_repo: ModelRepository,
    ):
        self.profile_repo = profile_repo
        self.template_repo = template_repo
        self.preset_repo = preset_repo
        self.persona_repo = persona_repo
        self.model_repo = model_repo

    def list_all(self) -> list[Profile]:
        """List all profiles"""
        return self.profile_repo.find_all_ordered()

    def list_paginated(self, limit: int = 10, offset: int = 0) -> tuple[list[Profile], int]:
        """List profiles with pagination"""
        return self.profile_repo.find_paginated_with_count(limit, offset)

    def get_by_id(self, profile_id: str) -> Profile:
        """Get profile by ID, raise 404 if not found"""
        return get_or_404(self.profile_repo, profile_id, "Profile")

    def create(
        self,
        name: str,
        description: str | None = None,
        is_default: bool = False,
        prompt_template_id: str | None = None,
        preset_id: str | None = None,
        persona_id: str | None = None,
        model_id: str | None = None,
        task_model_id: str | None = None,
    ) -> Profile:
        """Create new profile, validating any referenced entities exist."""
        self._validate_refs(prompt_template_id, preset_id, persona_id, model_id, task_model_id)

        if is_default:
            self.profile_repo.unset_all_defaults()

        profile = Profile(
            id=gen_id(),
            name=name,
            description=description,
            is_default=is_default,
            prompt_template_id=prompt_template_id,
            preset_id=preset_id,
            persona_id=persona_id,
            model_id=model_id,
            task_model_id=task_model_id,
        )
        created = self.profile_repo.create(profile)
        self.profile_repo.commit()
        return created

    def update(self, profile_id: str, updates: dict[str, Any]) -> Profile:
        """Update a profile from a partial payload (fields the client actually sent).

        Only keys present in ``updates`` are touched; an explicit ``None`` CLEARS
        that field — this is how a loadout's model/persona/preset/task model gets
        unselected. Provided non-null FK ids are validated for existence.
        """
        profile = self.get_by_id(profile_id)

        self._validate_refs(
            updates.get("prompt_template_id"),
            updates.get("preset_id"),
            updates.get("persona_id"),
            updates.get("model_id"),
            updates.get("task_model_id"),
        )

        if updates.get("is_default"):
            self.profile_repo.unset_all_defaults(exclude_id=profile_id)

        editable = {
            "name",
            "description",
            "is_default",
            "prompt_template_id",
            "preset_id",
            "persona_id",
            "model_id",
            "task_model_id",
        }
        for key, value in updates.items():
            if key not in editable:
                continue
            # Name is required — ignore an attempt to clear it.
            if key == "name" and not value:
                continue
            setattr(profile, key, value)

        updated = self.profile_repo.update(profile)
        self.profile_repo.commit()
        return updated

    def delete(self, profile_id: str) -> None:
        """Delete profile"""
        profile = self.get_by_id(profile_id)
        self.profile_repo.delete(profile)
        self.profile_repo.commit()

    def set_default(self, profile_id: str) -> Profile:
        """Set profile as default"""
        profile = self.get_by_id(profile_id)

        self.profile_repo.unset_all_defaults()

        profile.is_default = True
        updated = self.profile_repo.update(profile)
        self.profile_repo.commit()
        return updated

    def _validate_refs(
        self,
        prompt_template_id: str | None,
        preset_id: str | None,
        persona_id: str | None,
        model_id: str | None,
        task_model_id: str | None = None,
    ) -> None:
        """Raise 404 for any provided reference that does not resolve to a row."""
        if prompt_template_id is not None and not self.template_repo.exists(prompt_template_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt template with ID '{prompt_template_id}' not found",
            )
        if preset_id is not None and not self.preset_repo.exists(preset_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Preset with ID '{preset_id}' not found",
            )
        if persona_id is not None and not self.persona_repo.exists(persona_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona with ID '{persona_id}' not found",
            )
        if model_id is not None and not self.model_repo.exists(model_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model with ID '{model_id}' not found",
            )
        if task_model_id is not None and not self.model_repo.exists(task_model_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task model with ID '{task_model_id}' not found",
            )
