"""Dependency injection factories for chat session module"""

from typing import Annotated

from fastapi import Depends

from src.character.dependencies import get_character_repository
from src.character.repository import CharacterRepository
from src.chat_session.repository import ChatRepository
from src.chat_session.repository_async import AsyncChatRepository
from src.chat_session.service import ChatService
from src.core.persistence import AsyncDbSession, DbSession
from src.model.dependencies import get_model_repository
from src.model.repository import ModelRepository


# Sync repository (for CRUD operations)
def get_chat_repository(db: DbSession) -> ChatRepository:
    """Factory for sync ChatRepository"""
    return ChatRepository(db)


# Async repository (for message streaming)
async def get_async_chat_repository(db: AsyncDbSession) -> AsyncChatRepository:
    """Factory for async ChatRepository"""
    return AsyncChatRepository(db)


# Service (stays sync for now, only used in CRUD endpoints)
def get_chat_service(
    db: DbSession,
    chat_repo: Annotated[ChatRepository, Depends(get_chat_repository)],
    character_repo: Annotated[CharacterRepository, Depends(get_character_repository)],
    model_repo: Annotated[ModelRepository, Depends(get_model_repository)],
) -> ChatService:
    """Factory for ChatService.

    ProfileRepository is built from a lazy import to avoid an import-time cycle
    (profile -> preset -> st_import -> prompt_template -> chat_session).
    """
    from src.chat_message.repository import MessageRepository
    from src.persona.repository import PersonaRepository
    from src.profile.repository import ProfileRepository

    return ChatService(
        chat_repo,
        character_repo,
        model_repo,
        ProfileRepository(db),
        MessageRepository(db),
        PersonaRepository(db),
    )


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
ChatRepositoryDep = Annotated[ChatRepository, Depends(get_chat_repository)]
AsyncChatRepositoryDep = Annotated[AsyncChatRepository, Depends(get_async_chat_repository)]
