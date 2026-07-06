"""Data access layer for PromptTemplate entities"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.persistence import BaseRepository
from src.prompt_template.models import PromptTemplate


class PromptTemplateRepository(BaseRepository[PromptTemplate]):
    """Repository for PromptTemplate data access with custom queries"""

    def __init__(self, db: Session):
        """Initialize PromptTemplate repository"""
        super().__init__(db, PromptTemplate)

    def find_by_name(self, name: str) -> PromptTemplate | None:
        """Find a prompt template by name"""
        stmt = select(PromptTemplate).where(PromptTemplate.name == name)
        return self.db.execute(stmt).scalars().first()

    def find_default(self) -> PromptTemplate | None:
        """Find the default prompt template"""
        stmt = select(PromptTemplate).where(PromptTemplate.is_default)
        return self.db.execute(stmt).scalars().first()

    def find_all_ordered(self) -> list[PromptTemplate]:
        """Find all prompt templates ordered by creation date"""
        stmt = select(PromptTemplate).order_by(PromptTemplate.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def unset_all_defaults(self, exclude_id: str | None = None) -> None:
        """Unset all default prompt templates, optionally excluding one by ID"""
        stmt = select(PromptTemplate).where(PromptTemplate.is_default)
        if exclude_id:
            stmt = stmt.where(PromptTemplate.id != exclude_id)

        result = self.db.execute(stmt).scalars().all()
        for template in result:
            template.is_default = False
        self.db.flush()
