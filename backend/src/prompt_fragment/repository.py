"""Data access layer for PromptFragment and TemplateFragment entities"""

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, joinedload

from src.core.persistence import BaseRepository
from src.prompt_fragment.models import PromptFragment, TemplateFragment


class FragmentRepository(BaseRepository[PromptFragment]):
    """Repository for PromptFragment data access"""

    def __init__(self, db: Session):
        super().__init__(db, PromptFragment)

    def find_by_name(self, name: str) -> PromptFragment | None:
        """Find a fragment by its unique name"""
        stmt = select(PromptFragment).where(PromptFragment.name == name)
        return self.db.execute(stmt).scalars().first()

    def find_by_content(self, content: str) -> PromptFragment | None:
        """Find a fragment with exactly matching content, for import-time reuse."""
        stmt = select(PromptFragment).where(PromptFragment.content == content)
        return self.db.execute(stmt).scalars().first()

    def find_all_ordered(self) -> list[PromptFragment]:
        """Find all fragments ordered by creation date"""
        stmt = select(PromptFragment).order_by(PromptFragment.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def find_paginated_with_usage(
        self,
        limit: int = 10,
        offset: int = 0,
        fragment_type: str | None = None,
        is_global: bool | None = None,
        unused_only: bool = False,
    ) -> tuple[list[PromptFragment], int]:
        """Find fragments with pagination, filtering, and eager-loaded template usage."""
        filters = []
        if fragment_type is not None:
            filters.append(PromptFragment.fragment_type == fragment_type)
        if is_global is not None:
            filters.append(PromptFragment.is_global == is_global)
        if unused_only:
            attached = select(TemplateFragment.id).where(
                TemplateFragment.fragment_id == PromptFragment.id
            )
            filters.append(~exists(attached))

        count_stmt = select(func.count()).select_from(PromptFragment).where(*filters)
        total = self.db.execute(count_stmt).scalar_one()

        stmt = (
            select(PromptFragment)
            .options(
                joinedload(PromptFragment.template_fragments).joinedload(TemplateFragment.template)
            )
            .where(*filters)
            .order_by(PromptFragment.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list(self.db.execute(stmt).unique().scalars().all())
        return items, total

    def delete_orphaned(self, fragment_ids: list[str]) -> int:
        """Delete any of the given fragments left with zero attachments and not global.

        Call after detaching/deleting the templates that used to reference them
        (e.g. template deletion) so private, per-import fragments don't outlive
        the only thing that used them. Returns the number deleted.
        """
        if not fragment_ids:
            return 0

        still_used_stmt = (
            select(TemplateFragment.fragment_id)
            .where(TemplateFragment.fragment_id.in_(fragment_ids))
            .distinct()
        )
        still_used = {row[0] for row in self.db.execute(still_used_stmt)}
        candidates = [fid for fid in fragment_ids if fid not in still_used]
        if not candidates:
            return 0

        stmt = select(PromptFragment).where(
            PromptFragment.id.in_(candidates), PromptFragment.is_global.is_(False)
        )
        orphaned = list(self.db.execute(stmt).scalars().all())
        for fragment in orphaned:
            self.db.delete(fragment)
        if orphaned:
            self.db.flush()
        return len(orphaned)

    def find_by_type(self, fragment_type: str) -> list[PromptFragment]:
        """Find all fragments of a given type"""
        stmt = (
            select(PromptFragment)
            .where(PromptFragment.fragment_type == fragment_type)
            .order_by(PromptFragment.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def find_global(self) -> list[PromptFragment]:
        """Find all globally available fragments"""
        stmt = (
            select(PromptFragment)
            .where(PromptFragment.is_global.is_(True))
            .order_by(PromptFragment.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())


class TemplateFragmentRepository(BaseRepository[TemplateFragment]):
    """Repository for TemplateFragment (join table) data access"""

    def __init__(self, db: Session):
        super().__init__(db, TemplateFragment)

    def find_by_template_id(self, template_id: str) -> list[TemplateFragment]:
        """Find all fragment associations for a template, ordered by position then ordinal"""
        stmt = (
            select(TemplateFragment)
            .options(joinedload(TemplateFragment.fragment))
            .where(TemplateFragment.template_id == template_id)
            .order_by(TemplateFragment.position, TemplateFragment.ordinal)
        )
        return list(self.db.execute(stmt).scalars().unique().all())

    def find_by_template_and_fragment(
        self, template_id: str, fragment_id: str
    ) -> TemplateFragment | None:
        """Find a specific template-fragment association"""
        stmt = select(TemplateFragment).where(
            TemplateFragment.template_id == template_id,
            TemplateFragment.fragment_id == fragment_id,
        )
        return self.db.execute(stmt).scalars().first()

    def delete_by_template_and_fragment(self, template_id: str, fragment_id: str) -> bool:
        """Delete a template-fragment association. Returns True if found and deleted."""
        tf = self.find_by_template_and_fragment(template_id, fragment_id)
        if not tf:
            return False
        self.delete(tf)
        return True
