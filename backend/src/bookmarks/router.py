"""Bookmarks API endpoints for retrieving favorited items"""

from fastapi import APIRouter
from src.chat_session.dependencies import ChatServiceDep
from src.chat_session.schemas import ChatResponse

router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])


@router.get("/sessions")
def get_bookmarked_sessions(service: ChatServiceDep):
    """Get all bookmarked chat sessions"""
    chats = service.list_bookmarked()
    return {"items": [ChatResponse.model_validate(c) for c in chats]}


@router.get("/characters")
def get_bookmarked_characters():
    """Get all favorited characters"""
    return {"items": []}


@router.get("/messages")
def get_bookmarked_messages():
    """Get all pinned message fragments"""
    return {"items": []}
