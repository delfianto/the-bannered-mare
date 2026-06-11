"""Map a parsed SillyTavern preset onto a Candlekeep import plan (pure, no DB).

ST bundles samplers + a prompt structure in one preset; Candlekeep splits these
into ``Preset`` (samplers) and ``PromptTemplate`` + fragments (prompt structure).
The mapping is faithful where the models allow and records ``warnings`` for the
rest (lost roles, dropped format strings, unknown markers, etc.).
"""

from dataclasses import dataclass, field
from typing import Any

from src.core.persistence import DEFAULT_COMPONENT_ORDER
from src.st_import.schemas import STPreset, STPrompt, STPromptOrder

# ST marker identifier -> Candlekeep prompt component.
_MARKER_TO_COMPONENT: dict[str, str] = {
    "charDescription": "character_context",
    "charPersonality": "character_context",
    "scenario": "scenario",
    "personaDescription": "persona",
    "worldInfoBefore": "world_lore_before_character",
    "worldInfoAfter": "world_lore_after_character",
    "dialogueExamples": "example_dialogues",
    "chatHistory": "chat_history",
}

# Built-in content prompts -> fragment_type (`main` is handled separately).
_BUILTIN_FRAGMENT_TYPES: dict[str, str] = {
    "nsfw": "nsfw",
    "jailbreak": "jailbreak",
    "enhanceDefinitions": "instruction",
}

# ST sampler key -> Preset.parameters key (renamed where Candlekeep differs).
_SAMPLER_KEYS: dict[str, str] = {
    "temperature": "temperature",
    "top_p": "top_p",
    "top_k": "top_k",
    "top_a": "top_a",
    "min_p": "min_p",
    "frequency_penalty": "frequency_penalty",
    "presence_penalty": "presence_penalty",
    "repetition_penalty": "repetition_penalty",
    "openai_max_tokens": "max_tokens",
    "seed": "seed",
    "n": "n",
}

_FORMAT_STRING_KEYS = (
    "scenario_format",
    "personality_format",
    "wi_format",
    "new_chat_prompt",
    "new_example_chat_prompt",
    "new_group_chat_prompt",
    "group_nudge_prompt",
    "continue_nudge_prompt",
    "impersonation_prompt",
)

_GLOBAL_ORDER_PRIORITY = (100001, 100000)
_DEFAULT_SYSTEM_TEMPLATE = "You are {{char}}."
_DEFAULT_DEPTH = 4


@dataclass
class FragmentSpec:
    """A PromptFragment to create plus the TemplateFragment link to attach it."""

    name: str
    content: str
    fragment_type: str
    description: str | None
    position: str
    ordinal: int
    depth: int | None


@dataclass
class TemplateSpec:
    """The PromptTemplate to create."""

    name: str
    system_template: str
    description: str | None
    component_order: list[str]
    components_enabled: dict[str, bool]


@dataclass
class PresetSpec:
    """The sampler Preset to create (only when samplers are present)."""

    name: str
    description: str | None
    parameters: dict[str, Any]


@dataclass
class ImportPlan:
    """A fully-resolved (but not yet persisted) import."""

    template: TemplateSpec
    fragments: list[FragmentSpec] = field(default_factory=list)
    preset: PresetSpec | None = None
    warnings: list[str] = field(default_factory=list)


def _select_global_order(
    orders: list[STPromptOrder],
) -> tuple[STPromptOrder | None, str | None]:
    """Pick the global prompt_order (prefer 100001, then 100000, else first)."""
    if not orders:
        return None, None
    by_char = {o.character_id: o for o in orders}
    for cid in _GLOBAL_ORDER_PRIORITY:
        if cid in by_char:
            return by_char[cid], None
    first = orders[0]
    return first, (
        "No global prompt_order (character_id 100001/100000); used the first entry "
        f"(character_id {first.character_id})."
    )


def build_import_plan(preset: STPreset, base_name: str) -> ImportPlan:
    """Map a parsed preset to a Candlekeep ``ImportPlan`` (names are pre-collision)."""
    warnings: list[str] = []

    prompts_by_id: dict[str, STPrompt] = {}
    for p in preset.prompts:
        if p.identifier in prompts_by_id:
            warnings.append(f"Duplicate prompt identifier '{p.identifier}'; the later one wins.")
        prompts_by_id[p.identifier] = p

    order, order_warn = _select_global_order(preset.prompt_order)
    if order_warn:
        warnings.append(order_warn)
    order_items = order.order if order else []

    system_template = _DEFAULT_SYSTEM_TEMPLATE
    system_template_set = False
    components_enabled: dict[str, bool] = {}
    component_sequence: list[str] = []
    fragments: list[FragmentSpec] = []
    ordinals = {"after_system": 0, "pre_history": 0, "post_history": 0, "at_depth": 0}
    seen_chat_history = False
    seen_examples = False

    def enable_component(comp: str) -> None:
        nonlocal seen_chat_history, seen_examples
        if comp not in component_sequence:
            component_sequence.append(comp)
        components_enabled[comp] = True
        if comp == "chat_history":
            seen_chat_history = True
        if comp == "example_dialogues":
            seen_examples = True

    for item in order_items:
        if not item.enabled:
            continue
        ident = item.identifier
        prompt = prompts_by_id.get(ident)

        # Marker referenced by order; its definition may or may not be in prompts[].
        if prompt is None:
            if ident in _MARKER_TO_COMPONENT:
                enable_component(_MARKER_TO_COMPONENT[ident])
            else:
                warnings.append(f"prompt_order references unknown prompt '{ident}'; skipped.")
            continue

        if prompt.marker:
            comp = _MARKER_TO_COMPONENT.get(ident)
            if comp is None:
                warnings.append(f"Unknown marker '{ident}' dropped.")
            else:
                enable_component(comp)
            continue

        if ident == "main":
            if prompt.content.strip():
                system_template = prompt.content
                system_template_set = True
            else:
                warnings.append("'main' prompt has no content; used a default system prompt.")
            continue

        if not prompt.content.strip():
            warnings.append(f"Prompt '{prompt.name or ident}' has empty content; skipped.")
            continue

        if prompt.injection_position == 1:
            position = "at_depth"
            depth = prompt.injection_depth if prompt.injection_depth is not None else _DEFAULT_DEPTH
        else:
            depth = None
            if seen_chat_history:
                position = "post_history"
            elif seen_examples:
                position = "pre_history"
            else:
                position = "after_system"

        if prompt.role and prompt.role != "system":
            warnings.append(
                f"Prompt '{prompt.name or ident}' has role '{prompt.role}'; imported as a "
                "system fragment (Candlekeep fragments are system-only)."
            )

        name = (prompt.name or ident).strip() or ident
        fragments.append(
            FragmentSpec(
                name=name,
                content=prompt.content,
                fragment_type=_BUILTIN_FRAGMENT_TYPES.get(ident, "instruction"),
                description=f"Imported from SillyTavern preset '{base_name}'.",
                position=position,
                ordinal=ordinals[position],
                depth=depth,
            )
        )
        ordinals[position] += 1

    if not system_template_set and not _has_enabled_main(order_items, prompts_by_id):
        if "main" in prompts_by_id:
            warnings.append("'main' prompt is disabled; used a default system prompt.")
        else:
            warnings.append("No 'main' prompt found; used a default system prompt.")

    template = TemplateSpec(
        name=base_name,
        system_template=system_template,
        description=f"Imported from SillyTavern preset '{base_name}'.",
        component_order=_build_component_order(component_sequence, components_enabled),
        components_enabled=components_enabled,
    )

    preset_spec = _build_preset_spec(preset, base_name, warnings)

    dropped = [k for k in _FORMAT_STRING_KEYS if getattr(preset, k, None)]
    if dropped:
        warnings.append(
            "Dropped ST format/nudge strings with no Candlekeep equivalent: " + ", ".join(dropped)
        )

    return ImportPlan(template=template, fragments=fragments, preset=preset_spec, warnings=warnings)


def _has_enabled_main(order_items: list[Any], prompts_by_id: dict[str, STPrompt]) -> bool:
    return any(it.enabled and it.identifier == "main" for it in order_items)


def _build_component_order(
    component_sequence: list[str], components_enabled: dict[str, bool]
) -> list[str]:
    """system_prompt first, then ST-ordered components, then remaining defaults (disabled)."""
    order: list[str] = ["system_prompt"]
    components_enabled["system_prompt"] = True
    for comp in component_sequence:
        if comp not in order:
            order.append(comp)
    for comp in DEFAULT_COMPONENT_ORDER:
        if comp not in order:
            order.append(comp)
            components_enabled.setdefault(comp, False)
    return order


def _build_preset_spec(preset: STPreset, base_name: str, warnings: list[str]) -> PresetSpec | None:
    params: dict[str, Any] = {}
    for st_key, ck_key in _SAMPLER_KEYS.items():
        value = getattr(preset, st_key, None)
        if value is not None:
            params[ck_key] = value

    if preset.openai_max_context is not None:
        warnings.append("ST 'openai_max_context' is not enforced by Candlekeep; dropped.")

    if not params:
        warnings.append("No sampler settings found; created a prompt template only.")
        return None

    return PresetSpec(
        name=base_name,
        description=f"Sampler settings imported from SillyTavern preset '{base_name}'.",
        parameters=params,
    )
