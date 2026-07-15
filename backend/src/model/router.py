"""Canonical-model + route CRUD API endpoints."""

from fastapi import APIRouter, Depends, Query, status

from src.core.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from src.core.schemas import PaginatedResponse, page_response
from src.model.dependencies import ModelServiceDep
from src.model.schemas import (
    ActiveRouteUpdate,
    ModelCreate,
    ModelDetailResponse,
    ModelFilterParams,
    ModelFlagsUpdate,
    ModelListResponse,
    ModelResponse,
    ModelRouteCreate,
    ModelUpdate,
)

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("", response_model=PaginatedResponse[ModelListResponse])
def list_models(
    service: ModelServiceDep,
    filter_params: ModelFilterParams = Depends(),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
):
    """List canonical models with pagination and filtering."""
    offset = (page - 1) * limit
    items, total = service.list_paginated(
        limit=limit, offset=offset, filters=filter_params.to_filter_dict()
    )
    return page_response(items, total, page, limit)


@router.post("", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
def create_model(model_data: ModelCreate, service: ModelServiceDep):
    """Create a canonical model with its initial route(s)."""
    return service.create(**model_data.model_dump())


@router.get("/{model_id}", response_model=ModelDetailResponse)
def get_model(model_id: str, service: ModelServiceDep):
    """Get a canonical model by ID, with the embedded model family."""
    return service.get_by_id(model_id)


@router.put("/{model_id}", response_model=ModelResponse)
def update_model(model_id: str, model_data: ModelUpdate, service: ModelServiceDep):
    """Update canonical-model fields (routes are managed separately)."""
    return service.update(model_id, **model_data.model_dump(exclude_unset=True))


@router.patch("/{model_id}/flags", response_model=ModelResponse)
def update_model_flags(model_id: str, flag_data: ModelFlagsUpdate, service: ModelServiceDep):
    """Toggle the canonical model's enabled flag."""
    return service.update_flags(model_id, **flag_data.model_dump(exclude_unset=True))


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(model_id: str, service: ModelServiceDep):
    """Delete a canonical model (cascades to its routes)."""
    service.delete(model_id)
    return None


@router.post(
    "/{model_id}/routes", response_model=ModelResponse, status_code=status.HTTP_201_CREATED
)
def add_route(model_id: str, route_data: ModelRouteCreate, service: ModelServiceDep):
    """Add a provider route to a canonical model."""
    return service.add_route(
        model_id,
        provider_id=route_data.provider_id,
        model_identifier=route_data.model_identifier,
        enabled=route_data.enabled,
    )


@router.delete("/{model_id}/routes/{route_id}", response_model=ModelResponse)
def delete_route(model_id: str, route_id: str, service: ModelServiceDep):
    """Remove a route from a canonical model."""
    return service.delete_route(model_id, route_id)


@router.put("/{model_id}/active-route", response_model=ModelResponse)
def set_active_route(model_id: str, data: ActiveRouteUpdate, service: ModelServiceDep):
    """Flip which route the model resolves to (redirects existing chats)."""
    return service.set_active_route(model_id, data.route_id)
