"""Tests for Loose Coupling between ChatSession and Model"""

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from src.character import CharacterRepository
from src.chat_message import AsyncMessageRepository, ChatMessageService
from src.chat_session import Chat, ChatRepository, ChatService
from src.chat_session.repository_async import AsyncChatRepository
from src.model import ModelRepository, ModelService
from src.model_family.repository import ModelFamilyRepository
from src.prompt_template.prompt_builder import PromptBuilder
from src.prompt_template.repository import PromptTemplateRepository
from src.provider.repository import ProviderRepository


class TestLooseCoupling:
    """Test suite for loose coupling requirements"""

    def test_create_chat_without_model(self, db: Session, sample_character):
        """Test creating a chat without a model (model_id=None)"""
        chat_repo = ChatRepository(db)
        char_repo = CharacterRepository(db)
        model_repo = ModelRepository(db)
        service = ChatService(chat_repo, char_repo, model_repo)

        # Create chat with explicit None
        chat = service.create(
            character_id=sample_character.id,
            model_id=None,
            title="Chat without Model",
        )

        assert chat.id is not None
        assert chat.model_id is None
        assert chat.character_id == sample_character.id
        assert chat.title == "Chat without Model"

    def test_model_deletion_nullifies_chat_model_id(
        self, db: Session, sample_character, sample_model
    ):
        """Test that deleting a model sets chat.model_id to NULL"""
        # 1. Create Chat linked to Model
        chat = Chat(
            title="Linked Chat",
            character_id=sample_character.id,
            model_id=sample_model.id,
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)
        chat_id = chat.id

        assert chat.model_id == sample_model.id

        # 2. Delete Model via Service
        model_repo = ModelRepository(db)
        provider_repo = ProviderRepository(db)
        family_repo = ModelFamilyRepository(db)
        chat_repo = ChatRepository(db)
        model_service = ModelService(model_repo, provider_repo, family_repo, chat_repo)

        model_service.delete(sample_model.id)

        # 3. Refresh Chat and Verify
        db.expire_all()  # Ensure we fetch fresh data
        reloaded_chat = db.query(Chat).filter(Chat.id == chat_id).first()

        assert reloaded_chat is not None
        assert reloaded_chat.model_id is None
        assert reloaded_chat.title == "Linked Chat"

    @pytest.mark.asyncio
    async def test_send_message_fails_without_model(
        self, async_db_session: AsyncSession, db: Session, async_sample_character
    ):
        """Test that sending a message fails if chat has no model"""
        # 1. Create Chat without Model
        chat = Chat(
            title="Chat No Model",
            character_id=async_sample_character.id,
            model_id=None,
        )
        async_db_session.add(chat)
        await async_db_session.commit()
        chat_id = chat.id

        # 2. Setup Service
        message_repo = AsyncMessageRepository(async_db_session)
        chat_repo = AsyncChatRepository(async_db_session)
        template_repo = PromptTemplateRepository(db)
        prompt_builder = PromptBuilder(template_repo)
        service = ChatMessageService(message_repo, chat_repo, prompt_builder)

        # 3. Call send_message and expect 400
        with pytest.raises(HTTPException) as exc_info:
            await service.send_message(chat_id, "Hello")

        assert exc_info.value.status_code == 400
        assert "Chat does not have a valid model assigned" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_send_message_stream_fails_without_model(
        self, async_db_session: AsyncSession, db: Session, async_sample_character
    ):
        """Test that streaming a message fails if chat has no model"""
        # 1. Create Chat without Model
        chat = Chat(
            title="Chat No Model",
            character_id=async_sample_character.id,
            model_id=None,
        )
        async_db_session.add(chat)
        await async_db_session.commit()
        chat_id = chat.id

        # 2. Setup Service
        message_repo = AsyncMessageRepository(async_db_session)
        chat_repo = AsyncChatRepository(async_db_session)
        template_repo = PromptTemplateRepository(db)
        prompt_builder = PromptBuilder(template_repo)
        service = ChatMessageService(message_repo, chat_repo, prompt_builder)

        # 3. Call send_message_stream and expect 400
        with pytest.raises(HTTPException) as exc_info:
            async for _ in service.send_message_stream(chat_id, "Hello"):
                pass

        assert exc_info.value.status_code == 400
        assert "Chat does not have a valid model assigned" in exc_info.value.detail
