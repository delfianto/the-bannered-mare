"""Profile API endpoints"""

from fastapi import APIRouter, Query, status

from src.core.schemas import PaginatedResponse, page_response
from src.profile.dependencies import ProfileServiceDep
from src.profile.schemas import ProfileCreate, ProfileResponse, ProfileUpdate

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.get("/", response_model=PaginatedResponse[ProfileResponse])
def list_profiles(
    service: ProfileServiceDep,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
):
    """List profiles with pagination"""
    offset = (page - 1) * limit
    items, total = service.list_paginated(limit=limit, offset=offset)

    return page_response(items, total, page, limit)


@router.post("/", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(body: ProfileCreate, service: ProfileServiceDep):
    """Create new profile"""
    return service.create(
        name=body.name,
        description=body.description,
        is_default=body.is_default,
        prompt_template_id=body.prompt_template_id,
        preset_id=body.preset_id,
        persona_id=body.persona_id,
        model_id=body.model_id,
        task_model_id=body.task_model_id,
    )


@router.get("/{profile_id}", response_model=ProfileResponse)
def get_profile(profile_id: str, service: ProfileServiceDep):
    """Get profile by ID"""
    return service.get_by_id(profile_id)


@router.put("/{profile_id}", response_model=ProfileResponse)
def update_profile(profile_id: str, body: ProfileUpdate, service: ProfileServiceDep):
    """Update profile"""
    # exclude_unset so an explicitly-sent null clears a field (unselect), while an
    # omitted field is left unchanged.
    return service.update(profile_id, body.model_dump(exclude_unset=True))


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: str, service: ProfileServiceDep):
    """Delete profile"""
    service.delete(profile_id)
    return None


@router.post("/{profile_id}/default", response_model=ProfileResponse)
def set_default_profile(profile_id: str, service: ProfileServiceDep):
    """Set profile as default"""
    return service.set_default(profile_id)
