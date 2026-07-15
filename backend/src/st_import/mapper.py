"""Map a parsed SillyTavern preset onto a Bannered Mare import plan (pure, no DB).

ST bundles samplers + a prompt structure in one preset; The Bannered Mare splits these
into ``Preset`` (samplers) and ``PromptTemplate`` + fragments (prompt structure).
The mapping is faithful where the models allow and records ``warnings`` for the
rest (lost roles, dropped format strings, unknown markers, etc.).
"""

from dataclasses import dataclass, field
from typing import Any

from src.core.persistence import DEFAULT_COMPONENT_ORDER
from src.st_import.schemas import STOrderItem, STPreset, STPrompt, STPromptOrder

# ST marker identifier -> The Bannered Mare prompt component.
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

# ST sampler key -> Preset.parameters key (renamed where The Bannered Mare differs).
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
class ProfileSpec:
    """The Profile to create, tying the template + (optional) preset into one unit."""

    name: str
    description: str | None


@dataclass
class ImportPlan:
    """A fully-resolved (but not yet persisted) import."""

    template: TemplateSpec
    profile: ProfileSpec
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


@dataclass
class _OrderState:
    """Mutable accumulator threaded through order-item classification.

    Replaces the ``nonlocal``-mutating closure in the original loop: it owns the
    ST-ordered component sequence + enabled map, the running system template, the
    per-position fragment ordinals, and the seen-marker flags that decide where a
    relative fragment lands. Its methods are the branch handlers the loop calls.
    """

    base_name: str
    warnings: list[str]
    system_template: str = _DEFAULT_SYSTEM_TEMPLATE
    system_template_set: bool = False
    components_enabled: dict[str, bool] = field(default_factory=dict)
    component_sequence: list[str] = field(default_factory=list)
    fragments: list[FragmentSpec] = field(default_factory=list)
    ordinals: dict[str, int] = field(
        default_factory=lambda: {
            "after_system": 0,
            "pre_history": 0,
            "post_history": 0,
            "at_depth": 0,
        }
    )
    seen_chat_history: bool = False
    seen_examples: bool = False

    def enable_component(self, comp: str) -> None:
        """Enable a component, preserving first-seen ST order; track history/examples."""
        if comp not in self.component_sequence:
            self.component_sequence.append(comp)
        self.components_enabled[comp] = True
        if comp == "chat_history":
            self.seen_chat_history = True
        if comp == "example_dialogues":
            self.seen_examples = True

    def set_system_template(self, prompt: STPrompt) -> None:
        """Adopt the 'main' prompt as the system template (or warn if it is empty)."""
        if prompt.content.strip():
            self.system_template = prompt.content
            self.system_template_set = True
        else:
            self.warnings.append("'main' prompt has no content; used a default system prompt.")

    def add_custom_fragment(self, ident: str, prompt: STPrompt) -> None:
        """Append a system fragment for a non-marker content prompt."""
        position, depth = self._resolve_position(prompt)
        if prompt.role and prompt.role != "system":
            self.warnings.append(
                f"Prompt '{prompt.name or ident}' has role '{prompt.role}'; imported as a "
                "system fragment (The Bannered Mare fragments are system-only)."
            )
        name = (prompt.name or ident).strip() or ident
        self.fragments.append(
            FragmentSpec(
                name=name,
                content=prompt.content,
                fragment_type=_BUILTIN_FRAGMENT_TYPES.get(ident, "instruction"),
                description=f"Imported from SillyTavern preset '{self.base_name}'.",
                position=position,
                ordinal=self.ordinals[position],
                depth=depth,
            )
        )
        self.ordinals[position] += 1

    def _resolve_position(self, prompt: STPrompt) -> tuple[str, int | None]:
        """Absolute injection -> at_depth; else relative to the seen history/examples markers."""
        if prompt.injection_position == 1:
            depth = prompt.injection_depth if prompt.injection_depth is not None else _DEFAULT_DEPTH
            return "at_depth", depth
        if self.seen_chat_history:
            return "post_history", None
        if self.seen_examples:
            return "pre_history", None
        return "after_system", None


def _index_prompts(prompts: list[STPrompt], warnings: list[str]) -> dict[str, STPrompt]:
    """Index prompts by identifier; later duplicates win (with a warning)."""
    by_id: dict[str, STPrompt] = {}
    for p in prompts:
        if p.identifier in by_id:
            warnings.append(f"Duplicate prompt identifier '{p.identifier}'; the later one wins.")
        by_id[p.identifier] = p
    return by_id


def build_import_plan(preset: STPreset, base_name: str) -> ImportPlan:
    """Map a parsed preset to a Bannered Mare ``ImportPlan`` (names are pre-collision)."""
    warnings: list[str] = []
    prompts_by_id = _index_prompts(preset.prompts, warnings)

    order, order_warn = _select_global_order(preset.prompt_order)
    if order_warn:
        warnings.append(order_warn)
    order_items = order.order if order else []

    state = _OrderState(base_name=base_name, warnings=warnings)
    _classify_order_items(order_items, prompts_by_id, state)

    if not state.system_template_set and not _has_enabled_main(order_items, prompts_by_id):
        if "main" in prompts_by_id:
            warnings.append("'main' prompt is disabled; used a default system prompt.")
        else:
            warnings.append("No 'main' prompt found; used a default system prompt.")

    template = _build_template(base_name, state)
    preset_spec = _build_preset(preset, base_name, warnings)

    dropped = [k for k in _FORMAT_STRING_KEYS if getattr(preset, k, None)]
    if dropped:
        warnings.append(
            "Dropped ST format/nudge strings with no Bannered Mare equivalent: "
            + ", ".join(dropped)
        )

    return ImportPlan(
        template=template,
        profile=_build_profile(base_name),
        fragments=state.fragments,
        preset=preset_spec,
        warnings=warnings,
    )


def _classify_order_items(
    order_items: list[STOrderItem],
    prompts_by_id: dict[str, STPrompt],
    state: _OrderState,
) -> None:
    """Walk the global order, enabling components and collecting fragments into ``state``.

    Six item classes: disabled (skip); marker referenced by order but absent from
    prompts[]; marker prompt; 'main' (system template); empty custom (skip); and a
    custom content prompt (fragment). Each was a ``continue`` arm in the original loop.
    """
    for item in order_items:
        if not item.enabled:
            continue
        ident = item.identifier
        prompt = prompts_by_id.get(ident)

        if prompt is None:
            # Marker referenced by order; its definition may or may not be in prompts[].
            if ident in _MARKER_TO_COMPONENT:
                state.enable_component(_MARKER_TO_COMPONENT[ident])
            else:
                state.warnings.append(
                    f"prompt_order references unknown prompt '{ident}'; skipped."
                )
        elif prompt.marker:
            comp = _MARKER_TO_COMPONENT.get(ident)
            if comp is None:
                state.warnings.append(f"Unknown marker '{ident}' dropped.")
            else:
                state.enable_component(comp)
        elif ident == "main":
            state.set_system_template(prompt)
        elif not prompt.content.strip():
            state.warnings.append(f"Prompt '{prompt.name or ident}' has empty content; skipped.")
        else:
            state.add_custom_fragment(ident, prompt)


def _has_enabled_main(order_items: list[STOrderItem], prompts_by_id: dict[str, STPrompt]) -> bool:
    return any(it.enabled and it.identifier == "main" for it in order_items)


def _build_template(base_name: str, state: _OrderState) -> TemplateSpec:
    """Assemble the PromptTemplate spec from the classified order state."""
    return TemplateSpec(
        name=base_name,
        system_template=state.system_template,
        description=f"Imported from SillyTavern preset '{base_name}'.",
        component_order=_build_component_order(state.component_sequence, state.components_enabled),
        components_enabled=state.components_enabled,
    )


def _build_profile(base_name: str) -> ProfileSpec:
    """Assemble the Profile spec that ties the template + optional preset together."""
    return ProfileSpec(
        name=base_name,
        description=f"Imported from SillyTavern preset '{base_name}'.",
    )


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


def _build_preset(preset: STPreset, base_name: str, warnings: list[str]) -> PresetSpec | None:
    params: dict[str, Any] = {}
    for st_key, ck_key in _SAMPLER_KEYS.items():
        value = getattr(preset, st_key, None)
        if value is not None:
            params[ck_key] = value

    if preset.openai_max_context is not None:
        warnings.append("ST 'openai_max_context' is not enforced by The Bannered Mare; dropped.")

    if not params:
        warnings.append("No sampler settings found; created a prompt template only.")
        return None

    return PresetSpec(
        name=base_name,
        description=f"Sampler settings imported from SillyTavern preset '{base_name}'.",
        parameters=params,
    )
