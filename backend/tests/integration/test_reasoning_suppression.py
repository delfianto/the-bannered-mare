"""Live integration tests for auxiliary-call reasoning suppression.

These make REAL calls and are excluded from CI (`-m "not integration"`). They
verify that ``ProviderGateway(minimize_reasoning=True)`` — used for throwaway
auxiliary generations (titles, tone chips, reply suggestions) — actually reaches
the provider with the transport-appropriate "disable reasoning" signal and that a
thinking-capable model responds with far fewer tokens (no reasoning trace).

The suppression is gated on the family's ``reasoning_mode`` being ``OPTIONAL``, so
each gateway here is built on a mock family carrying that capability.
"""

import os

import httpx
import pytest
from src.core.persistence.enums import ProviderType, ReasoningMode
from src.provider.adapters.lmstudio import strip_v1_suffix
from src.provider.gateway import ProviderGateway

from tests.integration.conftest import (
    _lmstudio_host,
    _make_model,
    _make_provider,
    has_lmstudio,
    has_openrouter_key,
)

pytestmark = pytest.mark.integration

# A prompt that a thinking model will reason about before answering — the same
# shape as a real reply-suggestion call.
REASONING_PROMPT = [
    {
        "role": "user",
        "content": (
            "In a tavern roleplay, suggest 3 short things the traveler could say next. "
            "Reply with ONLY a JSON array of strings."
        ),
    }
]

# Above this completion-token count we treat the control (reasoning-on) call as
# having actually reasoned, and assert suppression cut it down sharply. Below it,
# the loaded model evidently isn't reasoning, so we only assert "never worse".
_REASONED_TOKENS = 150


def _lmstudio_loaded_model() -> str:
    host = _lmstudio_host()
    resp = httpx.get(f"{strip_v1_suffix(host)}/v1/models", timeout=2.0)
    return resp.json()["data"][0]["id"]


def _lmstudio_gateway(model_id: str, *, minimize: bool) -> ProviderGateway:
    """LM Studio gateway on a reasoning-capable (OPTIONAL) family. Generous
    max_tokens so the control call's reasoning is never truncated."""
    provider = _make_provider(ProviderType.LMSTUDIO, _lmstudio_host(), "")
    model = _make_model(
        model_id,
        model_params={"max_tokens": 2048, "temperature": 0},
        reasoning_mode=ReasoningMode.OPTIONAL,
    )
    return ProviderGateway(provider, model, model.model_identifier, minimize_reasoning=minimize)


@has_lmstudio
@pytest.mark.asyncio
async def test_lmstudio_minimize_reasoning_suppresses_thinking() -> None:
    """A live thinking model emits far fewer tokens with reasoning disabled, and
    the disable signal (reasoning_effort:"none") is accepted (no error)."""
    model_id = _lmstudio_loaded_model()

    control = await _lmstudio_gateway(model_id, minimize=False).chat_completion(REASONING_PROMPT)
    suppressed = await _lmstudio_gateway(model_id, minimize=True).chat_completion(REASONING_PROMPT)

    # Both round-trips are valid — critically, the suppressed one did not error,
    # proving the provider accepts the disable signal.
    assert control.content.strip() or (control.reasoning or "").strip()
    assert suppressed.content.strip() or (suppressed.reasoning or "").strip()

    # Suppression never costs more tokens...
    assert suppressed.usage.output_tokens <= control.usage.output_tokens, (
        f"suppressed={suppressed.usage.output_tokens} > control={control.usage.output_tokens}"
    )
    # ...and when the model actually reasoned, it cuts output down sharply.
    if control.usage.output_tokens >= _REASONED_TOKENS:
        assert suppressed.usage.output_tokens < control.usage.output_tokens / 2, (
            f"expected a large drop; control={control.usage.output_tokens} "
            f"suppressed={suppressed.usage.output_tokens}"
        )


@has_lmstudio
def test_lmstudio_disable_signal_is_reasoning_effort_none() -> None:
    """The LM Studio (OpenAI-compatible) transport disables via reasoning_effort:none."""
    gw = _lmstudio_gateway(_lmstudio_loaded_model(), minimize=True)
    assert gw._should_minimize_reasoning is True
    payload = gw.adapter.build_payload(
        REASONING_PROMPT, gw.active_identifier, False, gw._get_effective_parameters(), True
    )
    assert payload["reasoning_effort"] == "none"


@has_openrouter_key
@pytest.mark.asyncio
async def test_openrouter_minimize_reasoning_accepted() -> None:
    """OpenRouter accepts the transport's disable signal (reasoning:{enabled:false})
    live — a non-reasoning model just ignores it, so this guards the wire format."""
    provider = _make_provider(
        ProviderType.OPENROUTER, "https://openrouter.ai/api/v1", os.environ["OPENROUTER_API_KEY"]
    )
    model = _make_model(
        os.environ.get("TBM_LIVE_OPENROUTER_MODEL", "nvidia/nemotron-3-nano-30b-a3b:free"),
        model_params={"max_tokens": 256, "temperature": 0},
        reasoning_mode=ReasoningMode.OPTIONAL,
    )
    gw = ProviderGateway(provider, model, model.model_identifier, minimize_reasoning=True)

    # Structural: the OpenRouter adapter emits reasoning:{enabled:false}, not effort.
    payload = gw.adapter.build_payload(
        REASONING_PROMPT, gw.active_identifier, False, gw._get_effective_parameters(), True
    )
    assert payload["reasoning"] == {"enabled": False}
    assert "reasoning_effort" not in payload

    # Live: the call succeeds and returns output (the signal didn't 400).
    resp = await gw.chat_completion(REASONING_PROMPT)
    assert resp.content.strip() or (resp.reasoning or "").strip()
