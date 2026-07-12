"""Persona API endpoints"""

import os
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from src.core.config import settings
from src.core.schemas import PaginatedResponse, page_response
from src.persona.dependencies import PersonaServiceDep
from src.persona.schemas import PersonaFilterParams, PersonaResponse

router = APIRouter(prefix="/api/personas", tags=["personas"])


@router.get("/", response_model=PaginatedResponse[PersonaResponse])
def list_personas(
    service: PersonaServiceDep,
    filter_params: PersonaFilterParams = Depends(),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
):
    """List personas with pagination and filtering"""
    offset = (page - 1) * limit
    items, total = service.list_paginated(
        limit=limit, offset=offset, filters=filter_params.to_filter_dict()
    )

    return page_response(items, total, page, limit)


@router.post("/", response_model=PersonaResponse, status_code=status.HTTP_201_CREATED)
async def create_persona(
    name: Annotated[str, Form()],
    service: PersonaServiceDep,
    description: Annotated[str | None, Form()] = None,
    is_default: Annotated[bool, Form()] = False,
    avatar: Annotated[UploadFile | None, File()] = None,
):
    """Create new persona with optional avatar upload"""
    return await service.create(
        name=name, description=description, is_default=is_default, avatar=avatar
    )


@router.get("/{persona_id}", response_model=PersonaResponse)
def get_persona(persona_id: str, service: PersonaServiceDep):
    """Get persona by ID"""
    return service.get_by_id(persona_id)


@router.get("/{persona_id}/avatar")
def get_persona_avatar(persona_id: str, service: PersonaServiceDep):
    """Serve persona avatar image"""
    persona = service.get_by_id(persona_id)

    if not persona.avatar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona '{persona.name}' has no avatar",
        )

    avatar_full_path = os.path.join(settings.storage_path, persona.avatar)
    if not os.path.exists(avatar_full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avatar file not found",
        )

    return FileResponse(avatar_full_path)


@router.get("/{persona_id}/avatar_large")
def get_persona_avatar_large(persona_id: str, service: PersonaServiceDep):
    """Serve the large (<=512px) full-portrait persona avatar"""
    persona = service.get_by_id(persona_id)

    if not persona.avatar_large:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona '{persona.name}' has no large avatar",
        )

    avatar_full_path = os.path.join(settings.storage_path, persona.avatar_large)
    if not os.path.exists(avatar_full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Large avatar file not found",
        )

    return FileResponse(avatar_full_path)


@router.get("/{persona_id}/avatar_thumbnail")
def get_persona_avatar_thumbnail(persona_id: str, service: PersonaServiceDep):
    """Serve persona avatar thumbnail image"""
    persona = service.get_by_id(persona_id)

    if not persona.avatar_thumbnail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona '{persona.name}' has no avatar thumbnail",
        )

    avatar_full_path = os.path.join(settings.storage_path, persona.avatar_thumbnail)
    if not os.path.exists(avatar_full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avatar thumbnail file not found",
        )

    return FileResponse(avatar_full_path)


@router.put("/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: str,
    service: PersonaServiceDep,
    name: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    is_default: Annotated[bool | None, Form()] = None,
    avatar: Annotated[UploadFile | None, File()] = None,
):
    """Update persona"""
    return await service.update(
        persona_id=persona_id,
        name=name,
        description=description,
        is_default=is_default,
        avatar=avatar,
    )


@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_persona(persona_id: str, service: PersonaServiceDep):
    """Delete persona"""
    service.delete(persona_id)
    return None


@router.post("/{persona_id}/set-default", response_model=PersonaResponse)
def set_default_persona(persona_id: str, service: PersonaServiceDep):
    """Set persona as default"""
    return service.set_default(persona_id)
