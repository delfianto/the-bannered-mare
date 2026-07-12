"""Data access layer for Provider entities"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.persistence import BaseRepository
from src.provider.models import Provider, ProviderType


class ProviderRepository(BaseRepository[Provider]):
    """Repository for Provider data access with custom queries"""

    def __init__(self, db: Session):
        """Initialize Provider repository"""
        super().__init__(db, Provider)

    def find_by_name(self, name: str) -> Provider | None:
        """Find a provider by name"""
        stmt = select(Provider).where(Provider.name == name)
        return self.db.execute(stmt).scalars().first()

    def find_by_type(self, provider_type: str | ProviderType) -> Provider | None:
        """
        Find a provider by its type.

        Args:
            provider_type: The provider type to search for (string or enum)

        Returns:
            Provider if found, None otherwise
        """
        if isinstance(provider_type, str):
            provider_type = ProviderType(provider_type)

        stmt = select(Provider).where(Provider.provider_type == provider_type)
        return self.db.execute(stmt).scalars().first()
