"""Prompt Template CRUD business logic service"""

import logging
from typing import Any

from fastapi import HTTPException

from src.core.persistence import gen_id
from src.core.utils.template import TemplateService
from src.prompt_template.models import PromptTemplate
from src.prompt_template.repository import PromptTemplateRepository

logger = logging.getLogger(__name__)


class PromptTemplateService:
    """Service for prompt template CRUD operations (separate from template rendering service)"""

    def __init__(self, template_repo: PromptTemplateRepository):
        self.template_repo = template_repo
        self.template_service = TemplateService()

    def list_all(self) -> list[PromptTemplate]:
        """List all prompt templates"""
        return self.template_repo.find_all_ordered()

    def list_paginated(self, limit: int = 10, offset: int = 0) -> tuple[list[PromptTemplate], int]:
        """List templates with pagination"""
        return self.template_repo.find_paginated_with_count(limit, offset)

    def get_by_id(self, template_id: str) -> PromptTemplate:
        """Get prompt template by ID, raise 404 if not found"""
        template = self.template_repo.find_by_id(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Prompt template not found")
        return template

    def _validate_template_field(self, name: str, template_str: str | None) -> None:
        """Validate a Jinja2 template field, raising 400 if invalid."""
        if template_str is not None:
            is_valid, error = self.template_service.validate_template(template_str)
            if not is_valid:
                raise HTTPException(status_code=400, detail=f"Invalid {name} syntax: {error}")

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
            self.template_repo.unset_all_defaults()

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
        created = self.template_repo.create(template)
        self.template_repo.commit()

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
        """Update prompt template"""
        template = self.get_by_id(template_id)

        self._validate_template_field("system_template", system_template)

        if is_default:
            self.template_repo.unset_all_defaults(exclude_id=template_id)

        if name is not None:
            template.name = name
        if system_template is not None:
            template.system_template = system_template
        if description is not None:
            template.description = description
        if is_default is not None:
            template.is_default = is_default
        if component_order is not None:
            template.component_order = component_order
        if components_enabled is not None:
            template.components_enabled = components_enabled
        if max_history_tokens is not None:
            template.max_history_tokens = max_history_tokens

        updated = self.template_repo.update(template)
        self.template_repo.commit()

        return updated

    def delete(self, template_id: str) -> None:
        """Delete prompt template"""
        template = self.get_by_id(template_id)
        self.template_repo.delete(template)
        self.template_repo.commit()

    def set_default(self, template_id: str) -> PromptTemplate:
        """Set prompt template as default"""
        template = self.get_by_id(template_id)

        # Unset other defaults
        self.template_repo.unset_all_defaults()

        template.is_default = True
        _ = self.template_repo.update(template)
        self.template_repo.commit()

        return template
