"""Data access layer for PromptTemplate entities"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.persistence import DefaultableRepository, NamedRepository
from src.prompt_template.models import PromptTemplate


class PromptTemplateRepository(
    NamedRepository[PromptTemplate], DefaultableRepository[PromptTemplate]
):
    """Repository for PromptTemplate data access.

    Name lookup, ordered listing, and default-toggling come from the base
    repository + mixins; ``find_default`` is template-specific.
    """

    def __init__(self, db: Session):
        super().__init__(db, PromptTemplate)

    def find_default(self) -> PromptTemplate | None:
        """Find the default prompt template."""
        stmt = select(PromptTemplate).where(PromptTemplate.is_default)
        return self.db.execute(stmt).scalars().first()
