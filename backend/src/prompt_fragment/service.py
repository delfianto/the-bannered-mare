"""Prompt fragment business logic service"""

from typing import Self

from sqlalchemy.orm import Session

from src.core.base_service import get_or_404
from src.core.exceptions import ConflictError, NotFoundError, ValidationError
from src.core.persistence import UnitOfWork, gen_id
from src.prompt_fragment.models import PromptFragment, TemplateFragment
from src.prompt_fragment.repository import FragmentRepository, TemplateFragmentRepository
from src.templating import TemplateService


class FragmentService:
    """Service for prompt fragment CRUD and template attachment operations"""

    def __init__(
        self,
        fragment_repo: FragmentRepository,
        template_fragment_repo: TemplateFragmentRepository,
        template_service: TemplateService | None = None,
        uow: UnitOfWork | None = None,
    ):
        self.fragment_repo = fragment_repo
        self.template_fragment_repo = template_fragment_repo
        self.template_service = template_service or TemplateService()
        # The unit of work owns the transaction boundary; it wraps the same session
        # the repos share. Fallback keeps direct `FragmentService(...)` construction
        # (tests) valid — the DI factory injects the request-scoped UoW.
        self.uow = uow or UnitOfWork(fragment_repo.db)

    @classmethod
    def from_session(cls, db: Session, uow: UnitOfWork | None = None) -> Self:
        """Build the service (and its repositories) from a bare Session.

        Lets a caller that holds only a Session — e.g. another slice's default
        construction fallback (BE-H2) — obtain the published service without
        reaching for the fragment repositories itself, keeping the module boundary.
        """
        return cls(FragmentRepository(db), TemplateFragmentRepository(db), uow=uow)

    def _validate_content(self, content: str | None) -> None:
        """Validate Jinja2 content syntax, raising 400 if invalid."""
        if content is not None:
            is_valid, error = self.template_service.validate_template(content)
            if not is_valid:
                raise ValidationError(f"Invalid Jinja2 content: {error}")

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
        return get_or_404(self.fragment_repo, fragment_id, "Prompt fragment")

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
        self.uow.commit()
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
        self.uow.commit()
        return updated

    def delete(self, fragment_id: str) -> None:
        """Delete a prompt fragment"""
        fragment = self.get_by_id(fragment_id)
        self.fragment_repo.delete(fragment)
        self.uow.commit()

    def delete_orphaned(self, fragment_ids: list[str]) -> int:
        """Delete any of the given fragments now orphaned (unattached and not global).

        A cross-module cleanup seam (BE-H2): when a template is deleted, the template
        slice asks the fragment slice to remove the private fragments it leaves
        behind. Flush-only — it runs inside the CALLER's unit of work so the whole
        deletion commits through one boundary; it never commits on its own.
        """
        return self.fragment_repo.delete_orphaned(fragment_ids)

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
            raise ConflictError("Fragment is already attached to this template")

        tf = TemplateFragment(
            id=gen_id(),
            template_id=template_id,
            fragment_id=fragment_id,
            position=position,
            ordinal=ordinal,
        )
        created = self.template_fragment_repo.create(tf)
        self.uow.commit()
        return created

    def detach_from_template(self, template_id: str, fragment_id: str) -> None:
        """Detach a fragment from a template"""
        deleted = self.template_fragment_repo.delete_by_template_and_fragment(
            template_id, fragment_id
        )
        if not deleted:
            raise NotFoundError("Fragment is not attached to this template")
        self.uow.commit()

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
                raise NotFoundError(
                    f"Fragment {fragment_id} is not attached to template {template_id}"
                )
            tf.position = str(item["position"])
            tf.ordinal = int(item["ordinal"])
            self.template_fragment_repo.update(tf)

        self.uow.commit()
        return self.template_fragment_repo.find_by_template_id(template_id)

    # --- SillyTavern import seam (BE-H2) ---

    def find_by_name(self, name: str) -> PromptFragment | None:
        """Look up a fragment by exact name (import unique-naming)."""
        return self.fragment_repo.find_by_name(name)

    def find_by_content(self, content: str) -> PromptFragment | None:
        """Look up a fragment by exact content (import de-dup)."""
        return self.fragment_repo.find_by_content(content)

    def create_imported(
        self,
        name: str,
        content: str,
        fragment_type: str,
        description: str | None = None,
    ) -> PromptFragment:
        """Create a fragment from a trusted import, skipping Jinja2 validation.

        Flush-only — SillyTavern content carries ST macros the normal ``create``
        would reject, and the whole preset import must commit as one transaction
        under the caller's unit of work.
        """
        fragment = PromptFragment(
            id=gen_id(),
            name=name,
            description=description,
            fragment_type=fragment_type,
            content=content,
            is_global=False,
        )
        return self.fragment_repo.create(fragment)

    def attach_imported(
        self,
        template_id: str,
        fragment_id: str,
        position: str,
        ordinal: int,
        depth: int | None = None,
    ) -> TemplateFragment:
        """Attach a fragment to a template with an explicit ``depth`` (import join row).

        Flush-only. Unlike ``attach_to_template`` it sets ``depth`` (ST ``at_depth``
        insertion) and skips the already-attached check — the import builds fresh
        join rows in one transaction.
        """
        tf = TemplateFragment(
            id=gen_id(),
            template_id=template_id,
            fragment_id=fragment_id,
            position=position,
            ordinal=ordinal,
            depth=depth,
        )
        return self.template_fragment_repo.create(tf)
