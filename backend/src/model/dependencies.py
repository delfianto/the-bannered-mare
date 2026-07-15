from typing import Annotated

from fastapi import Depends

from src.chat_session.model_snapshot import ChatModelSnapshotService
from src.chat_session.repository import ChatRepository
from src.core.persistence import DbSession
from src.model.repository import ModelRepository
from src.model.service import ModelService
from src.model_family.dependencies import get_model_family_service
from src.model_family.service import ModelFamilyService
from src.provider.dependencies import get_provider_repository
from src.provider.repository import ProviderRepository


def get_model_repository(db: DbSession) -> ModelRepository:
    """Factory for ModelRepository with DB injected"""
    return ModelRepository(db)


def get_model_service(
    model_repo: Annotated[ModelRepository, Depends(get_model_repository)],
    provider_repo: Annotated[ProviderRepository, Depends(get_provider_repository)],
    family_service: Annotated[ModelFamilyService, Depends(get_model_family_service)],
    db: DbSession,
) -> ModelService:
    """Factory for ModelService with its cross-module read seams injected.

    The concrete ``ProviderRepository`` satisfies the ``ReadPort`` the service asks
    for; family reads go through the published ``ModelFamilyService``.
    """
    chat_snapshot = ChatModelSnapshotService(ChatRepository(db))
    return ModelService(model_repo, provider_repo, family_service, chat_snapshot)


ModelServiceDep = Annotated[ModelService, Depends(get_model_service)]
ModelRepositoryDep = Annotated[ModelRepository, Depends(get_model_repository)]
