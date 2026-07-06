"""Tests for the lore activation engine — pure function tests, no mocking needed."""

from unittest.mock import MagicMock

from src.core.persistence.enums import InsertionPosition, MessageRole, SecondaryLogic
from src.core.utils.tokenizer import TokenizerService
from src.lore.activation_engine import activate_entries


def _make_entry(**kwargs):
    """Create a mock LoreEntry with sensible defaults."""
    entry = MagicMock()
    entry.enabled = kwargs.get("enabled", True)
    entry.constant = kwargs.get("constant", False)
    entry.keys = kwargs.get("keys", [])
    entry.secondary_keys = kwargs.get("secondary_keys", [])
    entry.secondary_logic = kwargs.get("secondary_logic", SecondaryLogic.AND_ANY)
    entry.case_sensitive = kwargs.get("case_sensitive", False)
    entry.match_whole_words = kwargs.get("match_whole_words", False)
    entry.use_regex = kwargs.get("use_regex", False)
    entry.content = kwargs.get("content", "Lore content")
    entry.position = kwargs.get("position", InsertionPosition.AFTER_CHARACTER)
    entry.depth = kwargs.get("depth", 4)
    entry.role = kwargs.get("role", MessageRole.SYSTEM)
    entry.priority = kwargs.get("priority", 100)
    entry.ignore_budget = kwargs.get("ignore_budget", False)
    return entry


tokenizer = TokenizerService()


class TestActivationEngine:
    def test_constant_entry_always_activates(self):
        entry = _make_entry(constant=True, content="Always here")
        result = activate_entries([entry], "random text", 0, tokenizer)
        assert len(result) == 1
        assert result[0].content == "Always here"

    def test_keyword_match_activates(self):
        entry = _make_entry(keys=["dragon"], content="Dragons breathe fire")
        result = activate_entries([entry], "I see a dragon ahead", 0, tokenizer)
        assert len(result) == 1
        assert result[0].content == "Dragons breathe fire"

    def test_keyword_no_match_skips(self):
        entry = _make_entry(keys=["dragon"], content="Dragons breathe fire")
        result = activate_entries([entry], "The cat sat on the mat", 0, tokenizer)
        assert len(result) == 0

    def test_case_insensitive_default(self):
        entry = _make_entry(keys=["Dragon"], case_sensitive=False)
        result = activate_entries([entry], "i see a dragon", 0, tokenizer)
        assert len(result) == 1

    def test_case_sensitive_match(self):
        entry = _make_entry(keys=["Dragon"], case_sensitive=True)
        result_lower = activate_entries([entry], "i see a dragon", 0, tokenizer)
        result_upper = activate_entries([entry], "i see a Dragon", 0, tokenizer)
        assert len(result_lower) == 0
        assert len(result_upper) == 1

    def test_whole_word_match(self):
        entry = _make_entry(keys=["war"], match_whole_words=True)
        result_partial = activate_entries([entry], "beware of the warlock", 0, tokenizer)
        result_whole = activate_entries([entry], "the war began", 0, tokenizer)
        assert len(result_partial) == 0
        assert len(result_whole) == 1

    def test_regex_match(self):
        entry = _make_entry(keys=[r"dragon|wyrm"], use_regex=True)
        result1 = activate_entries([entry], "the dragon roars", 0, tokenizer)
        result2 = activate_entries([entry], "an ancient wyrm", 0, tokenizer)
        result3 = activate_entries([entry], "a simple cat", 0, tokenizer)
        assert len(result1) == 1
        assert len(result2) == 1
        assert len(result3) == 0

    def test_multiple_primary_keys_any_match(self):
        entry = _make_entry(keys=["castle", "fortress", "keep"])
        result = activate_entries([entry], "the old fortress stands", 0, tokenizer)
        assert len(result) == 1

    def test_secondary_logic_and_any(self):
        entry = _make_entry(
            keys=["magic"],
            secondary_keys=["fire", "ice"],
            secondary_logic=SecondaryLogic.AND_ANY,
        )
        result = activate_entries([entry], "magic fire spell", 0, tokenizer)
        assert len(result) == 1

    def test_secondary_logic_and_all(self):
        entry = _make_entry(
            keys=["magic"],
            secondary_keys=["fire", "ice"],
            secondary_logic=SecondaryLogic.AND_ALL,
        )
        result_partial = activate_entries([entry], "magic fire spell", 0, tokenizer)
        result_both = activate_entries([entry], "magic fire and ice", 0, tokenizer)
        assert len(result_partial) == 0
        assert len(result_both) == 1

    def test_secondary_logic_not_any(self):
        entry = _make_entry(
            keys=["magic"],
            secondary_keys=["forbidden"],
            secondary_logic=SecondaryLogic.NOT_ANY,
        )
        result_safe = activate_entries([entry], "magic light spell", 0, tokenizer)
        result_forbidden = activate_entries([entry], "forbidden magic", 0, tokenizer)
        assert len(result_safe) == 1
        assert len(result_forbidden) == 0

    def test_secondary_logic_not_all(self):
        entry = _make_entry(
            keys=["magic"],
            secondary_keys=["dark", "evil"],
            secondary_logic=SecondaryLogic.NOT_ALL,
        )
        result_one = activate_entries([entry], "dark magic spell", 0, tokenizer)
        result_both = activate_entries([entry], "dark evil magic", 0, tokenizer)
        assert len(result_one) == 1
        assert len(result_both) == 0

    def test_priority_ordering(self):
        high = _make_entry(keys=["town"], content="Capital city", priority=200)
        low = _make_entry(keys=["town"], content="Small village", priority=50)
        result = activate_entries([low, high], "the town square", 0, tokenizer)
        assert len(result) == 2
        assert result[0].content == "Capital city"
        assert result[1].content == "Small village"

    def test_token_budget_enforcement(self):
        big = _make_entry(keys=["lore"], content="A" * 500, priority=100)
        small = _make_entry(keys=["lore"], content="Short", priority=50)
        result = activate_entries([big, small], "lore text", 20, tokenizer)
        assert len(result) == 1
        assert result[0].content == "Short"

    def test_disabled_entry_skipped(self):
        entry = _make_entry(keys=["test"], enabled=False)
        result = activate_entries([entry], "test text", 0, tokenizer)
        assert len(result) == 0

    def test_empty_keys_no_match(self):
        entry = _make_entry(keys=[], constant=False)
        result = activate_entries([entry], "anything", 0, tokenizer)
        assert len(result) == 0

    def test_position_preserved(self):
        entry = _make_entry(
            keys=["elf"],
            position=InsertionPosition.BEFORE_CHARACTER,
            depth=2,
            role=MessageRole.USER,
        )
        result = activate_entries([entry], "an elf appears", 0, tokenizer)
        assert result[0].position == InsertionPosition.BEFORE_CHARACTER
        assert result[0].depth == 2
        assert result[0].role == "user"
