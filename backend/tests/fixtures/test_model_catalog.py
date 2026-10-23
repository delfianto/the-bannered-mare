"""Catalog refreshes must preserve user choices and provider-specific contracts."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from src.fixtures.families import MODEL_FAMILIES_SEED_DATA
from src.fixtures.models import ALL_MODELS
from src.fixtures.seed_model_families import seed_model_families
from src.fixtures.seed_models import seed_models
from src.fixtures.seed_providers import seed_providers
from src.model.lineage import normalize_slug, resolve_family
from src.model.models import ModelRegistry, ModelRoute
from src.model.repository import ModelRepository
from src.model_family.models import ModelFamily
from src.model_family.repository import ModelFamilyRepository
from src.provider.adapters.anthropic import AnthropicAdapter
from src.provider.adapters.gemini import GeminiAdapter
from src.provider.adapters.openrouter import OpenRouterAdapter
from src.provider.parameters import resolve_effective_parameters, should_minimize_reasoning
from src.provider.repository import ProviderRepository


def test_full_catalog_seeds_all_canonical_models_and_routes(
    db: Session, monkeypatch: pytest.MonkeyPatch
):
    providers = ProviderRepository(db)
    families = ModelFamilyRepository(db)
    models = ModelRepository(db)
    seed_providers(providers)
    seed_model_families(families)
    monkeypatch.setenv("SEED_MODELS", "true")
    expected_routes = set()
    for provider, entries in ALL_MODELS.items():
        monkeypatch.setenv(f"SEED_MODELS_{provider.upper()}", "true")
        for entry in entries:
            slug = entry.get("slug") or normalize_slug(entry["model_identifier"])
            expected_routes.add((slug, provider))

    seed_models(models, families, providers)
    registries = list(db.scalars(select(ModelRegistry)).all())
    assert {r.slug for r in registries} == {slug for slug, _ in expected_routes}
    assert db.scalar(select(func.count()).select_from(ModelRoute)) == len(expected_routes)
    for registry in registries:
        assert registry.active_route is not None
        assert registry.active_route.model_registry_id == registry.id
        assert all(
            route.provider.provider_type.value in registry.model_family.provider_types
            for route in registry.routes
        )


def test_incremental_seed_preserves_user_choices(db: Session, monkeypatch: pytest.MonkeyPatch):
    providers = ProviderRepository(db)
    families = ModelFamilyRepository(db)
    models = ModelRepository(db)
    seed_providers(providers)
    seed_model_families(families)

    family = families.find_by_identifier("openai/gpt-6")
    provider = providers.find_by_type("openai")
    assert family is not None and provider is not None
    custom = models.create(
        ModelRegistry(
            slug="gpt-6-sol",
            display_name="My Sol",
            original_identifier="gpt-6-sol",
            model_family_id=family.id,
            parameters={"max_completion_tokens": 512},
            enabled=True,
        )
    )
    route = models.add_route(
        ModelRoute(
            model_registry_id=custom.id,
            provider_id=provider.id,
            model_identifier="gpt-6-sol",
            enabled=False,
        )
    )
    custom.active_route_id = route.id
    db.commit()

    # Exercise real new entries on a populated registry, then add an alternate route.
    subset = {
        "openai": [
            m for m in ALL_MODELS["openai"] if m["model_identifier"] in {"gpt-6-sol", "gpt-6-astra"}
        ],
        "openrouter": [
            m for m in ALL_MODELS["openrouter"] if m["model_identifier"] == "openai/gpt-6-sol"
        ],
    }
    monkeypatch.setattr("src.fixtures.seed_models.ALL_MODELS", subset)
    monkeypatch.setenv("SEED_MODELS", "true")
    monkeypatch.setenv("SEED_MODELS_OPENAI", "true")
    monkeypatch.setenv("SEED_MODELS_OPENROUTER", "false")
    seed_models(models, families, providers)
    assert models.find_by_slug("gpt-6-astra") is not None

    monkeypatch.setenv("SEED_MODELS_OPENROUTER", "true")
    seed_models(models, families, providers)
    seed_models(models, families, providers)
    db.refresh(custom)
    db.refresh(route)
    assert custom.display_name == "My Sol"
    assert custom.parameters == {"max_completion_tokens": 512}
    assert custom.enabled is True
    assert custom.active_route_id == route.id
    assert route.enabled is False
    assert models.count() == 2
    assert db.scalar(select(func.count()).select_from(ModelRoute)) == 3


@pytest.mark.parametrize(
    ("identifier", "family_identifier"),
    [
        ("openai/gpt-6-astra", "openai/gpt-6-reasoning"),
        ("gpt-6.1-sol", "openai/gpt-6-reasoning"),
        ("anthropic/claude-sonnet-5.5", "anthropic/claude-sonnet-5.5"),
        ("gemini-4-argon", "google/gemini-4"),
        ("deepseek-v4.1-flash", "deepseek/deepseek-v4.1"),
        ("glm-5.3-flash", "zai/glm-5.3-flash"),
        ("qwen3.8-max", "qwen/qwen3.8"),
        ("minimax-m3.1-flash", "minimax/minimax-m3.1"),
        ("mimo-v2.6-pro", "xiaomi/mimo-v2.6"),
        ("meta/muse-spark-open", "meta/muse-spark-open"),
        ("meta/muse-spark-1.3-contributor", "meta/muse-spark-1.3-contributor"),
        ("meta/muse-glimmer-30b", "meta/muse-glimmer"),
        ("meta-llama/llama-4-scout", "meta/llama-4-scout"),
        ("meta-llama/llama-4-maverick", "meta/llama-4-maverick"),
        ("meta-llama/llama-3.3-70b-instruct", "meta/llama-3.3-instruct"),
    ],
)
def test_discovery_uses_exact_catalog_family(db: Session, identifier: str, family_identifier: str):
    seed_model_families(ModelFamilyRepository(db))
    family = resolve_family(db, identifier)
    assert family is not None
    assert family.family_identifier == family_identifier


@pytest.mark.parametrize(
    "family_identifier",
    [
        "openai/gpt-6-reasoning",
        "anthropic/claude-opus-5.5",
        "anthropic/claude-fable-5.1",
        "meta/muse-wonder",
        "meta/muse-spark-1.3",
        "meta/muse-spark-1.3-contributor",
        "meta/muse-spark-open",
        "meta/muse-glimmer",
    ],
)
def test_required_thinking_is_not_disabled_for_auxiliary_calls(family_identifier: str):
    data = next(f for f in MODEL_FAMILIES_SEED_DATA if f["family_identifier"] == family_identifier)
    family = ModelFamily(**data)
    registry = ModelRegistry(model_family=family)
    assert should_minimize_reasoning(registry, True) is False


def test_sonnet_55_auxiliary_call_uses_between_tools():
    payload = AnthropicAdapter().build_payload(
        [{"role": "user", "content": "Suggest a short title"}],
        "claude-sonnet-5-5",
        False,
        {"max_tokens": 1024, "effort": "xhigh"},
        minimize_reasoning=True,
    )
    assert payload["thinking"] == {"type": "between_tools"}
    assert payload["output_config"] == {"effort": "low"}


@pytest.mark.parametrize("model", ["gemini-3.8-flash", "gemini-4-argon"])
def test_new_gemini_auxiliary_calls_use_low_thinking(model: str):
    payload = GeminiAdapter().build_payload(
        [{"role": "user", "content": "Suggest a title"}],
        model,
        False,
        {"max_output_tokens": 8192, "thinking_level": "high"},
        minimize_reasoning=True,
    )
    assert payload["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "low"}


def test_gemini_38_and_argon_exclude_minimal_thinking():
    for identifier in ("google/gemini-3.8", "google/gemini-4"):
        family = next(f for f in MODEL_FAMILIES_SEED_DATA if f["family_identifier"] == identifier)
        assert family["parameters"]["thinking_level"].get("str_values") == ["low", "medium", "high"]
        assert family["parameters"]["max_output_tokens"].get("max_value") == 65536
        assert {"temperature", "top_p", "top_k"} <= set(family.get("unsupported_parameters", []))


@pytest.mark.parametrize(
    ("model", "parameters", "budget"),
    [
        ("google/gemini-4-argon", {"max_output_tokens": 32768, "thinking_level": "low"}, 32768),
        (
            "anthropic/claude-opus-5.5",
            {"max_tokens": 16384, "effort": "low", "thinking": {"type": "adaptive"}},
            16384,
        ),
    ],
)
def test_openrouter_translates_native_budget_and_effort(model, parameters, budget):
    payload = OpenRouterAdapter().build_payload(
        [{"role": "user", "content": "Continue the scene"}], model, True, parameters
    )
    assert payload["max_tokens"] == budget
    assert payload["reasoning_effort"] == "low"


def test_openrouter_respects_explicit_thinking_off_over_effort():
    payload = OpenRouterAdapter().build_payload(
        [{"role": "user", "content": "Continue the scene"}],
        "anthropic/claude-haiku-5.5",
        True,
        {"max_tokens": 8192, "effort": "low", "thinking": {"type": "disabled"}},
    )
    assert payload["reasoning"] == {"enabled": False}
    assert "reasoning_effort" not in payload


def test_openrouter_only_seed_retains_native_defaults(db: Session, monkeypatch: pytest.MonkeyPatch):
    providers = ProviderRepository(db)
    families = ModelFamilyRepository(db)
    models = ModelRepository(db)
    seed_providers(providers)
    seed_model_families(families)
    native = next(m for m in ALL_MODELS["google"] if m["model_identifier"] == "gemini-4-argon")
    alternate = next(
        m for m in ALL_MODELS["openrouter"] if m["model_identifier"] == "google/gemini-4-argon"
    )
    monkeypatch.setattr("src.fixtures.seed_models.ALL_MODELS", {"openrouter": [alternate]})
    monkeypatch.setenv("SEED_MODELS", "true")
    monkeypatch.setenv("SEED_MODELS_OPENROUTER", "true")
    seed_models(models, families, providers)

    registry = models.find_by_slug("gemini-4-argon")
    assert registry is not None
    assert registry.parameters == native["parameters"]


def test_hosted_muse_drops_incompatible_rp_presets():
    family = ModelFamily(
        **next(f for f in MODEL_FAMILIES_SEED_DATA if f["family_identifier"] == "meta/muse-wonder")
    )
    registry = ModelRegistry(model_family=family)
    parameters = resolve_effective_parameters(
        registry,
        {
            "thinking": {"type": "disabled"},
            "min_p": 0.05,
            "stop": ["User:"],
            "frequency_penalty": 0.5,
            "reasoning_effort": "low",
        },
    )
    payload = OpenRouterAdapter().build_payload(
        [{"role": "user", "content": "Continue"}],
        "meta/muse-wonder",
        True,
        parameters,
        minimize_reasoning=should_minimize_reasoning(registry, True),
    )
    assert payload["reasoning_effort"] == "low"
    assert not {"reasoning", "min_p", "stop", "frequency_penalty"} & payload.keys()


def test_muse_effort_ranges_respect_contributor_and_open_contracts():
    families = {f["family_identifier"]: f for f in MODEL_FAMILIES_SEED_DATA}
    for identifier in ("meta/muse-wonder", "meta/muse-spark-1.3"):
        schema = families[identifier]["parameters"]["reasoning_effort"]
        assert schema["type"] == "enum"
        assert "max" in schema["str_values"]
    for identifier in (
        "meta/muse-spark-1.3-contributor",
        "meta/muse-spark-open",
        "meta/muse-glimmer",
    ):
        schema = families[identifier]["parameters"]["reasoning_effort"]
        assert schema["type"] == "enum"
        efforts = schema["str_values"]
        assert "max" not in efforts and "none" not in efforts
