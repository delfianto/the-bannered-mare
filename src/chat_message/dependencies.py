"""Dependency injection factories for chat message module (ASYNC)"""

from typing import Annotated

from fastapi import Depends

from src.chat_message.repository_async import (
    AsyncMessageAlternativeRepository,
    AsyncMessageRepository,
)
from src.chat_message.service import ChatMessageService
from src.chat_session.dependencies import get_async_chat_repository
from src.chat_session.repository_async import AsyncChatRepository
from src.core.persistence import AsyncDbSession
from src.lore.dependencies import get_lore_service
from src.lore.service import LoreService
from src.prompt_template.dependencies import get_prompt_template_repository
from src.rag.dependencies import get_retrieval_service
from src.rag.retrieval_service import RetrievalService
from src.prompt_template.prompt_builder import PromptBuilder
from src.prompt_template.repository import PromptTemplateRepository


async def get_async_message_repository(db: AsyncDbSession) -> AsyncMessageRepository:
    """Factory for AsyncMessageRepository with async DB injected"""
    return AsyncMessageRepository(db)


async def get_async_alternative_repository(
    db: AsyncDbSession,
) -> AsyncMessageAlternativeRepository:
    """Factory for AsyncMessageAlternativeRepository"""
    return AsyncMessageAlternativeRepository(db)


def get_prompt_builder(
    template_repo: Annotated[PromptTemplateRepository, Depends(get_prompt_template_repository)],
) -> PromptBuilder:
    """Factory for PromptBuilder with repository injected"""
    return PromptBuilder(template_repo)


async def get_chat_message_service(
    message_repo: Annotated[AsyncMessageRepository, Depends(get_async_message_repository)],
    chat_repo: Annotated[AsyncChatRepository, Depends(get_async_chat_repository)],
    prompt_builder: Annotated[PromptBuilder, Depends(get_prompt_builder)],
    lore_service: Annotated[LoreService, Depends(get_lore_service)],
    alt_repo: Annotated[
        AsyncMessageAlternativeRepository, Depends(get_async_alternative_repository)
    ],
    retrieval_service: Annotated[RetrievalService, Depends(get_retrieval_service)],
) -> ChatMessageService:
    """Factory for ChatMessageService with async repositories injected"""
    return ChatMessageService(
        message_repo, chat_repo, prompt_builder, lore_service, alt_repo, retrieval_service
    )


ChatMessageServiceDep = Annotated[ChatMessageService, Depends(get_chat_message_service)]
AsyncMessageRepositoryDep = Annotated[AsyncMessageRepository, Depends(get_async_message_repository)]
