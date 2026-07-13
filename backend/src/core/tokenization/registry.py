"""Resolve a model family to a cached ``Tokenizer`` (never raises).

``ModelFamily`` lives in the shared kernel (``core.persistence.models``), so this
module can depend on it without inverting the domain layering.
"""

from src.core.logging import get_logger
from src.core.persistence.models import ModelFamily
from src.core.tokenization.backends import (
    HeuristicTokenizer,
    HuggingFaceTokenizer,
    TiktokenTokenizer,
)
from src.core.tokenization.base import Tokenizer
from src.core.tokenization.specs import (
    DEFAULT_SPEC,
    TokenizerKind,
    TokenizerSpec,
    default_spec_for,
)

logger = get_logger(__name__)

_CACHE: dict[str, Tokenizer] = {}


def get_tokenizer(family: ModelFamily | None) -> Tokenizer:
    """Cached tokenizer for a model family. Loading a HF tokenizer that turns out
    unreachable/gated degrades to a tiktoken proxy; never raises."""
    key = family.family_identifier if family else ""
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    tokenizer = _build(_resolve_spec(family))
    _CACHE[key] = tokenizer
    return tokenizer


def _resolve_spec(family: ModelFamily | None) -> TokenizerSpec:
    if family is None:
        return DEFAULT_SPEC
    override = (family.extra_metadata or {}).get("tokenizer")
    if isinstance(override, dict):
        try:
            return TokenizerSpec.from_metadata(override)
        except KeyError, ValueError:
            logger.warning("tokenizer_spec_invalid", family=family.family_identifier)
    return default_spec_for(family.family_identifier)


def _build(spec: TokenizerSpec) -> Tokenizer:
    if spec.kind == TokenizerKind.HEURISTIC:
        return HeuristicTokenizer(spec.chars_per_token)
    if spec.kind == TokenizerKind.HF and spec.repo_id:
        try:
            return HuggingFaceTokenizer(spec.repo_id)
        except Exception as e:
            # Offline / gated / missing repo — fall back to an offline proxy.
            logger.warning("tokenizer_hf_load_failed", repo_id=spec.repo_id, error=str(e))
            return TiktokenTokenizer("o200k_base")
    return TiktokenTokenizer(spec.encoding)


def reset_cache() -> None:
    """Clear the per-family cache (used by tests)."""
    _CACHE.clear()
