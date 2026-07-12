"""Message business logic service (FULLY ASYNC)"""

import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status

from src.audit.writer import audit_logger
from src.chat_message import gateway_factory, transcripts
from src.chat_message.alternatives import AlternativesService
from src.chat_message.models import Message, MessageRole
from src.chat_message.normalize import parse_structured_list, sanitize_narrative
from src.chat_message.repository_async import (
    AsyncMessageAlternativeRepository,
    AsyncMessageRepository,
)
from src.chat_message.schemas import MessageResponse, StreamEvent
from src.chat_session.models import Chat
from src.chat_session.repository_async import AsyncChatRepository
from src.core.config import settings
from src.core.exceptions import (
    ProviderAuthError,
    ProviderException,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from src.core.logging.logger_config import get_logger
from src.core.persistence import gen_id
from src.core.persistence.models import MessageAlternative
from src.core.schemas import PaginatedResponse, PaginationMeta
from src.core.utils.reasoning import parse_reasoning_tags
from src.core.utils.tokenizer import TokenizerService
from src.lore.activation_engine import ActivatedEntry
from src.lore.service import LoreService
from src.prompt_template.prompt_builder import PromptBuilder
from src.provider.adapters.base import TokenUsage
from src.provider.completion_outcome import CompletionOutcome, classify_completion
from src.provider.gateway import ProviderGateway
from src.rag.retrieval_service import RetrievalService

logger = get_logger(__name__)

# Appended to the cheap suggestion/tone prompts. Reply candidates and tone chips
# are throwaway scaffolding, so the task model should answer immediately with a
# bare JSON array. Thinking-capable task models otherwise spend hundreds of
# reasoning tokens and wrap the answer in ```json fences before the real payload
# (parse_structured_list copes, but it is pure waste). This directive steers them
# to skip the reasoning trace and the fences; models that respect it emit only the
# array, and parsing stays tolerant for those that don't.
_JSON_ARRAY_ONLY = (
    "Do not think out loud, explain, or add any preamble. Reply with ONLY a compact "
    "JSON array of strings and nothing else — no reasoning, no markdown, no code "
    'fences. Begin the reply with "[" and end it with "]".'
)


def _classify_error(exc: Exception) -> str:
    if isinstance(exc, ProviderRateLimitError):
        return "rate_limit"
    if isinstance(exc, ProviderAuthError):
        return "auth_error"
    if isinstance(exc, ProviderTimeoutError):
        return "timeout"
    if isinstance(exc, ProviderException):
        return "provider_error"
    return "internal_error"


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
        self.prompt_builder = prompt_builder
        self.lore_service = lore_service
        self.alt_repo = alt_repo
        self.retrieval_service = retrieval_service
        self.tokenizer = TokenizerService()
        self.alternatives = AlternativesService(message_repo, alt_repo)

    def _get_activated_lore(
        self, chat: Chat, messages: list[Message]
    ) -> list[ActivatedEntry] | None:
        """Run lore activation engine against recent messages."""
        if not self.lore_service:
            return None
        scan_text = " ".join(msg.content for msg in messages[-20:])
        return self.lore_service.get_activated_entries(
            character_id=chat.character_id, scan_text=scan_text
        )

    async def _retrieve_rag_context(self, chat: Chat, messages: list[Message]) -> list[Any] | None:
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
        """Helper to get chat with all relations or raise 404."""
        chat = await self.chat_repo.find_by_id_with_relations(chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat with ID '{chat_id}' not found",
            )
        return chat

    def _log_token_budget(self, api_messages: list[dict[str, Any]]) -> int:
        """Log estimated prompt token count and return the total."""
        total = self.tokenizer.count_messages(api_messages)
        logger.info(
            "prompt_token_estimate", estimated_tokens=total, message_count=len(api_messages)
        )
        return total

    async def _record_llm_audit(
        self,
        *,
        gateway: ProviderGateway,
        api_messages: list[dict[str, Any]],
        chat_id: str,
        latency_ms: float,
        error: Exception | None = None,
        content: str | None = None,
        reasoning: str | None = None,
        finish_reason: str | None = None,
        usage: TokenUsage | None = None,
        raw: dict[str, Any] | None = None,
        status_override: str | None = None,
    ) -> None:
        """Record one LLM-call audit row (fire-and-forget; never raises).

        ``status_override`` records a non-error but non-``success`` outcome
        (filtered / empty / truncated) so LLM Logs no longer files these as
        successes.
        """
        try:
            provider = gateway.provider.provider_type.value
            model = gateway.active_identifier
            if error is not None:
                await audit_logger.log_llm_call(
                    chat_id=chat_id,
                    provider=provider,
                    model=model,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    latency_ms=latency_ms,
                    status=_classify_error(error),
                    error_message=str(error),
                    request_payload=api_messages,
                    response_payload=None,
                )
                return

            usage_dict = None
            in_tok = out_tok = tot_tok = 0
            if usage is not None:
                in_tok, out_tok, tot_tok = (
                    usage.input_tokens,
                    usage.output_tokens,
                    usage.total_tokens,
                )
                usage_dict = {
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "total_tokens": usage.total_tokens,
                    "cache_read_tokens": usage.cache_read_tokens,
                    "cache_creation_tokens": usage.cache_creation_tokens,
                }
            response_payload: dict[str, Any] = {
                "content": content,
                "reasoning": reasoning,
                "finish_reason": finish_reason,
                "usage": usage_dict,
            }
            if raw is not None:
                response_payload["raw"] = raw

            await audit_logger.log_llm_call(
                chat_id=chat_id,
                provider=provider,
                model=model,
                prompt_tokens=in_tok,
                completion_tokens=out_tok,
                total_tokens=tot_tok,
                latency_ms=latency_ms,
                status=status_override or "success",
                request_payload=api_messages,
                response_payload=response_payload,
            )
        except Exception:
            logger.warning("llm_audit_capture_failed", exc_info=True)

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
        """Generate next-turn suggestions for the chat.

        - ``reply``: several short candidate user turns (rendered as cards).
        - ``impersonate``: one drafted user message in the user's voice.
        - ``tones``: several short tone/approach labels for the scene (chips).

        Routing by cost: ``reply`` and ``tones`` are disposable scaffolding the
        user picks from or discards, so they run on the cheap **task model** with
        a compact prompt (recent exchange + who's-who) rather than the full system
        prompt + character card + persona + lorebook + RAG + history. Only
        ``impersonate`` — which drafts the user's *actual* next message — keeps
        the full context on the main model for quality.
        """
        chat = await self._get_chat_by_id(chat_id)

        messages = await self.message_repo.find_by_chat_id(chat_id)
        user_name = chat.persona.name if chat.persona else "the user"
        char_name = chat.character.name if chat.character else "the character"

        if mode == "tones":
            # Tone chips are throwaway metadata — a few emotional-direction labels.
            # They don't need the system prompt, character card, persona, lorebook,
            # RAG or full history, so we skip build_api_messages entirely and send a
            # compact recent transcript to the cheap task model (the same lean shape
            # as title generation). This drops the request from ~5.7K prompt tokens
            # to a few hundred for ~46 tokens of output.
            transcript = transcripts.recent_transcript(chat, messages)
            instruction = (
                f"Below is the recent exchange in a roleplay between {user_name} (the human "
                f"user) and {char_name}:\n\n{transcript}\n\n"
                f"Suggest {count} short labels (1-3 words each) for distinct tones or approaches "
                f"{user_name} could take in their next message, fitting the scene and what "
                f"{char_name} just said or did. Vary the emotional direction. Style examples "
                'only (do not reuse): "Stand your ground", "De-escalate", "Flirt back".\n\n'
                + _JSON_ARRAY_ONLY
            )
            api_messages = [{"role": "user", "content": instruction}]
            gateway = gateway_factory.build_task_gateway(chat, minimize_reasoning=True)
        elif mode == "reply":
            # Reply candidates are disposable — the user picks one, edits it, or
            # ignores them — so they don't warrant the full scene context on the
            # main model. Send a compact prompt (recent exchange + who's-who +
            # a short persona voice cue) to the cheap task model instead.
            transcript = transcripts.recent_transcript(chat, messages)
            persona_hint = transcripts.persona_hint(chat)
            instruction = (
                f"This is a roleplay between {user_name} (the human user) and {char_name}."
                f"{persona_hint}\n\nRecent exchange:\n{transcript}\n\n"
                f"Suggest {count} distinct, short options for what {user_name} could say next — "
                f"written in {user_name}'s voice and grounded in what {char_name} just said or "
                "did, each a different tone or direction, one or two sentences. Do not continue "
                f"the scene as {char_name}.\n\n"
                + _JSON_ARRAY_ONLY
                + ' Example: ["...", "...", "..."].'
            )
            api_messages = [{"role": "user", "content": instruction}]
            gateway = gateway_factory.build_task_gateway(chat, minimize_reasoning=True)
        else:
            # impersonate drafts the user's *actual* next message, so it keeps the
            # full scene context on the main model for quality.
            activated_lore = self._get_activated_lore(chat, messages)
            rag_results = await self._retrieve_rag_context(chat, messages)
            api_messages = self.prompt_builder.build_api_messages(
                chat, messages, activated_lore=activated_lore, rag_results=rag_results
            )

            tone_clause = f" Give it a {tone} tone." if tone else ""
            instruction = (
                f"You are now writing on behalf of {user_name} (the human user), NOT "
                f"{char_name}. Compose {user_name}'s next message in the first person, in "
                f"their voice, continuing the scene naturally.{tone_clause} Output only the "
                "message text — no quotation marks, no name label, and no commentary about "
                "the task."
            )

            # Keep role alternation valid (some providers reject consecutive user
            # turns): merge the directive into a trailing user message, else append.
            if api_messages and api_messages[-1].get("role") == "user":
                last = dict(api_messages[-1])
                last["content"] = f"{last['content']}\n\n{instruction}"
                api_messages = [*api_messages[:-1], last]
            else:
                api_messages = [*api_messages, {"role": "user", "content": instruction}]

            gateway = gateway_factory.build_gateway(chat)
        start = time.perf_counter()
        try:
            response = await gateway.chat_completion(api_messages)
        except Exception as e:
            await self._audit_error(
                gateway=gateway, api_messages=api_messages, chat_id=chat_id, start=start, error=e
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error communicating with AI provider: {e!s}",
            ) from e

        await self._record_llm_audit(
            gateway=gateway,
            api_messages=api_messages,
            chat_id=chat_id,
            latency_ms=(time.perf_counter() - start) * 1000,
            content=response.content,
            finish_reason=response.finish_reason,
            usage=response.usage,
        )

        content = (response.content or "").strip()
        if mode == "impersonate":
            draft = content.strip().strip('"').strip()
            return [draft] if draft else []
        return parse_structured_list(content, count)

    async def generate_title(self, chat_id: str) -> str:
        """Generate and persist a concise chat title via the task model."""
        chat = await self._get_chat_by_id(chat_id)
        messages = await self.message_repo.find_by_chat_id(chat_id)
        transcript = transcripts.title_transcript(chat, messages)
        if not transcript:
            return chat.title or ""

        instruction = (
            "Generate a concise, specific title for the roleplay conversation below. "
            "3-6 words, Title Case, no quotation marks, no trailing punctuation. Reply "
            "with only the title.\n\n"
            f"{transcript}"
        )
        api_messages = [{"role": "user", "content": instruction}]
        gateway = gateway_factory.build_task_gateway(chat, minimize_reasoning=True)
        start = time.perf_counter()
        try:
            response = await gateway.chat_completion(api_messages)
        except Exception as e:
            await self._audit_error(
                gateway=gateway, api_messages=api_messages, chat_id=chat_id, start=start, error=e
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error communicating with AI provider: {e!s}",
            ) from e

        title = transcripts.clean_title(response.content or "")
        if title:
            chat.title = title
            _ = await self.chat_repo.update(chat)
            await self.chat_repo.commit()
        return chat.title or ""

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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Message '{message_id}' not found in chat '{chat_id}'",
            )

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

    async def _classify_and_audit(
        self,
        *,
        gateway: ProviderGateway,
        api_messages: list[dict[str, Any]],
        chat_id: str,
        start: float,
        content: str | None,
        reasoning: str | None,
        finish_reason: str | None,
        usage: TokenUsage | None,
        raw: dict[str, Any] | None = None,
    ) -> CompletionOutcome:
        """Classify the completion, record the audit (status = the outcome), and
        warn on a non-usable result. The caller decides how to surface it (raise
        vs stream error event)."""
        outcome = classify_completion(content, reasoning, finish_reason)
        await self._record_llm_audit(
            gateway=gateway,
            api_messages=api_messages,
            chat_id=chat_id,
            latency_ms=(time.perf_counter() - start) * 1000,
            content=content,
            reasoning=reasoning,
            finish_reason=finish_reason,
            usage=usage,
            raw=raw,
            status_override=None if outcome == CompletionOutcome.USABLE else outcome.value,
        )
        if outcome != CompletionOutcome.USABLE:
            logger.warning(
                "non_usable_completion",
                chat_id=chat_id,
                outcome=outcome.value,
                finish_reason=finish_reason,
            )
        return outcome

    async def _audit_error(
        self,
        *,
        gateway: ProviderGateway,
        api_messages: list[dict[str, Any]],
        chat_id: str,
        start: float,
        error: Exception,
    ) -> None:
        """Record a failed LLM call (exception path)."""
        await self._record_llm_audit(
            gateway=gateway,
            api_messages=api_messages,
            chat_id=chat_id,
            latency_ms=(time.perf_counter() - start) * 1000,
            error=error,
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
        activated_lore = self._get_activated_lore(chat, messages)
        rag_results = await self._retrieve_rag_context(chat, messages)
        api_messages = self.prompt_builder.build_api_messages(
            chat, messages, activated_lore=activated_lore, rag_results=rag_results
        )

        estimated_tokens = self._log_token_budget(api_messages)

        gateway = gateway_factory.build_gateway(chat)
        start = time.perf_counter()
        try:
            response = await gateway.chat_completion(api_messages)
        except Exception as e:
            await self._audit_error(
                gateway=gateway, api_messages=api_messages, chat_id=chat_id, start=start, error=e
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error communicating with AI provider: {str(e)}",
            ) from e

        outcome = await self._classify_and_audit(
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
        # An empty/filtered/truncated result is not a real reply — surface it
        # rather than saving a blank assistant message.
        if outcome != CompletionOutcome.USABLE:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail=_outcome_message(outcome)
            )

        try:
            # Log token drift if provider reports actual usage
            if response.usage.input_tokens:
                logger.info(
                    "token_drift",
                    estimated=estimated_tokens,
                    actual=response.usage.input_tokens,
                )
            if response.usage.cache_read_tokens:
                logger.info(
                    "prompt_cache_hit",
                    cached_tokens=response.usage.cache_read_tokens,
                    created_tokens=response.usage.cache_creation_tokens,
                )

            assistant_content, reasoning, token_count = self._normalize_reply(
                response.content, response.reasoning, response.usage
            )

            assistant_message = Message(
                chat_id=chat_id,
                role=MessageRole.ASSISTANT,
                content=assistant_content,
                token_count=token_count,
                reasoning_content=reasoning,
            )
            created = await self.message_repo.create(assistant_message)
            await self.message_repo.commit()

            await self._update_chat_metadata(chat_id, assistant_content)

            await self._vectorize(user_message)
            await self._vectorize(created)
            return created

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error communicating with AI provider: {str(e)}",
            ) from e

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
            outcome = await self._classify_and_audit(
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

                if existing_message and self.alt_repo:
                    # Regeneration with alternatives: store as alternative
                    await self.alternatives.store(existing_message, full_content, token_count)
                elif existing_message:
                    # Regeneration without alt_repo: update in-place
                    existing_message.content = full_content
                    existing_message.token_count = token_count
                    existing_message.reasoning_content = reasoning
                    await self.message_repo.update(existing_message)
                    await self.message_repo.commit()
                else:
                    # New message
                    assistant_message = Message(
                        id=message_id,
                        chat_id=chat_id,
                        role=MessageRole.ASSISTANT,
                        content=full_content,
                        token_count=token_count,
                        reasoning_content=reasoning,
                    )
                    _ = await self.message_repo.create(assistant_message)
                    await self.message_repo.commit()
                    await self._vectorize(assistant_message)

                await self._update_chat_metadata(chat_id, full_content)

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
            await self._audit_error(
                gateway=gateway, api_messages=api_messages, chat_id=chat_id, start=start, error=e
            )
            logger.error(f"Error during streaming: {e!s}")
            yield StreamEvent(type="error", message=str(e), code=_classify_error(e))

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
        activated_lore = self._get_activated_lore(chat, messages)
        rag_results = await self._retrieve_rag_context(chat, messages)
        api_messages = self.prompt_builder.build_api_messages(
            chat, messages, activated_lore=activated_lore, rag_results=rag_results
        )

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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot regenerate: No messages in chat",
            )

        last_message = latest_messages[0]
        if last_message.role != MessageRole.ASSISTANT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot regenerate: Last message is not from assistant",
            )

        gateway_factory.validate_model_and_key(chat)

        # Build prompt excluding the last assistant message
        messages = await self.message_repo.find_by_chat_id(chat_id)
        messages_for_prompt = [m for m in messages if m.id != last_message.id]
        activated_lore = self._get_activated_lore(chat, messages_for_prompt)
        rag_results = await self._retrieve_rag_context(chat, messages_for_prompt)
        api_messages = self.prompt_builder.build_api_messages(
            chat, messages_for_prompt, activated_lore=activated_lore, rag_results=rag_results
        )

        gateway = gateway_factory.build_gateway(chat)
        start = time.perf_counter()
        try:
            response = await gateway.chat_completion(api_messages)
        except Exception as e:
            await self._audit_error(
                gateway=gateway, api_messages=api_messages, chat_id=chat_id, start=start, error=e
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error communicating with AI provider: {str(e)}",
            ) from e

        await self._record_llm_audit(
            gateway=gateway,
            api_messages=api_messages,
            chat_id=chat_id,
            latency_ms=(time.perf_counter() - start) * 1000,
            content=response.content,
            reasoning=response.reasoning,
            finish_reason=response.finish_reason,
            usage=response.usage,
            raw=response.raw,
        )

        assistant_content = sanitize_narrative(response.content)
        token_count = response.usage.output_tokens or self.tokenizer.count_tokens(assistant_content)

        await self.alternatives.store(last_message, assistant_content, token_count)
        await self._update_chat_metadata(chat_id, assistant_content)

        return last_message

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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot regenerate: No messages in chat",
            )

        last_message = latest_messages[0]
        # Replace the last assistant turn; for a dangling user turn, append instead.
        existing = last_message if last_message.role == MessageRole.ASSISTANT else None

        gateway_factory.validate_model_and_key(chat)

        messages = await self.message_repo.find_by_chat_id(chat_id)
        messages_for_prompt = (
            [m for m in messages if m.id != last_message.id] if existing else messages
        )
        activated_lore = self._get_activated_lore(chat, messages_for_prompt)
        rag_results = await self._retrieve_rag_context(chat, messages_for_prompt)
        api_messages = self.prompt_builder.build_api_messages(
            chat, messages_for_prompt, activated_lore=activated_lore, rag_results=rag_results
        )

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
