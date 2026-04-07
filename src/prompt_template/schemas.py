"""Pydantic schemas for PromptTemplate API"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.prompt_template.models import (
    DEFAULT_COMPONENT_ORDER,
    DEFAULT_COMPONENTS_ENABLED,
)


class PromptTemplateBase(BaseModel):
    """Base prompt template schema"""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=1000)
    is_default: bool = Field(False)
    system_template: str = Field(
        ..., min_length=1, max_length=50000, description="Jinja2 template for system prompt"
    )
    component_order: list[str] = Field(default_factory=lambda: DEFAULT_COMPONENT_ORDER.copy())
    components_enabled: dict[str, bool] = Field(
        default_factory=lambda: DEFAULT_COMPONENTS_ENABLED.copy()
    )
    max_history_tokens: int | None = Field(None, ge=0, le=1000000)


class PromptTemplateCreate(PromptTemplateBase):
    """Schema for creating a prompt template"""

    pass


class PromptTemplateUpdate(BaseModel):
    """Schema for updating a prompt template"""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=1000)
    is_default: bool | None = None
    system_template: str | None = Field(None, min_length=1, max_length=50000)
    component_order: list[str] | None = None
    components_enabled: dict[str, bool] | None = None
    max_history_tokens: int | None = Field(None, ge=0, le=1000000)


class PromptTemplateResponse(PromptTemplateBase):
    """Schema for prompt template response"""

    id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TemplatePreviewRequest(BaseModel):
    """Schema for template preview request"""

    character_name: str = Field(default="Alice")
    character_description: str = Field(default="A helpful AI assistant")
    character_personality: str = Field(default="Friendly and knowledgeable")
    character_scenario: str = Field(default="Casual conversation")
    persona_name: str = Field(default="User")
    persona_description: str = Field(default="A curious person")


class TemplatePreviewResponse(BaseModel):
    """Schema for template preview response"""

    rendered: str = Field(..., description="Rendered template output")
    variables_used: dict[str, str] = Field(..., description="Template variables that were used")
