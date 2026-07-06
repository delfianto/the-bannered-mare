"""Seed-data integrity: local GGUF families must list both local runners."""

from src.fixtures.families import MODEL_FAMILIES_SEED_DATA
from src.fixtures.model_families import ModelFamilySeedData


def _family(identifier: str) -> ModelFamilySeedData:
    return next(f for f in MODEL_FAMILIES_SEED_DATA if f["family_identifier"] == identifier)


def test_local_gguf_families_include_lmstudio():
    """Ollama and LM Studio both run local GGUF, so they travel together."""
    for identifier in [
        "google/gemma-4",
        "mistral/mistral-nemo",
        "mistral/mistral-small",
        "meta/llama-3",
    ]:
        provider_types = _family(identifier)["provider_types"]
        assert "ollama" in provider_types, f"{identifier} lost ollama"
        assert "lmstudio" in provider_types, f"{identifier} missing lmstudio"


def test_lmstudio_accompanies_ollama_everywhere():
    """Any family that can run on Ollama can also run on LM Studio."""
    for family in MODEL_FAMILIES_SEED_DATA:
        provider_types = family["provider_types"]
        if "ollama" in provider_types:
            assert "lmstudio" in provider_types, (
                f"{family['family_identifier']} has ollama but not lmstudio"
            )
