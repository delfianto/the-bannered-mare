"""Aggregates all model family seed data into a single list.

Families are grouped by real base-model lineage (provider-agnostic), not by
provider. ``provider_types`` on each record declares where it can run.
"""

from src.fixtures.families.claude_fable import CLAUDE_FABLE_FAMILIES
from src.fixtures.families.claude_haiku import CLAUDE_HAIKU_FAMILIES
from src.fixtures.families.claude_opus import CLAUDE_OPUS_FAMILIES
from src.fixtures.families.claude_sonnet import CLAUDE_SONNET_FAMILIES
from src.fixtures.families.deepseek import DEEPSEEK_FAMILIES
from src.fixtures.families.gemma import GEMMA_FAMILIES
from src.fixtures.families.glm import GLM_FAMILIES
from src.fixtures.families.google import GOOGLE_FAMILIES
from src.fixtures.families.mistral import MISTRAL_FAMILIES
from src.fixtures.families.openai import OPENAI_FAMILIES
from src.fixtures.families.openrouter import OPENROUTER_FAMILIES
from src.fixtures.families.xai import XAI_FAMILIES
from src.fixtures.model_families import ModelFamilySeedData

MODEL_FAMILIES_SEED_DATA: list[ModelFamilySeedData] = [
    *OPENAI_FAMILIES,
    *CLAUDE_FABLE_FAMILIES,
    *CLAUDE_OPUS_FAMILIES,
    *CLAUDE_SONNET_FAMILIES,
    *CLAUDE_HAIKU_FAMILIES,
    *GOOGLE_FAMILIES,
    *XAI_FAMILIES,
    *GEMMA_FAMILIES,
    *MISTRAL_FAMILIES,
    *DEEPSEEK_FAMILIES,
    *GLM_FAMILIES,
    *OPENROUTER_FAMILIES,
]
