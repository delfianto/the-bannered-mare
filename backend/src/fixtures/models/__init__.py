"""Model seed data — per-provider modules aggregated here."""

from src.fixtures.models._types import ModelSeedData
from src.fixtures.models.anthropic import ANTHROPIC_MODELS
from src.fixtures.models.google import GOOGLE_MODELS
from src.fixtures.models.openai import OPENAI_MODELS
from src.fixtures.models.opencode import OPENCODE_MODELS
from src.fixtures.models.opencode_go import OPENCODE_GO_MODELS
from src.fixtures.models.openrouter import OPENROUTER_MODELS
from src.fixtures.models.openrouter_alt import OPENROUTER_ALT_MODELS
from src.fixtures.models.xai import XAI_MODELS

# Iteration order matters: the first provider to introduce a canonical slug creates
# the registry (its route becomes active); later providers with the same slug add
# routes. Native providers (openai/anthropic/google/xai) run first so a proprietary
# model's default route is its native provider; the aggregator routes attach after.
# `openrouter_alt` + `opencode` carry the alternate routes for those native models.
ALL_MODELS: dict[str, list[ModelSeedData]] = {
    "openai": OPENAI_MODELS,
    "anthropic": ANTHROPIC_MODELS,
    "google": GOOGLE_MODELS,
    "xai": XAI_MODELS,
    "openrouter": OPENROUTER_MODELS + OPENROUTER_ALT_MODELS,
    "opencode": OPENCODE_MODELS,
    "opencode_go": OPENCODE_GO_MODELS,
}

__all__ = ["ALL_MODELS", "ModelSeedData"]
