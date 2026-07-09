"""Character CRUD API endpoints"""

import os
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, Response

from src.character.dependencies import CharacterServiceDep
from src.character.schemas import CharacterFilterParams, CharacterResponse
from src.core.config import settings
from src.core.schemas import PaginatedResponse, PaginationMeta

router = APIRouter(prefix="/api/characters", tags=["characters"])


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

    # Calculate has_more for page-based pagination
    has_more = (offset + limit) < total

    return PaginatedResponse(
        items=items,
        meta=PaginationMeta(limit=limit, has_more=has_more, total=total, page=page, cursor=None),
    )


@router.post("", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
async def create_character(
    name: Annotated[str, Form()],
    service: CharacterServiceDep,
    description: Annotated[str | None, Form()] = None,
    personality: Annotated[str | None, Form()] = None,
    first_message: Annotated[str | None, Form()] = None,
    example_dialogues: Annotated[str | None, Form()] = None,  # JSON string
    scenario: Annotated[str | None, Form()] = None,
    post_history_instructions: Annotated[str | None, Form()] = None,
    alternate_greetings: Annotated[str | None, Form()] = None,  # JSON string
    tags: Annotated[str | None, Form()] = None,  # JSON string
    gender: Annotated[str | None, Form()] = None,
    custom_gender: Annotated[str | None, Form()] = None,
    creator: Annotated[str | None, Form()] = None,
    version: Annotated[int | None, Form()] = 1,
    system_prompt: Annotated[str | None, Form()] = None,
    creator_notes: Annotated[str | None, Form()] = None,
    species: Annotated[str | None, Form()] = None,
    age: Annotated[str | None, Form()] = None,
    avatar: Annotated[UploadFile | None, File()] = None,
):
    """Create a new character with optional avatar upload"""
    return await service.create(
        name=name,
        description=description,
        personality=personality,
        first_message=first_message,
        example_dialogues=example_dialogues,
        scenario=scenario,
        post_history_instructions=post_history_instructions,
        alternate_greetings=alternate_greetings,
        tags=tags,
        gender=gender,
        custom_gender=custom_gender,
        creator=creator,
        version=version,
        system_prompt=system_prompt,
        creator_notes=creator_notes,
        species=species,
        age=age,
        avatar=avatar,
    )


@router.get("/{character_id}", response_model=CharacterResponse)
def get_character(character_id: str, service: CharacterServiceDep):
    """Get character details by ID"""
    return service.get_by_id(character_id)


@router.get("/{character_id}/avatar")
def get_character_avatar(character_id: str, service: CharacterServiceDep):
    """Serve character avatar image"""
    character = service.get_by_id(character_id)

    if not character.avatar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character '{character.name}' has no avatar",
        )

    avatar_full_path = os.path.join(settings.storage_path, character.avatar)
    if not os.path.exists(avatar_full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avatar file not found",
        )

    return FileResponse(avatar_full_path)


@router.get("/{character_id}/avatar_large")
def get_character_avatar_large(character_id: str, service: CharacterServiceDep):
    """Serve the large (<=512px) full-portrait avatar"""
    character = service.get_by_id(character_id)

    if not character.avatar_large:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character '{character.name}' has no large avatar",
        )

    avatar_full_path = os.path.join(settings.storage_path, character.avatar_large)
    if not os.path.exists(avatar_full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Large avatar file not found",
        )

    return FileResponse(avatar_full_path)


@router.get("/{character_id}/avatar_thumbnail")
def get_character_avatar_thumbnail(character_id: str, service: CharacterServiceDep):
    """Serve character avatar thumbnail image"""
    character = service.get_by_id(character_id)

    if not character.avatar_thumbnail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character '{character.name}' has no avatar thumbnail",
        )

    avatar_full_path = os.path.join(settings.storage_path, character.avatar_thumbnail)
    if not os.path.exists(avatar_full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avatar thumbnail file not found",
        )

    return FileResponse(avatar_full_path)


@router.put("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: str,
    service: CharacterServiceDep,
    name: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    personality: Annotated[str | None, Form()] = None,
    first_message: Annotated[str | None, Form()] = None,
    example_dialogues: Annotated[str | None, Form()] = None,  # JSON string
    scenario: Annotated[str | None, Form()] = None,
    post_history_instructions: Annotated[str | None, Form()] = None,
    alternate_greetings: Annotated[str | None, Form()] = None,  # JSON string
    tags: Annotated[str | None, Form()] = None,  # JSON string
    gender: Annotated[str | None, Form()] = None,
    custom_gender: Annotated[str | None, Form()] = None,
    creator: Annotated[str | None, Form()] = None,
    version: Annotated[int | None, Form()] = None,
    system_prompt: Annotated[str | None, Form()] = None,
    creator_notes: Annotated[str | None, Form()] = None,
    species: Annotated[str | None, Form()] = None,
    age: Annotated[str | None, Form()] = None,
    avatar: Annotated[UploadFile | None, File()] = None,
):
    """Update character"""
    return await service.update(
        character_id=character_id,
        name=name,
        description=description,
        personality=personality,
        first_message=first_message,
        example_dialogues=example_dialogues,
        scenario=scenario,
        post_history_instructions=post_history_instructions,
        alternate_greetings=alternate_greetings,
        tags=tags,
        gender=gender,
        custom_gender=custom_gender,
        creator=creator,
        version=version,
        system_prompt=system_prompt,
        creator_notes=creator_notes,
        species=species,
        age=age,
        avatar=avatar,
    )


@router.post("/import", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
async def import_character(
    service: CharacterServiceDep,
    file: Annotated[UploadFile, File(description="PNG or JSON character card file")],
):
    """Import a character from a TavernCard V1/V2 PNG or JSON file."""
    return await service.import_card(file)


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
