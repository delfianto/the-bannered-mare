"Service for building LLM prompts using templates and context"

import math
from dataclasses import dataclass
from typing import Any

from src.character.models import Character
from src.chat_session.models import Chat
from src.core.persistence.enums import InsertionPosition
from src.core.persistence.models import Message, ModelFamily
from src.core.tokenization import get_tokenizer
from src.core.utils.template import TemplateContext, TemplateService
from src.lore.activation_engine import ActivatedEntry
from src.persona.models import Persona
from src.prompt_template.models import PromptTemplate
from src.prompt_template.repository import PromptTemplateRepository

# Default depth (messages from the end) for at_depth fragments without an explicit depth.
DEFAULT_DEPTH = 4

# History eviction rounds the dropped-count up to a multiple of this block so the
# kept prefix is byte-stable for ~EVICTION_BLOCK turns between evictions — prefix
# caching (and llama.cpp KV reuse) only matches when the window start is fixed.
EVICTION_BLOCK = 8


@dataclass
class DepthInjection:
    """A snippet spliced into the chat history at a given depth from the end.

    Shared mechanism for lore AT_DEPTH entries and `at_depth` prompt fragments
    (drift-prevention reminders) — both keep instructions near the generation point.
    """

    content: str
    depth: int
    role: str


class PromptBuilder:
    """Builder for constructing multi-component LLM prompts"""

    def __init__(self, template_repo: PromptTemplateRepository):
        self.template_repo = template_repo
        self.template_service = TemplateService()

    def build_api_messages(
        self,
        chat: Chat,
        messages: list[Message],
        persona: Persona | None = None,
        activated_lore: list[ActivatedEntry] | None = None,
        rag_results: list[Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Build message array for API call based on chat context and template"""
        template = chat.template
        if not template and chat.model:
            template = chat.model.template
        if not template:
            template = self.template_repo.find_default()

        if not template:
            return self._build_fallback_messages(chat, messages)

        context = TemplateContext(
            character=chat.character,
            persona=persona or chat.persona,
            chat=chat,
        )

        # Group lore entries by position
        lore_by_position = self._group_lore(activated_lore)

        # Depth-injected content: lore AT_DEPTH entries + at_depth prompt fragments
        # (drift reminders) ride the same in-history injection mechanism.
        depth_injections: list[DepthInjection] = [
            DepthInjection(content=e.content, depth=e.depth, role=e.role)
            for e in lore_by_position.get(InsertionPosition.AT_DEPTH, [])
        ]
        depth_injections.extend(self._build_depth_fragments(template, context))

        system_content = self._resolve_system_prompt(chat.character, template, context)

        components: dict[str, list[dict[str, Any]]] = {
            "system_prompt": [{"role": "system", "content": system_content}],
            "world_lore_before_character": self._lore_to_messages(
                lore_by_position.get(InsertionPosition.BEFORE_CHARACTER, [])
            ),
            "character_context": self._build_character_context(chat.character),
            "world_lore_after_character": self._lore_to_messages(
                lore_by_position.get(InsertionPosition.AFTER_CHARACTER, [])
            ),
            "scenario": self._build_scenario(chat.character),
            "persona": self._build_persona_context(persona or chat.persona),
            "world_lore_before_examples": self._lore_to_messages(
                lore_by_position.get(InsertionPosition.BEFORE_EXAMPLES, [])
            ),
            "example_dialogues": self._build_example_dialogues(chat.character),
            "chat_history": self._build_chat_history(
                messages,
                template,
                depth_injections,
                chat.model.model_family if chat.model else None,
            ),
            "post_history_instructions": self._build_post_history_instructions(chat.character),
        }

        # Fragment injection positions — inject after specific components
        _FRAGMENT_POSITIONS: dict[str, str] = {
            "system_prompt": "after_system",
            "example_dialogues": "pre_history",
            "chat_history": "post_history",
        }

        api_messages: list[dict[str, Any]] = []

        component_order = template.component_order
        for component_name in component_order:
            # RAG is emitted authoritatively after chat_history (below) so the
            # cacheable prefix is not severed by per-turn retrieval — ignore it
            # wherever the stored template order places it.
            if component_name == "rag_context":
                continue
            if template.components_enabled.get(component_name, True):
                api_messages.extend(components.get(component_name, []))
            if component_name == "chat_history" and template.components_enabled.get(
                "rag_context", True
            ):
                api_messages.extend(self._build_rag_context(rag_results))
            # Inject fragments after specific components
            if component_name in _FRAGMENT_POSITIONS:
                position = _FRAGMENT_POSITIONS[component_name]
                api_messages.extend(self._build_fragments(template, context, position))

        return api_messages

    def _resolve_system_prompt(
        self, character: Character, template: PromptTemplate, context: TemplateContext
    ) -> str:
        """Resolve system prompt: character.system_prompt overrides template.system_template."""
        if character.system_prompt:
            return self.template_service.render(character.system_prompt, context)
        return self.template_service.render(template.system_template, context)

    def _build_fragments(
        self, template: PromptTemplate, context: TemplateContext, position: str
    ) -> list[dict[str, Any]]:
        """Render attached prompt fragments at a given injection position."""
        if not hasattr(template, "template_fragments") or not template.template_fragments:
            return []
        messages: list[dict[str, Any]] = []
        for tf in template.template_fragments:
            if tf.position == position:
                rendered = self.template_service.render(tf.fragment.content, context)
                if rendered.strip():
                    messages.append({"role": "system", "content": rendered})
        return messages

    def _build_depth_fragments(
        self, template: PromptTemplate, context: TemplateContext
    ) -> list[DepthInjection]:
        """Render `at_depth` prompt fragments (drift reminders) into depth injections."""
        if not getattr(template, "template_fragments", None):
            return []
        out: list[DepthInjection] = []
        for tf in template.template_fragments:
            if tf.position == "at_depth":
                rendered = self.template_service.render(tf.fragment.content, context)
                if rendered.strip():
                    out.append(
                        DepthInjection(
                            content=rendered,
                            depth=tf.depth or DEFAULT_DEPTH,
                            role="system",
                        )
                    )
        return out

    def _build_rag_context(self, results: list[Any] | None) -> list[dict[str, Any]]:
        """Build RAG context from retrieved chunks."""
        if not results:
            return []
        texts = [r.content if hasattr(r, "content") else str(r) for r in results]
        if not texts:
            return []
        context = "Relevant context from previous conversations and knowledge:\n" + "\n---\n".join(
            texts
        )
        return [{"role": "system", "content": context}]

    def _group_lore(
        self, entries: list[ActivatedEntry] | None
    ) -> dict[InsertionPosition, list[ActivatedEntry]]:
        """Group activated lore entries by insertion position."""
        grouped: dict[InsertionPosition, list[ActivatedEntry]] = {
            pos: [] for pos in InsertionPosition
        }
        if not entries:
            return grouped
        for entry in entries:
            grouped[entry.position].append(entry)
        return grouped

    def _lore_to_messages(self, entries: list[ActivatedEntry]) -> list[dict[str, Any]]:
        """Convert lore entries to API message dicts."""
        return [{"role": entry.role, "content": entry.content} for entry in entries]

    def _build_character_context(self, character: Character) -> list[dict[str, Any]]:
        """Build character context (description, personality)"""
        content = []
        if character.description:
            content.append(f"Description: {character.description}")
        if character.personality:
            content.append(f"Personality: {character.personality}")

        if not content:
            return []

        return [{"role": "system", "content": "\n".join(content)}]

    def _build_scenario(self, character: Character) -> list[dict[str, Any]]:
        """Build scenario context"""
        if not character.scenario:
            return []
        return [{"role": "system", "content": f"Scenario: {character.scenario}"}]

    def _build_persona_context(self, persona: Persona | None) -> list[dict[str, Any]]:
        """Build user persona context"""
        if not persona or not persona.description:
            return []
        return [{"role": "system", "content": f"User Persona: {persona.description}"}]

    def _build_example_dialogues(self, character: Character) -> list[dict[str, Any]]:
        """Build example dialogues from character data"""
        if not character.example_dialogues:
            return []

        messages = []
        for dialogue in character.example_dialogues:
            if isinstance(dialogue, dict) and "role" in dialogue and "content" in dialogue:
                messages.append(dialogue)
            elif isinstance(dialogue, str):
                if dialogue.startswith(f"{character.name}:"):
                    messages.append({"role": "assistant", "content": dialogue})
                else:
                    messages.append({"role": "user", "content": dialogue})
        return messages

    def _build_chat_history(
        self,
        messages: list[Message],
        template: PromptTemplate,
        depth_injections: list[DepthInjection] | None = None,
        family: ModelFamily | None = None,
    ) -> list[dict[str, Any]]:
        """Build chat history with token budget + depth-injected reminders (lore + fragments).

        Eviction is block-chunked: the minimum number of oldest messages that must
        be dropped to fit the budget (``cut_min``) is rounded up to a multiple of
        ``EVICTION_BLOCK``. Because ``cut_min`` is monotonically non-decreasing as
        the chat grows and old message token counts never change, the rounded cut
        only moves once per ``EVICTION_BLOCK`` turns → the history prefix is
        byte-stable between evictions, so prefix caching / KV reuse can match it.
        Rounding up always fits the budget (drops at least ``cut_min``).
        """
        max_tokens = template.max_history_tokens or 4096

        # Only messages missing a persisted count need live counting (rare), so the
        # family tokenizer is resolved lazily — avoids loading it for the common
        # all-counted case and for the empty-history preview.
        tokenizer = None
        counts = []
        for msg in messages:
            msg_tokens = msg.token_count
            if msg_tokens is None:
                if tokenizer is None:
                    tokenizer = get_tokenizer(family)
                msg_tokens = tokenizer.count(msg.content)
            counts.append(msg_tokens + 3)

        total = sum(counts)
        cut_min = 0
        while cut_min < len(messages) and total > max_tokens:
            total -= counts[cut_min]
            cut_min += 1

        if cut_min:
            cut = min(len(messages), math.ceil(cut_min / EVICTION_BLOCK) * EVICTION_BLOCK)
        else:
            cut = 0

        history = [{"role": m.role.value, "content": m.content} for m in messages[cut:]]

        # Splice depth-anchored content (lore AT_DEPTH + at_depth fragments) into history.
        # Deeper entries first so earlier insertions don't shift later indices.
        if depth_injections and history:
            for inj in sorted(depth_injections, key=lambda d: d.depth, reverse=True):
                insert_idx = max(0, len(history) - inj.depth)
                history.insert(insert_idx, {"role": inj.role, "content": inj.content})

        return history

    def _build_post_history_instructions(self, character: Character) -> list[dict[str, Any]]:
        """Build post-history instructions (jailbreaks, specific RP rules)"""
        if not character.post_history_instructions:
            return []
        return [{"role": "system", "content": character.post_history_instructions}]

    def _build_fallback_messages(self, chat: Chat, messages: list[Message]) -> list[dict[str, Any]]:
        """Fallback basic message construction if no template exists"""
        api_messages = []

        char_ctx = f"You are {chat.character.name}."
        if chat.character.description:
            char_ctx += f" {chat.character.description}"
        api_messages.append({"role": "system", "content": char_ctx})

        for msg in messages:
            api_messages.append({"role": msg.role.value, "content": msg.content})

        return api_messages
