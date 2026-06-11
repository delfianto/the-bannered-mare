"""Data access layer for PromptFragment and TemplateFragment entities"""

from sqlalchemy import select
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

    def find_all_ordered(self) -> list[PromptFragment]:
        """Find all fragments ordered by creation date"""
        stmt = select(PromptFragment).order_by(PromptFragment.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

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
