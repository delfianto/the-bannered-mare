"""Small shared helpers for the chat_message flow."""

from fastapi import HTTPException, status

from src.chat_session.models import Chat
from src.chat_session.repository_async import AsyncChatRepository


async def get_chat_or_404(chat_repo: AsyncChatRepository, chat_id: str) -> Chat:
    """Fetch a chat with all relations loaded, or raise 404."""
    chat = await chat_repo.find_by_id_with_relations(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat with ID '{chat_id}' not found",
        )
    return chat
