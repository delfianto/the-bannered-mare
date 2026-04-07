"""Model seed data — per-provider modules aggregated here."""

from src.fixtures.models._types import ModelSeedData
from src.fixtures.models.anthropic import ANTHROPIC_MODELS
from src.fixtures.models.google import GOOGLE_MODELS
from src.fixtures.models.ollama import OLLAMA_MODELS
from src.fixtures.models.openai import OPENAI_MODELS
from src.fixtures.models.openrouter import OPENROUTER_MODELS
from src.fixtures.models.xai import XAI_MODELS

ALL_MODELS: dict[str, list[ModelSeedData]] = {
    "openai": OPENAI_MODELS,
    "anthropic": ANTHROPIC_MODELS,
    "google": GOOGLE_MODELS,
    "xai": XAI_MODELS,
    "openrouter": OPENROUTER_MODELS,
    "ollama": OLLAMA_MODELS,
}

__all__ = ["ALL_MODELS", "ModelSeedData"]
