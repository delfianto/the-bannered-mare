"""Tests for PromptBuilder — component ordering, lore injection, system prompt override, multi-template slots."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session
from src.core.persistence.enums import InsertionPosition
from src.core.persistence.models import (
    DEFAULT_COMPONENT_ORDER,
    DEFAULT_COMPONENTS_ENABLED,
    ModelFamily,
)
from src.lore.activation_engine import ActivatedEntry
from src.prompt_template.models import PromptTemplate
from src.prompt_template.prompt_builder import (
    DEFAULT_MAX_HISTORY_TOKENS,
    DEFAULT_RESERVED_OUTPUT_TOKENS,
    EVICTION_BLOCK,
    PromptBuilder,
)
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
    # No real family/preset in these unit tests: an unknown context window keeps
    # history budgeting on the flat template cap (what these cases assert against).
    model.model_family = None

    chat = MagicMock()
    chat.character = character
    chat.persona = persona
    chat.model = model
    chat.template = template
    chat.preset = None
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


def _make_template_fragment(
    content: str, position: str = "after_system", ordinal: int = 0, depth: int | None = None
) -> Any:
    """Create a mock TemplateFragment with its associated fragment."""
    fragment = MagicMock()
    fragment.content = content

    tf = MagicMock()
    tf.position = position
    tf.ordinal = ordinal
    tf.depth = depth
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

    def test_fragment_at_depth_injected_into_history(self, db: Session) -> None:
        """at_depth fragments (drift reminders) are spliced into chat history by depth."""
        tf = _make_template_fragment("Stay in character as {{char}}.", "at_depth", depth=2)
        template = _make_template(template_fragments=[tf])
        chat = _make_chat(template=template)
        messages = [
            _make_message("user", "msg1"),
            _make_message("assistant", "reply1"),
            _make_message("user", "msg2"),
            _make_message("assistant", "reply2"),
        ]

        repo = PromptTemplateRepository(db)
        builder = PromptBuilder(repo)
        result = builder.build_api_messages(chat, messages, activated_lore=None)

        contents = [m["content"] for m in result]
        reminder = "Stay in character as Alice."
        assert reminder in contents
        # depth=2 → 2 messages from the end: before "msg2"/"reply2".
        assert contents.index(reminder) < contents.index("msg2")
        assert contents.index("reply1") < contents.index(reminder)

    def test_fragment_at_depth_default_depth(self, db: Session) -> None:
        """at_depth fragment with no explicit depth falls back to DEFAULT_DEPTH."""
        tf = _make_template_fragment("Reminder for {{char}}.", "at_depth", depth=None)
        template = _make_template(template_fragments=[tf])
        chat = _make_chat(template=template)
        messages = [_make_message("user", "only message")]

        repo = PromptTemplateRepository(db)
        builder = PromptBuilder(repo)
        result = builder.build_api_messages(chat, messages, activated_lore=None)

        contents = [m["content"] for m in result]
        reminder = "Reminder for Alice."
        # DEFAULT_DEPTH exceeds history length → clamps to the front of history.
        assert reminder in contents
        assert contents.index(reminder) < contents.index("only message")

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


def _make_rag_result(content: str) -> Any:
    """Create a mock RAG result with a ``.content`` attribute."""
    r = MagicMock()
    r.content = content
    return r


# Stored order predating the post-history RAG fix — rag_context sits *before*
# chat_history. The builder must ignore that and emit RAG after the history.
_OLD_RAG_EARLY_ORDER = [
    "system_prompt",
    "world_lore_before_character",
    "character_context",
    "world_lore_after_character",
    "scenario",
    "persona",
    "world_lore_before_examples",
    "example_dialogues",
    "rag_context",
    "chat_history",
    "post_history_instructions",
]


class TestPromptBuilderRagContextPlacement:
    def test_rag_after_history_even_when_stored_order_is_early(self, db: Session) -> None:
        """RAG lands after the last history message and before post_history_instructions,
        even when the stored component_order places rag_context before chat_history."""
        template = _make_template(component_order=_OLD_RAG_EARLY_ORDER)
        chat = _make_chat(template=template)
        chat.character.post_history_instructions = "Post-history jailbreak."
        messages = [
            _make_message("user", "Hello"),
            _make_message("assistant", "Hi there"),
        ]
        rag_results = [_make_rag_result("Remembered fact from RAG.")]

        repo = PromptTemplateRepository(db)
        builder = PromptBuilder(repo)
        result = builder.build_api_messages(
            chat, messages, activated_lore=None, rag_results=rag_results
        )

        contents = [m["content"] for m in result]
        rag_idx = next(i for i, c in enumerate(contents) if "Relevant context" in c)
        last_history_idx = contents.index("Hi there")
        post_hist_idx = contents.index("Post-history jailbreak.")
        assert last_history_idx < rag_idx < post_hist_idx

    def test_rag_before_post_history_fragments(self, db: Session) -> None:
        """RAG is emitted before post_history fragments (which fire after chat_history)."""
        tf = _make_template_fragment("Stay in character as {{char}}.", "post_history")
        template = _make_template(component_order=_OLD_RAG_EARLY_ORDER, template_fragments=[tf])
        chat = _make_chat(template=template)
        messages = [_make_message("user", "Hello")]
        rag_results = [_make_rag_result("RAG fact.")]

        repo = PromptTemplateRepository(db)
        builder = PromptBuilder(repo)
        result = builder.build_api_messages(
            chat, messages, activated_lore=None, rag_results=rag_results
        )

        contents = [m["content"] for m in result]
        rag_idx = next(i for i, c in enumerate(contents) if "Relevant context" in c)
        frag_idx = contents.index("Stay in character as Alice.")
        user_idx = contents.index("Hello")
        assert user_idx < rag_idx < frag_idx

    def test_rag_disabled_no_emission(self, db: Session) -> None:
        """components_enabled rag_context=False suppresses RAG even with results."""
        template = _make_template(
            component_order=_OLD_RAG_EARLY_ORDER,
            components_enabled={**DEFAULT_COMPONENTS_ENABLED, "rag_context": False},
        )
        chat = _make_chat(template=template)
        messages = [_make_message("user", "Hello")]
        rag_results = [_make_rag_result("RAG fact.")]

        repo = PromptTemplateRepository(db)
        builder = PromptBuilder(repo)
        result = builder.build_api_messages(
            chat, messages, activated_lore=None, rag_results=rag_results
        )

        contents = [m["content"] for m in result]
        assert not any("Relevant context" in c for c in contents)

    def test_rag_none_no_emission(self, db: Session) -> None:
        """rag_results=None produces no RAG message."""
        template = _make_template()
        chat = _make_chat(template=template)
        messages = [_make_message("user", "Hello")]

        repo = PromptTemplateRepository(db)
        builder = PromptBuilder(repo)
        result = builder.build_api_messages(chat, messages, activated_lore=None, rag_results=None)

        contents = [m["content"] for m in result]
        assert not any("Relevant context" in c for c in contents)


def _make_history_messages(n: int, prefix: str = "msg") -> list[Any]:
    """n single-word messages: token_count=1 → cost 4 each (1 + 3 framing)."""
    return [_make_message("user", f"{prefix}{i:02d}") for i in range(n)]


class TestPromptBuilderHistoryEviction:
    def test_under_budget_keeps_all_history(self, db: Session) -> None:
        """Under the token budget, every message is included in order (cut_min=0 → cut=0)."""
        template = _make_template(max_history_tokens=4096)
        chat = _make_chat(template=template)
        messages = _make_history_messages(5)

        repo = PromptTemplateRepository(db)
        builder = PromptBuilder(repo)
        result = builder.build_api_messages(chat, messages, activated_lore=None)

        contents = [m["content"] for m in result]
        for m in messages:
            assert m.content in contents
        # History preserved in original order
        hist_contents = [c for c in contents if c.startswith("msg")]
        assert hist_contents == [m.content for m in messages]

    def test_over_budget_prefix_stable_within_eviction_block(self, db: Session) -> None:
        """Once over budget, growing the history by 1..EVICTION_BLOCK-1 messages
        does not change the first included message — the window start is byte-stable
        between evictions so prefix caching can match it."""
        # 1-word messages (cost 4), budget 40 → kept window = 10 messages.
        # N=19 → cut_min=9 (block bottom of [9..16]) → cut=16, first included = msg16.
        template = _make_template(max_history_tokens=40)
        chat = _make_chat(template=template)
        repo = PromptTemplateRepository(db)
        builder = PromptBuilder(repo)

        messages = _make_history_messages(19)
        result = builder.build_api_messages(chat, messages, activated_lore=None)
        hist = [m["content"] for m in result if m["content"].startswith("msg")]
        first_included = hist[0]

        # Grow the history by 1..EVICTION_BLOCK-1 appended messages; the first
        # included message must not move until the next block boundary.
        for added in range(1, EVICTION_BLOCK):
            grown = messages + _make_history_messages(EVICTION_BLOCK, prefix="new")
            result = builder.build_api_messages(chat, grown[: 19 + added], activated_lore=None)
            hist = [m["content"] for m in result if m["content"].startswith("msg")]
            assert hist[0] == first_included, (
                f"first included changed after +{added} msgs: {hist[0]} != {first_included}"
            )

        # The 8th added message crosses the block boundary → eviction fires.
        grown = messages + _make_history_messages(EVICTION_BLOCK, prefix="new")
        result = builder.build_api_messages(chat, grown, activated_lore=None)
        hist = [m["content"] for m in result if m["content"].startswith(("msg", "new"))]
        assert hist[0] != first_included

    @pytest.mark.parametrize("n", [0, 1, 5, 10, 17, 19, 23, 24, 25, 30, 40])
    def test_rounded_cut_never_exceeds_budget(self, db: Session, n: int) -> None:
        """The kept history's total token cost never exceeds max_history_tokens,
        for any history length — block rounding drops at least cut_min messages."""
        max_tokens = 40
        template = _make_template(max_history_tokens=max_tokens)
        chat = _make_chat(template=template)
        messages = _make_history_messages(n)

        repo = PromptTemplateRepository(db)
        builder = PromptBuilder(repo)
        result = builder.build_api_messages(chat, messages, activated_lore=None)
        hist = [m for m in result if m["content"].startswith("msg")]

        total = sum(len(m["content"].split()) + 3 for m in hist)
        assert total <= max_tokens, f"n={n}: kept cost {total} > budget {max_tokens}"


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


def _make_family(
    context_window: int | None, parameters: dict[str, Any] | None = None
) -> ModelFamily:
    """Real ModelFamily so context_window/parameters behave via the actual property.

    A ``test/*`` identifier has no vendor mapping, so its tokenizer resolves to the
    offline heuristic — no network in unit tests.
    """
    return ModelFamily(
        name="Test Family",
        family_identifier="test/family",
        provider_types=["openrouter"],
        parameters=parameters or {},
        extra_metadata={"context_window": context_window} if context_window else {},
    )


def _chat_for_reserved(
    *,
    preset_params: dict[str, Any] | None = None,
    model_params: dict[str, Any] | None = None,
    family: ModelFamily | None = None,
) -> Any:
    chat = MagicMock()
    chat.preset = MagicMock(parameters=preset_params) if preset_params is not None else None
    model = MagicMock()
    model.parameters = model_params if model_params is not None else {}
    model.model_family = family
    chat.model = model
    return chat


class TestReservedOutput:
    def test_preset_param_wins(self) -> None:
        chat = _chat_for_reserved(
            preset_params={"max_tokens": 512}, model_params={"max_tokens": 256}
        )
        assert PromptBuilder._reserved_output(chat) == 512

    def test_model_param_when_no_preset(self) -> None:
        chat = _chat_for_reserved(model_params={"max_completion_tokens": 300})
        assert PromptBuilder._reserved_output(chat) == 300

    def test_family_default_when_neither(self) -> None:
        family = _make_family(8000, {"max_tokens": {"type": "int", "default": 128}})
        chat = _chat_for_reserved(model_params={}, family=family)
        assert PromptBuilder._reserved_output(chat) == 128

    def test_flat_default_when_nothing_resolves(self) -> None:
        chat = _chat_for_reserved(model_params={}, family=_make_family(8000))
        assert PromptBuilder._reserved_output(chat) == DEFAULT_RESERVED_OUTPUT_TOKENS

    def test_ignores_non_positive_value(self) -> None:
        chat = _chat_for_reserved(model_params={"max_tokens": 0})
        assert PromptBuilder._reserved_output(chat) == DEFAULT_RESERVED_OUTPUT_TOKENS


class TestHistoryBudget:
    def test_unknown_window_uses_template_cap(self) -> None:
        template = _make_template(max_history_tokens=1234)
        budget = PromptBuilder._history_budget(
            template, None, non_history_tokens=0, reserved_output=0
        )
        assert budget == 1234

    def test_unknown_window_no_cap_uses_default(self) -> None:
        template = _make_template(max_history_tokens=None)
        budget = PromptBuilder._history_budget(
            template, None, non_history_tokens=0, reserved_output=0
        )
        assert budget == DEFAULT_MAX_HISTORY_TOKENS

    def test_known_window_subtracts_components_and_reply(self) -> None:
        template = _make_template(max_history_tokens=None)
        family = _make_family(10000)
        # int(10000 * 0.9) - 500 reserved - 200 non-history = 8300.
        budget = PromptBuilder._history_budget(
            template, family, non_history_tokens=200, reserved_output=500
        )
        assert budget == 8300

    def test_template_cap_bounds_a_large_window(self) -> None:
        template = _make_template(max_history_tokens=50)
        family = _make_family(1_000_000)
        budget = PromptBuilder._history_budget(
            template, family, non_history_tokens=0, reserved_output=0
        )
        assert budget == 50

    def test_non_history_reduces_budget(self) -> None:
        template = _make_template(max_history_tokens=None)
        family = _make_family(10000)
        lean = PromptBuilder._history_budget(
            template, family, non_history_tokens=100, reserved_output=0
        )
        heavy = PromptBuilder._history_budget(
            template, family, non_history_tokens=5000, reserved_output=0
        )
        assert heavy == lean - 4900

    def test_budget_floored_at_zero(self) -> None:
        template = _make_template(max_history_tokens=None)
        family = _make_family(100)
        budget = PromptBuilder._history_budget(
            template, family, non_history_tokens=0, reserved_output=1000
        )
        assert budget == 0


class TestRealWindowTruncation:
    def test_small_window_evicts_more_than_flat_default(self, db: Session) -> None:
        """A small real context window keeps fewer history turns than the flat 4096
        default the same chat would use when its window is unknown."""
        messages = _make_history_messages(30)
        template = _make_template(max_history_tokens=DEFAULT_MAX_HISTORY_TOKENS)
        repo = PromptTemplateRepository(db)
        builder = PromptBuilder(repo)

        # Unknown window → flat 4096 cap keeps everything (30 × cost-4 = 120 ≪ 4096).
        default_chat = _make_chat(template=template)
        default_hist = [
            m
            for m in builder.build_api_messages(default_chat, messages, activated_lore=None)
            if m["content"].startswith("msg")
        ]

        # A tiny real window (safe ≈ 90 tokens) forces heavy eviction.
        small_chat = _make_chat(template=template)
        small_chat.model.model_family = _make_family(
            100, {"max_tokens": {"type": "int", "default": 10}}
        )
        small_hist = [
            m
            for m in builder.build_api_messages(small_chat, messages, activated_lore=None)
            if m["content"].startswith("msg")
        ]

        assert len(default_hist) == 30
        assert len(small_hist) < len(default_hist)
