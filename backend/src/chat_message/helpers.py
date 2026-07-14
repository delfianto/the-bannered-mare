"""Small shared helpers for the chat_message flow."""

from src.chat_session.models import Chat
from src.chat_session.repository_async import AsyncChatRepository
from src.core.base_service import async_get_or_404


async def get_chat_or_404(chat_repo: AsyncChatRepository, chat_id: str) -> Chat:
    """Fetch a chat with all relations loaded, or raise NotFoundError (→ 404)."""
    return await async_get_or_404(
        chat_repo,
        chat_id,
        f"Chat with ID '{chat_id}'",
        finder=chat_repo.find_by_id_with_relations,
    )
