"""Model definition CRUD API endpoints"""

from fastapi import APIRouter, Depends, Query, status

from src.core.schemas import PaginatedResponse, PaginationMeta
from src.model.dependencies import ModelServiceDep
from src.model.schemas import (
    ModelCreate,
    ModelDetailResponse,
    ModelFilterParams,
    ModelFlagsUpdate,
    ModelListResponse,
    ModelResponse,
    ModelUpdate,
)

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("", response_model=PaginatedResponse[ModelListResponse])
def list_models(
    service: ModelServiceDep,
    filter_params: ModelFilterParams = Depends(),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
):
    """List model definitions with pagination and filtering"""
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


@router.post("", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
def create_model(model_data: ModelCreate, service: ModelServiceDep):
    """Create a new model definition"""
    data = model_data.model_dump()
    return service.create(**data)


@router.get("/{model_id}", response_model=ModelDetailResponse)
def get_model(model_id: str, service: ModelServiceDep):
    """
    Get model definition by ID.
    Returns detailed information including the embedded Model Family.
    """
    return service.get_by_id(model_id)


@router.put("/{model_id}", response_model=ModelResponse)
def update_model(model_id: str, model_data: ModelUpdate, service: ModelServiceDep):
    """Update model definition"""
    update_data = model_data.model_dump(exclude_unset=True)
    return service.update(model_id, **update_data)


@router.patch("/{model_id}/flags", response_model=ModelResponse)
def update_model_flags(model_id: str, flag_data: ModelFlagsUpdate, service: ModelServiceDep):
    """Toggle model enabled and OpenRouter routing flags"""
    update_data = flag_data.model_dump(exclude_unset=True)
    return service.update_flags(model_id, **update_data)


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(model_id: str, service: ModelServiceDep):
    """Delete model definition"""
    service.delete(model_id)
    return None
