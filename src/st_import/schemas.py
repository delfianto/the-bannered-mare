"""Typed models for SillyTavern chat-completion presets and the import result.

The ST models mirror the on-disk preset JSON (lenient: unknown keys ignored,
null name/content coerced to empty) so the parser can validate untrusted files.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


class STOrderItem(BaseModel):
    """One entry in a prompt_order list: an identifier plus its on/off flag."""

    identifier: str
    enabled: bool = True

    model_config = ConfigDict(extra="ignore")


class STPromptOrder(BaseModel):
    """A per-character assembly order. character_id 100001/100000 is the global one."""

    character_id: int
    order: list[STOrderItem] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class STPrompt(BaseModel):
    """A single entry in the preset's `prompts` library (marker, built-in, or custom)."""

    identifier: str
    name: str = ""
    role: str = "system"
    content: str = ""
    system_prompt: bool = False
    marker: bool = False
    injection_position: int | None = None
    injection_depth: int | None = None
    injection_order: int | None = None
    forbid_overrides: bool = False
    # Advisory only; prompt_order[].order[].enabled is authoritative. Can be null in the wild.
    enabled: bool | None = True

    model_config = ConfigDict(extra="ignore")

    @field_validator("name", "content", "role", mode="before")
    @classmethod
    def _coerce_none(cls, v: Any, info: ValidationInfo) -> Any:
        """Tolerate explicit nulls for text fields (markers/older exports)."""
        if v is not None:
            return v
        return "system" if info.field_name == "role" else ""


class STPreset(BaseModel):
    """A SillyTavern chat-completion preset (sampler block optional)."""

    # Sampler / generation settings (all optional; absent in prompts-only presets).
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    top_a: float | None = None
    min_p: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    repetition_penalty: float | None = None
    openai_max_tokens: int | None = None
    openai_max_context: int | None = None
    seed: int | None = None
    n: int | None = None

    # Prompt structure.
    prompts: list[STPrompt] = Field(default_factory=list)
    prompt_order: list[STPromptOrder] = Field(default_factory=list)

    # Format / nudge strings (no Candlekeep equivalent; tracked for warnings).
    scenario_format: str | None = None
    personality_format: str | None = None
    wi_format: str | None = None
    new_chat_prompt: str | None = None
    new_example_chat_prompt: str | None = None
    new_group_chat_prompt: str | None = None
    group_nudge_prompt: str | None = None
    continue_nudge_prompt: str | None = None
    impersonation_prompt: str | None = None

    model_config = ConfigDict(extra="ignore")


class STImportResult(BaseModel):
    """What an import produced, plus warnings for anything that didn't transfer cleanly."""

    template_id: str
    template_name: str
    fragment_ids: list[str] = Field(default_factory=list)
    preset_id: str | None = None
    preset_name: str | None = None
    warnings: list[str] = Field(default_factory=list)
