"""Chat and message business logic service"""

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import TYPE_CHECKING, Any

from src.chat_session.models import Chat
from src.chat_session.repository import ChatRepository
from src.core.base_service import BaseCrudService, get_or_404
from src.core.exceptions import NotFoundError
from src.core.logging.logger_config import get_logger
from src.core.pagination import DEFAULT_PAGE_SIZE
from src.core.persistence import UnitOfWork
from src.core.tokenization import get_tokenizer
from src.templating import TemplateContext, TemplateService

if TYPE_CHECKING:
    # Cross-slice READS depend on a structural ReadPort; the greeting-seed WRITE
    # goes through chat_message's published MessageSeedService seam (BE-H7) — not
    # its repository. All stay under TYPE_CHECKING: they're annotation-only, and a
    # runtime import of a chat_message module here would re-enter
    # chat_message.dependencies -> chat_session.dependencies at module load.
    from src.character.models import Character
    from src.chat_message.seeding import MessageSeedService
    from src.core.persistence import ModelRegistry, Persona, Profile, ReadPort

logger = get_logger(__name__)

# Sentinel distinguishing "field omitted" from an explicit None (which clears a
# nullable axis like task_model_id / persona_id). Typed Any so it's a valid
# default for `str | None` params.
_UNSET: Any = object()


class ChatService(BaseCrudService[Chat, ChatRepository]):
    """Service for chat and message-related business logic (inherits list_all/get_by_id/delete)."""

    def __init__(
        self,
        chat_repo: ChatRepository,
        character_repo: ReadPort[Character],
        model_repo: ReadPort[ModelRegistry],
        profile_repo: ReadPort[Profile],
        message_seeder: MessageSeedService,
        persona_repo: ReadPort[Persona],
        template_service: TemplateService | None = None,
        uow: UnitOfWork | None = None,
    ):
        super().__init__(chat_repo, uow or UnitOfWork(chat_repo.db), "Chat")
        # character/model/profile/persona are cross-slice reads → structural
        # ReadPorts (BE-H2); the concrete repos injected by DI satisfy them.
        self.character_repo = character_repo
        self.model_repo = model_repo
        self.profile_repo = profile_repo
        # The opening-greeting write goes through chat_message's published seam
        # (BE-H7), not its repository; it flushes into this service's transaction.
        self.message_seeder = message_seeder
        self.persona_repo = persona_repo
        self.template_service = template_service or TemplateService()

    def list_bookmarked(self) -> list[Chat]:
        """List all bookmarked chat sessions."""
        return self.repo.find_bookmarked()

    def list_paginated(
        self,
        limit: int = DEFAULT_PAGE_SIZE,
        cursor: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[Chat], str | None]:
        """List chats with cursor-based pagination and filtering"""
        cursor_dt = None
        if cursor:
            with contextlib.suppress(ValueError):
                # Handle "Z" suffix if present from JS Date.toISOString()
                cursor_dt = datetime.fromisoformat(cursor.replace("Z", "+00:00"))

        items, has_more = self.repo.find_paginated_by_cursor(limit, cursor_dt, filters)

        next_cursor = None
        if has_more and items:
            next_cursor = items[-1].updated_at.isoformat()

        return items, next_cursor

    def create(
        self,
        character_id: str,
        model_id: str | None = None,
        title: str | None = None,
        profile_id: str | None = None,
    ) -> Chat:
        """Create a new chat, optionally applying a profile's settings."""
        character = get_or_404(self.character_repo, character_id, "Character")

        chat = Chat(character_id=character_id, title=title)

        if profile_id is not None:
            self._apply_profile(chat, profile_id)
            # initial_profile_name records the chat's birth config; immutable afterwards.
            chat.initial_profile_name = chat.last_profile_name

        # An explicit model_id overrides whatever model the profile carried.
        if model_id is not None:
            self._set_model(chat, model_id)

        created = self.repo.create(chat)
        self._seed_greeting(created, character)
        self.uow.commit()
        return created

    def _seed_greeting(self, chat: Chat, character: Character) -> None:
        """Seed the character's greeting as the opening assistant message.

        The greeting (first_message) is canned character content shown when a
        session begins — SillyTavern-style, not a model call. {{char}}/{{user}}
        macros are resolved so it reads correctly before the first user turn.
        """
        greeting = (character.first_message or "").strip()
        if not greeting:
            return

        persona = None
        if chat.persona_id:
            persona = self.persona_repo.find_by_id(chat.persona_id)

        context = TemplateContext(character=character, persona=persona, chat=chat)
        try:
            rendered = self.template_service.render(greeting, context)
        except Exception:
            # A malformed greeting template must not block starting the tale.
            logger.warning("greeting_render_failed", character_id=character.id, exc_info=True)
            rendered = greeting

        tokenizer = get_tokenizer(chat.model.model_family if chat.model else None)
        self.message_seeder.seed_greeting(chat.id, rendered, tokenizer.count(rendered))
        chat.preview = rendered[:50]

    def update(
        self,
        chat_id: str,
        title: str | None = None,
        model_id: str | None = None,
        is_bookmarked: bool | None = None,
        task_model_id: str | None = _UNSET,
        persona_id: str | None = _UNSET,
    ) -> Chat:
        """Update chat axes. Re-applying a profile goes through apply_profile.

        task_model_id / persona_id use an _UNSET sentinel so an explicit ``None``
        clears that axis (vs. omitting it to leave it alone).
        """
        chat = self.get_by_id(chat_id)

        if model_id is not None:
            self._set_model(chat, model_id)

        if task_model_id is not _UNSET:
            self._set_task_model(chat, task_model_id)

        if persona_id is not _UNSET:
            self._set_persona(chat, persona_id)

        if title is not None:
            chat.title = title

        if is_bookmarked is not None:
            chat.is_bookmarked = is_bookmarked

        updated = self.repo.update(chat)
        self.uow.commit()
        return updated

    def _set_task_model(self, chat: Chat, task_model_id: str | None) -> None:
        """Set (or clear, when None) the chat's auxiliary task model."""
        if task_model_id is None:
            chat.task_model_id = None
            return
        get_or_404(self.model_repo, task_model_id, "Model")
        chat.task_model_id = task_model_id

    def _set_persona(self, chat: Chat, persona_id: str | None) -> None:
        """Set (or clear, when None) the chat's persona."""
        if persona_id is None:
            chat.persona_id = None
            return
        if not self.persona_repo.find_by_id(persona_id):
            raise NotFoundError(f"Persona with ID '{persona_id}' not found")
        chat.persona_id = persona_id

    def apply_profile(self, chat_id: str, profile_id: str) -> Chat:
        """Apply a profile to an existing chat: copy its axes, update last_profile_name."""
        chat = self.get_by_id(chat_id)
        self._apply_profile(chat, profile_id)
        updated = self.repo.update(chat)
        self.uow.commit()
        return updated

    def _set_model(self, chat: Chat, model_id: str) -> None:
        """Validate a model and set it on the chat, snapshotting its name."""
        model = get_or_404(self.model_repo, model_id, "Model")
        chat.model_id = model_id
        chat.model_name = model.display_name

    def _apply_profile(self, chat: Chat, profile_id: str) -> None:
        """Copy a profile's non-null axes onto the chat, snapshotting the profile name.

        The chat owns the copied FKs as its live config; ``last_profile_name`` is a
        provenance snapshot (a name, not a link), so renaming/deleting the profile
        never affects the chat.
        """
        profile = get_or_404(self.profile_repo, profile_id, "Profile")

        chat.last_profile_name = profile.name
        if profile.prompt_template_id is not None:
            chat.template_id = profile.prompt_template_id
        if profile.preset_id is not None:
            chat.preset_id = profile.preset_id
        if profile.persona_id is not None:
            chat.persona_id = profile.persona_id
        if profile.model_id is not None:
            self._set_model(chat, profile.model_id)
        if profile.task_model_id is not None:
            chat.task_model_id = profile.task_model_id
