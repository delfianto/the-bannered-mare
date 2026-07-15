"""Profile business logic service"""

from typing import Any

from src.core.base_service import get_or_404, set_as_default
from src.core.exceptions import NotFoundError
from src.core.persistence import ExistsPort, UnitOfWork, gen_id
from src.profile.models import Profile
from src.profile.repository import ProfileRepository


class ProfileService:
    """Service for profile-related business logic"""

    def __init__(
        self,
        profile_repo: ProfileRepository,
        template_repo: ExistsPort,
        preset_repo: ExistsPort,
        persona_repo: ExistsPort,
        model_repo: ExistsPort,
        uow: UnitOfWork | None = None,
    ):
        self.profile_repo = profile_repo
        self.template_repo = template_repo
        self.preset_repo = preset_repo
        self.persona_repo = persona_repo
        self.model_repo = model_repo
        # The unit of work owns the transaction boundary; it wraps the same session
        # the repos share. Fallback keeps direct `ProfileService(...)` construction
        # (tests) valid — the DI factory injects the request-scoped UoW.
        self.uow = uow or UnitOfWork(profile_repo.db)

    def list_all(self) -> list[Profile]:
        """List all profiles"""
        return self.profile_repo.find_all_ordered()

    def list_paginated(self, limit: int = 10, offset: int = 0) -> tuple[list[Profile], int]:
        """List profiles with pagination"""
        return self.profile_repo.find_paginated_ordered(limit, offset)

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
        self.uow.commit()
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
        self.uow.commit()
        return updated

    def delete(self, profile_id: str) -> None:
        """Delete profile"""
        profile = self.get_by_id(profile_id)
        self.profile_repo.delete(profile)
        self.uow.commit()

    # --- SillyTavern import seam (BE-H2) ---

    def find_by_name(self, name: str) -> Profile | None:
        """Look up a profile by exact name (import unique-naming)."""
        return self.profile_repo.find_by_name(name)

    def create_imported(
        self,
        name: str,
        prompt_template_id: str,
        preset_id: str | None,
        description: str | None = None,
        source: str | None = None,
        source_filename: str | None = None,
    ) -> Profile:
        """Create a profile from a trusted import (its FKs were created in this unit).

        Flush-only — participates in the caller's UoW; skips ``_validate_refs`` since
        the template/preset were just created in the same transaction, and records
        the import provenance (``source``/``source_filename``).
        """
        profile = Profile(
            id=gen_id(),
            name=name,
            description=description,
            prompt_template_id=prompt_template_id,
            preset_id=preset_id,
            source=source,
            source_filename=source_filename,
            is_default=False,
        )
        return self.profile_repo.create(profile)

    def set_default(self, profile_id: str) -> Profile:
        """Set profile as default"""
        return set_as_default(self.profile_repo, self.get_by_id(profile_id), self.uow)

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
            raise NotFoundError(f"Prompt template with ID '{prompt_template_id}' not found")
        if preset_id is not None and not self.preset_repo.exists(preset_id):
            raise NotFoundError(f"Preset with ID '{preset_id}' not found")
        if persona_id is not None and not self.persona_repo.exists(persona_id):
            raise NotFoundError(f"Persona with ID '{persona_id}' not found")
        if model_id is not None and not self.model_repo.exists(model_id):
            raise NotFoundError(f"Model with ID '{model_id}' not found")
        if task_model_id is not None and not self.model_repo.exists(task_model_id):
            raise NotFoundError(f"Task model with ID '{task_model_id}' not found")
