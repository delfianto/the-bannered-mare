"""Message business logic service (FULLY ASYNC)"""

import re
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, status

from src.audit.writer import audit_logger
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
from src.provider.gateway import ProviderGateway
from src.rag.retrieval_service import RetrievalService

if TYPE_CHECKING:
    from src.model.models import ModelRegistry

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

    def _resolve_active_route(self, model: ModelRegistry):
        """The route a canonical model currently resolves to (provider + identifier)."""
        route = model.active_route
        if route is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{model.display_name}' has no active route configured.",
            )
        return route

    def _validate_model_and_key(self, chat: Chat):
        """Validate that the chat has a model whose active route's provider is keyed."""
        if not chat.model:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chat does not have a valid model assigned.",
            )
        provider = self._resolve_active_route(chat.model).provider
        if not provider.has_api_key():
            env_var_name = provider.get_env_var_name()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"API key not configured for provider '{provider.name}'. Set {env_var_name}",
            )

    async def _build_gateway(self, chat: Chat) -> ProviderGateway:
        """Build a ProviderGateway from the model's active route + optional preset params."""
        if chat.model is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chat does not have a valid model assigned.",
            )
        route = self._resolve_active_route(chat.model)
        preset_params = chat.preset.parameters if chat.preset else None
        return ProviderGateway(
            route.provider,
            chat.model,
            route.model_identifier,
            preset_parameters=preset_params,
        )

    async def _build_task_gateway(self, chat: Chat) -> ProviderGateway:
        """Gateway for auxiliary calls (titles, suggestions, future RAG query
        building). Uses the chat's configured task model, falling back to the
        main chat model. Runs at model defaults — RP preset params don't apply.
        """
        model = chat.task_model or chat.model
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chat does not have a valid model assigned.",
            )
        route = self._resolve_active_route(model)
        provider = route.provider
        if not provider.has_api_key():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"API key not configured for provider '{provider.name}'. "
                    f"Set {provider.get_env_var_name()}"
                ),
            )
        return ProviderGateway(
            route.provider,
            model,
            route.model_identifier,
            preset_parameters=None,
        )

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
    ) -> None:
        """Record one LLM-call audit row (fire-and-forget; never raises)."""
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
                status="success",
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
            transcript = self._recent_transcript(chat, messages)
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
            gateway = await self._build_task_gateway(chat)
        elif mode == "reply":
            # Reply candidates are disposable — the user picks one, edits it, or
            # ignores them — so they don't warrant the full scene context on the
            # main model. Send a compact prompt (recent exchange + who's-who +
            # a short persona voice cue) to the cheap task model instead.
            transcript = self._recent_transcript(chat, messages)
            persona_hint = self._persona_hint(chat)
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
            gateway = await self._build_task_gateway(chat)
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

            gateway = await self._build_gateway(chat)
        start = time.perf_counter()
        try:
            response = await gateway.chat_completion(api_messages)
        except Exception as e:
            await self._record_llm_audit(
                gateway=gateway,
                api_messages=api_messages,
                chat_id=chat_id,
                latency_ms=(time.perf_counter() - start) * 1000,
                error=e,
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

    # --- Title generation (auxiliary; routed through the task model) ---

    @staticmethod
    def _clean_title(text: str) -> str:
        """Reduce model output to a single clean title line."""
        stripped = text.strip()
        line = stripped.splitlines()[0] if stripped else ""
        line = line.strip().strip('"').strip("'").strip()
        line = re.sub(r"[.\s]+$", "", line)
        return line[:200]

    def _title_transcript(self, chat: Chat, messages: list[Message], max_chars: int = 1500) -> str:
        """Compact speaker-tagged transcript of the latest turns for titling."""
        char_name = chat.character.name if chat.character else "Character"
        user_name = chat.persona.name if chat.persona else "User"
        lines: list[str] = []
        for msg in messages[-6:]:
            speaker = user_name if msg.role == MessageRole.USER else char_name
            text = " ".join(msg.content.split())
            if text:
                lines.append(f"{speaker}: {text}")
        return "\n".join(lines)[:max_chars]

    def _persona_hint(self, chat: Chat, max_chars: int = 240) -> str:
        """A short voice cue for the user's persona, for compact suggestion prompts.

        Keeps reply candidates in the user's voice without shipping the whole
        persona card. Empty when no persona/description is set.
        """
        persona = chat.persona
        if not persona or not persona.description:
            return ""
        desc = " ".join(persona.description.split())
        if len(desc) > max_chars:
            desc = desc[:max_chars].rstrip() + "…"
        return f" {persona.name} is: {desc}"

    def _recent_transcript(
        self, chat: Chat, messages: list[Message], turns: int = 4, per_msg: int = 600
    ) -> str:
        """Compact recent transcript for cheap auxiliary calls (tone chips).

        Unlike ``_title_transcript`` this caps each message individually so the
        latest turn (the one tones react to) is always kept intact, rather than
        truncating the whole joined string from the end.
        """
        char_name = chat.character.name if chat.character else "Character"
        user_name = chat.persona.name if chat.persona else "User"
        lines: list[str] = []
        for msg in messages[-turns:]:
            speaker = user_name if msg.role == MessageRole.USER else char_name
            text = " ".join(msg.content.split())
            if len(text) > per_msg:
                text = text[:per_msg].rstrip() + "…"
            if text:
                lines.append(f"{speaker}: {text}")
        return "\n".join(lines)

    async def generate_title(self, chat_id: str) -> str:
        """Generate and persist a concise chat title via the task model."""
        chat = await self._get_chat_by_id(chat_id)
        messages = await self.message_repo.find_by_chat_id(chat_id)
        transcript = self._title_transcript(chat, messages)
        if not transcript:
            return chat.title or ""

        instruction = (
            "Generate a concise, specific title for the roleplay conversation below. "
            "3-6 words, Title Case, no quotation marks, no trailing punctuation. Reply "
            "with only the title.\n\n"
            f"{transcript}"
        )
        api_messages = [{"role": "user", "content": instruction}]
        gateway = await self._build_task_gateway(chat)
        start = time.perf_counter()
        try:
            response = await gateway.chat_completion(api_messages)
        except Exception as e:
            await self._record_llm_audit(
                gateway=gateway,
                api_messages=api_messages,
                chat_id=chat_id,
                latency_ms=(time.perf_counter() - start) * 1000,
                error=e,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error communicating with AI provider: {e!s}",
            ) from e

        title = self._clean_title(response.content or "")
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
        gateway = await self._build_gateway(chat)
        route = self._resolve_active_route(chat.model) if chat.model else None
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

    async def send_message(self, chat_id: str, content: str) -> Message:
        """Send a message and get an AI response (non-streaming)"""
        chat = await self._get_chat_by_id(chat_id)
        self._validate_model_and_key(chat)

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

        gateway = await self._build_gateway(chat)
        start = time.perf_counter()
        try:
            response = await gateway.chat_completion(api_messages)
        except Exception as e:
            await self._record_llm_audit(
                gateway=gateway,
                api_messages=api_messages,
                chat_id=chat_id,
                latency_ms=(time.perf_counter() - start) * 1000,
                error=e,
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

            assistant_content = response.content
            reasoning = response.reasoning

            # Auto-parse think tags if API didn't provide reasoning
            if not reasoning:
                assistant_content, reasoning = parse_reasoning_tags(assistant_content)

            # Strip any HTML/graphics the model leaked into the prose before we
            # store it, so history and token counts stay clean.
            assistant_content = sanitize_narrative(assistant_content)

            token_count = response.usage.output_tokens or self.tokenizer.count_tokens(
                assistant_content
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

        gateway = await self._build_gateway(chat)
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

            # Capture the audit from the raw assembled stream, before think-tag parsing
            await self._record_llm_audit(
                gateway=gateway,
                api_messages=api_messages,
                chat_id=chat_id,
                latency_ms=(time.perf_counter() - start) * 1000,
                content=full_content or None,
                reasoning=full_reasoning or None,
                finish_reason=last_finish_reason,
                usage=last_usage,
            )

            if full_content:
                reasoning = full_reasoning or None

                # Auto-parse think tags if API didn't provide reasoning
                if not reasoning:
                    full_content, reasoning = parse_reasoning_tags(full_content)

                # Strip leaked HTML/graphics before storing (UI also strips on render).
                full_content = sanitize_narrative(full_content)

                token_count = (
                    last_usage.output_tokens
                    if last_usage and last_usage.output_tokens
                    else self.tokenizer.count_tokens(full_content)
                )

                if existing_message and self.alt_repo:
                    # Regeneration with alternatives: store as alternative
                    await self._store_alternative(existing_message, full_content, token_count)
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
            await self._record_llm_audit(
                gateway=gateway,
                api_messages=api_messages,
                chat_id=chat_id,
                latency_ms=(time.perf_counter() - start) * 1000,
                error=e,
            )
            logger.error(f"Error during streaming: {e!s}")
            yield StreamEvent(type="error", message=str(e), code=_classify_error(e))

    async def send_message_stream(self, chat_id: str, content: str) -> AsyncIterator[StreamEvent]:
        """Send a message and get a streaming AI response."""
        chat = await self._get_chat_by_id(chat_id)
        self._validate_model_and_key(chat)

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

    async def _store_alternative(
        self, message: Message, new_content: str, token_count: int
    ) -> None:
        """Preserve old content as alternative and update message with new content."""
        if not self.alt_repo:
            return

        # On first regeneration, preserve original content as ordinal 0
        existing_count = await self.alt_repo.count_by_message_id(message.id)
        if existing_count == 0:
            original_alt = MessageAlternative(
                message_id=message.id,
                content=message.content,
                token_count=message.token_count,
                ordinal=0,
            )
            await self.alt_repo.create(original_alt)
            existing_count = 1

        # Store new response as next alternative
        new_alt = MessageAlternative(
            message_id=message.id,
            content=new_content,
            token_count=token_count,
            ordinal=existing_count,
        )
        await self.alt_repo.create(new_alt)

        # Update message to show new content
        message.content = new_content
        message.token_count = token_count
        message.active_index = existing_count
        await self.message_repo.update(message)
        await self.message_repo.commit()

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

        self._validate_model_and_key(chat)

        # Build prompt excluding the last assistant message
        messages = await self.message_repo.find_by_chat_id(chat_id)
        messages_for_prompt = [m for m in messages if m.id != last_message.id]
        activated_lore = self._get_activated_lore(chat, messages_for_prompt)
        rag_results = await self._retrieve_rag_context(chat, messages_for_prompt)
        api_messages = self.prompt_builder.build_api_messages(
            chat, messages_for_prompt, activated_lore=activated_lore, rag_results=rag_results
        )

        gateway = await self._build_gateway(chat)
        start = time.perf_counter()
        try:
            response = await gateway.chat_completion(api_messages)
        except Exception as e:
            await self._record_llm_audit(
                gateway=gateway,
                api_messages=api_messages,
                chat_id=chat_id,
                latency_ms=(time.perf_counter() - start) * 1000,
                error=e,
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

        await self._store_alternative(last_message, assistant_content, token_count)
        await self._update_chat_metadata(chat_id, assistant_content)

        return last_message

    async def regenerate_stream(self, chat_id: str) -> AsyncIterator[StreamEvent]:
        """Regenerate the last assistant message (streaming). Stores old content as alternative."""
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

        self._validate_model_and_key(chat)

        messages = await self.message_repo.find_by_chat_id(chat_id)
        messages_for_prompt = [m for m in messages if m.id != last_message.id]
        activated_lore = self._get_activated_lore(chat, messages_for_prompt)
        rag_results = await self._retrieve_rag_context(chat, messages_for_prompt)
        api_messages = self.prompt_builder.build_api_messages(
            chat, messages_for_prompt, activated_lore=activated_lore, rag_results=rag_results
        )

        async for event in self._stream_completion(
            chat_id, chat, api_messages, existing_message=last_message
        ):
            yield event

    # --- Alternative Management ---

    async def list_alternatives(self, chat_id: str, message_id: str) -> list[MessageAlternative]:
        """List all alternatives for a message."""
        message = await self.message_repo.find_by_id_in_chat(message_id, chat_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Message '{message_id}' not found",
            )
        if not self.alt_repo:
            return []
        return await self.alt_repo.find_by_message_id(message_id)

    async def activate_alternative(
        self, chat_id: str, message_id: str, alternative_id: str
    ) -> Message:
        """Switch the active alternative on a message."""
        message = await self.message_repo.find_by_id_in_chat(message_id, chat_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Message '{message_id}' not found",
            )

        if not self.alt_repo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Alternatives system not available",
            )

        alt = await self.alt_repo.find_by_id(alternative_id)
        if not alt or alt.message_id != message_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alternative '{alternative_id}' not found for message '{message_id}'",
            )

        message.content = alt.content
        message.token_count = alt.token_count
        message.active_index = alt.ordinal
        await self.message_repo.update(message)
        await self.message_repo.commit()
        return message
