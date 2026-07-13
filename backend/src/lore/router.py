"""Lorebook and LoreEntry API endpoints"""

from fastapi import APIRouter, Query, status

from src.core.schemas import PaginatedResponse, collection_response
from src.lore.dependencies import LoreServiceDep
from src.lore.schemas import (
    LorebookCreate,
    LorebookDetailResponse,
    LorebookResponse,
    LorebookUpdate,
    LoreEntryCreate,
    LoreEntryResponse,
    LoreEntryUpdate,
)

router = APIRouter(prefix="/api/lorebooks", tags=["lorebooks"])


# --- Lorebook endpoints ---


@router.get("", response_model=PaginatedResponse[LorebookResponse])
def list_lorebooks(
    service: LoreServiceDep,
    character_id: str | None = Query(None, description="Filter by character"),
    is_global: bool | None = Query(None, description="Filter global lorebooks"),
):
    """List lorebooks with optional filters."""
    return collection_response(
        service.list_lorebooks(character_id=character_id, is_global=is_global)
    )


@router.post("", response_model=LorebookResponse, status_code=status.HTTP_201_CREATED)
def create_lorebook(data: LorebookCreate, service: LoreServiceDep):
    """Create a new lorebook."""
    return service.create_lorebook(data)


@router.get("/{lorebook_id}", response_model=LorebookDetailResponse)
def get_lorebook(lorebook_id: str, service: LoreServiceDep):
    """Get lorebook with all entries."""
    return service.get_lorebook(lorebook_id)


@router.put("/{lorebook_id}", response_model=LorebookResponse)
def update_lorebook(lorebook_id: str, data: LorebookUpdate, service: LoreServiceDep):
    """Update lorebook metadata."""
    return service.update_lorebook(lorebook_id, data)


@router.delete("/{lorebook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lorebook(lorebook_id: str, service: LoreServiceDep):
    """Delete lorebook and all its entries."""
    service.delete_lorebook(lorebook_id)
    return None


# --- Entry endpoints ---


@router.post(
    "/{lorebook_id}/entries",
    response_model=LoreEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_entry(lorebook_id: str, data: LoreEntryCreate, service: LoreServiceDep):
    """Add a lore entry to a lorebook."""
    return service.create_entry(lorebook_id, data)


@router.put("/{lorebook_id}/entries/{entry_id}", response_model=LoreEntryResponse)
def update_entry(lorebook_id: str, entry_id: str, data: LoreEntryUpdate, service: LoreServiceDep):
    """Update a lore entry."""
    return service.update_entry(lorebook_id, entry_id, data)


@router.delete("/{lorebook_id}/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(lorebook_id: str, entry_id: str, service: LoreServiceDep):
    """Delete a lore entry."""
    service.delete_entry(lorebook_id, entry_id)
    return None
