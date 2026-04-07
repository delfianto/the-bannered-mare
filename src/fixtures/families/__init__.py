"""Aggregates all per-provider model family seed data into a single list."""

from src.fixtures.families.anthropic import ANTHROPIC_FAMILIES
from src.fixtures.families.google import GOOGLE_FAMILIES
from src.fixtures.families.ollama import OLLAMA_FAMILIES
from src.fixtures.families.openai import OPENAI_FAMILIES
from src.fixtures.families.openrouter import OPENROUTER_FAMILIES
from src.fixtures.families.xai import XAI_FAMILIES
from src.fixtures.model_families import ModelFamilySeedData

MODEL_FAMILIES_SEED_DATA: list[ModelFamilySeedData] = [
    *OPENAI_FAMILIES,
    *ANTHROPIC_FAMILIES,
    *GOOGLE_FAMILIES,
    *XAI_FAMILIES,
    *OPENROUTER_FAMILIES,
    *OLLAMA_FAMILIES,
]
