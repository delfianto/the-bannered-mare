"""Small shared helpers for the chat_message flow."""

from src.chat_session.models import Chat
from src.chat_session.repository_async import AsyncChatRepository
from src.core.exceptions import NotFoundError


async def get_chat_or_404(chat_repo: AsyncChatRepository, chat_id: str) -> Chat:
    """Fetch a chat with all relations loaded, or raise NotFoundError (→ 404)."""
    chat = await chat_repo.find_by_id_with_relations(chat_id)
    if chat is None:
        raise NotFoundError(f"Chat with ID '{chat_id}' not found")
    return chat
