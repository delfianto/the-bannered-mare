"""Tests for PromptBuilder — component ordering, lore injection, system prompt override, multi-template slots."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session
from src.core.persistence.enums import InsertionPosition
from src.core.persistence.models import DEFAULT_COMPONENT_ORDER, DEFAULT_COMPONENTS_ENABLED
from src.lore.activation_engine import ActivatedEntry
from src.prompt_template.models import PromptTemplate
from src.prompt_template.prompt_builder import PromptBuilder
from src.prompt_template.repository import PromptTemplateRepository


def _make_chat(
    character_name: str = "Alice",
    character_description: str = "A brave knight",
    character_personality: str = "Bold and kind",
    character_scenario: str = "A quest",
    character_system_prompt: str | None = None,
    template: PromptTemplate | None = None,
):
    """Create a mock Chat with character, persona, model, and template."""
    character = MagicMock()
    character.name = character_name
    character.description = character_description
    character.personality = character_personality
    character.scenario = character_scenario
    character.system_prompt = character_system_prompt
    character.first_message = None
    character.example_dialogues = None
    character.post_history_instructions = None
    character.alternate_greetings = None

    persona = MagicMock()
    persona.name = "Bob"
    persona.description = "A curious adventurer"

    model = MagicMock()
    model.template = None

    chat = MagicMock()
    chat.character = character
    chat.persona = persona
    chat.model = model
    chat.template = template
    chat.title = "Test Chat"
    return chat


def _make_message(role: str, content: str) -> Any:
    msg = MagicMock()
    msg.role = MagicMock(value=role)
    msg.content = content
    msg.token_count = len(content.split())
    return msg


def _make_template(**kwargs) -> PromptTemplate:
    template = MagicMock(spec=PromptTemplate)
    template.system_template = kwargs.get("system_template", "You are {{char}}.")
    template.component_order = kwargs.get("component_order", DEFAULT_COMPONENT_ORDER.copy())
    template.components_enabled = kwargs.get(
        "components_enabled", DEFAULT_COMPONENTS_ENABLED.copy()
    )
    template.max_history_tokens = kwargs.get("max_history_tokens", 4096)
    template.template_fragments = kwargs.get("template_fragments", [])
    return template


class TestPromptBuilderLoreInjection:
    def test_lore_before_character_position(self, db: Session) -> None:
        """BEFORE_CHARACTER lore appears between system_prompt and character_context."""
        template = _make_template(
            components_enabled={**DEFAULT_COMPONENTS_ENABLED, "character_context": True},
        )
        chat = _make_chat(template=template)
        messages = [_make_message("user", "Hello")]

        lore = [
            ActivatedEntry(
                content="Ancient dragon lore",
                position=InsertionPosition.BEFORE_CHARACTER,
                depth=0,
                role="system",
                priority=100,
            )
        ]

        repo = PromptTemplateRepository(db)
        builder = PromptBuilder(repo)
        result = builder.build_api_messages(chat, messages, activated_lore=lore)

        contents = [m["content"] for m in result]
        assert "Ancient dragon lore" in contents
        lore_idx = contents.index("Ancient dragon lore")
        # Find system_prompt (first) and character_context
        system_idx = 0  # system_prompt is always first
        char_idx = next(i for i, c in enumerate(contents) if "Description:" in c)
        assert system_idx < lore_idx < char_idx

    def test_lore_after_character_position(self, db: Session) -> None:
        """AFTER_CHARACTER lore appears after character_context."""
        template = _make_template(
            components_enabled={**DEFAULT_COMPONENTS_ENABLED, "character_context": True},
        )
        chat = _make_chat(template=template)
        messages = [_make_message("user", "Hello")]

        lore = [
            ActivatedEntry(
                content="Faction: Knights of Dawn",
                position=InsertionPosition.AFTER_CHARACTER,
                depth=0,
                role="system",
                priority=100,
            )
        ]

        repo = PromptTemplateRepository(db)
        builder = PromptBuilder(repo)
        result = builder.build_api_messages(chat, messages, activated_lore=lore)

        contents = [m["content"] for m in result]
        assert "Faction: Knights of Dawn" in contents
        char_idx = next(i for i, c in enumerate(contents) if "Description:" in c)
        lore_idx = contents.index("Faction: Knights of Dawn")
        assert char_idx < lore_idx

    def test_at_depth_injection(self, db: Session) -> None:
        """AT_DEPTH entry injected at correct position in chat history."""
        template = _make_template()
        chat = _make_chat(template=template)
        messages = [
            _make_message("user", "msg1"),
            _make_message("assistant", "reply1"),
            _make_message("user", "msg2"),
            _make_message("assistant", "reply2"),
        ]

        lore = [
            ActivatedEntry(
                content="Depth injected lore",
                position=InsertionPosition.AT_DEPTH,
                depth=2,
                role="system",
                priority=100,
            )
        ]

        repo = PromptTemplateRepository(db)
        builder = PromptBuilder(repo)
        result = builder.build_api_messages(chat, messages, activated_lore=lore)

        # Find the lore in the result
        contents = [m["content"] for m in result]
        assert "Depth injected lore" in contents
        lore_idx = contents.index("Depth injected lore")
        # Depth 2 means 2 messages from the end of chat history
        msg2_idx = contents.index("reply2")
        assert lore_idx < msg2_idx

    def test_no_lore_backward_compat(self, db: Session) -> None:
        """activated_lore=None produces valid output without errors."""
        template = _make_template()
        chat = _make_chat(template=template)
        messages = [_make_message("user", "Hello")]

        repo = PromptTemplateRepository(db)
        builder = PromptBuilder(repo)
        result = builder.build_api_messages(chat, messages, activated_lore=None)

        assert len(result) >= 2  # system_prompt + at least user message
        assert result[0]["role"] == "system"

    def test_old_component_order_still_works(self, db: Session) -> None:
        """Template with old 7-item order works — lore components silently absent."""
        old_order = [
            "system_prompt",
            "character_context",
            "scenario",
            "persona",
            "example_dialogues",
            "chat_history",
            "post_history_instructions",
        ]
        template = _make_template(component_order=old_order)
        chat = _make_chat(template=template)
        messages = [_make_message("user", "Hello")]

        lore = [
            ActivatedEntry(
                content="This should not appear",
                position=InsertionPosition.BEFORE_CHARACTER,
                depth=0,
                role="system",
                priority=100,
            )
        ]

        repo = PromptTemplateRepository(db)
        builder = PromptBuilder(repo)
        result = builder.build_api_messages(chat, messages, activated_lore=lore)

        contents = [m["content"] for m in result]
        # BEFORE_CHARACTER lore not in old order → should not appear
        assert "This should not appear" not in contents


class TestPromptBuilderSystemPromptOverride:
    def test_character_system_prompt_override(self, db: Session) -> None:
        """character.system_prompt replaces template.system_template."""
        template = _make_template(system_template="Template default for {{char}}.")
        chat = _make_chat(
            character_system_prompt="Custom prompt for {{char}} from card.",
            template=template,
        )
        messages = [_make_message("user", "Hello")]

        repo = PromptTemplateRepository(db)
        builder = PromptBuilder(repo)
        result = builder.build_api_messages(chat, messages, activated_lore=None)

        system_msg = result[0]
        assert system_msg["role"] == "system"
        assert "Custom prompt for Alice from card." in system_msg["content"]
        assert "Template default" not in system_msg["content"]

    def test_character_system_prompt_none_uses_template(self, db: Session) -> None:
        """Empty system_prompt falls back to template."""
        template = _make_template(system_template="Template for {{char}}.")
        chat = _make_chat(character_system_prompt=None, template=template)
        messages = [_make_message("user", "Hello")]

        repo = PromptTemplateRepository(db)
        builder = PromptBuilder(repo)
        result = builder.build_api_messages(chat, messages, activated_lore=None)

        system_msg = result[0]
        assert "Template for Alice." in system_msg["content"]


def _make_template_fragment(content: str, position: str = "after_system", ordinal: int = 0) -> Any:
    """Create a mock TemplateFragment with its associated fragment."""
    fragment = MagicMock()
    fragment.content = content

    tf = MagicMock()
    tf.position = position
    tf.ordinal = ordinal
    tf.fragment = fragment
    return tf


class TestPromptBuilderFragments:
    def test_fragment_after_system_position(self, db: Session) -> None:
        """Fragments at after_system appear right after system_prompt."""
        tf = _make_template_fragment("NSFW allowed for {{char}}.", "after_system")
        template = _make_template(template_fragments=[tf])
        chat = _make_chat(template=template)
        messages = [_make_message("user", "Hello")]

        repo = PromptTemplateRepository(db)
        builder = PromptBuilder(repo)
        result = builder.build_api_messages(chat, messages, activated_lore=None)

        contents = [m["content"] for m in result]
        assert "NSFW allowed for Alice." in contents
        # Should be right after system prompt
        sys_idx = 0
        frag_idx = contents.index("NSFW allowed for Alice.")
        assert frag_idx == sys_idx + 1

    def test_fragment_post_history_position(self, db: Session) -> None:
        """Fragments at post_history appear after chat_history."""
        tf = _make_template_fragment("Stay in character as {{char}}.", "post_history")
        template = _make_template(template_fragments=[tf])
        chat = _make_chat(template=template)
        messages = [_make_message("user", "Hello")]

        repo = PromptTemplateRepository(db)
        builder = PromptBuilder(repo)
        result = builder.build_api_messages(chat, messages, activated_lore=None)

        contents = [m["content"] for m in result]
        assert "Stay in character as Alice." in contents
        # Should be after the user message (chat_history)
        user_idx = next(i for i, c in enumerate(contents) if c == "Hello")
        frag_idx = contents.index("Stay in character as Alice.")
        assert frag_idx > user_idx

    def test_multiple_fragments_ordered(self, db: Session) -> None:
        """Multiple fragments at same position are ordered by ordinal."""
        tf1 = _make_template_fragment("First instruction.", "after_system", ordinal=0)
        tf2 = _make_template_fragment("Second instruction.", "after_system", ordinal=1)
        template = _make_template(template_fragments=[tf1, tf2])
        chat = _make_chat(template=template)
        messages = [_make_message("user", "Hello")]

        repo = PromptTemplateRepository(db)
        builder = PromptBuilder(repo)
        result = builder.build_api_messages(chat, messages, activated_lore=None)

        contents = [m["content"] for m in result]
        idx1 = contents.index("First instruction.")
        idx2 = contents.index("Second instruction.")
        assert idx1 < idx2

    def test_no_fragments_backward_compat(self, db: Session) -> None:
        """Templates without fragments work normally."""
        template = _make_template(template_fragments=[])
        chat = _make_chat(template=template)
        messages = [_make_message("user", "Hello")]

        repo = PromptTemplateRepository(db)
        builder = PromptBuilder(repo)
        result = builder.build_api_messages(chat, messages, activated_lore=None)

        assert len(result) >= 2
        assert result[0]["role"] == "system"


class TestDefaultComponentOrder:
    def test_default_order_has_11_components(self) -> None:
        assert len(DEFAULT_COMPONENT_ORDER) == 11

    def test_lore_components_present(self) -> None:
        assert "world_lore_before_character" in DEFAULT_COMPONENT_ORDER
        assert "world_lore_after_character" in DEFAULT_COMPONENT_ORDER
        assert "world_lore_before_examples" in DEFAULT_COMPONENT_ORDER

    def test_nsfw_jailbreak_removed_from_order(self) -> None:
        assert "nsfw_prompt" not in DEFAULT_COMPONENT_ORDER
        assert "jailbreak_prompt" not in DEFAULT_COMPONENT_ORDER

    def test_system_prompt_first_post_history_last(self) -> None:
        assert DEFAULT_COMPONENT_ORDER[0] == "system_prompt"
        assert DEFAULT_COMPONENT_ORDER[-1] == "post_history_instructions"

    @pytest.mark.parametrize(
        "key",
        DEFAULT_COMPONENT_ORDER,
    )
    def test_all_order_items_in_enabled(self, key: str) -> None:
        assert key in DEFAULT_COMPONENTS_ENABLED
