"""Chat and message business logic service"""

import contextlib
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status

from src.character.repository import CharacterRepository
from src.chat_session.models import Chat
from src.chat_session.repository import ChatRepository
from src.model.repository import ModelRepository


class ChatService:
    """Service for chat and message-related business logic"""

    def __init__(
        self,
        chat_repo: ChatRepository,
        character_repo: CharacterRepository,
        model_repo: ModelRepository,
    ):
        self.chat_repo = chat_repo
        self.character_repo = character_repo
        self.model_repo = model_repo

    def list_all(self) -> list[Chat]:
        """List all chats"""
        return self.chat_repo.find_all_ordered()

    def list_paginated(
        self, limit: int = 10, cursor: str | None = None, filters: dict[str, Any] | None = None
    ) -> tuple[list[Chat], str | None]:
        """List chats with cursor-based pagination and filtering"""
        cursor_dt = None
        if cursor:
            with contextlib.suppress(ValueError):
                # Handle "Z" suffix if present from JS Date.toISOString()
                cursor_dt = datetime.fromisoformat(cursor.replace("Z", "+00:00"))

        items, has_more = self.chat_repo.find_paginated_by_cursor(limit, cursor_dt, filters)

        next_cursor = None
        if has_more and items:
            next_cursor = items[-1].updated_at.isoformat()

        return items, next_cursor

    def get_by_id(self, chat_id: str) -> Chat:
        """Get chat by ID, raise 404 if not found"""
        chat = self.chat_repo.find_by_id(chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat with ID '{chat_id}' not found",
            )
        return chat

    def create(
        self, character_id: str, model_id: str | None = None, title: str | None = None
    ) -> Chat:
        """Create a new chat"""
        if not self.character_repo.exists(character_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Character with ID '{character_id}' not found",
            )

        model_name = None
        if model_id is not None:
            model = self.model_repo.find_by_id(model_id)
            if not model:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Model with ID '{model_id}' not found",
                )
            model_name = model.name

        chat = Chat(
            character_id=character_id, model_id=model_id, title=title, model_name=model_name
        )
        created = self.chat_repo.create(chat)
        self.chat_repo.commit()
        return created

    def update(self, chat_id: str, title: str | None = None, model_id: str | None = None) -> Chat:
        """Update chat (e.g., change title or model)"""
        chat = self.get_by_id(chat_id)

        # If updating model_id, verify new model exists and update snapshot
        if model_id is not None:
            model = self.model_repo.find_by_id(model_id)
            if not model:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Model with ID '{model_id}' not found",
                )
            chat.model_id = model_id
            chat.model_name = model.name

        # Update title if provided
        if title is not None:
            chat.title = title

        updated = self.chat_repo.update(chat)
        self.chat_repo.commit()
        return updated

    def delete(self, chat_id: str) -> None:
        """Delete chat"""
        chat = self.get_by_id(chat_id)
        self.chat_repo.delete(chat)
        self.chat_repo.commit()
