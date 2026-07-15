"""PromptTemplate API endpoints"""

from fastapi import APIRouter, Query

from src.character.models import Character
from src.chat_session.models import Chat
from src.core.exceptions import BadRequestError
from src.core.schemas import PaginatedResponse, page_response
from src.persona.models import Persona
from src.prompt_template.dependencies import PromptTemplateServiceDep
from src.prompt_template.schemas import (
    PromptTemplateCreate,
    PromptTemplateResponse,
    PromptTemplateUpdate,
    TemplatePreviewRequest,
    TemplatePreviewResponse,
)
from src.templating import TemplateContext
from src.templating.dependencies import TemplateServiceDep

router = APIRouter(prefix="/api/prompt-templates", tags=["prompt-templates"])


@router.get("/", response_model=PaginatedResponse[PromptTemplateResponse])
def list_templates(
    service: PromptTemplateServiceDep,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
):
    """List prompt templates with pagination"""
    offset = (page - 1) * limit
    items, total = service.list_paginated(limit=limit, offset=offset)

    return page_response(items, total, page, limit)


@router.post("/", response_model=PromptTemplateResponse, status_code=201)
def create_template(data: PromptTemplateCreate, service: PromptTemplateServiceDep):
    """Create new prompt template"""
    create_data = data.model_dump()
    return service.create(**create_data)


@router.get("/{template_id}", response_model=PromptTemplateResponse)
def get_template(template_id: str, service: PromptTemplateServiceDep):
    """Get prompt template by ID"""
    return service.get_by_id(template_id)


@router.put("/{template_id}", response_model=PromptTemplateResponse)
def update_template(
    template_id: str,
    data: PromptTemplateUpdate,
    service: PromptTemplateServiceDep,
):
    """Update prompt template"""
    update_data = data.model_dump(exclude_unset=True)
    return service.update(template_id, **update_data)


@router.delete("/{template_id}")
def delete_template(template_id: str, service: PromptTemplateServiceDep):
    """Delete prompt template"""
    service.delete(template_id)
    return {"message": "Prompt template deleted successfully"}


@router.post("/{template_id}/set-default", response_model=PromptTemplateResponse)
def set_default_template(template_id: str, service: PromptTemplateServiceDep):
    """Set prompt template as default"""
    return service.set_default(template_id)


@router.post("/{template_id}/preview", response_model=TemplatePreviewResponse)
def preview_template(
    template_id: str,
    preview_data: TemplatePreviewRequest,
    service: PromptTemplateServiceDep,
    template_service: TemplateServiceDep,
):
    """Preview template rendering with sample data"""
    template = service.get_by_id(template_id)

    # Create mock objects from preview data
    mock_character = Character(
        id="preview",
        name=preview_data.character_name,
        description=preview_data.character_description,
        personality=preview_data.character_personality,
        scenario=preview_data.character_scenario,
    )

    mock_persona = Persona(
        id="preview",
        name=preview_data.persona_name,
        description=preview_data.persona_description,
    )

    # Mock chat object (minimal fields needed for template rendering)
    mock_chat = Chat(
        id="preview",
        title="Preview Chat",
        character_id="preview",
        model_id="preview",
    )

    context = TemplateContext(
        character=mock_character,
        persona=mock_persona,
        chat=mock_chat,
    )

    try:
        rendered = template_service.render(template.system_template, context)
        variables_used = template_service.build_variables(context)
    except ValueError as e:
        # render() wraps Jinja syntax/security errors as ValueError with a concise,
        # author-facing message; anything else is unexpected and propagates to the
        # global handler (a sanitized 500) rather than leaking here as a 400.
        raise BadRequestError(str(e)) from e

    return TemplatePreviewResponse(
        rendered=rendered,
        variables_used=variables_used,
    )
