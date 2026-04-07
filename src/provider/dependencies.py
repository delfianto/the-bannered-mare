"""Dependency injection factories for provider module"""

from typing import Annotated

from fastapi import Depends

from src.core.persistence import DbSession
from src.provider.repository import ProviderRepository
from src.provider.service import ProviderService


def get_provider_repository(db: DbSession) -> ProviderRepository:
    """Factory for ProviderRepository with DB injected"""
    return ProviderRepository(db)


def get_provider_service(
    provider_repo: Annotated[ProviderRepository, Depends(get_provider_repository)],
) -> ProviderService:
    """Factory for ProviderService with repository injected"""
    return ProviderService(provider_repo)


ProviderServiceDep = Annotated[ProviderService, Depends(get_provider_service)]
ProviderRepositoryDep = Annotated[ProviderRepository, Depends(get_provider_repository)]
