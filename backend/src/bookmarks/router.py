"""Bookmarks API endpoints for retrieving favorited items"""

from fastapi import APIRouter
from src.character.schemas import CharacterResponse
from src.chat_message.schemas import MessageResponse
from src.chat_session.dependencies import ChatServiceDep
from src.chat_session.schemas import ChatResponse
from src.core.schemas import PaginatedResponse, collection_response

router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])


@router.get("/sessions", response_model=PaginatedResponse[ChatResponse])
def get_bookmarked_sessions(service: ChatServiceDep):
    """Get all bookmarked chat sessions"""
    chats = service.list_bookmarked()
    return collection_response([ChatResponse.model_validate(c) for c in chats])


@router.get("/characters", response_model=PaginatedResponse[CharacterResponse])
def get_bookmarked_characters():
    """Get all favorited characters (placeholder until favoriting lands)."""
    return collection_response([])


@router.get("/messages", response_model=PaginatedResponse[MessageResponse])
def get_bookmarked_messages():
    """Get all pinned message fragments (placeholder until pinning lands)."""
    return collection_response([])
