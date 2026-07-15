"""Pure request-parameter/reasoning resolution for provider calls.

Extracted from ``ProviderGateway`` so the merge/strip logic is a pure function of
the model registry + preset overrides — unit-testable without constructing a
gateway or mocking a provider.
"""

import logging
from typing import Any, cast

from src.core.persistence.enums import ReasoningMode
from src.model.models import ModelRegistry

logger = logging.getLogger(__name__)


def resolve_effective_parameters(
    registry: ModelRegistry, preset_parameters: dict[str, Any] | None
) -> dict[str, Any]:
    """Merge ModelFamily defaults → Model overrides → Preset overrides."""
    effective_params: dict[str, Any] = {}

    family = registry.model_family
    if family:
        family_params = family.parameters or {}
        for param_key, cfg in family_params.items():
            if "default" in cfg and cfg["default"] is not None:
                effective_params[param_key] = cfg["default"]

    if registry.parameters:
        effective_params.update(cast(Any, registry.parameters))

    if preset_parameters:
        effective_params.update(preset_parameters)

    # Drop parameters the family explicitly rejects before they reach the
    # provider. Family defaults never include these — only a model/preset
    # override can, so a stale loadout can't 400 the request (e.g. temperature
    # on a reasoning model, stop on Grok). The UI warns the user separately.
    if family and family.unsupported_parameters:
        unsupported = set(family.unsupported_parameters)
        dropped = [key for key in effective_params if key in unsupported]
        for key in dropped:
            del effective_params[key]
        if dropped:
            logger.info(
                "Stripped unsupported parameters %s for model %s (family %s)",
                dropped,
                registry.display_name,
                family.family_identifier,
            )

    # Remove negative seeds (e.g., -1 for random seed) since APIs expect unsigned/positive integers.
    if "seed" in effective_params:
        seed_val = effective_params["seed"]
        if isinstance(seed_val, (int, float)) and seed_val < 0:
            del effective_params["seed"]

    return effective_params


def should_minimize_reasoning(registry: ModelRegistry, minimize_reasoning: bool) -> bool:
    """Whether to signal reasoning-off to the adapter for this call.

    Only when the caller requested it AND the family's declared reasoning is
    actually controllable — a non-reasoning model has nothing to disable, and an
    always-on reasoner (e.g. minimax-m2) would only get an ignored param.
    """
    if not minimize_reasoning:
        return False
    family = registry.model_family
    return bool(family and family.reasoning_mode == ReasoningMode.OPTIONAL)
