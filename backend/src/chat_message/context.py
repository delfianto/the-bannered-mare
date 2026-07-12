"""Assembles the provider ``api_messages`` for a chat turn.

Owns the lore-activation + RAG-retrieval + prompt-rendering pipeline that turns a
chat's message history into the message list sent to the provider. Extracted from
ChatMessageService so the same assembly is shared by the send/regenerate flows and
the auxiliary generators (reply suggestions / impersonation) without duplicating
the lore + RAG plumbing.
"""

from typing import Any

from src.chat_message.models import Message
from src.chat_session.models import Chat
from src.core.logging.logger_config import get_logger
from src.lore.activation_engine import ActivatedEntry
from src.lore.service import LoreService
from src.prompt_template.prompt_builder import PromptBuilder
from src.rag.retrieval_service import RetrievalService

logger = get_logger(__name__)


class MessageContextBuilder:
    """Builds ``api_messages`` (lore + RAG + prompt render) for a chat turn."""

    def __init__(
        self,
        prompt_builder: PromptBuilder,
        lore_service: LoreService | None = None,
        retrieval_service: RetrievalService | None = None,
    ):
        self.prompt_builder = prompt_builder
        self.lore_service = lore_service
        self.retrieval_service = retrieval_service

    def get_activated_lore(
        self, chat: Chat, messages: list[Message]
    ) -> list[ActivatedEntry] | None:
        """Run the lore activation engine against recent messages."""
        if not self.lore_service:
            return None
        scan_text = " ".join(msg.content for msg in messages[-20:])
        return self.lore_service.get_activated_entries(
            character_id=chat.character_id, scan_text=scan_text
        )

    async def retrieve_rag_context(self, chat: Chat, messages: list[Message]) -> list[Any] | None:
        """Retrieve relevant context via RAG (semantic search over history + data bank)."""
        if not self.retrieval_service:
            return None
        try:
            query_text = " ".join(msg.content for msg in messages[-2:])
            return await self.retrieval_service.retrieve(
                chat_id=chat.id, query_text=query_text, character_id=chat.character_id
            )
        except Exception:
            logger.warning("rag_retrieval_failed", exc_info=True)
            return None

    async def assemble(self, chat: Chat, messages: list[Message]) -> list[dict[str, Any]]:
        """Assemble the provider ``api_messages`` for a turn: activate lore + RAG
        over ``messages``, then render via the prompt builder."""
        activated_lore = self.get_activated_lore(chat, messages)
        rag_results = await self.retrieve_rag_context(chat, messages)
        return self.prompt_builder.build_api_messages(
            chat, messages, activated_lore=activated_lore, rag_results=rag_results
        )
