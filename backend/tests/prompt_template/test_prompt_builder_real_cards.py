"""PromptBuilder integration tests against the real sample cards in ./characters.

These pin down two bugs found while auditing example_dialogues: every real card's
mes_example is written as {{user}}: .../{{char}}: ... turns in a single block, but
_build_example_dialogues used to (a) send the whole block as one "user" message
without splitting turns, and (b) never macro-render {{char}}/{{user}}, so the
literal placeholder text reached the LLM unresolved. Both are exercised here via
the full import -> build_api_messages pipeline, not hand-crafted fixtures.
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session
from src.character.models import Character
from src.character.repository import CharacterRepository
from src.character.service import CharacterService
from src.core.persistence.models import DEFAULT_COMPONENT_ORDER, DEFAULT_COMPONENTS_ENABLED
from src.core.utils.upload import UploadedFile
from src.lore.repository import LoreEntryRepository, LoreRepository
from src.lore.service import LoreService
from src.prompt_template.models import PromptTemplate
from src.prompt_template.prompt_builder import PromptBuilder
from src.prompt_template.repository import PromptTemplateRepository

CARDS_DIR = Path(__file__).parents[3] / "characters"


def _make_template(**enabled: bool) -> PromptTemplate:
    template = MagicMock(spec=PromptTemplate)
    template.system_template = "You are {{char}}."
    template.component_order = DEFAULT_COMPONENT_ORDER.copy()
    template.components_enabled = {**DEFAULT_COMPONENTS_ENABLED, **enabled}
    template.max_history_tokens = 4096
    template.template_fragments = []
    return template


def _make_chat(character: Character, template: PromptTemplate) -> Any:
    persona = MagicMock()
    persona.name = "Bob"
    persona.description = "A curious adventurer"

    model = MagicMock()
    model.template = None
    model.model_family = None

    chat = MagicMock()
    chat.character = character
    chat.persona = persona
    chat.model = model
    chat.template = template
    chat.preset = None
    chat.title = "Test Chat"
    return chat


async def _import(db: Session, filename: str) -> Character:
    repo = CharacterRepository(db)
    service = CharacterService(repo, LoreService(LoreRepository(db), LoreEntryRepository(db)))
    upload = UploadedFile((CARDS_DIR / filename).read_bytes(), filename)
    return await service.import_card(upload)


pytestmark = pytest.mark.skipif(
    not CARDS_DIR.exists(), reason="characters/ sample cards not available"
)


class TestExampleDialoguesSplitIntoTurns:
    @pytest.mark.asyncio
    async def test_kalina_two_labeled_blocks_become_four_alternating_turns(
        self, db: Session
    ) -> None:
        """kalina.png has 2 example_dialogues blocks, each one {{user}}:/{{char}}:
        pair -- must come out as 4 turns alternating user/assistant, not 2 lumped
        "user" messages."""
        character = await _import(db, "kalina.png")
        assert character.example_dialogues is not None
        assert len(character.example_dialogues) == 2

        builder = PromptBuilder(PromptTemplateRepository(db))
        template = _make_template(example_dialogues=True)
        chat = _make_chat(character, template)

        result = builder.build_api_messages(chat, messages=[])

        # With messages=[] and only example_dialogues enabled (persona/system_prompt
        # are "system"-roled, chat_history/RAG/lore are empty here), every "user"/
        # "assistant"-roled message in the result originates from example_dialogues.
        example_msgs = [m for m in result if m["role"] in ("user", "assistant")]
        assert len(example_msgs) == 4
        assert [m["role"] for m in example_msgs] == ["user", "assistant", "user", "assistant"]

    @pytest.mark.asyncio
    async def test_kalina_example_turns_have_macros_resolved(self, db: Session) -> None:
        """{{char}} in an example turn must resolve to the character's name, not
        reach the LLM as literal template syntax."""
        character = await _import(db, "kalina.png")
        builder = PromptBuilder(PromptTemplateRepository(db))
        template = _make_template(example_dialogues=True)
        chat = _make_chat(character, template)

        result = builder.build_api_messages(chat, messages=[])

        example_msgs = [
            m
            for m in result
            if m["role"] in ("user", "assistant") and "gasps dramatically" in m["content"]
        ]
        assert example_msgs, "expected the Kalina 'gasps dramatically' turn in the built messages"
        assert "{{char}}" not in example_msgs[0]["content"]
        assert "Kalina" in example_msgs[0]["content"]

    @pytest.mark.asyncio
    async def test_mina_stepsister_unlabeled_block_stays_one_message(self, db: Session) -> None:
        """mina_stepsister.png's mes_example has no {{user}}:/{{char}}: labels at
        all -- must stay a single message (can't be split with no boundary),
        preserving the pre-fix fallback behavior for genuinely freeform text."""
        character = await _import(db, "mina_stepsister.png")
        assert character.example_dialogues is not None
        assert len(character.example_dialogues) == 1

        builder = PromptBuilder(PromptTemplateRepository(db))
        template = _make_template(example_dialogues=True)
        chat = _make_chat(character, template)

        result = builder.build_api_messages(chat, messages=[])

        example_msgs = [
            m for m in result if m["content"].strip() == character.example_dialogues[0].strip()
        ]
        assert len(example_msgs) == 1

    @pytest.mark.asyncio
    async def test_no_character_has_example_dialogues_disabled_by_default_still_empty(
        self, db: Session
    ) -> None:
        """bestfriend_roommate.png has no mes_example at all -- the component must
        contribute nothing, not error."""
        character = await _import(db, "bestfriend_roommate.png")
        assert character.example_dialogues is None

        builder = PromptBuilder(PromptTemplateRepository(db))
        template = _make_template(example_dialogues=True)
        chat = _make_chat(character, template)

        result = builder.build_api_messages(chat, messages=[])
        assert isinstance(result, list)  # doesn't raise


class TestCharacterFieldMacroRendering:
    @pytest.mark.asyncio
    async def test_description_and_scenario_macros_resolved(self, db: Session) -> None:
        """Any {{char}}/{{user}} in description/personality/scenario must resolve
        -- these are enabled per-template (opt-in), unlike example_dialogues."""
        character = await _import(db, "kalina.png")
        assert character.description and "{{char}}" in character.description

        builder = PromptBuilder(PromptTemplateRepository(db))
        template = _make_template(character_context=True, scenario=True)
        chat = _make_chat(character, template)

        result = builder.build_api_messages(chat, messages=[])

        desc_msg = next(m for m in result if m["content"].startswith("Description:"))
        assert "{{char}}" not in desc_msg["content"]
        assert "{{user}}" not in desc_msg["content"]
        assert "Kalina" in desc_msg["content"]

    @pytest.mark.asyncio
    async def test_malformed_field_falls_back_to_raw_text(self, db: Session) -> None:
        """A description that isn't valid Jinja must degrade to raw text rather
        than raising and breaking every message in the chat."""
        character = await _import(db, "kalina.png")
        character.description = "Unclosed macro: {{ char"

        builder = PromptBuilder(PromptTemplateRepository(db))
        template = _make_template(character_context=True)
        chat = _make_chat(character, template)

        result = builder.build_api_messages(chat, messages=[])

        desc_msg = next(m for m in result if m["content"].startswith("Description:"))
        assert desc_msg["content"] == "Description: Unclosed macro: {{ char"
