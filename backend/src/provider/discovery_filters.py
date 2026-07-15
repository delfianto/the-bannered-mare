"""Pure filters over a provider's discovered model list.

Extracted from ProviderService so the blacklist/allow-list rules are pure
functions — unit-testable without a service, repo, or provider. The default
blacklist *data* lives in ``core/model_filters.py``; this module is the logic
that applies it.
"""

import re

from src.core.config import settings
from src.provider.schemas import DiscoveredModel

# OpenAI o-series reasoning models (o1, o3-mini, o4-mini, …). Matched as a
# name-segment prefix — not a loose "o1" substring, which would also hit RP
# finetunes like "sao10k/…" — so these deep-thinking, pricey models stay out of
# the RP picker.
_REASONING_MODEL_RE = re.compile(r"^o[1-9]([.-]|$)")

# OpenAI ships dated GPT snapshots (gpt-5-2025-08-07, gpt-5.4-2026-03-05)
# alongside the bare/rolling id they pin, so they only clutter the RP picker —
# drop them. NOT the "-chat-latest" aliases: those are the *only* callable form
# of the chat SKUs (there is no bare "gpt-5-chat"), so they must stay. Scoped to
# gpt/chatgpt so other vendors' dated names (e.g. Claude's) are untouched.
_OPENAI_ALIAS_RE = re.compile(r"^(?:chat)?gpt.*-\d{4}-\d{2}-\d{2}$")


def dedupe_preserving_order(identifiers: list[str]) -> list[str]:
    """Trim, drop blanks, and de-duplicate while keeping first-seen order."""
    seen: set[str] = set()
    result: list[str] = []
    for raw in identifiers:
        value = raw.strip()
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def filter_blacklisted(models: list[DiscoveredModel]) -> list[DiscoveredModel]:
    """Drop non-chat/non-RP models via three configurable rules.

    The identifier splits as ``vendor/name`` (or just ``name`` for vendor-less
    providers like OpenAI). Rules:
    - ``settings.model_vendor_blacklist`` substrings vs the **vendor** — whole
      vendors dropped (Perplexity, Cohere, OpenRouter meta-routers…).
    - ``settings.model_blacklist`` substrings vs the **name** only (not the
      vendor, so ``sao10k/l3.3-euryale-70b`` isn't nuked for the "o1" in
      "sao10k"; and not the display name, which may read "Research Preview" on a
      fine chat model).
    - the OpenAI o-series reasoning models (o1/o3/o4…) by name prefix.
    - OpenAI's redundant GPT "-latest"/dated-snapshot aliases by name.
    """
    name_bl = [k.lower() for k in settings.model_blacklist]
    vendor_bl = [k.lower() for k in settings.model_vendor_blacklist]
    kept: list[DiscoveredModel] = []
    for m in models:
        vendor, _, name = m.identifier.lower().rpartition("/")
        if vendor and any(v in vendor for v in vendor_bl):
            continue
        if _REASONING_MODEL_RE.match(name):
            continue
        if _OPENAI_ALIAS_RE.match(name):
            continue
        if any(k in name for k in name_bl):
            continue
        kept.append(m)
    return kept


def apply_allow_list(
    allowed_models: list[str] | None, models: list[DiscoveredModel]
) -> list[DiscoveredModel]:
    """Keep only allow-listed identifiers; an empty/None allow-list keeps all."""
    allowed = set(allowed_models or [])
    if not allowed:
        return models
    return [m for m in models if m.identifier in allowed]
