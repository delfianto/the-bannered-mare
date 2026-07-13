"""Tokenizer specs and the built-in family → backend defaults.

A family resolves to a spec via (1) an explicit ``extra_metadata['tokenizer']``
override, else (2) the vendor prefix of its ``family_identifier`` (the part before
``/``), else (3) the heuristic fallback. HF repo ids prefer ungated mirrors
(``Xenova/*``); any that turn out wrong/unreachable degrade to a tiktoken proxy at
build time (see ``registry``), so this map is best-effort, not load-bearing.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class TokenizerKind(StrEnum):
    TIKTOKEN = "tiktoken"
    HF = "hf"
    HEURISTIC = "heuristic"


@dataclass(frozen=True)
class TokenizerSpec:
    kind: TokenizerKind
    encoding: str = "o200k_base"  # tiktoken
    repo_id: str | None = None  # hf
    chars_per_token: float = 3.8  # heuristic

    @classmethod
    def from_metadata(cls, raw: dict[str, Any]) -> TokenizerSpec:
        """Build a spec from an ``extra_metadata['tokenizer']`` dict; raises on a
        bad ``kind`` so the registry can fall back to the vendor default."""
        kind = TokenizerKind(raw["kind"])
        return cls(
            kind=kind,
            encoding=raw.get("encoding", "o200k_base"),
            repo_id=raw.get("repo_id"),
            chars_per_token=float(raw.get("chars_per_token", 3.8)),
        )


_O200K = TokenizerSpec(TokenizerKind.TIKTOKEN, encoding="o200k_base")
_HEURISTIC = TokenizerSpec(TokenizerKind.HEURISTIC)


def _hf(repo_id: str) -> TokenizerSpec:
    return TokenizerSpec(TokenizerKind.HF, repo_id=repo_id)


# Keyed by the family_identifier vendor prefix. Open-weight vendors → an ungated
# HF mirror hosting tokenizer.json; proprietary (no public tokenizer) → heuristic.
_VENDOR_DEFAULTS: dict[str, TokenizerSpec] = {
    "openai": _O200K,
    # Gemini shares Gemma's tokenizer.
    "google": _hf("Xenova/gemma-2-tokenizer"),
    "deepseek": _hf("deepseek-ai/DeepSeek-V3"),
    "meta": _hf("Xenova/llama-3-tokenizer"),
    "mistral": _hf("Xenova/mistral-tokenizer-v3"),
    "qwen": _hf("Qwen/Qwen2.5-7B-Instruct"),
    "zai": _hf("zai-org/GLM-4.5"),
    "moonshot": _hf("moonshotai/Kimi-K2-Instruct"),
    "minimax": _hf("MiniMaxAI/MiniMax-Text-01"),
    "xiaomi": _hf("XiaomiMiMo/MiMo-7B-RL"),
    # No public offline tokenizer → estimate.
    "anthropic": _HEURISTIC,
    "xai": _HEURISTIC,
    "poolside": _HEURISTIC,
    "openrouter": _HEURISTIC,
}

# Family-less / unknown-vendor default: a general offline proxy (better than a raw
# char count, and never needs the network).
DEFAULT_SPEC = _O200K


def default_spec_for(family_identifier: str) -> TokenizerSpec:
    """Vendor-prefix default spec for a family_identifier (e.g. ``openai/gpt-4o``)."""
    vendor = family_identifier.split("/", 1)[0].lower()
    return _VENDOR_DEFAULTS.get(vendor, DEFAULT_SPEC)
