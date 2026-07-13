"""Tests for ChatService"""

from typing import Any

import pytest
from sqlalchemy.orm import Session
from src.character import CharacterRepository
from src.chat_message.repository import MessageRepository
from src.chat_session import Chat, ChatRepository, ChatService
from src.core.exceptions import BanneredMareException
from src.model import ModelRegistry, ModelRepository, ModelRoute
from src.persona import Persona, PersonaRepository
from src.profile.repository import ProfileRepository


class TestChatService:
    """Test suite for ChatService"""

    def test_list_all(self, db: Session, sample_character: Any, sample_model: Any) -> None:
        """Test listing all chats"""
        # Create chats
        chat1 = Chat(title="Chat 1", character_id=sample_character.id, model_id=sample_model.id)
        chat2 = Chat(title="Chat 2", character_id=sample_character.id, model_id=sample_model.id)
        db.add_all([chat1, chat2])
        db.commit()

        chat_repo = ChatRepository(db)
        char_repo = CharacterRepository(db)
        model_repo = ModelRepository(db)
        service = ChatService(
            chat_repo,
            char_repo,
            model_repo,
            ProfileRepository(db),
            MessageRepository(db),
            PersonaRepository(db),
        )
        chats = service.list_all()

        assert len(chats) == 2
        assert any(c.title == "Chat 1" for c in chats)
        assert any(c.title == "Chat 2" for c in chats)

    def test_get_by_id_success(self, db: Session, sample_character: Any, sample_model: Any) -> None:
        """Test getting a chat by ID successfully"""
        chat = Chat(title="Test Chat", character_id=sample_character.id, model_id=sample_model.id)
        db.add(chat)
        db.commit()
        db.refresh(chat)

        chat_repo = ChatRepository(db)
        char_repo = CharacterRepository(db)
        model_repo = ModelRepository(db)
        service = ChatService(
            chat_repo,
            char_repo,
            model_repo,
            ProfileRepository(db),
            MessageRepository(db),
            PersonaRepository(db),
        )
        result = service.get_by_id(chat.id)

        assert result.id == chat.id
        assert result.title == "Test Chat"

    def test_get_by_id_not_found(self, db: Session) -> None:
        """Test getting a chat that doesn't exist raises 404"""
        chat_repo = ChatRepository(db)
        char_repo = CharacterRepository(db)
        model_repo = ModelRepository(db)
        service = ChatService(
            chat_repo,
            char_repo,
            model_repo,
            ProfileRepository(db),
            MessageRepository(db),
            PersonaRepository(db),
        )

        with pytest.raises(BanneredMareException) as exc_info:
            _ = service.get_by_id("nonexistent-id")

        assert exc_info.value.status_code == 404

    def test_create_chat_success(
        self, db: Session, sample_character: Any, sample_model: Any
    ) -> None:
        """Test creating a chat successfully"""
        chat_repo = ChatRepository(db)
        char_repo = CharacterRepository(db)
        model_repo = ModelRepository(db)
        service = ChatService(
            chat_repo,
            char_repo,
            model_repo,
            ProfileRepository(db),
            MessageRepository(db),
            PersonaRepository(db),
        )
        chat = service.create(
            character_id=sample_character.id,
            model_id=sample_model.id,
            title="Test Chat",
        )

        assert chat.character_id == sample_character.id
        assert chat.model_id == sample_model.id
        assert chat.title == "Test Chat"
        assert chat.id is not None

    def test_create_chat_character_not_found(self, db: Session, sample_model: Any) -> None:
        """Test creating chat with non-existent character raises error"""
        chat_repo = ChatRepository(db)
        char_repo = CharacterRepository(db)
        model_repo = ModelRepository(db)
        service = ChatService(
            chat_repo,
            char_repo,
            model_repo,
            ProfileRepository(db),
            MessageRepository(db),
            PersonaRepository(db),
        )
        with pytest.raises(BanneredMareException) as exc_info:
            _ = service.create(
                character_id="nonexistent-character",
                model_id=sample_model.id,
            )

        assert exc_info.value.status_code == 404
        assert "Character" in exc_info.value.message

    def test_create_chat_model_not_found(self, db: Session, sample_character: Any) -> None:
        """Test creating chat with non-existent model raises error"""
        chat_repo = ChatRepository(db)
        char_repo = CharacterRepository(db)
        model_repo = ModelRepository(db)
        service = ChatService(
            chat_repo,
            char_repo,
            model_repo,
            ProfileRepository(db),
            MessageRepository(db),
            PersonaRepository(db),
        )
        with pytest.raises(BanneredMareException) as exc_info:
            _ = service.create(
                character_id=sample_character.id,
                model_id="nonexistent-model",
            )

        assert exc_info.value.status_code == 404
        assert "Model" in exc_info.value.message

    def test_update_chat_title(self, db: Session, sample_character: Any, sample_model: Any) -> None:
        """Test updating chat title"""
        chat = Chat(title="Old Title", character_id=sample_character.id, model_id=sample_model.id)
        db.add(chat)
        db.commit()
        db.refresh(chat)

        chat_repo = ChatRepository(db)
        char_repo = CharacterRepository(db)
        model_repo = ModelRepository(db)
        service = ChatService(
            chat_repo,
            char_repo,
            model_repo,
            ProfileRepository(db),
            MessageRepository(db),
            PersonaRepository(db),
        )
        updated = service.update(chat.id, title="New Title")

        assert updated.title == "New Title"
        assert updated.model_id == sample_model.id  # Unchanged

    def test_update_chat_model(
        self,
        db: Session,
        sample_character: Any,
        sample_model: Any,
        sample_provider: Any,
        sample_family: Any,
    ) -> None:
        """Test updating chat model"""
        model2 = ModelRegistry(
            slug="gpt-3.5-turbo",
            display_name="GPT-3.5",
            original_identifier="gpt-3.5-turbo",
            model_family_id=sample_family.id,
        )
        db.add(model2)
        db.flush()
        route2 = ModelRoute(
            model_registry_id=model2.id,
            provider_id=sample_provider.id,
            model_identifier="gpt-3.5-turbo",
        )
        db.add(route2)
        db.flush()
        model2.active_route_id = route2.id
        db.commit()

        chat = Chat(title="Chat", character_id=sample_character.id, model_id=sample_model.id)
        db.add(chat)
        db.commit()
        db.refresh(chat)

        chat_repo = ChatRepository(db)
        char_repo = CharacterRepository(db)
        model_repo = ModelRepository(db)
        service = ChatService(
            chat_repo,
            char_repo,
            model_repo,
            ProfileRepository(db),
            MessageRepository(db),
            PersonaRepository(db),
        )
        updated = service.update(chat.id, model_id=model2.id)

        assert updated.model_id == model2.id
        assert updated.title == "Chat"  # Unchanged

    def test_update_chat_model_not_found(
        self, db: Session, sample_character: Any, sample_model: Any
    ) -> None:
        """Test updating chat with non-existent model raises error"""
        chat = Chat(title="Chat", character_id=sample_character.id, model_id=sample_model.id)
        db.add(chat)
        db.commit()
        db.refresh(chat)

        chat_repo = ChatRepository(db)
        char_repo = CharacterRepository(db)
        model_repo = ModelRepository(db)
        service = ChatService(
            chat_repo,
            char_repo,
            model_repo,
            ProfileRepository(db),
            MessageRepository(db),
            PersonaRepository(db),
        )
        with pytest.raises(BanneredMareException) as exc_info:
            _ = service.update(chat.id, model_id="nonexistent-model")

        assert exc_info.value.status_code == 404
        assert "Model" in exc_info.value.message

    def _service(self, db: Session) -> ChatService:
        return ChatService(
            ChatRepository(db),
            CharacterRepository(db),
            ModelRepository(db),
            ProfileRepository(db),
            message_repo=MessageRepository(db),
            persona_repo=PersonaRepository(db),
        )

    def test_update_chat_task_model_set_and_clear(
        self, db: Session, sample_character: Any, sample_model: Any
    ) -> None:
        """task_model_id can be set, then cleared with an explicit None."""
        chat = Chat(title="Chat", character_id=sample_character.id, model_id=sample_model.id)
        db.add(chat)
        db.commit()
        db.refresh(chat)
        service = self._service(db)

        assert (
            service.update(chat.id, task_model_id=sample_model.id).task_model_id == sample_model.id
        )
        assert service.update(chat.id, task_model_id=None).task_model_id is None

    def test_update_chat_task_model_omitted_is_preserved(
        self, db: Session, sample_character: Any, sample_model: Any
    ) -> None:
        """Omitting task_model_id (the _UNSET default) leaves an existing one intact."""
        chat = Chat(
            title="Chat",
            character_id=sample_character.id,
            model_id=sample_model.id,
            task_model_id=sample_model.id,
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)

        updated = self._service(db).update(chat.id, title="Renamed")  # task_model_id not passed
        assert updated.task_model_id == sample_model.id

    def test_update_chat_task_model_not_found(
        self, db: Session, sample_character: Any, sample_model: Any
    ) -> None:
        chat = Chat(title="Chat", character_id=sample_character.id, model_id=sample_model.id)
        db.add(chat)
        db.commit()
        db.refresh(chat)
        with pytest.raises(BanneredMareException) as exc_info:
            _ = self._service(db).update(chat.id, task_model_id="nonexistent-model")
        assert exc_info.value.status_code == 404

    def test_update_chat_persona_set_and_clear(
        self, db: Session, sample_character: Any, sample_model: Any
    ) -> None:
        persona = Persona(name="Hero", description="A brave soul")
        db.add(persona)
        db.commit()
        db.refresh(persona)
        chat = Chat(title="Chat", character_id=sample_character.id, model_id=sample_model.id)
        db.add(chat)
        db.commit()
        db.refresh(chat)
        service = self._service(db)

        assert service.update(chat.id, persona_id=persona.id).persona_id == persona.id
        assert service.update(chat.id, persona_id=None).persona_id is None

    def test_update_chat_persona_not_found(
        self, db: Session, sample_character: Any, sample_model: Any
    ) -> None:
        chat = Chat(title="Chat", character_id=sample_character.id, model_id=sample_model.id)
        db.add(chat)
        db.commit()
        db.refresh(chat)
        with pytest.raises(BanneredMareException) as exc_info:
            _ = self._service(db).update(chat.id, persona_id="nonexistent-persona")
        assert exc_info.value.status_code == 404

    def test_delete_chat_success(
        self, db: Session, sample_character: Any, sample_model: Any
    ) -> None:
        """Test deleting a chat successfully"""
        chat = Chat(title="Chat", character_id=sample_character.id, model_id=sample_model.id)
        db.add(chat)
        db.commit()
        db.refresh(chat)
        chat_id = chat.id

        chat_repo = ChatRepository(db)
        char_repo = CharacterRepository(db)
        model_repo = ModelRepository(db)
        service = ChatService(
            chat_repo,
            char_repo,
            model_repo,
            ProfileRepository(db),
            MessageRepository(db),
            PersonaRepository(db),
        )
        service.delete(chat_id)

        # Verify chat is deleted
        deleted = db.query(Chat).filter(Chat.id == chat_id).first()
        assert deleted is None
