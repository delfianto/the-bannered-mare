"""Unit tests for pure provider parameter/reasoning resolution.

These call ``resolve_effective_parameters`` / ``should_minimize_reasoning``
directly — no gateway, no provider mock — which is the point of extracting them
from ProviderGateway.
"""

from typing import Any
from unittest.mock import MagicMock

from src.core.persistence.enums import ReasoningMode
from src.provider.parameters import resolve_effective_parameters, should_minimize_reasoning


def _registry(parameters: dict[str, Any], family: Any) -> Any:
    registry = MagicMock()
    registry.parameters = parameters
    registry.model_family = family
    registry.display_name = "Test Model"
    return registry


def test_family_defaults_only() -> None:
    """Family defaults populate when the registry has no overrides."""
    family = MagicMock()
    family.parameters = {
        "temperature": {"type": "float", "default": 0.9},
        "max_tokens": {"type": "int", "default": 4096},
    }
    family.unsupported_parameters = []

    params = resolve_effective_parameters(_registry({}, family), None)
    assert params["temperature"] == 0.9
    assert params["max_tokens"] == 4096


def test_model_overrides_family() -> None:
    """Registry-level overrides take precedence over family defaults."""
    family = MagicMock()
    family.parameters = {
        "temperature": {"type": "float", "default": 1.0},
        "max_tokens": {"type": "int", "default": 2048},
    }
    family.unsupported_parameters = []

    params = resolve_effective_parameters(_registry({"temperature": 0.7}, family), None)
    assert params["temperature"] == 0.7
    assert params["max_tokens"] == 2048


def test_preset_overrides_all() -> None:
    """Preset parameters override both family defaults and registry overrides."""
    family = MagicMock()
    family.parameters = {"temperature": {"type": "float", "default": 1.0}}
    family.unsupported_parameters = []

    params = resolve_effective_parameters(
        _registry({"temperature": 0.7}, family),
        {"temperature": 0.3, "max_tokens": 512, "top_p": 0.95},
    )
    assert params["temperature"] == 0.3
    assert params["max_tokens"] == 512
    assert params["top_p"] == 0.95


def test_no_family() -> None:
    """Handles a registry with no model_family gracefully."""
    params = resolve_effective_parameters(_registry({"temperature": 0.5}, None), None)
    assert params == {"temperature": 0.5}


def test_skips_null_defaults() -> None:
    """Family params with default=None are skipped."""
    family = MagicMock()
    family.parameters = {
        "temperature": {"type": "float", "default": None},
        "max_tokens": {"type": "int", "default": 1024},
    }
    family.unsupported_parameters = []

    params = resolve_effective_parameters(_registry({}, family), None)
    assert "temperature" not in params
    assert params["max_tokens"] == 1024


def test_strips_unsupported() -> None:
    """Params the family lists as unsupported are dropped from a registry/preset override."""
    family = MagicMock()
    family.parameters = {"max_tokens": {"type": "int", "default": 8192}}
    family.family_identifier = "openai/gpt-5-thinking"
    # A reasoning model rejects sampling knobs (400 if sent).
    family.unsupported_parameters = ["temperature", "top_p", "frequency_penalty"]

    params = resolve_effective_parameters(
        _registry({"temperature": 0.8}, family),  # stale registry override
        {"top_p": 0.9, "frequency_penalty": 0.5, "max_tokens": 4096},
    )
    assert "temperature" not in params
    assert "top_p" not in params
    assert "frequency_penalty" not in params
    # Supported overrides survive.
    assert params["max_tokens"] == 4096


def test_removes_negative_seed() -> None:
    """A seed with value < 0 (e.g. -1) is removed; a non-negative seed is kept."""
    from_preset = resolve_effective_parameters(
        _registry({}, None), {"seed": -1, "temperature": 0.7}
    )
    assert "seed" not in from_preset
    assert from_preset["temperature"] == 0.7

    assert "seed" not in resolve_effective_parameters(_registry({"seed": -2}, None), None)
    assert resolve_effective_parameters(_registry({}, None), {"seed": 42})["seed"] == 42


def _registry_with_mode(mode: ReasoningMode) -> Any:
    family = MagicMock()
    family.reasoning_mode = mode
    registry = MagicMock()
    registry.model_family = family
    return registry


def test_minimize_requires_the_flag() -> None:
    """The gate is off unless the caller opts in, regardless of capability."""
    assert should_minimize_reasoning(_registry_with_mode(ReasoningMode.OPTIONAL), False) is False


def test_minimize_only_when_controllable() -> None:
    """With the flag set, only an OPTIONAL (controllable) family is minimized;
    NONE has nothing to disable and ALWAYS_ON can't be, so both are skipped."""
    for mode, expected in (
        (ReasoningMode.OPTIONAL, True),
        (ReasoningMode.NONE, False),
        (ReasoningMode.ALWAYS_ON, False),
    ):
        assert should_minimize_reasoning(_registry_with_mode(mode), True) is expected
