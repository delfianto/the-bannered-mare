"""Chat and message business logic service"""

import contextlib
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status

from src.character.repository import CharacterRepository
from src.chat_session.models import Chat
from src.chat_session.repository import ChatRepository
from src.model.repository import ModelRepository
from src.profile.repository import ProfileRepository


class ChatService:
    """Service for chat and message-related business logic"""

    def __init__(
        self,
        chat_repo: ChatRepository,
        character_repo: CharacterRepository,
        model_repo: ModelRepository,
        profile_repo: ProfileRepository,
    ):
        self.chat_repo = chat_repo
        self.character_repo = character_repo
        self.model_repo = model_repo
        self.profile_repo = profile_repo

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
        self,
        character_id: str,
        model_id: str | None = None,
        title: str | None = None,
        profile_id: str | None = None,
    ) -> Chat:
        """Create a new chat, optionally applying a profile's settings."""
        if not self.character_repo.exists(character_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Character with ID '{character_id}' not found",
            )

        chat = Chat(character_id=character_id, title=title)

        if profile_id is not None:
            self._apply_profile(chat, profile_id)
            # initial_profile_name records the chat's birth config; immutable afterwards.
            chat.initial_profile_name = chat.last_profile_name

        # An explicit model_id overrides whatever model the profile carried.
        if model_id is not None:
            self._set_model(chat, model_id)

        created = self.chat_repo.create(chat)
        self.chat_repo.commit()
        return created

    def update(
        self,
        chat_id: str,
        title: str | None = None,
        model_id: str | None = None,
        is_bookmarked: bool | None = None,
    ) -> Chat:
        """Update chat (title and/or model, bookmark status). Re-applying a profile goes through apply_profile."""
        chat = self.get_by_id(chat_id)

        if model_id is not None:
            self._set_model(chat, model_id)

        if title is not None:
            chat.title = title

        if is_bookmarked is not None:
            chat.is_bookmarked = is_bookmarked

        updated = self.chat_repo.update(chat)
        self.chat_repo.commit()
        return updated

    def apply_profile(self, chat_id: str, profile_id: str) -> Chat:
        """Apply a profile to an existing chat: copy its axes, update last_profile_name."""
        chat = self.get_by_id(chat_id)
        self._apply_profile(chat, profile_id)
        updated = self.chat_repo.update(chat)
        self.chat_repo.commit()
        return updated

    def _set_model(self, chat: Chat, model_id: str) -> None:
        """Validate a model and set it on the chat, snapshotting its name."""
        model = self.model_repo.find_by_id(model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model with ID '{model_id}' not found",
            )
        chat.model_id = model_id
        chat.model_name = model.name

    def _apply_profile(self, chat: Chat, profile_id: str) -> None:
        """Copy a profile's non-null axes onto the chat, snapshotting the profile name.

        The chat owns the copied FKs as its live config; ``last_profile_name`` is a
        provenance snapshot (a name, not a link), so renaming/deleting the profile
        never affects the chat.
        """
        profile = self.profile_repo.find_by_id(profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile with ID '{profile_id}' not found",
            )

        chat.last_profile_name = profile.name
        if profile.prompt_template_id is not None:
            chat.template_id = profile.prompt_template_id
        if profile.preset_id is not None:
            chat.preset_id = profile.preset_id
        if profile.persona_id is not None:
            chat.persona_id = profile.persona_id
        if profile.model_id is not None:
            self._set_model(chat, profile.model_id)

    def delete(self, chat_id: str) -> None:
        """Delete chat"""
        chat = self.get_by_id(chat_id)
        self.chat_repo.delete(chat)
        self.chat_repo.commit()
