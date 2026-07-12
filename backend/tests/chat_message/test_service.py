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
    gateway_factory,
)
from src.chat_message.schemas import StreamEvent
from src.chat_session.models import Chat
from src.chat_session.repository_async import AsyncChatRepository
from src.core.persistence.enums import ProviderType
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
            patch("src.chat_message.gateway_factory.ProviderGateway") as mock_gateway_class,
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

    @pytest.mark.asyncio
    async def test_send_message_vectorizes_both_turns(
        self,
        async_db_session: AsyncSession,
        db: Session,
        async_sample_character: Any,
        async_sample_model: Any,
        monkeypatch: Any,
    ) -> None:
        """With a retrieval service present, the user and assistant turns are indexed."""
        from src.core.config import settings

        monkeypatch.setattr(settings.rag, "vectorize_messages", True)

        chat = Chat(
            title="Chat",
            character_id=async_sample_character.id,
            model_id=async_sample_model.id,
        )
        async_db_session.add(chat)
        await async_db_session.commit()
        await async_db_session.refresh(chat)

        mock_response = CompletionResponse(
            content="A reply.", finish_reason="stop", usage=TokenUsage()
        )
        message_repo = AsyncMessageRepository(async_db_session)
        chat_repo = AsyncChatRepository(async_db_session)
        prompt_builder = PromptBuilder(PromptTemplateRepository(db))

        retrieval = AsyncMock()
        retrieval.retrieve.return_value = []  # keep RAG context empty for prompt building
        service = ChatMessageService(
            message_repo, chat_repo, prompt_builder, retrieval_service=retrieval
        )

        with (
            patch.object(Provider, "has_api_key", return_value=True),
            patch("src.chat_message.gateway_factory.ProviderGateway") as mock_gateway_class,
        ):
            mock_client = AsyncMock()
            mock_client.chat_completion.return_value = mock_response
            mock_gateway_class.return_value = mock_client
            await service.send_message(chat.id, "Hello")

        assert retrieval.vectorize_message.await_count == 2
        indexed = {call.kwargs["content"] for call in retrieval.vectorize_message.await_args_list}
        assert indexed == {"Hello", "A reply."}

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
            patch("src.chat_message.gateway_factory.ProviderGateway") as mock_gateway_class,
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
    async def test_regenerate_stream_on_user_turn_generates_reply(
        self,
        async_db_session: AsyncSession,
        db: Session,
        async_sample_character: Any,
        async_sample_model: Any,
    ) -> None:
        """Retry after a rejected/empty reply: the last turn is the user's, so
        regenerate appends a fresh assistant reply instead of 400-ing."""
        chat = Chat(
            title="Chat",
            character_id=async_sample_character.id,
            model_id=async_sample_model.id,
        )
        async_db_session.add(chat)
        await async_db_session.commit()
        await async_db_session.refresh(chat)
        # Only a user turn exists (the prior generation was rejected, not persisted).
        async_db_session.add(Message(chat_id=chat.id, role=MessageRole.USER, content="Hello?"))
        await async_db_session.commit()

        service = ChatMessageService(
            AsyncMessageRepository(async_db_session),
            AsyncChatRepository(async_db_session),
            PromptBuilder(PromptTemplateRepository(db)),
        )

        async def mock_stream_gen(messages):
            yield StreamChunk(content="A proper reply.")
            yield StreamChunk(finish_reason="stop")

        with (
            patch.object(Provider, "has_api_key", return_value=True),
            patch("src.chat_message.gateway_factory.ProviderGateway") as mock_gateway_class,
        ):
            mock_client = AsyncMock()
            mock_client.chat_completion_stream = MagicMock(side_effect=mock_stream_gen)
            mock_gateway_class.return_value = mock_client
            events = [e async for e in service.regenerate_stream(chat.id)]

        assert not any(e.type == "error" for e in events)
        assert events[-1].type == "done"

        from sqlalchemy import select

        rows = (
            (
                await async_db_session.execute(
                    select(Message).where(Message.chat_id == chat.id).order_by(Message.created_at)
                )
            )
            .scalars()
            .all()
        )
        assert [m.role for m in rows] == [MessageRole.USER, MessageRole.ASSISTANT]
        assert rows[1].content == "A proper reply."

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("finish_reason", "expected_code"),
        [("stop", "empty"), ("content_filter", "filtered")],
    )
    async def test_send_message_stream_empty_completion_emits_error(
        self,
        async_db_session: AsyncSession,
        db: Session,
        async_sample_character: Any,
        async_sample_model: Any,
        finish_reason: str,
        expected_code: str,
    ) -> None:
        """An empty/filtered completion surfaces a typed error instead of silently
        persisting a blank assistant message (the DeepSeek soft-filter case)."""
        chat = Chat(
            title="Chat",
            character_id=async_sample_character.id,
            model_id=async_sample_model.id,
        )
        async_db_session.add(chat)
        await async_db_session.commit()
        await async_db_session.refresh(chat)

        message_repo = AsyncMessageRepository(async_db_session)
        chat_repo = AsyncChatRepository(async_db_session)
        service = ChatMessageService(
            message_repo, chat_repo, PromptBuilder(PromptTemplateRepository(db))
        )

        # Stream yields no content — only a terminal finish_reason (empty completion).
        async def mock_empty_stream(messages):
            yield StreamChunk(finish_reason=finish_reason)

        with (
            patch.object(Provider, "has_api_key", return_value=True),
            patch("src.chat_message.gateway_factory.ProviderGateway") as mock_gateway_class,
        ):
            mock_client = AsyncMock()
            mock_client.chat_completion_stream = MagicMock(side_effect=mock_empty_stream)
            mock_gateway_class.return_value = mock_client

            events = [e async for e in service.send_message_stream(chat.id, "I draw my blade.")]

        error_events = [e for e in events if e.type == "error"]
        assert len(error_events) == 1
        assert error_events[0].code == expected_code
        assert error_events[0].message  # a human-readable explanation
        # No "done" — the stream short-circuits on a non-usable outcome.
        assert not any(e.type == "done" for e in events)

        # Only the user message persisted; no blank assistant reply.
        from sqlalchemy import select

        rows = (
            (await async_db_session.execute(select(Message).where(Message.chat_id == chat.id)))
            .scalars()
            .all()
        )
        assert [m.role for m in rows] == [MessageRole.USER]

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

    @pytest.mark.asyncio
    async def test_build_task_gateway_uses_active_route_provider(self) -> None:
        """The task gateway resolves through the model's active route (provider + identifier)."""
        provider = MagicMock()
        provider.provider_type = ProviderType.OPENAI
        provider.get_base_url.return_value = "https://api.openai.com/v1"
        provider.get_api_key.return_value = "sk-x"
        provider.has_api_key.return_value = True
        provider.name = "OpenAI"

        route = MagicMock()
        route.provider = provider
        route.model_identifier = "gpt-4o-mini"

        model = MagicMock()
        model.active_route = route

        chat = MagicMock()
        chat.task_model = None
        chat.model = model

        gateway = gateway_factory.build_task_gateway(chat)

        assert gateway.provider is provider
        assert gateway.active_identifier == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_task_model_family_is_eager_loaded(
        self,
        async_db_session: AsyncSession,
        async_sample_provider: Provider,
        async_sample_family: Any,
        async_sample_model: Any,
        async_sample_character: Any,
    ) -> None:
        """Regression: a chat's task model must eager-load its model_family.

        The task gateway resolves family-default params for the task model too,
        so a lazy model_family raises MissingGreenlet in the async session — the
        "cannot reach the model" failure when auto-generating tones/titles with a
        distinct task model configured.
        """
        from src.model import ModelRegistry, ModelRoute
        from src.model_family import ModelFamily

        # The task model must have a DISTINCT family from the main model: sharing
        # one lets the main model's eager-loaded family satisfy the access from
        # the identity map, masking the missing task-model joinedload.
        task_family = ModelFamily(
            name="Task Family",
            family_identifier="test.task",
            provider_types=["openai"],
            parameters={
                "temperature": {"type": "float", "default": 0.7, "min_value": 0.0, "max_value": 2.0}
            },
        )
        async_db_session.add(task_family)
        await async_db_session.flush()

        task_model = ModelRegistry(
            slug="task-mini",
            display_name="Task Mini",
            original_identifier="gpt-task-mini",
            model_family_id=task_family.id,
        )
        async_db_session.add(task_model)
        await async_db_session.flush()
        task_route = ModelRoute(
            model_registry_id=task_model.id,
            provider_id=async_sample_provider.id,
            model_identifier="gpt-task-mini",
        )
        async_db_session.add(task_route)
        await async_db_session.flush()
        task_model.active_route_id = task_route.id

        chat = Chat(
            title="Chat",
            character_id=async_sample_character.id,
            model_id=async_sample_model.id,
            task_model_id=task_model.id,
        )
        async_db_session.add(chat)
        await async_db_session.commit()

        # Clear the identity map so the query's eager-load options decide what's
        # loaded (in-session instances would otherwise mask a missing joinedload).
        async_db_session.expunge_all()

        chat_repo = AsyncChatRepository(async_db_session)
        loaded = await chat_repo.find_by_id_with_relations(chat.id)

        assert loaded is not None and loaded.task_model is not None
        # These would raise MissingGreenlet before the fix (async lazy-load):
        assert loaded.task_model.model_family is not None
        assert loaded.task_model.model_family.family_identifier == "test.task"
        route = loaded.task_model.active_route
        assert route is not None and route.provider is not None

    @pytest.mark.asyncio
    async def test_reply_suggestions_use_task_model_with_compact_prompt(
        self,
        async_db_session: AsyncSession,
        db: Session,
        async_sample_character: Any,
        async_sample_model: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Reply candidates run on the cheap task model with a compact prompt,
        not the main model with the full system prompt / card / RAG."""
        chat = Chat(
            title="Chat",
            character_id=async_sample_character.id,
            model_id=async_sample_model.id,
            task_model_id=async_sample_model.id,
        )
        async_db_session.add(chat)
        await async_db_session.commit()
        await async_db_session.refresh(chat)

        async_db_session.add(
            Message(chat_id=chat.id, role=MessageRole.USER, content="I draw my blade.")
        )
        async_db_session.add(
            Message(chat_id=chat.id, role=MessageRole.ASSISTANT, content="The guard sneers at you.")
        )
        await async_db_session.commit()

        message_repo = AsyncMessageRepository(async_db_session)
        chat_repo = AsyncChatRepository(async_db_session)
        template_repo = PromptTemplateRepository(db)
        prompt_builder = PromptBuilder(template_repo)
        service = ChatMessageService(message_repo, chat_repo, prompt_builder)

        task_gateway = MagicMock()
        task_gateway.chat_completion = AsyncMock(
            return_value=CompletionResponse(
                content='["Stand firm.", "Sheathe it.", "Taunt him."]',
                finish_reason="stop",
                usage=TokenUsage(),
            )
        )
        build_task = MagicMock(return_value=task_gateway)
        build_main = MagicMock(side_effect=AssertionError("reply must not use the main gateway"))
        monkeypatch.setattr(gateway_factory, "build_task_gateway", build_task)
        monkeypatch.setattr(gateway_factory, "build_gateway", build_main)
        monkeypatch.setattr(service, "_record_llm_audit", AsyncMock())

        result = await service.generate_suggestions(chat.id, mode="reply", count=3)

        assert result == ["Stand firm.", "Sheathe it.", "Taunt him."]
        build_task.assert_called_once()
        build_main.assert_not_called()

        # Compact: a single user message carrying the recent exchange (grounded in
        # the last turn), not the full built prompt.
        sent = task_gateway.chat_completion.await_args.args[0]
        assert len(sent) == 1 and sent[0]["role"] == "user"
        prompt = sent[0]["content"]
        assert "Recent exchange:" in prompt
        assert "The guard sneers at you." in prompt

    @pytest.mark.asyncio
    async def test_preview_prompt_returns_scaffolding_and_params(
        self,
        async_db_session: AsyncSession,
        db: Session,
        async_sample_character: Any,
        async_sample_model: Any,
    ) -> None:
        """preview_prompt returns the model/provider, effective params, and the
        assembled scaffolding messages (no LLM call, no live conversation)."""
        chat = Chat(
            title="Chat",
            character_id=async_sample_character.id,
            model_id=async_sample_model.id,
        )
        async_db_session.add(chat)
        await async_db_session.commit()
        await async_db_session.refresh(chat)

        message_repo = AsyncMessageRepository(async_db_session)
        chat_repo = AsyncChatRepository(async_db_session)
        service = ChatMessageService(
            message_repo, chat_repo, PromptBuilder(PromptTemplateRepository(db))
        )

        preview = await service.preview_prompt(chat.id)

        assert preview["model_display_name"] == async_sample_model.display_name
        assert preview["provider_name"] == "OpenAI"
        assert preview["model_identifier"] == "gpt-4"
        # Effective params include the family default (temperature) from the fixture.
        assert preview["parameters"]["temperature"] == 1.0
        assert isinstance(preview["messages"], list)
        assert all(isinstance(m["content"], str) for m in preview["messages"])
