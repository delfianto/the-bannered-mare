"""Pydantic schemas for Preset API"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PresetBase(BaseModel):
    """Base preset schema"""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(
        None, max_length=5000, description="Brief description of the preset's purpose"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Sampling parameter overrides (temperature, top_p, etc.)"
    )
    is_default: bool = Field(False, description="Set as default preset")


class PresetCreate(PresetBase):
    """Schema for creating a preset"""

    pass


class PresetUpdate(BaseModel):
    """Schema for updating a preset"""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=5000)
    parameters: dict[str, Any] | None = None
    is_default: bool | None = None


class PresetResponse(PresetBase):
    """Schema for preset response"""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
