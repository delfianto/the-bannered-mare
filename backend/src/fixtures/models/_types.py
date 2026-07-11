"""Shared type definitions for model seed data."""

from typing import Any, NotRequired, TypedDict


class ModelSeedData(TypedDict):
    """Type definition for model seed data.

    A seed entry describes one *route* (a provider + identifier). Entries that
    share a canonical ``slug`` fold into one ModelRegistry: the first-seen entry
    creates the registry (name/family/parameters), later ones just add routes.
    ``slug`` is optional — when omitted it's derived from ``model_identifier``
    (via ``normalize_slug``); alternate-provider routes set it explicitly to the
    native identifier so they merge across the per-provider naming divergence
    (e.g. ``claude-opus-4-8`` native vs ``anthropic/claude-opus-4.8`` on OpenRouter).
    """

    name: str
    model_identifier: str
    family_identifier: str
    provider_type: str
    parameters: dict[str, Any]
    enabled: bool
    slug: NotRequired[str]
