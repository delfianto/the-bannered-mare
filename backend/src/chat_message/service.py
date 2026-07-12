"""Message business logic service (FULLY ASYNC)"""

import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from src.chat_message import gateway_factory, llm_audit
from src.chat_message.alternatives import AlternativesService
from src.chat_message.auxiliary import AuxiliaryGenerationService
from src.chat_message.context import MessageContextBuilder
from src.chat_message.helpers import get_chat_or_404
from src.chat_message.models import Message, MessageRole
from src.chat_message.normalize import sanitize_narrative
from src.chat_message.repository_async import (
    AsyncMessageAlternativeRepository,
    AsyncMessageRepository,
)
from src.chat_message.schemas import MessageResponse, StreamEvent
from src.chat_session.models import Chat
from src.chat_session.repository_async import AsyncChatRepository
from src.core.config import settings
from src.core.exceptions import NotFoundError, ProviderException, ValidationError
from src.core.logging.logger_config import get_logger
from src.core.persistence import gen_id
from src.core.persistence.models import MessageAlternative
from src.core.schemas import PaginatedResponse, PaginationMeta
from src.core.utils.reasoning import parse_reasoning_tags
from src.core.utils.tokenizer import TokenizerService
from src.lore.service import LoreService
from src.prompt_template.prompt_builder import PromptBuilder
from src.provider.adapters.base import TokenUsage
from src.provider.completion_outcome import CompletionOutcome
from src.rag.retrieval_service import RetrievalService

logger = get_logger(__name__)

# User-facing explanation for a non-USABLE completion (empty/filtered/etc.), shown
# in place of a silent blank reply. USABLE never surfaces one.
_OUTCOME_MESSAGES: dict[CompletionOutcome, str] = {
    CompletionOutcome.FILTERED: (
        "The model declined to respond to this scene (content filter). Try rephrasing, "
        "or switch this chat to a less restrictive model."
    ),
    CompletionOutcome.TRUNCATED: (
        "The model hit its output limit before replying. Raise max tokens, or lower the "
        "reasoning effort for this model."
    ),
    CompletionOutcome.REASONING_ONLY: (
        "The model spent its entire budget reasoning without writing a reply. Raise max "
        "tokens so it has room to answer."
    ),
    CompletionOutcome.EMPTY: (
        "The model returned an empty response — some models do this as a soft content "
        "filter. Try regenerating, or switch models."
    ),
}


def _outcome_message(outcome: CompletionOutcome) -> str:
    return _OUTCOME_MESSAGES.get(outcome, "The model returned no usable reply.")


class ChatMessageService:
    """Service for message-related business logic (FULLY ASYNC)"""

    def __init__(
        self,
        message_repo: AsyncMessageRepository,
        chat_repo: AsyncChatRepository,
        prompt_builder: PromptBuilder,
        lore_service: LoreService | None = None,
        alt_repo: AsyncMessageAlternativeRepository | None = None,
        retrieval_service: RetrievalService | None = None,
    ):
        self.message_repo = message_repo
        self.chat_repo = chat_repo
        self.prompt_builder = prompt_builder  # retained for the scaffolding-only preview
        self.alt_repo = alt_repo
        self.retrieval_service = retrieval_service  # retained for _vectorize
        self.tokenizer = TokenizerService()
        self.context = MessageContextBuilder(prompt_builder, lore_service, retrieval_service)
        self.alternatives = AlternativesService(message_repo, alt_repo)
        self.aux = AuxiliaryGenerationService(message_repo, chat_repo, self.context)

    async def _vectorize(self, message: Message) -> None:
        """Embed and store a message for RAG (best-effort — never blocks the reply).

        Gated on RAG being enabled (retrieval_service present) and the
        vectorize_messages flag; failures are swallowed so indexing can never
        break a send.
        """
        if self.retrieval_service is None or not settings.rag.vectorize_messages:
            return
        try:
            await self.retrieval_service.vectorize_message(
                message_id=message.id,
                content=message.content,
                model_name=settings.rag.embedding.model,
                dimensions=settings.rag.embedding.dimensions,
            )
        except Exception:
            logger.warning("message_vectorize_failed", message_id=message.id, exc_info=True)

    async def _get_chat_by_id(self, chat_id: str) -> Chat:
        """Get a chat with all relations or raise 404."""
        return await get_chat_or_404(self.chat_repo, chat_id)

    def _log_token_budget(self, api_messages: list[dict[str, Any]]) -> int:
        """Log estimated prompt token count and return the total."""
        total = self.tokenizer.count_messages(api_messages)
        logger.info(
            "prompt_token_estimate", estimated_tokens=total, message_count=len(api_messages)
        )
        return total

    async def get_messages(
        self, chat_id: str, limit: int = 20, cursor: str | None = None
    ) -> PaginatedResponse[MessageResponse]:
        """Get messages with cursor-based pagination."""
        await self._get_chat_by_id(chat_id)

        before_time = None
        if cursor:
            try:
                before_time = datetime.fromisoformat(cursor.replace("Z", "+00:00"))
            except ValueError:
                logger.warning(f"Invalid cursor format: {cursor}")

        fetch_limit = limit + 1

        raw_messages = await self.message_repo.find_latest_by_chat_id(
            chat_id=chat_id, limit=fetch_limit, before=before_time
        )

        has_more = False
        if len(raw_messages) > limit:
            has_more = True
            raw_messages = raw_messages[:limit]

        next_cursor = None
        if raw_messages:
            next_cursor = raw_messages[-1].created_at.isoformat()

        return PaginatedResponse(
            items=[MessageResponse.model_validate(msg) for msg in raw_messages],
            meta=PaginationMeta(
                limit=limit, has_more=has_more, cursor=next_cursor, total=None, page=None
            ),
        )

    async def _update_chat_metadata(self, chat_id: str, last_message: str):
        """Update chat snippet and timestamp for the list view"""
        chat = await self.chat_repo.find_by_id(chat_id)
        if chat:
            chat.preview = last_message[:50]
            chat.updated_at = datetime.now(UTC)
            await self.chat_repo.update(chat)
            await self.chat_repo.commit()

    # --- Next-turn Suggestions (reply candidates / impersonation) ---

    async def generate_suggestions(
        self, chat_id: str, mode: str = "reply", tone: str | None = None, count: int = 3
    ) -> list[str]:
        """Generate next-turn suggestions (reply cards / impersonation / tone chips)."""
        return await self.aux.generate_suggestions(chat_id, mode=mode, tone=tone, count=count)

    async def generate_title(self, chat_id: str) -> str:
        """Generate and persist a concise chat title via the task model."""
        return await self.aux.generate_title(chat_id)

    # --- Prompt preview (Session info) ---

    async def preview_prompt(self, chat_id: str) -> dict[str, Any]:
        """Resolved prompt scaffolding + effective sampler params for a chat.

        Builds the template scaffolding with an EMPTY conversation (system prompt,
        character card, scenario, persona, examples, fragments — everything the
        model always sees, minus the live turns) and the effective parameters the
        gateway would send. No LLM call; used by the chat drawer's Session tab.
        """
        chat = await self._get_chat_by_id(chat_id)
        api_messages = self.prompt_builder.build_api_messages(
            chat, messages=[], activated_lore=None, rag_results=None
        )
        gateway = gateway_factory.build_gateway(chat)
        route = gateway_factory.resolve_active_route(chat.model) if chat.model else None
        return {
            "model_display_name": chat.model.display_name if chat.model else None,
            "provider_name": route.provider.name if route else None,
            "model_identifier": route.model_identifier if route else None,
            "parameters": gateway.effective_parameters(),
            "messages": [
                {"role": m.get("role", ""), "content": m.get("content", "")} for m in api_messages
            ],
        }

    # --- Message Editing (6.1) ---

    async def edit_message(self, chat_id: str, message_id: str, content: str) -> Message:
        """Edit a message's content and recount tokens."""
        await self._get_chat_by_id(chat_id)

        message = await self.message_repo.find_by_id_in_chat(message_id, chat_id)
        if not message:
            raise NotFoundError(f"Message '{message_id}' not found in chat '{chat_id}'")

        message.content = content
        message.token_count = self.tokenizer.count_tokens(content)
        updated = await self.message_repo.update(message)
        await self.message_repo.commit()
        return updated

    # --- Message Send ---

    # --- Shared completion pipeline (blocking + streaming) ---

    def _normalize_reply(
        self, content: str, reasoning: str | None, usage: TokenUsage | None
    ) -> tuple[str, str | None, int]:
        """Post-process a usable reply: split think-tags when the API didn't
        provide reasoning, strip leaked HTML/graphics, and compute the token
        count. Shared by the blocking and streaming paths so the logic exists once.
        """
        if not reasoning:
            content, reasoning = parse_reasoning_tags(content)
        content = sanitize_narrative(content)
        token_count = (
            usage.output_tokens
            if usage and usage.output_tokens
            else self.tokenizer.count_tokens(content)
        )
        return content, reasoning, token_count

    async def _persist_reply(
        self,
        *,
        chat_id: str,
        content: str,
        reasoning: str | None,
        token_count: int,
        existing_message: Message | None,
        message_id: str | None = None,
    ) -> Message:
        """Persist a usable assistant reply and refresh chat metadata.

        Three modes, shared by the blocking and streaming paths:
        - regeneration with alt_repo → store as a swipe alternative;
        - regeneration without alt_repo → overwrite the message in place;
        - a new turn → create a message (and vectorize it).
        """
        if existing_message and self.alt_repo:
            await self.alternatives.store(existing_message, content, token_count)
            stored = existing_message
        elif existing_message:
            existing_message.content = content
            existing_message.token_count = token_count
            existing_message.reasoning_content = reasoning
            stored = await self.message_repo.update(existing_message)
            await self.message_repo.commit()
        else:
            stored = await self.message_repo.create(
                Message(
                    id=message_id or gen_id(),
                    chat_id=chat_id,
                    role=MessageRole.ASSISTANT,
                    content=content,
                    token_count=token_count,
                    reasoning_content=reasoning,
                )
            )
            await self.message_repo.commit()
            await self._vectorize(stored)
        await self._update_chat_metadata(chat_id, content)
        return stored

    async def _run_blocking_completion(
        self,
        *,
        chat: Chat,
        chat_id: str,
        api_messages: list[dict[str, Any]],
        existing_message: Message | None,
        estimated_tokens: int | None = None,
    ) -> Message:
        """Run a non-streaming completion end to end and persist a usable reply.

        Shared by send_message (new turn) and regenerate (alternative). Calls the
        model, audits, classifies, then normalizes + persists. Raises 500 on a
        provider error and 502 when the reply is empty / filtered / truncated, so a
        blank turn is never persisted.
        """
        gateway = gateway_factory.build_gateway(chat)
        start = time.perf_counter()
        try:
            response = await gateway.chat_completion(api_messages)
        except Exception as e:
            await llm_audit.audit_error(
                gateway=gateway, api_messages=api_messages, chat_id=chat_id, start=start, error=e
            )
            raise ProviderException("Error communicating with AI provider.") from e

        outcome = await llm_audit.classify_and_audit(
            gateway=gateway,
            api_messages=api_messages,
            chat_id=chat_id,
            start=start,
            content=response.content,
            reasoning=response.reasoning,
            finish_reason=response.finish_reason,
            usage=response.usage,
            raw=response.raw,
        )
        if outcome != CompletionOutcome.USABLE:
            raise ProviderException(_outcome_message(outcome))

        # Prompt-budget observability (send only; regenerate passes no estimate).
        if estimated_tokens is not None and response.usage:
            if response.usage.input_tokens:
                logger.info(
                    "token_drift", estimated=estimated_tokens, actual=response.usage.input_tokens
                )
            if response.usage.cache_read_tokens:
                logger.info(
                    "prompt_cache_hit",
                    cached_tokens=response.usage.cache_read_tokens,
                    created_tokens=response.usage.cache_creation_tokens,
                )

        content, reasoning, token_count = self._normalize_reply(
            response.content, response.reasoning, response.usage
        )
        return await self._persist_reply(
            chat_id=chat_id,
            content=content,
            reasoning=reasoning,
            token_count=token_count,
            existing_message=existing_message,
        )

    async def send_message(self, chat_id: str, content: str) -> Message:
        """Send a message and get an AI response (non-streaming)"""
        chat = await self._get_chat_by_id(chat_id)
        gateway_factory.validate_model_and_key(chat)

        user_message = Message(
            chat_id=chat_id,
            role=MessageRole.USER,
            content=content,
            token_count=self.tokenizer.count_tokens(content),
        )
        _ = await self.message_repo.create(user_message)
        await self.message_repo.commit()

        await self._update_chat_metadata(chat_id, content)

        messages = await self.message_repo.find_by_chat_id(chat_id)
        api_messages = await self.context.assemble(chat, messages)
        estimated_tokens = self._log_token_budget(api_messages)

        created = await self._run_blocking_completion(
            chat=chat,
            chat_id=chat_id,
            api_messages=api_messages,
            existing_message=None,
            estimated_tokens=estimated_tokens,
        )
        await self._vectorize(user_message)
        return created

    async def _stream_completion(
        self,
        chat_id: str,
        chat: Chat,
        api_messages: list[dict[str, Any]],
        existing_message: Message | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """
        Core streaming logic shared by send_message_stream and regenerate_stream.

        If existing_message is provided (regeneration), stores result as alternative
        instead of creating a new message.
        """
        message_id = existing_message.id if existing_message else gen_id()
        yield StreamEvent(type="start", message_id=message_id)

        full_content = ""
        full_reasoning = ""
        last_usage = None
        last_finish_reason = None

        gateway = gateway_factory.build_gateway(chat)
        start = time.perf_counter()
        try:
            async for chunk in gateway.chat_completion_stream(api_messages):
                if chunk.content:
                    full_content += chunk.content
                    yield StreamEvent(type="text", content=chunk.content)
                if chunk.reasoning:
                    full_reasoning += chunk.reasoning
                    yield StreamEvent(type="reasoning", content=chunk.reasoning)
                if chunk.usage:
                    last_usage = chunk.usage
                if chunk.finish_reason:
                    last_finish_reason = chunk.finish_reason

            # Classify the assembled stream (audit before think-tag parsing); an
            # empty/filtered/truncated result is surfaced instead of persisted.
            outcome = await llm_audit.classify_and_audit(
                gateway=gateway,
                api_messages=api_messages,
                chat_id=chat_id,
                start=start,
                content=full_content or None,
                reasoning=full_reasoning or None,
                finish_reason=last_finish_reason,
                usage=last_usage,
            )
            if outcome != CompletionOutcome.USABLE:
                yield StreamEvent(
                    type="error", message=_outcome_message(outcome), code=outcome.value
                )
                return

            if full_content:
                full_content, reasoning, token_count = self._normalize_reply(
                    full_content, full_reasoning or None, last_usage
                )
                await self._persist_reply(
                    chat_id=chat_id,
                    content=full_content,
                    reasoning=reasoning,
                    token_count=token_count,
                    existing_message=existing_message,
                    message_id=message_id,
                )

            if last_usage:
                yield StreamEvent(
                    type="usage",
                    input_tokens=last_usage.input_tokens,
                    output_tokens=last_usage.output_tokens,
                    total_tokens=last_usage.total_tokens,
                    cache_read_tokens=last_usage.cache_read_tokens or None,
                    cache_creation_tokens=last_usage.cache_creation_tokens or None,
                )

            yield StreamEvent(type="done", finish_reason=last_finish_reason or "stop")

        except Exception as e:
            await llm_audit.audit_error(
                gateway=gateway, api_messages=api_messages, chat_id=chat_id, start=start, error=e
            )
            logger.error(f"Error during streaming: {e!s}")
            yield StreamEvent(type="error", message=str(e), code=llm_audit.classify_error(e))

    async def send_message_stream(self, chat_id: str, content: str) -> AsyncIterator[StreamEvent]:
        """Send a message and get a streaming AI response."""
        chat = await self._get_chat_by_id(chat_id)
        gateway_factory.validate_model_and_key(chat)

        user_message = Message(
            chat_id=chat_id,
            role=MessageRole.USER,
            content=content,
            token_count=self.tokenizer.count_tokens(content),
        )
        _ = await self.message_repo.create(user_message)
        await self.message_repo.commit()
        await self._update_chat_metadata(chat_id, content)

        messages = await self.message_repo.find_by_chat_id(chat_id)
        api_messages = await self.context.assemble(chat, messages)

        async for event in self._stream_completion(chat_id, chat, api_messages):
            yield event

        # Index the user turn after the reply has streamed (keeps embedding off
        # the pre-generation path); the assistant turn is indexed in-stream.
        await self._vectorize(user_message)

    # --- Regeneration with Alternatives (6.2) ---

    async def regenerate(self, chat_id: str) -> Message:
        """Regenerate the last assistant message. Stores old content as alternative."""
        chat = await self._get_chat_by_id(chat_id)

        latest_messages = await self.message_repo.find_latest_by_chat_id(chat_id, limit=1)
        if not latest_messages:
            raise ValidationError("Cannot regenerate: No messages in chat")

        last_message = latest_messages[0]
        if last_message.role != MessageRole.ASSISTANT:
            raise ValidationError("Cannot regenerate: Last message is not from assistant")

        gateway_factory.validate_model_and_key(chat)

        # Build prompt excluding the last assistant message
        messages = await self.message_repo.find_by_chat_id(chat_id)
        messages_for_prompt = [m for m in messages if m.id != last_message.id]
        api_messages = await self.context.assemble(chat, messages_for_prompt)

        return await self._run_blocking_completion(
            chat=chat,
            chat_id=chat_id,
            api_messages=api_messages,
            existing_message=last_message,
        )

    async def regenerate_stream(self, chat_id: str) -> AsyncIterator[StreamEvent]:
        """Regenerate the tail assistant reply (streaming).

        Normally replaces the last assistant message (storing the old content as an
        alternative). When the last turn is instead the *user's* — e.g. the prior
        generation was rejected/empty and never persisted — there is nothing to
        replace, so a fresh reply is generated for that turn. This is what powers
        "retry" after a filtered/empty reply.
        """
        chat = await self._get_chat_by_id(chat_id)

        latest_messages = await self.message_repo.find_latest_by_chat_id(chat_id, limit=1)
        if not latest_messages:
            raise ValidationError("Cannot regenerate: No messages in chat")

        last_message = latest_messages[0]
        # Replace the last assistant turn; for a dangling user turn, append instead.
        existing = last_message if last_message.role == MessageRole.ASSISTANT else None

        gateway_factory.validate_model_and_key(chat)

        messages = await self.message_repo.find_by_chat_id(chat_id)
        messages_for_prompt = (
            [m for m in messages if m.id != last_message.id] if existing else messages
        )
        api_messages = await self.context.assemble(chat, messages_for_prompt)

        async for event in self._stream_completion(
            chat_id, chat, api_messages, existing_message=existing
        ):
            yield event

    # --- Alternative Management ---

    async def list_alternatives(self, chat_id: str, message_id: str) -> list[MessageAlternative]:
        """List all alternatives for a message."""
        return await self.alternatives.list(chat_id, message_id)

    async def activate_alternative(
        self, chat_id: str, message_id: str, alternative_id: str
    ) -> Message:
        """Switch the active alternative on a message."""
        return await self.alternatives.activate(chat_id, message_id, alternative_id)
