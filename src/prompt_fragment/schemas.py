"""Pydantic schemas for PromptFragment API"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FragmentBase(BaseModel):
    """Base prompt fragment schema"""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=5000)
    fragment_type: str = Field("instruction", max_length=50)
    content: str = Field(..., min_length=1, max_length=50000, description="Jinja2 template content")
    is_global: bool = Field(False)


class FragmentCreate(FragmentBase):
    """Schema for creating a prompt fragment"""

    pass


class FragmentUpdate(BaseModel):
    """Schema for updating a prompt fragment — all fields optional"""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=5000)
    fragment_type: str | None = Field(None, max_length=50)
    content: str | None = Field(None, min_length=1, max_length=50000)
    is_global: bool | None = None


class FragmentResponse(FragmentBase):
    """Schema for prompt fragment response"""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttachFragmentRequest(BaseModel):
    """Schema for attaching a fragment to a template"""

    fragment_id: str
    position: str = Field("after_system", max_length=50)
    ordinal: int = Field(0, ge=0)


class TemplateFragmentResponse(BaseModel):
    """Schema for template-fragment association response"""

    id: str
    template_id: str
    fragment_id: str
    position: str
    ordinal: int
    created_at: datetime
    fragment: FragmentResponse

    model_config = ConfigDict(from_attributes=True)
