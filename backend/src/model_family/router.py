"""Model Family CRUD API endpoints"""

from fastapi import APIRouter, Depends, Query, status

from src.core.schemas import PaginatedResponse, PaginationMeta
from src.fixtures.parameter_definitions import PARAMETER_DEFINITIONS_SEED_DATA
from src.model_family.dependencies import ModelFamilyServiceDep
from src.model_family.schemas import (
    ModelFamilyCreate,
    ModelFamilyFilterParams,
    ModelFamilyListResponse,
    ModelFamilyResponse,
    ModelFamilyUpdate,
)

router = APIRouter(prefix="/api/model-families", tags=["model-families"])


@router.get("/parameter-docs")
def get_parameter_definitions():
    """Returns documentation for all known model parameters."""
    return PARAMETER_DEFINITIONS_SEED_DATA


@router.get("", response_model=PaginatedResponse[ModelFamilyListResponse])
def list_model_families(
    service: ModelFamilyServiceDep,
    filter_params: ModelFamilyFilterParams = Depends(),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
):
    """List all model families with pagination and filtering"""
    offset = (page - 1) * limit
    items, total = service.list_paginated(
        limit=limit, offset=offset, filters=filter_params.to_filter_dict()
    )

    # Calculate has_more for page-based pagination
    has_more = (offset + limit) < total

    return PaginatedResponse(
        items=items,
        meta=PaginationMeta(limit=limit, has_more=has_more, total=total, page=page, cursor=None),
    )


@router.post("", response_model=ModelFamilyResponse, status_code=status.HTTP_201_CREATED)
def create_model_family(family_data: ModelFamilyCreate, service: ModelFamilyServiceDep):
    """Create a new model family"""
    return service.create(family_data)


@router.get("/{family_id}", response_model=ModelFamilyResponse)
def get_model_family(family_id: str, service: ModelFamilyServiceDep):
    """Get model family details by ID"""
    return service.get_by_id(family_id)


@router.put("/{family_id}", response_model=ModelFamilyResponse)
def update_model_family(
    family_id: str, family_data: ModelFamilyUpdate, service: ModelFamilyServiceDep
):
    """Update model family"""
    return service.update(family_id, family_data)


@router.delete("/{family_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model_family(family_id: str, service: ModelFamilyServiceDep):
    """Delete model family"""
    service.delete(family_id)
    return None
