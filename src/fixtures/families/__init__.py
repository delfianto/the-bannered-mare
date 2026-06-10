"""Aggregates all model family seed data into a single list.

Families are grouped by real base-model lineage (provider-agnostic), not by
provider. ``provider_types`` on each record declares where it can run.
"""

from src.fixtures.families.anthropic import ANTHROPIC_FAMILIES
from src.fixtures.families.gemma import GEMMA_FAMILIES
from src.fixtures.families.google import GOOGLE_FAMILIES
from src.fixtures.families.mistral import MISTRAL_FAMILIES
from src.fixtures.families.openai import OPENAI_FAMILIES
from src.fixtures.families.openrouter import OPENROUTER_FAMILIES
from src.fixtures.families.xai import XAI_FAMILIES
from src.fixtures.model_families import ModelFamilySeedData

MODEL_FAMILIES_SEED_DATA: list[ModelFamilySeedData] = [
    *OPENAI_FAMILIES,
    *ANTHROPIC_FAMILIES,
    *GOOGLE_FAMILIES,
    *XAI_FAMILIES,
    *GEMMA_FAMILIES,
    *MISTRAL_FAMILIES,
    *OPENROUTER_FAMILIES,
]
