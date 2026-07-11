"""Model seed data — per-provider modules aggregated here."""

from src.fixtures.models._types import ModelSeedData
from src.fixtures.models.anthropic import ANTHROPIC_MODELS
from src.fixtures.models.google import GOOGLE_MODELS
from src.fixtures.models.openai import OPENAI_MODELS
from src.fixtures.models.opencode_go import OPENCODE_GO_MODELS
from src.fixtures.models.openrouter import OPENROUTER_MODELS
from src.fixtures.models.xai import XAI_MODELS

# Iteration order matters: the first provider to introduce a given canonical slug
# creates the registry (and its route becomes active). OpenRouter is processed
# before OpenCode Go so an open-weight model's default route is the aggregator.
ALL_MODELS: dict[str, list[ModelSeedData]] = {
    "openai": OPENAI_MODELS,
    "anthropic": ANTHROPIC_MODELS,
    "google": GOOGLE_MODELS,
    "xai": XAI_MODELS,
    "openrouter": OPENROUTER_MODELS,
    "opencode_go": OPENCODE_GO_MODELS,
}

__all__ = ["ALL_MODELS", "ModelSeedData"]
