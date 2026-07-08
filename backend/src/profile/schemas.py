"""Pydantic schemas for Profile API"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProfileBase(BaseModel):
    """Base profile schema"""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(
        default=None, max_length=5000, description="Brief description of the profile's purpose"
    )
    is_default: bool = Field(False, description="Set as default profile")
    prompt_template_id: str | None = Field(
        default=None, max_length=12, description="Prompt template to apply"
    )
    preset_id: str | None = Field(
        default=None, max_length=12, description="Sampler preset to apply"
    )
    persona_id: str | None = Field(
        default=None, max_length=12, description="Default persona to apply"
    )
    model_id: str | None = Field(default=None, max_length=12, description="Default model to apply")
    task_model_id: str | None = Field(
        default=None,
        max_length=12,
        description="Cheaper model for auxiliary calls (titles, suggestions); "
        "falls back to the chat model when unset",
    )


class ProfileCreate(ProfileBase):
    """Schema for creating a profile"""

    pass


class ProfileUpdate(BaseModel):
    """Schema for updating a profile"""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=5000)
    is_default: bool | None = None
    prompt_template_id: str | None = Field(default=None, max_length=12)
    preset_id: str | None = Field(default=None, max_length=12)
    persona_id: str | None = Field(default=None, max_length=12)
    model_id: str | None = Field(default=None, max_length=12)
    task_model_id: str | None = Field(default=None, max_length=12)


class ProfileResponse(ProfileBase):
    """Schema for profile response"""

    id: str
    source: str
    source_filename: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
