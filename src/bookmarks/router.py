"""Bookmarks API endpoints for retrieving favorited items"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.persistence.database import get_db
from src.core.persistence import Chat
from src.chat_session.schemas import ChatResponse

router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])


@router.get("/sessions")
def get_bookmarked_sessions(db: Session = Depends(get_db)):
    """Get all bookmarked chat sessions"""
    stmt = select(Chat).where(Chat.is_bookmarked == True)
    chats = db.execute(stmt).scalars().all()
    return {
        "items": [ChatResponse.model_validate(c) for c in chats]
    }


@router.get("/characters")
def get_bookmarked_characters():
    """Get all favorited characters"""
    return {"items": []}


@router.get("/messages")
def get_bookmarked_messages():
    """Get all pinned message fragments"""
    return {"items": []}
