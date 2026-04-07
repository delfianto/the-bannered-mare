"""Chat and message API endpoints"""

from fastapi import APIRouter, Depends, Query, status

from src.chat_session.dependencies import ChatServiceDep
from src.chat_session.schemas import (
    ChatCreate,
    ChatResponse,
    ChatSessionFilterParams,
    ChatUpdate,
)
from src.core.schemas import PaginatedResponse, PaginationMeta

router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.get("", response_model=PaginatedResponse[ChatResponse])
def list_chats(
    service: ChatServiceDep,
    filter_params: ChatSessionFilterParams = Depends(),
    cursor: str | None = Query(None, description="ISO 8601 timestamp cursor for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """List chats with cursor-based pagination and filtering"""
    items, next_cursor = service.list_paginated(
        limit=limit, cursor=cursor, filters=filter_params.to_filter_dict()
    )

    return PaginatedResponse(
        items=items,
        meta=PaginationMeta(
            limit=limit,
            has_more=(next_cursor is not None),
            cursor=next_cursor,
            total=None,
            page=None,
        ),
    )


@router.post("", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
def create_chat(chat_data: ChatCreate, service: ChatServiceDep):
    """Create a new chat"""
    return service.create(
        character_id=chat_data.character_id,
        model_id=chat_data.model_id,
        title=chat_data.title if hasattr(chat_data, "title") else None,
    )


@router.get("/{chat_id}", response_model=ChatResponse)
def get_chat(chat_id: str, service: ChatServiceDep):
    """Get chat details by ID"""
    return service.get_by_id(chat_id)


@router.put("/{chat_id}", response_model=ChatResponse)
def update_chat(chat_id: str, chat_data: ChatUpdate, service: ChatServiceDep):
    """Update chat (e.g., change title or model)"""
    update_data = chat_data.model_dump(exclude_unset=True)

    return service.update(
        chat_id=chat_id,
        title=update_data.get("title"),
        model_id=update_data.get("model_id"),
    )


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(chat_id: str, service: ChatServiceDep):
    """Delete chat"""
    service.delete(chat_id)
    return None
