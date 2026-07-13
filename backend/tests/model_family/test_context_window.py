"""Tests for the ModelFamily.context_window property + seed-data coverage."""

from src.core.persistence.models import ModelFamily
from src.fixtures.families import MODEL_FAMILIES_SEED_DATA


def _family(**metadata: object) -> ModelFamily:
    return ModelFamily(
        name="Test",
        family_identifier="test/family",
        provider_types=["openrouter"],
        extra_metadata=dict(metadata) if metadata else None,
    )


class TestContextWindowProperty:
    def test_reads_positive_int(self) -> None:
        assert _family(context_window=128000).context_window == 128000

    def test_missing_metadata_is_none(self) -> None:
        assert _family().context_window is None

    def test_missing_key_is_none(self) -> None:
        assert _family(reasoning_mode="none").context_window is None

    def test_non_int_is_none(self) -> None:
        assert _family(context_window="128000").context_window is None

    def test_non_positive_is_none(self) -> None:
        assert _family(context_window=0).context_window is None
        assert _family(context_window=-1).context_window is None


def test_every_seeded_family_declares_a_context_window() -> None:
    """Truncation budgeting (N2) relies on a real window per family."""
    for family in MODEL_FAMILIES_SEED_DATA:
        window = (family["extra_metadata"] or {}).get("context_window")
        assert isinstance(window, int) and window > 0, (
            f"{family['family_identifier']} missing a positive context_window"
        )
