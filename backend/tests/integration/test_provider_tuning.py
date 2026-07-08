"""Live provider tests for loadout tuning parameters.

Prove that the sampling/reasoning knobs we forward per provider are actually
ACCEPTED by the real APIs (no 400) end-to-end, and that unsupported knobs are
stripped before the request. Each family's real seed schema drives the test, so
these guard the strip (gateway) + forwarding (adapters) work against live APIs.

Local only:
- Each test is skipped when the provider's API key is absent from the environment
  (loaded from .env by the integration conftest).
- The suite is marked `integration`, which CI excludes via `pytest -m "not integration"`.

Model identifiers default to cheap current models, overridable per provider via
TBM_LIVE_<PROVIDER>_MODEL env vars in case a default is retired.

Run locally with:  pytest tests/integration/test_provider_tuning.py -v
"""

import os

import pytest
from src.core.persistence.enums import ProviderType
from src.fixtures.families import MODEL_FAMILIES_SEED_DATA
from src.fixtures.model_families import ModelFamilySeedData
from src.provider.adapters import CompletionResponse
from src.provider.gateway import ProviderGateway

from tests.integration.conftest import (
    _make_model,
    _make_provider,
    has_anthropic_key,
    has_google_key,
    has_openai_key,
    has_openrouter_key,
)

pytestmark = pytest.mark.integration

PROMPT = [{"role": "user", "content": "Reply with exactly one word: pong"}]


def _family_seed(identifier: str) -> ModelFamilySeedData:
    return next(f for f in MODEL_FAMILIES_SEED_DATA if f["family_identifier"] == identifier)


def _assert_output(resp: CompletionResponse) -> None:
    """A valid round-trip returns text — or, for a reasoning model, reasoning."""
    assert isinstance(resp, CompletionResponse)
    assert resp.content.strip() or (resp.reasoning or "").strip(), "no content or reasoning"


@has_openai_key
@pytest.mark.asyncio
async def test_openai_tuned_params_accepted() -> None:
    """OpenAI accepts the classic sampling surface we forward."""
    seed = _family_seed("openai/gpt-4o")
    provider = _make_provider(
        ProviderType.OPENAI, "https://api.openai.com/v1", os.environ["OPENAI_API_KEY"]
    )
    model = _make_model(
        os.environ.get("TBM_LIVE_OPENAI_MODEL", "gpt-4o-mini"),
        family_params=seed["parameters"],
        unsupported_params=seed.get("unsupported_parameters", []),
    )
    preset = {
        "temperature": 0.7,
        "top_p": 0.9,
        "frequency_penalty": 0.2,
        "presence_penalty": 0.1,
        "max_completion_tokens": 16,
        "seed": 42,
    }
    gw = ProviderGateway(provider, model, preset_parameters=preset)
    _assert_output(await gw.chat_completion(PROMPT))


@has_openai_key
@pytest.mark.asyncio
async def test_openai_unsupported_param_stripped() -> None:
    """An unsupported knob (reasoning_effort on gpt-4o) is stripped so the request still succeeds."""
    seed = _family_seed("openai/gpt-4o")
    assert "reasoning_effort" in seed.get("unsupported_parameters", [])
    provider = _make_provider(
        ProviderType.OPENAI, "https://api.openai.com/v1", os.environ["OPENAI_API_KEY"]
    )
    model = _make_model(
        os.environ.get("TBM_LIVE_OPENAI_MODEL", "gpt-4o-mini"),
        family_params=seed["parameters"],
        unsupported_params=seed.get("unsupported_parameters", []),
    )
    preset = {"temperature": 0.5, "max_completion_tokens": 16, "reasoning_effort": "high"}
    gw = ProviderGateway(provider, model, preset_parameters=preset)
    _assert_output(await gw.chat_completion(PROMPT))


@has_anthropic_key
@pytest.mark.asyncio
async def test_anthropic_tuned_params_accepted() -> None:
    """temperature and top_p are both set; the adapter must drop top_p (Claude 400s on both)."""
    seed = _family_seed("anthropic/claude-haiku-4.5")
    provider = _make_provider(
        ProviderType.ANTHROPIC, "https://api.anthropic.com/v1", os.environ["ANTHROPIC_API_KEY"]
    )
    model = _make_model(
        os.environ.get("TBM_LIVE_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
        family_params=seed["parameters"],
        unsupported_params=seed.get("unsupported_parameters", []),
    )
    preset = {"temperature": 0.7, "top_p": 0.9, "top_k": 40, "max_tokens": 16}
    gw = ProviderGateway(provider, model, preset_parameters=preset)
    _assert_output(await gw.chat_completion(PROMPT))


@has_google_key
@pytest.mark.asyncio
async def test_google_tuned_params_accepted() -> None:
    """Includes thinking_budget=0 to exercise thinkingConfig forwarding (Flash can disable it)."""
    seed = _family_seed("google/gemini-2.5")
    provider = _make_provider(
        ProviderType.GOOGLE,
        "https://generativelanguage.googleapis.com",
        os.environ["GOOGLE_API_KEY"],
    )
    model = _make_model(
        os.environ.get("TBM_LIVE_GOOGLE_MODEL", "gemini-2.5-flash"),
        family_params=seed["parameters"],
        unsupported_params=seed.get("unsupported_parameters", []),
    )
    preset = {
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 40,
        "max_output_tokens": 16,
        "thinking_budget": 0,
    }
    gw = ProviderGateway(provider, model, preset_parameters=preset)
    _assert_output(await gw.chat_completion(PROMPT))


@has_openrouter_key
@pytest.mark.asyncio
async def test_openrouter_extra_samplers_accepted() -> None:
    """The extra sampler forwarding (top_k/min_p/top_a/repetition_penalty) must not 400."""
    provider = _make_provider(
        ProviderType.OPENROUTER,
        "https://openrouter.ai/api/v1",
        os.environ["OPENROUTER_API_KEY"],
    )
    model = _make_model(
        os.environ.get("TBM_LIVE_OPENROUTER_MODEL", "nvidia/nemotron-3-nano-30b-a3b:free"),
        family_params={},
        model_params={"max_tokens": 256},
    )
    preset = {
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 40,
        "min_p": 0.05,
        "top_a": 0.1,
        "repetition_penalty": 1.1,
    }
    gw = ProviderGateway(provider, model, preset_parameters=preset)
    _assert_output(await gw.chat_completion(PROMPT))
