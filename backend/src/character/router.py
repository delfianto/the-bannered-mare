"""Character CRUD API endpoints"""

import os
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse, Response

from src.character.dependencies import CharacterServiceDep
from src.character.schemas import CharacterFilterParams, CharacterFormBase, CharacterResponse
from src.core.config import settings
from src.core.exceptions import NotFoundError
from src.core.schemas import PaginatedResponse, page_response
from src.core.utils.upload import read_upload

router = APIRouter(prefix="/api/characters", tags=["characters"])


class CharacterFormPayload(CharacterFormBase):
    """Router-only transport: the service DTO plus the avatar upload. Kept here (not
    in schemas) so the FastAPI ``UploadFile`` type stays out of the service layer.
    An ``UploadFile`` field inside a ``Form()`` model is how FastAPI spreads the
    fields as individual multipart parts *and* accepts the file in one request."""

    avatar: UploadFile | None = None


@router.get("", response_model=PaginatedResponse[CharacterResponse])
def list_characters(
    service: CharacterServiceDep,
    filter_params: CharacterFilterParams = Depends(),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
):
    """List characters with pagination and filtering"""
    offset = (page - 1) * limit
    items, total = service.list_paginated(
        limit=limit, offset=offset, filters=filter_params.to_filter_dict()
    )

    return page_response(items, total, page, limit)


@router.post("", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
async def create_character(
    service: CharacterServiceDep,
    data: Annotated[CharacterFormPayload, Form()],
):
    """Create a new character with optional avatar upload"""
    avatar_upload = await read_upload(data.avatar) if data.avatar else None
    form = CharacterFormBase(**data.model_dump(exclude={"avatar"}))
    return await service.create(form, avatar=avatar_upload)


@router.get("/{character_id}", response_model=CharacterResponse)
def get_character(character_id: str, service: CharacterServiceDep):
    """Get character details by ID"""
    return service.get_by_id(character_id)


@router.get("/{character_id}/avatar")
def get_character_avatar(character_id: str, service: CharacterServiceDep):
    """Serve character avatar image"""
    character = service.get_by_id(character_id)

    if not character.avatar:
        raise NotFoundError(f"Character '{character.name}' has no avatar")

    avatar_full_path = os.path.join(settings.storage_path, character.avatar)
    if not os.path.exists(avatar_full_path):
        raise NotFoundError("Avatar file not found")

    return FileResponse(avatar_full_path)


@router.get("/{character_id}/avatar_large")
def get_character_avatar_large(character_id: str, service: CharacterServiceDep):
    """Serve the large (<=512px) full-portrait avatar"""
    character = service.get_by_id(character_id)

    if not character.avatar_large:
        raise NotFoundError(f"Character '{character.name}' has no large avatar")

    avatar_full_path = os.path.join(settings.storage_path, character.avatar_large)
    if not os.path.exists(avatar_full_path):
        raise NotFoundError("Large avatar file not found")

    return FileResponse(avatar_full_path)


@router.get("/{character_id}/avatar_thumbnail")
def get_character_avatar_thumbnail(character_id: str, service: CharacterServiceDep):
    """Serve character avatar thumbnail image"""
    character = service.get_by_id(character_id)

    if not character.avatar_thumbnail:
        raise NotFoundError(f"Character '{character.name}' has no avatar thumbnail")

    avatar_full_path = os.path.join(settings.storage_path, character.avatar_thumbnail)
    if not os.path.exists(avatar_full_path):
        raise NotFoundError("Avatar thumbnail file not found")

    return FileResponse(avatar_full_path)


@router.put("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: str,
    service: CharacterServiceDep,
    data: Annotated[CharacterFormPayload, Form()],
):
    """Update character"""
    avatar_upload = await read_upload(data.avatar) if data.avatar else None
    form = CharacterFormBase(**data.model_dump(exclude={"avatar"}))
    return await service.update(character_id, form, avatar=avatar_upload)


@router.post("/import", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
async def import_character(
    service: CharacterServiceDep,
    file: Annotated[UploadFile, File(description="PNG or JSON character card file")],
):
    """Import a character from a TavernCard V1/V2 PNG or JSON file."""
    return await service.import_card(await read_upload(file))


@router.get("/{character_id}/export/json")
def export_character_json(character_id: str, service: CharacterServiceDep):
    """Export character as TavernCard V2 JSON."""
    json_str = service.export_as_json(character_id)
    character = service.get_by_id(character_id)
    filename = f"{character.name}.json"
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{character_id}/export/png")
def export_character_png(character_id: str, service: CharacterServiceDep):
    """Export character as PNG with embedded TavernCard V2 JSON."""
    png_bytes = service.export_as_png(character_id)
    character = service.get_by_id(character_id)
    filename = f"{character.name}.png"
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_character(character_id: str, service: CharacterServiceDep):
    """Delete character"""
    service.delete(character_id)
    return None
