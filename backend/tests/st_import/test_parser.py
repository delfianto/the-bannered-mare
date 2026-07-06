"""Tests for the ST preset parser/validator — happy paths, malformed input, wrong artifacts."""

import json

import pytest
from src.st_import.errors import STImportError
from src.st_import.parser import parse_st_preset

from tests.st_import.factories import preset_dict, st_marker, st_prompt


def _valid_preset_json(**kwargs) -> str:
    data = preset_dict(
        prompts=[st_prompt("main", system_prompt=True, content="You are {{char}}.")],
        order_items=["main", "chatHistory"],
        **kwargs,
    )
    # chatHistory marker must exist in prompts[] too
    data["prompts"].append(st_marker("chatHistory"))
    return json.dumps(data)


class TestParserHappy:
    def test_parses_prompts_and_order(self) -> None:
        preset = parse_st_preset(_valid_preset_json())
        assert len(preset.prompts) == 2
        assert len(preset.prompt_order) == 1
        assert preset.prompt_order[0].character_id == 100001

    def test_parses_with_samplers(self) -> None:
        preset = parse_st_preset(
            _valid_preset_json(
                samplers={"temperature": 0.8, "top_p": 0.9, "openai_max_tokens": 500}
            )
        )
        assert preset.temperature == 0.8
        assert preset.top_p == 0.9
        assert preset.openai_max_tokens == 500

    def test_accepts_bytes(self) -> None:
        preset = parse_st_preset(_valid_preset_json().encode("utf-8"))
        assert preset.prompts

    def test_ignores_unknown_top_level_keys(self) -> None:
        preset = parse_st_preset(
            _valid_preset_json(extra={"chat_completion_source": "openai", "openai_model": "gpt-4o"})
        )
        assert preset.prompts  # unknown keys silently ignored

    def test_enabled_null_in_prompts_ok(self) -> None:
        data = preset_dict(
            prompts=[st_prompt("jailbreak", system_prompt=True, content="JB", enabled=None)],
            order_items=["jailbreak"],
        )
        preset = parse_st_preset(json.dumps(data))
        assert preset.prompts[0].enabled is None

    def test_null_content_coerced_to_empty(self) -> None:
        data = preset_dict(prompts=[st_prompt("x", content=None)], order_items=["x"])  # type: ignore[arg-type]
        preset = parse_st_preset(json.dumps(data))
        assert preset.prompts[0].content == ""

    def test_marker_with_content_tolerated(self) -> None:
        data = preset_dict(
            prompts=[{**st_marker("charDescription"), "content": "oops"}],
            order_items=["charDescription"],
        )
        preset = parse_st_preset(json.dumps(data))
        assert preset.prompts[0].marker is True

    def test_duplicate_identifiers_both_parsed(self) -> None:
        data = preset_dict(
            prompts=[st_prompt("dup", content="a"), st_prompt("dup", content="b")],
            order_items=["dup"],
        )
        preset = parse_st_preset(json.dumps(data))
        assert len(preset.prompts) == 2

    def test_huge_content_parses(self) -> None:
        data = preset_dict(prompts=[st_prompt("big", content="x" * 60000)], order_items=["big"])
        preset = parse_st_preset(json.dumps(data))
        assert len(preset.prompts[0].content) == 60000

    def test_unknown_role_parses(self) -> None:
        data = preset_dict(prompts=[st_prompt("t", role="tool", content="c")], order_items=["t"])
        preset = parse_st_preset(json.dumps(data))
        assert preset.prompts[0].role == "tool"


class TestParserRejects:
    def test_malformed_json(self) -> None:
        with pytest.raises(STImportError, match="Invalid JSON"):
            parse_st_preset(b"{not valid json")

    @pytest.mark.parametrize("body", ["[]", '"a string"', "5", "true", "null"])
    def test_non_object_top_level(self, body: str) -> None:
        with pytest.raises(STImportError, match="must be a JSON object"):
            parse_st_preset(body)

    def test_empty_file(self) -> None:
        with pytest.raises(STImportError, match="empty"):
            parse_st_preset(b"")

    def test_whitespace_only_file(self) -> None:
        with pytest.raises(STImportError, match="empty"):
            parse_st_preset("   \n  ")

    def test_non_utf8_bytes(self) -> None:
        with pytest.raises(STImportError, match="UTF-8"):
            parse_st_preset(b"\xff\xfe\x00\x01")

    def test_text_completion_preset_rejected(self) -> None:
        body = json.dumps({"temp": 0.7, "rep_pen": 1.1, "instruct": {}})
        with pytest.raises(STImportError, match="text-completion"):
            parse_st_preset(body)

    def test_regex_script_rejected(self) -> None:
        body = json.dumps({"findRegex": "/x/", "replaceString": "y"})
        with pytest.raises(STImportError, match="regex"):
            parse_st_preset(body)

    def test_character_card_rejected(self) -> None:
        body = json.dumps({"spec": "chara_card_v2", "data": {"name": "Alice"}})
        with pytest.raises(STImportError, match="character card"):
            parse_st_preset(body)

    def test_missing_prompt_order(self) -> None:
        body = json.dumps({"prompts": [st_prompt("main", content="x")]})
        with pytest.raises(STImportError, match="prompt_order"):
            parse_st_preset(body)

    def test_missing_prompts(self) -> None:
        body = json.dumps({"prompt_order": [{"character_id": 100001, "order": []}]})
        with pytest.raises(STImportError, match="prompts"):
            parse_st_preset(body)

    def test_empty_object_rejected(self) -> None:
        with pytest.raises(STImportError, match="missing 'prompts' and 'prompt_order'"):
            parse_st_preset("{}")
