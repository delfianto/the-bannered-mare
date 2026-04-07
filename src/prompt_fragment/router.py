"""PromptFragment API endpoints"""

from fastapi import APIRouter, Query, status

from src.prompt_fragment.dependencies import FragmentServiceDep
from src.prompt_fragment.schemas import (
    AttachFragmentRequest,
    FragmentCreate,
    FragmentResponse,
    FragmentUpdate,
    TemplateFragmentResponse,
)

fragment_router = APIRouter(prefix="/api/prompt-fragments", tags=["prompt-fragments"])
template_fragment_router = APIRouter(
    prefix="/api/prompt-templates/{template_id}/fragments",
    tags=["template-fragments"],
)


# -- Fragment CRUD --


@fragment_router.get("/", response_model=list[FragmentResponse])
def list_fragments(
    service: FragmentServiceDep,
    fragment_type: str | None = Query(None, description="Filter by fragment type"),
    is_global: bool | None = Query(None, description="Filter by global status"),
):
    """List prompt fragments with optional filtering"""
    return service.list_all(fragment_type=fragment_type, is_global=is_global)


@fragment_router.post("/", response_model=FragmentResponse, status_code=status.HTTP_201_CREATED)
def create_fragment(data: FragmentCreate, service: FragmentServiceDep):
    """Create a new prompt fragment"""
    return service.create(**data.model_dump())


@fragment_router.get("/{fragment_id}", response_model=FragmentResponse)
def get_fragment(fragment_id: str, service: FragmentServiceDep):
    """Get prompt fragment by ID"""
    return service.get_by_id(fragment_id)


@fragment_router.put("/{fragment_id}", response_model=FragmentResponse)
def update_fragment(fragment_id: str, data: FragmentUpdate, service: FragmentServiceDep):
    """Update prompt fragment"""
    return service.update(fragment_id, **data.model_dump(exclude_unset=True))


@fragment_router.delete("/{fragment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fragment(fragment_id: str, service: FragmentServiceDep):
    """Delete prompt fragment"""
    service.delete(fragment_id)
    return None


# -- Template-Fragment attachment --


@template_fragment_router.post(
    "/", response_model=TemplateFragmentResponse, status_code=status.HTTP_201_CREATED
)
def attach_fragment(
    template_id: str,
    data: AttachFragmentRequest,
    service: FragmentServiceDep,
):
    """Attach a prompt fragment to a template"""
    return service.attach_to_template(
        template_id=template_id,
        fragment_id=data.fragment_id,
        position=data.position,
        ordinal=data.ordinal,
    )


@template_fragment_router.delete("/{fragment_id}", status_code=status.HTTP_204_NO_CONTENT)
def detach_fragment(
    template_id: str,
    fragment_id: str,
    service: FragmentServiceDep,
):
    """Detach a prompt fragment from a template"""
    service.detach_from_template(template_id, fragment_id)
    return None


@template_fragment_router.get("/", response_model=list[TemplateFragmentResponse])
def list_template_fragments(
    template_id: str,
    service: FragmentServiceDep,
):
    """List all prompt fragments attached to a template"""
    return service.list_template_fragments(template_id)
