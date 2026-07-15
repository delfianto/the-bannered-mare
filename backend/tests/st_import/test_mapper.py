"""Tests for build_import_plan — marker/builtin/custom mapping, positions, samplers, warnings."""

import pytest
from src.st_import.mapper import build_import_plan
from src.st_import.schemas import STPreset

from tests.st_import.factories import preset_dict, st_marker, st_prompt

_MARKER_COMPONENT = {
    "charDescription": "character_context",
    "charPersonality": "character_context",
    "scenario": "scenario",
    "personaDescription": "persona",
    "worldInfoBefore": "world_lore_before_character",
    "worldInfoAfter": "world_lore_after_character",
    "dialogueExamples": "example_dialogues",
    "chatHistory": "chat_history",
}


def _plan(prompts, order_items, *, base_name="My Preset", **kw):
    preset = STPreset.model_validate(preset_dict(prompts, order_items, **kw))
    return build_import_plan(preset, base_name)


class TestMarkers:
    @pytest.mark.parametrize("marker,component", list(_MARKER_COMPONENT.items()))
    def test_marker_enables_component(self, marker: str, component: str) -> None:
        plan = _plan([st_marker(marker)], [marker])
        assert plan.template.components_enabled.get(component) is True
        assert component in plan.template.component_order

    def test_char_description_and_personality_dedupe(self) -> None:
        plan = _plan(
            [st_marker("charDescription"), st_marker("charPersonality")],
            ["charDescription", "charPersonality"],
        )
        assert plan.template.component_order.count("character_context") == 1

    def test_component_order_follows_st_order(self) -> None:
        plan = _plan(
            [st_marker("scenario"), st_marker("charDescription")],
            ["scenario", "charDescription"],
        )
        order = plan.template.component_order
        assert order[0] == "system_prompt"
        assert order.index("scenario") < order.index("character_context")

    def test_unknown_marker_warns(self) -> None:
        plan = _plan([{"identifier": "weird", "name": "w", "marker": True}], ["weird"])
        assert any("Unknown marker 'weird'" in w for w in plan.warnings)

    def test_order_references_missing_prompt_warns(self) -> None:
        plan = _plan([st_prompt("real", content="c")], ["real", "ghost"])
        assert any("unknown prompt 'ghost'" in w for w in plan.warnings)

    def test_marker_in_order_without_prompt_definition_enables_component(self) -> None:
        # ST presets may list a marker in prompt_order without a matching prompts[]
        # entry; it must still enable the component, not warn as an unknown prompt.
        plan = _plan(
            [st_prompt("main", system_prompt=True, content="Be {{char}}.")],
            ["main", "chatHistory"],
        )
        assert plan.template.components_enabled.get("chat_history") is True
        assert "chat_history" in plan.template.component_order
        assert not any("unknown prompt 'chatHistory'" in w for w in plan.warnings)


class TestMainAndBuiltins:
    def test_main_becomes_system_template(self) -> None:
        plan = _plan([st_prompt("main", system_prompt=True, content="Be {{char}}.")], ["main"])
        assert plan.template.system_template == "Be {{char}}."

    def test_main_empty_uses_default_and_warns(self) -> None:
        plan = _plan([st_prompt("main", system_prompt=True, content="")], ["main"])
        assert plan.template.system_template == "You are {{char}}."
        assert any("no content" in w for w in plan.warnings)

    def test_main_absent_warns(self) -> None:
        plan = _plan([st_marker("chatHistory")], ["chatHistory"])
        assert any("No 'main' prompt found" in w for w in plan.warnings)

    def test_main_disabled_warns(self) -> None:
        plan = _plan(
            [st_prompt("main", system_prompt=True, content="X"), st_marker("chatHistory")],
            [("main", False), ("chatHistory", True)],
        )
        assert any("disabled" in w for w in plan.warnings)
        assert plan.template.system_template == "You are {{char}}."

    @pytest.mark.parametrize(
        "ident,frag_type",
        [("nsfw", "nsfw"), ("jailbreak", "jailbreak"), ("enhanceDefinitions", "instruction")],
    )
    def test_builtin_fragment_types(self, ident: str, frag_type: str) -> None:
        plan = _plan([st_prompt(ident, system_prompt=True, content="rules")], [ident])
        assert len(plan.fragments) == 1
        assert plan.fragments[0].fragment_type == frag_type

    def test_empty_builtin_skipped_and_warns(self) -> None:
        plan = _plan([st_prompt("nsfw", system_prompt=True, content="")], ["nsfw"])
        assert plan.fragments == []
        assert any("empty content" in w for w in plan.warnings)


class TestCustomPositions:
    def test_relative_before_chat_history_is_after_system(self) -> None:
        plan = _plan(
            [st_prompt("c", content="x"), st_marker("chatHistory")],
            ["c", "chatHistory"],
        )
        assert plan.fragments[0].position == "after_system"
        assert plan.fragments[0].depth is None

    def test_relative_after_chat_history_is_post_history(self) -> None:
        plan = _plan(
            [st_marker("chatHistory"), st_prompt("c", content="x")],
            ["chatHistory", "c"],
        )
        assert plan.fragments[0].position == "post_history"

    def test_relative_between_examples_and_history_is_pre_history(self) -> None:
        plan = _plan(
            [st_marker("dialogueExamples"), st_prompt("c", content="x"), st_marker("chatHistory")],
            ["dialogueExamples", "c", "chatHistory"],
        )
        assert plan.fragments[0].position == "pre_history"

    def test_absolute_maps_to_at_depth_with_depth(self) -> None:
        plan = _plan(
            [st_prompt("c", content="x", injection_position=1, injection_depth=7)],
            ["c"],
        )
        assert plan.fragments[0].position == "at_depth"
        assert plan.fragments[0].depth == 7

    def test_absolute_missing_depth_defaults_to_4(self) -> None:
        plan = _plan(
            [st_prompt("c", content="x", injection_position=1, injection_depth=None)],
            ["c"],
        )
        assert plan.fragments[0].depth == 4

    def test_ordinals_monotonic_skipping_disabled(self) -> None:
        plan = _plan(
            [
                st_prompt("a", content="A"),
                st_prompt("b", content="B"),
                st_prompt("c", content="C"),
            ],
            [("a", True), ("b", False), ("c", True)],
        )
        after_system = [f for f in plan.fragments if f.position == "after_system"]
        assert [f.ordinal for f in after_system] == [0, 1]
        assert {f.name for f in after_system} == {"a", "c"}


class TestEnabledSemantics:
    def test_disabled_order_item_dropped(self) -> None:
        plan = _plan([st_prompt("c", content="x")], [("c", False)])
        assert plan.fragments == []

    def test_order_enabled_overrides_prompt_enabled_false(self) -> None:
        plan = _plan([st_prompt("c", content="x", enabled=False)], [("c", True)])
        assert len(plan.fragments) == 1

    def test_order_enabled_overrides_prompt_enabled_null(self) -> None:
        plan = _plan([st_prompt("c", content="x", enabled=None)], [("c", True)])
        assert len(plan.fragments) == 1


class TestRoleAndFormats:
    def test_non_system_role_warns_but_imports(self) -> None:
        plan = _plan([st_prompt("c", content="x", role="user")], ["c"])
        assert len(plan.fragments) == 1
        assert any("role 'user'" in w for w in plan.warnings)

    def test_format_strings_warn(self) -> None:
        plan = _plan(
            [st_prompt("c", content="x")],
            ["c"],
            extra={"wi_format": "{0}", "scenario_format": "{{scenario}}"},
        )
        assert any("format/nudge strings" in w for w in plan.warnings)


class TestSamplers:
    def test_no_sampler_yields_no_preset(self) -> None:
        plan = _plan([st_prompt("c", content="x")], ["c"])
        assert plan.preset is None
        assert any("No sampler settings" in w for w in plan.warnings)

    def test_samplers_map_with_rename(self) -> None:
        plan = _plan(
            [st_prompt("c", content="x")],
            ["c"],
            samplers={"temperature": 0.8, "openai_max_tokens": 1000},
        )
        assert plan.preset is not None
        assert plan.preset.parameters == {"temperature": 0.8, "max_tokens": 1000}

    def test_sentinel_values_passed_through(self) -> None:
        plan = _plan(
            [st_prompt("c", content="x")],
            ["c"],
            samplers={"top_k": 0, "seed": -1},
        )
        assert plan.preset is not None
        assert plan.preset.parameters == {"top_k": 0, "seed": -1}

    def test_max_context_warns_and_dropped(self) -> None:
        plan = _plan(
            [st_prompt("c", content="x")],
            ["c"],
            samplers={"temperature": 0.5, "openai_max_context": 8000},
        )
        assert plan.preset is not None
        assert "max_context" not in plan.preset.parameters
        assert any("openai_max_context" in w for w in plan.warnings)


class TestNamingAndOrderSelection:
    def test_base_name_flows_into_specs(self) -> None:
        plan = _plan(
            [st_prompt("c", content="x")],
            ["c"],
            base_name="Cool Preset",
            samplers={"temperature": 0.7},
        )
        assert plan.template.name == "Cool Preset"
        assert plan.preset is not None and plan.preset.name == "Cool Preset"
        assert "Cool Preset" in (plan.fragments[0].description or "")

    def test_global_order_prefers_100001(self) -> None:
        preset = STPreset.model_validate(
            {
                "prompts": [st_prompt("a", content="A"), st_prompt("b", content="B")],
                "prompt_order": [
                    {"character_id": 100000, "order": [{"identifier": "a", "enabled": True}]},
                    {"character_id": 100001, "order": [{"identifier": "b", "enabled": True}]},
                ],
            }
        )
        plan = build_import_plan(preset, "p")
        assert [f.name for f in plan.fragments] == ["b"]

    def test_non_global_order_warns_and_uses_first(self) -> None:
        preset = STPreset.model_validate(
            {
                "prompts": [st_prompt("a", content="A")],
                "prompt_order": [
                    {"character_id": 42, "order": [{"identifier": "a", "enabled": True}]}
                ],
            }
        )
        plan = build_import_plan(preset, "p")
        assert [f.name for f in plan.fragments] == ["a"]
        assert any("No global prompt_order" in w for w in plan.warnings)
