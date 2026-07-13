"""Task-model auxiliary text generation for a chat.

Reply suggestions, tone chips, impersonation drafts, and titles — cheap,
disposable outputs kept off the main send/regenerate path. The ``reply`` and
``tones`` modes run on the cheap task model with a compact prompt; only
``impersonate`` reuses the shared MessageContextBuilder for full scene context.
"""

import time
from typing import Any

from src.chat_message import gateway_factory, llm_audit, transcripts
from src.chat_message.context import MessageContextBuilder
from src.chat_message.helpers import get_chat_or_404
from src.chat_message.normalize import parse_structured_list
from src.chat_message.repository_async import AsyncMessageRepository
from src.chat_message.schemas import SuggestionMode
from src.chat_session.repository_async import AsyncChatRepository
from src.core.exceptions import ProviderException

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


class AuxiliaryGenerationService:
    """Task-model scaffolding generation (suggestions + titles)."""

    def __init__(
        self,
        message_repo: AsyncMessageRepository,
        chat_repo: AsyncChatRepository,
        context: MessageContextBuilder,
    ):
        self.message_repo = message_repo
        self.chat_repo = chat_repo
        self.context = context

    async def generate_suggestions(
        self,
        chat_id: str,
        mode: SuggestionMode = SuggestionMode.REPLY,
        tone: str | None = None,
        count: int = 3,
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
        chat = await get_chat_or_404(self.chat_repo, chat_id)

        messages = await self.message_repo.find_by_chat_id(chat_id)
        user_name = chat.persona.name if chat.persona else "the user"
        char_name = chat.character.name if chat.character else "the character"

        if mode == SuggestionMode.TONES:
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
        elif mode == SuggestionMode.REPLY:
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
            api_messages = await self.context.assemble(chat, messages)

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
            await llm_audit.audit_error(
                gateway=gateway, api_messages=api_messages, chat_id=chat_id, start=start, error=e
            )
            raise ProviderException("Error communicating with AI provider.") from e

        await llm_audit.record_llm_audit(
            gateway=gateway,
            api_messages=api_messages,
            chat_id=chat_id,
            latency_ms=(time.perf_counter() - start) * 1000,
            content=response.content,
            finish_reason=response.finish_reason,
            usage=response.usage,
        )

        content = (response.content or "").strip()
        if mode == SuggestionMode.IMPERSONATE:
            draft = content.strip().strip('"').strip()
            return [draft] if draft else []
        return parse_structured_list(content, count)

    async def generate_title(self, chat_id: str) -> str:
        """Generate and persist a concise chat title via the task model."""
        chat = await get_chat_or_404(self.chat_repo, chat_id)
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
        api_messages: list[dict[str, Any]] = [{"role": "user", "content": instruction}]
        gateway = gateway_factory.build_task_gateway(chat, minimize_reasoning=True)
        start = time.perf_counter()
        try:
            response = await gateway.chat_completion(api_messages)
        except Exception as e:
            await llm_audit.audit_error(
                gateway=gateway, api_messages=api_messages, chat_id=chat_id, start=start, error=e
            )
            raise ProviderException("Error communicating with AI provider.") from e

        title = transcripts.clean_title(response.content or "")
        if title:
            chat.title = title
            _ = await self.chat_repo.update(chat)
            await self.chat_repo.commit()
        return chat.title or ""
