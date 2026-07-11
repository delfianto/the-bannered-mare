"""Tests for provider-identifier lineage helpers (slug normalisation + family guess)."""

from sqlalchemy.orm import Session
from src.model.lineage import normalize_slug, resolve_family
from src.model_family import ModelFamily


class TestNormalizeSlug:
    def test_strips_vendor_prefix(self) -> None:
        assert normalize_slug("deepseek/deepseek-v4-pro") == "deepseek-v4-pro"

    def test_strips_variant_suffix(self) -> None:
        assert normalize_slug("llama-3.3-70b:free") == "llama-3.3-70b"

    def test_strips_both_and_lowercases(self) -> None:
        assert normalize_slug("Meta/Llama-3.3-70B:free") == "llama-3.3-70b"

    def test_bare_identifier_is_unchanged_but_lowered(self) -> None:
        assert normalize_slug("GPT-4o") == "gpt-4o"


class TestResolveFamily:
    def test_resolves_by_keyword_to_matching_family(self, db: Session) -> None:
        family = ModelFamily(
            name="DeepSeek V3",
            family_identifier="deepseek/v3",
            provider_types=["openrouter"],
        )
        db.add(family)
        db.commit()
        db.refresh(family)

        resolved = resolve_family(db, "deepseek/deepseek-v3")

        assert resolved is not None
        assert resolved.id == family.id

    def test_unknown_identifier_returns_none(self, db: Session) -> None:
        assert resolve_family(db, "some-unheard-of-model-xyz") is None

    def test_keyword_match_without_family_returns_none(self, db: Session) -> None:
        """A rule matches the identifier, but no family with that name exists."""
        assert resolve_family(db, "deepseek/deepseek-v3") is None
