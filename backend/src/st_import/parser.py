"""Parse and validate a SillyTavern chat-completion preset from raw bytes/JSON."""

import json
from typing import Any

from pydantic import ValidationError

from src.core.logging import get_logger
from src.st_import.errors import STImportError
from src.st_import.schemas import STPreset

logger = get_logger(__name__)

# Telltale keys of a text-completion (instruct) preset, which we do NOT support.
_TEXT_COMPLETION_KEYS = ("temp", "rep_pen", "rep_pen_range", "instruct", "context", "genamt")


def parse_st_preset(raw: str | bytes) -> STPreset:
    """Parse raw input into a validated ``STPreset``.

    Args:
        raw: The uploaded file contents (UTF-8 bytes or text).

    Returns:
        A validated ``STPreset``.

    Raises:
        STImportError: On bad encoding/JSON, a non-object body, a non-preset
            artifact (character card, regex script, text-completion preset), or
            a body missing the chat-completion prompt structure.
    """
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError as e:
            raise STImportError("File is not valid UTF-8 text.") from e

    if not raw.strip():
        raise STImportError("File is empty.")

    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as e:
        raise STImportError(f"Invalid JSON: {e}") from e

    if not isinstance(data, dict):
        raise STImportError("A preset must be a JSON object.")

    _reject_non_preset(data)

    try:
        return STPreset.model_validate(data)
    except ValidationError as e:
        # Log the full pydantic detail server-side; don't dump internal field
        # structure back to the client.
        logger.warning("preset_validation_failed", error=str(e))
        raise STImportError("Preset failed validation: unexpected structure.") from e


def _reject_non_preset(data: dict[str, Any]) -> None:
    """Reject artifacts that are clearly not chat-completion presets."""
    if "spec" in data and str(data.get("spec", "")).startswith("chara_card"):
        raise STImportError(
            "This looks like a character card, not a preset. Use the character importer."
        )
    if "findRegex" in data and "replaceString" in data:
        raise STImportError("This looks like a regex script, not a chat-completion preset.")

    has_prompts = isinstance(data.get("prompts"), list)
    has_order = isinstance(data.get("prompt_order"), list)

    if not has_prompts and not has_order:
        if any(k in data for k in _TEXT_COMPLETION_KEYS):
            raise STImportError(
                "This looks like a text-completion preset. Only chat-completion presets "
                "(with 'prompts' and 'prompt_order') can be imported."
            )
        raise STImportError(
            "Not a SillyTavern chat-completion preset: missing 'prompts' and 'prompt_order'."
        )
    if not has_prompts:
        raise STImportError("Preset is missing the 'prompts' array.")
    if not has_order:
        raise STImportError("Preset is missing the 'prompt_order' array.")
