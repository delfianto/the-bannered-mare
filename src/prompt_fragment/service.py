"""Prompt fragment business logic service"""

from fastapi import HTTPException

from src.core.persistence import gen_id
from src.core.utils.template import TemplateService
from src.prompt_fragment.models import PromptFragment, TemplateFragment
from src.prompt_fragment.repository import FragmentRepository, TemplateFragmentRepository


class FragmentService:
    """Service for prompt fragment CRUD and template attachment operations"""

    def __init__(
        self,
        fragment_repo: FragmentRepository,
        template_fragment_repo: TemplateFragmentRepository,
    ):
        self.fragment_repo = fragment_repo
        self.template_fragment_repo = template_fragment_repo
        self.template_service = TemplateService()

    def _validate_content(self, content: str | None) -> None:
        """Validate Jinja2 content syntax, raising 400 if invalid."""
        if content is not None:
            is_valid, error = self.template_service.validate_template(content)
            if not is_valid:
                raise HTTPException(status_code=400, detail=f"Invalid Jinja2 content: {error}")

    # -- Fragment CRUD --

    def list_all(
        self,
        fragment_type: str | None = None,
        is_global: bool | None = None,
    ) -> list[PromptFragment]:
        """List fragments with optional filtering"""
        if fragment_type is not None:
            return self.fragment_repo.find_by_type(fragment_type)
        if is_global is True:
            return self.fragment_repo.find_global()
        return self.fragment_repo.find_all_ordered()

    def list_paginated(
        self,
        limit: int = 10,
        offset: int = 0,
        fragment_type: str | None = None,
        is_global: bool | None = None,
        unused_only: bool = False,
    ) -> tuple[list[PromptFragment], int]:
        """List fragments with pagination, filtering, and template-usage info"""
        return self.fragment_repo.find_paginated_with_usage(
            limit=limit,
            offset=offset,
            fragment_type=fragment_type,
            is_global=is_global,
            unused_only=unused_only,
        )

    def get_by_id(self, fragment_id: str) -> PromptFragment:
        """Get fragment by ID, raise 404 if not found"""
        fragment = self.fragment_repo.find_by_id(fragment_id)
        if not fragment:
            raise HTTPException(status_code=404, detail="Prompt fragment not found")
        return fragment

    def create(
        self,
        name: str,
        content: str,
        description: str | None = None,
        fragment_type: str = "instruction",
        is_global: bool = False,
    ) -> PromptFragment:
        """Create a new prompt fragment"""
        self._validate_content(content)

        fragment = PromptFragment(
            id=gen_id(),
            name=name,
            content=content,
            description=description,
            fragment_type=fragment_type,
            is_global=is_global,
        )
        created = self.fragment_repo.create(fragment)
        self.fragment_repo.commit()
        return created

    def update(
        self,
        fragment_id: str,
        name: str | None = None,
        content: str | None = None,
        description: str | None = None,
        fragment_type: str | None = None,
        is_global: bool | None = None,
    ) -> PromptFragment:
        """Update an existing prompt fragment"""
        fragment = self.get_by_id(fragment_id)
        self._validate_content(content)

        if name is not None:
            fragment.name = name
        if content is not None:
            fragment.content = content
        if description is not None:
            fragment.description = description
        if fragment_type is not None:
            fragment.fragment_type = fragment_type
        if is_global is not None:
            fragment.is_global = is_global

        updated = self.fragment_repo.update(fragment)
        self.fragment_repo.commit()
        return updated

    def delete(self, fragment_id: str) -> None:
        """Delete a prompt fragment"""
        fragment = self.get_by_id(fragment_id)
        self.fragment_repo.delete(fragment)
        self.fragment_repo.commit()

    # -- Template-Fragment attachment --

    def attach_to_template(
        self,
        template_id: str,
        fragment_id: str,
        position: str = "after_system",
        ordinal: int = 0,
    ) -> TemplateFragment:
        """Attach a fragment to a template at a given position"""
        # Verify the fragment exists
        self.get_by_id(fragment_id)

        existing = self.template_fragment_repo.find_by_template_and_fragment(
            template_id, fragment_id
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail="Fragment is already attached to this template",
            )

        tf = TemplateFragment(
            id=gen_id(),
            template_id=template_id,
            fragment_id=fragment_id,
            position=position,
            ordinal=ordinal,
        )
        created = self.template_fragment_repo.create(tf)
        self.template_fragment_repo.commit()
        return created

    def detach_from_template(self, template_id: str, fragment_id: str) -> None:
        """Detach a fragment from a template"""
        deleted = self.template_fragment_repo.delete_by_template_and_fragment(
            template_id, fragment_id
        )
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail="Fragment is not attached to this template",
            )
        self.template_fragment_repo.commit()

    def list_template_fragments(self, template_id: str) -> list[TemplateFragment]:
        """List all fragments attached to a template, ordered by position and ordinal"""
        return self.template_fragment_repo.find_by_template_id(template_id)

    def reorder_template_fragments(
        self, template_id: str, items: list[dict[str, str | int]]
    ) -> list[TemplateFragment]:
        """Bulk update positions/ordinals for a template's fragments.

        Each item must contain: fragment_id, position, ordinal
        """
        for item in items:
            fragment_id = str(item["fragment_id"])
            tf = self.template_fragment_repo.find_by_template_and_fragment(template_id, fragment_id)
            if not tf:
                raise HTTPException(
                    status_code=404,
                    detail=f"Fragment {fragment_id} is not attached to template {template_id}",
                )
            tf.position = str(item["position"])
            tf.ordinal = int(item["ordinal"])
            self.template_fragment_repo.update(tf)

        self.template_fragment_repo.commit()
        return self.template_fragment_repo.find_by_template_id(template_id)
