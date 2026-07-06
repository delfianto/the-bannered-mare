"""Preset API endpoints"""

from typing import Annotated

from fastapi import APIRouter, File, Query, UploadFile, status

from src.core.schemas import PaginatedResponse, PaginationMeta
from src.preset.dependencies import PresetServiceDep
from src.preset.schemas import PresetCreate, PresetResponse, PresetUpdate
from src.st_import.dependencies import STImportServiceDep
from src.st_import.schemas import STImportResult

router = APIRouter(prefix="/api/presets", tags=["presets"])


@router.get("/", response_model=PaginatedResponse[PresetResponse])
def list_presets(
    service: PresetServiceDep,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
):
    """List presets with pagination"""
    offset = (page - 1) * limit
    items, total = service.list_paginated(limit=limit, offset=offset)

    has_more = (offset + limit) < total

    return PaginatedResponse(
        items=items,
        meta=PaginationMeta(limit=limit, has_more=has_more, total=total, page=page, cursor=None),
    )


@router.post("/", response_model=PresetResponse, status_code=status.HTTP_201_CREATED)
def create_preset(
    body: PresetCreate,
    service: PresetServiceDep,
):
    """Create new preset"""
    return service.create(
        name=body.name,
        description=body.description,
        parameters=body.parameters,
        is_default=body.is_default,
    )


@router.post("/import", response_model=STImportResult, status_code=status.HTTP_201_CREATED)
async def import_st_preset(
    service: STImportServiceDep,
    file: Annotated[UploadFile, File(description="SillyTavern chat-completion preset .json")],
) -> STImportResult:
    """Import a SillyTavern chat-completion preset.

    Maps the prompt structure to a PromptTemplate + fragments and, when sampler
    settings are present, a Preset. Returns what was created plus warnings for
    anything that did not transfer cleanly.
    """
    return await service.import_preset(file)


@router.get("/{preset_id}", response_model=PresetResponse)
def get_preset(preset_id: str, service: PresetServiceDep):
    """Get preset by ID"""
    return service.get_by_id(preset_id)


@router.put("/{preset_id}", response_model=PresetResponse)
def update_preset(
    preset_id: str,
    body: PresetUpdate,
    service: PresetServiceDep,
):
    """Update preset"""
    return service.update(
        preset_id=preset_id,
        name=body.name,
        description=body.description,
        parameters=body.parameters,
        is_default=body.is_default,
    )


@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_preset(preset_id: str, service: PresetServiceDep):
    """Delete preset"""
    service.delete(preset_id)
    return None


@router.post("/{preset_id}/default", response_model=PresetResponse)
def set_default_preset(preset_id: str, service: PresetServiceDep):
    """Set preset as default"""
    return service.set_default(preset_id)
