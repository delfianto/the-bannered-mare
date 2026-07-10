"""Shared type definitions for model seed data."""

from typing import Any, TypedDict


class ModelSeedData(TypedDict):
    """Type definition for model seed data"""

    name: str
    model_identifier: str
    family_identifier: str
    provider_type: str
    parameters: dict[str, Any]
    enabled: bool
