"""Sync seam for seeding canned (non-generated) messages into a chat (BE-H7).

The chat_session service seeds a character's greeting as a chat's opening message
on create — a sync, non-LLM write into the chat_message domain. It lives here
(not on the async ``ChatMessageService``) so ``chat_session`` can depend on a
published chat_message service rather than the message repository, while staying
on the sync request path. Flush-only: it participates in the caller's unit of
work, so the chat and its greeting commit together.
"""

from src.chat_message.repository import MessageRepository
from src.core.persistence import Message, MessageRole


class MessageSeedService:
    """Persist canned messages (e.g. a chat's opening greeting)."""

    def __init__(self, message_repo: MessageRepository):
        self.message_repo = message_repo

    def seed_greeting(self, chat_id: str, content: str, token_count: int) -> Message:
        """Stage the assistant greeting as a chat's opening message (flush-only).

        Participates in the caller's unit of work — chat creation commits the chat
        and its greeting together — so this never commits on its own.
        """
        return self.message_repo.create(
            Message(
                chat_id=chat_id,
                role=MessageRole.ASSISTANT,
                content=content,
                token_count=token_count,
            )
        )
