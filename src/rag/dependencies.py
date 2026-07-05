"""Dependency injection factories for RAG module"""

from typing import Annotated

from fastapi import Depends

from src.core.config import settings
from src.core.persistence import AsyncDbSession, DbSession
from src.rag.embedding_service import EmbeddingService
from src.rag.repository import DataBankRepository
from src.rag.repository_async import AsyncEmbeddingRepository
from src.rag.retrieval_service import RetrievalService
from src.rag.service import DataBankService


def get_data_bank_repository(db: DbSession) -> DataBankRepository:
    """Factory for DataBankRepository with DB injected"""
    return DataBankRepository(db)


def get_data_bank_service(
    repo: Annotated[DataBankRepository, Depends(get_data_bank_repository)],
) -> DataBankService:
    """Factory for DataBankService with repository injected"""
    return DataBankService(repo)


async def get_async_embedding_repository(db: AsyncDbSession) -> AsyncEmbeddingRepository:
    """Factory for AsyncEmbeddingRepository with async DB injected"""
    return AsyncEmbeddingRepository(db)


def get_embedding_service() -> EmbeddingService:
    """Factory for EmbeddingService using global RAG settings"""
    return EmbeddingService(settings.rag.embedding)


async def get_retrieval_service(
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    embedding_repo: Annotated[AsyncEmbeddingRepository, Depends(get_async_embedding_repository)],
    data_bank_repo: Annotated[DataBankRepository, Depends(get_data_bank_repository)],
) -> RetrievalService | None:
    """Factory for RetrievalService, or None when RAG is disabled.

    ``settings.rag.enabled`` is the master switch: when off, chat sends skip
    auto-retrieval and manual search returns a disabled error — so no embedding
    calls are attempted against a backend that may not be configured.
    """
    if not settings.rag.enabled:
        return None
    return RetrievalService(embedding_service, embedding_repo, data_bank_repo)


DataBankServiceDep = Annotated[DataBankService, Depends(get_data_bank_service)]
RetrievalServiceDep = Annotated[RetrievalService | None, Depends(get_retrieval_service)]
