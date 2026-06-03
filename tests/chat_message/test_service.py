"""Tests for ChatMessageService"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from src.chat_message import (
    AsyncMessageRepository,
    ChatMessageService,
    Message,
    MessageRole,
)
from src.chat_message.schemas import StreamEvent
from src.chat_session.models import Chat
from src.chat_session.repository_async import AsyncChatRepository
from src.prompt_template.prompt_builder import PromptBuilder
from src.prompt_template.repository import PromptTemplateRepository
from src.provider import Provider
from src.provider.adapters import CompletionResponse, StreamChunk, TokenUsage


class TestChatMessageService:
    """Test suite for ChatMessageService"""

    @pytest.mark.asyncio
    async def test_get_messages(
        self,
        async_db_session: AsyncSession,
        db: Session,
        async_sample_character: Any,
        async_sample_model: Any,
    ) -> None:
        """Test getting messages for a chat with pagination wrapper"""
        chat = Chat(
            title="Chat",
            character_id=async_sample_character.id,
            model_id=async_sample_model.id,
        )
        async_db_session.add(chat)
        await async_db_session.commit()

        # Add messages
        msg1 = Message(chat_id=chat.id, role=MessageRole.USER, content="Hello")
        msg2 = Message(chat_id=chat.id, role=MessageRole.ASSISTANT, content="Hi there!")
        async_db_session.add_all([msg1, msg2])
        await async_db_session.commit()

        message_repo = AsyncMessageRepository(async_db_session)
        chat_repo = AsyncChatRepository(async_db_session)
        # Note: PromptTemplateRepository stays sync, uses separate db session
        template_repo = PromptTemplateRepository(db)
        prompt_builder = PromptBuilder(template_repo)
        service = ChatMessageService(message_repo, chat_repo, prompt_builder)
        result = await service.get_messages(chat.id)

        # Verify response structure
        assert hasattr(result, "items")
        assert hasattr(result, "meta")
        assert len(result.items) == 2

        # Verify messages are in newest-first order (DESC)
        assert result.items[0].role == MessageRole.ASSISTANT
        assert result.items[0].content == "Hi there!"
        assert result.items[1].role == MessageRole.USER
        assert result.items[1].content == "Hello"

        # Verify metadata
        assert result.meta.limit == 20
        assert result.meta.has_more is False
        assert (
            result.meta.cursor is not None
        )  # Should be the timestamp of the last (oldest) message

    @pytest.mark.asyncio
    async def test_send_message_success(
        self,
        async_db_session: AsyncSession,
        db: Session,
        async_sample_character: Any,
        async_sample_model: Any,
    ) -> None:
        """Test sending a message successfully"""
        chat = Chat(
            title="Chat",
            character_id=async_sample_character.id,
            model_id=async_sample_model.id,
        )
        async_db_session.add(chat)
        await async_db_session.commit()
        await async_db_session.refresh(chat)

        mock_response = CompletionResponse(
            content="Hello! How can I help you?",
            finish_reason="stop",
            usage=TokenUsage(),
        )

        message_repo = AsyncMessageRepository(async_db_session)
        chat_repo = AsyncChatRepository(async_db_session)
        # Note: PromptTemplateRepository stays sync, uses separate db session
        template_repo = PromptTemplateRepository(db)
        prompt_builder = PromptBuilder(template_repo)
        service = ChatMessageService(message_repo, chat_repo, prompt_builder)

        with (
            patch.object(Provider, "has_api_key", return_value=True),
            patch("src.chat_message.service.ProviderGateway") as mock_gateway_class,
        ):
            mock_client = AsyncMock()
            mock_client.chat_completion.return_value = mock_response
            mock_gateway_class.return_value = mock_client

            assistant_message = await service.send_message(chat.id, "Hello")

        assert assistant_message.role == MessageRole.ASSISTANT
        assert assistant_message.content == "Hello! How can I help you?"
        assert assistant_message.chat_id == chat.id

        # Verify user message was saved
        from sqlalchemy import select

        stmt = select(Message).where(Message.chat_id == chat.id)
        result = await async_db_session.execute(stmt)
        messages = list(result.scalars().all())
        assert len(messages) == 2
        assert messages[0].role == MessageRole.USER
        assert messages[0].content == "Hello"

    def test_prompt_builder_integration(
        self, db: Session, sample_character: Any, sample_model: Any
    ) -> None:
        """Test building API messages using PromptBuilder integration"""

        chat = Chat(title="Chat", character_id=sample_character.id, model_id=sample_model.id)
        db.add(chat)
        db.commit()
        db.refresh(chat)

        # Add messages
        msg1 = Message(chat_id=chat.id, role=MessageRole.USER, content="Hello")
        msg2 = Message(chat_id=chat.id, role=MessageRole.ASSISTANT, content="Hi!")
        messages = [msg1, msg2]

        template_repo = PromptTemplateRepository(db)
        prompt_builder = PromptBuilder(template_repo)

        api_messages = prompt_builder.build_api_messages(chat, messages)

        # Since we haven't seeded templates in this test DB, it should use fallback
        assert len(api_messages) >= 3  # system + character + history

    @pytest.mark.asyncio
    async def test_regenerate_stream(
        self,
        async_db_session: AsyncSession,
        db: Session,
        async_sample_character: Any,
        async_sample_model: Any,
    ) -> None:
        """Test regenerating the last message"""
        chat = Chat(
            title="Chat",
            character_id=async_sample_character.id,
            model_id=async_sample_model.id,
        )
        async_db_session.add(chat)
        await async_db_session.commit()
        await async_db_session.refresh(chat)

        # Add messages: User -> Assistant (Bad)
        msg1 = Message(chat_id=chat.id, role=MessageRole.USER, content="Hello")
        msg2 = Message(chat_id=chat.id, role=MessageRole.ASSISTANT, content="Bad response")
        async_db_session.add_all([msg1, msg2])
        await async_db_session.commit()

        message_repo = AsyncMessageRepository(async_db_session)
        chat_repo = AsyncChatRepository(async_db_session)
        template_repo = PromptTemplateRepository(db)
        prompt_builder = PromptBuilder(template_repo)
        service = ChatMessageService(message_repo, chat_repo, prompt_builder)

        async def mock_stream_gen(messages):
            yield StreamChunk(content="Better ")
            yield StreamChunk(content="response")
            yield StreamChunk(finish_reason="stop")

        with (
            patch.object(Provider, "has_api_key", return_value=True),
            patch("src.chat_message.service.ProviderGateway") as mock_gateway_class,
        ):
            mock_client = AsyncMock()
            mock_client.chat_completion_stream = MagicMock(side_effect=mock_stream_gen)
            mock_gateway_class.return_value = mock_client

            events: list[StreamEvent] = []
            async for event in service.regenerate_stream(chat.id):
                events.append(event)

            assert events[0].type == "start"
            assert events[0].message_id is not None

            text_events = [e for e in events if e.type == "text"]
            full_text = "".join(e.content or "" for e in text_events)
            assert full_text == "Better response"

            assert events[-1].type == "done"
            assert events[-1].finish_reason == "stop"

        # Verify DB state: Old assistant message deleted, new one added
        from sqlalchemy import select

        stmt = select(Message).where(Message.chat_id == chat.id).order_by(Message.created_at.asc())
        result = await async_db_session.execute(stmt)
        messages = list(result.scalars().all())

        assert len(messages) == 2
        assert messages[0].content == "Hello"
        assert messages[1].content == "Better response"

    @pytest.mark.asyncio
    async def test_edit_message(
        self,
        async_db_session: AsyncSession,
        db: Session,
        async_sample_character: Any,
        async_sample_model: Any,
    ) -> None:
        """Test editing a message updates content and token_count."""
        chat = Chat(
            title="Chat",
            character_id=async_sample_character.id,
            model_id=async_sample_model.id,
        )
        async_db_session.add(chat)
        await async_db_session.commit()

        msg = Message(chat_id=chat.id, role=MessageRole.USER, content="Original text")
        async_db_session.add(msg)
        await async_db_session.commit()
        await async_db_session.refresh(msg)

        message_repo = AsyncMessageRepository(async_db_session)
        chat_repo = AsyncChatRepository(async_db_session)
        template_repo = PromptTemplateRepository(db)
        prompt_builder = PromptBuilder(template_repo)
        service = ChatMessageService(message_repo, chat_repo, prompt_builder)

        updated = await service.edit_message(chat.id, msg.id, "Edited text")

        assert updated.content == "Edited text"
        assert updated.token_count is not None
        assert updated.token_count > 0

        # Verify token_count was recomputed (not zero or the same as original)
        from src.core.utils.tokenizer import TokenizerService

        tokenizer = TokenizerService()
        expected_tokens = tokenizer.count_tokens("Edited text")
        assert updated.token_count == expected_tokens

    @pytest.mark.asyncio
    async def test_edit_message_not_found(
        self,
        async_db_session: AsyncSession,
        db: Session,
        async_sample_character: Any,
        async_sample_model: Any,
    ) -> None:
        """Test editing a nonexistent message raises 404."""
        from fastapi import HTTPException

        chat = Chat(
            title="Chat",
            character_id=async_sample_character.id,
            model_id=async_sample_model.id,
        )
        async_db_session.add(chat)
        await async_db_session.commit()

        message_repo = AsyncMessageRepository(async_db_session)
        chat_repo = AsyncChatRepository(async_db_session)
        template_repo = PromptTemplateRepository(db)
        prompt_builder = PromptBuilder(template_repo)
        service = ChatMessageService(message_repo, chat_repo, prompt_builder)

        with pytest.raises(HTTPException) as exc_info:
            await service.edit_message(chat.id, "nonexistent_id", "New content")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_regenerate_not_assistant(
        self,
        async_db_session: AsyncSession,
        db: Session,
        async_sample_character: Any,
        async_sample_model: Any,
    ) -> None:
        """Test regenerate raises 400 when last message is not from assistant."""
        from fastapi import HTTPException

        chat = Chat(
            title="Chat",
            character_id=async_sample_character.id,
            model_id=async_sample_model.id,
        )
        async_db_session.add(chat)
        await async_db_session.commit()
        await async_db_session.refresh(chat)

        # Only a user message, no assistant reply yet
        msg = Message(chat_id=chat.id, role=MessageRole.USER, content="Hello")
        async_db_session.add(msg)
        await async_db_session.commit()

        message_repo = AsyncMessageRepository(async_db_session)
        chat_repo = AsyncChatRepository(async_db_session)
        template_repo = PromptTemplateRepository(db)
        prompt_builder = PromptBuilder(template_repo)
        service = ChatMessageService(message_repo, chat_repo, prompt_builder)

        with pytest.raises(HTTPException) as exc_info:
            await service.regenerate(chat.id)

        assert exc_info.value.status_code == 400
        assert "not from assistant" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_retrieve_rag_context_none(
        self,
        async_db_session: AsyncSession,
        db: Session,
        async_sample_character: Any,
        async_sample_model: Any,
    ) -> None:
        """Test _retrieve_rag_context returns None when no retrieval_service."""
        chat = Chat(
            title="Chat",
            character_id=async_sample_character.id,
            model_id=async_sample_model.id,
        )
        async_db_session.add(chat)
        await async_db_session.commit()
        await async_db_session.refresh(chat)

        msg = Message(chat_id=chat.id, role=MessageRole.USER, content="Hello")
        async_db_session.add(msg)
        await async_db_session.commit()

        message_repo = AsyncMessageRepository(async_db_session)
        chat_repo = AsyncChatRepository(async_db_session)
        template_repo = PromptTemplateRepository(db)
        prompt_builder = PromptBuilder(template_repo)
        # No retrieval_service passed — defaults to None
        service = ChatMessageService(message_repo, chat_repo, prompt_builder)

        messages = [msg]
        result = await service._retrieve_rag_context(chat, messages)

        assert result is None
