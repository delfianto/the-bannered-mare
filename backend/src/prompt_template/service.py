"""Prompt Template CRUD business logic service"""

import logging
from typing import Any

from src.core.base_service import BaseCrudService, apply_update, set_as_default
from src.core.exceptions import ValidationError
from src.core.pagination import DEFAULT_PAGE_SIZE
from src.core.persistence import UnitOfWork, gen_id
from src.prompt_fragment.service import FragmentService
from src.prompt_template.models import PromptTemplate
from src.prompt_template.repository import PromptTemplateRepository
from src.templating import TemplateService

logger = logging.getLogger(__name__)

_EDITABLE = {
    "name",
    "system_template",
    "description",
    "is_default",
    "component_order",
    "components_enabled",
    "max_history_tokens",
}


class PromptTemplateService(BaseCrudService[PromptTemplate, PromptTemplateRepository]):
    """Prompt template CRUD (separate from the template-rendering service)."""

    def __init__(
        self,
        template_repo: PromptTemplateRepository,
        fragment_service: FragmentService | None = None,
        template_service: TemplateService | None = None,
        uow: UnitOfWork | None = None,
    ):
        super().__init__(template_repo, uow or UnitOfWork(template_repo.db), "Prompt template")
        # Orphan cleanup on delete goes through the fragment slice's published
        # service, not its repository (BE-H2). Fallback keeps direct construction
        # (tests) valid — the DI factory injects the request-scoped service.
        self.fragment_service = fragment_service or FragmentService.from_session(template_repo.db)
        self.template_service = template_service or TemplateService()

    def list_paginated(
        self, limit: int = DEFAULT_PAGE_SIZE, offset: int = 0
    ) -> tuple[list[PromptTemplate], int]:
        """List templates with pagination"""
        return self.repo.find_paginated_ordered(limit, offset)

    # --- SillyTavern import seam (BE-H2) ---

    def find_by_name(self, name: str) -> PromptTemplate | None:
        """Look up a template by exact name (import unique-naming)."""
        return self.repo.find_by_name(name)

    def create_imported(
        self,
        name: str,
        system_template: str,
        description: str | None = None,
        component_order: list[str] | None = None,
        components_enabled: dict[str, Any] | None = None,
    ) -> PromptTemplate:
        """Create a template from a trusted import, skipping Jinja2 validation.

        Flush-only — SillyTavern templates carry ST-specific macros the normal
        ``create`` would reject, and the whole preset import must commit as one
        transaction under the caller's unit of work.
        """
        template = PromptTemplate(
            id=gen_id(),
            name=name,
            system_template=system_template,
            description=description,
            is_default=False,
            component_order=component_order,
            components_enabled=components_enabled,
        )
        return self.repo.create(template)

    def _validate_template_field(self, name: str, template_str: str | None) -> None:
        """Validate a Jinja2 template field, raising 400 if invalid."""
        if template_str is not None:
            is_valid, error = self.template_service.validate_template(template_str)
            if not is_valid:
                raise ValidationError(f"Invalid {name} syntax: {error}")

    def create(
        self,
        name: str,
        system_template: str,
        description: str | None = None,
        is_default: bool = False,
        component_order: list[str] | None = None,
        components_enabled: dict[str, Any] | None = None,
        max_history_tokens: int | None = None,
    ) -> PromptTemplate:
        """Create new prompt template"""
        self._validate_template_field("system_template", system_template)

        if is_default:
            self.repo.unset_all_defaults()

        template = PromptTemplate(
            id=gen_id(),
            name=name,
            system_template=system_template,
            description=description,
            is_default=is_default,
            component_order=component_order,
            components_enabled=components_enabled,
            max_history_tokens=max_history_tokens,
        )
        created = self.repo.create(template)
        self.uow.commit()

        return created

    def update(
        self,
        template_id: str,
        name: str | None = None,
        system_template: str | None = None,
        description: str | None = None,
        is_default: bool | None = None,
        component_order: list[str] | None = None,
        components_enabled: dict[str, Any] | None = None,
        max_history_tokens: int | None = None,
    ) -> PromptTemplate:
        """Update prompt template (skip-on-None: only provided fields change)."""
        template = self.get_by_id(template_id)

        self._validate_template_field("system_template", system_template)

        if is_default:
            self.repo.unset_all_defaults(exclude_id=template_id)

        patch = {
            "name": name,
            "system_template": system_template,
            "description": description,
            "is_default": is_default,
            "component_order": component_order,
            "components_enabled": components_enabled,
            "max_history_tokens": max_history_tokens,
        }
        apply_update(template, {k: v for k, v in patch.items() if v is not None}, _EDITABLE)

        updated = self.repo.update(template)
        self.uow.commit()

        return updated

    def delete(self, template_id: str) -> None:
        """Delete prompt template.

        Also removes any attached fragments left with no other usage — ST-imported
        fragments are private to the template that generated them, not a shared
        library entry, so they shouldn't outlive the only thing that used them.
        """
        template = self.get_by_id(template_id)
        fragment_ids = [tf.fragment_id for tf in template.template_fragments]
        self.repo.delete(template)
        cleaned_up = self.fragment_service.delete_orphaned(fragment_ids)
        self.uow.commit()
        if cleaned_up:
            logger.info(
                "Cleaned up %d orphaned fragment(s) after deleting template %s",
                cleaned_up,
                template_id,
            )

    def set_default(self, template_id: str) -> PromptTemplate:
        """Set prompt template as default"""
        return set_as_default(self.repo, self.get_by_id(template_id), self.uow)
