"""Tests that ChatMessageService records an LLM audit entry per completion."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from src.chat_message import AsyncMessageRepository, ChatMessageService
from src.chat_session.models import Chat
from src.chat_session.repository_async import AsyncChatRepository
from src.core.exceptions import ProviderException
from src.prompt_template.prompt_builder import PromptBuilder
from src.prompt_template.repository import PromptTemplateRepository
from src.provider import Provider
from src.provider.adapters import CompletionResponse, StreamChunk, TokenUsage


async def _make_chat(session: AsyncSession, character_id: str, model_id: str) -> Chat:
    chat = Chat(title="Chat", character_id=character_id, model_id=model_id)
    session.add(chat)
    await session.commit()
    await session.refresh(chat)
    return chat


def _service(async_db_session: AsyncSession, db: Session) -> ChatMessageService:
    return ChatMessageService(
        AsyncMessageRepository(async_db_session),
        AsyncChatRepository(async_db_session),
        PromptBuilder(PromptTemplateRepository(db)),
    )


@pytest.mark.asyncio
async def test_send_message_records_success_audit(
    async_db_session: AsyncSession,
    db: Session,
    async_sample_character: Any,
    async_sample_model: Any,
) -> None:
    chat = await _make_chat(async_db_session, async_sample_character.id, async_sample_model.id)
    service = _service(async_db_session, db)

    mock_response = CompletionResponse(
        content="Hi there", finish_reason="stop", usage=TokenUsage(output_tokens=7)
    )

    with (
        patch.object(Provider, "has_api_key", return_value=True),
        patch("src.chat_message.gateway_factory.ProviderGateway") as mock_gateway_class,
        patch("src.chat_message.llm_audit.audit_logger") as mock_audit,
    ):
        mock_audit.log_llm_call = AsyncMock()
        mock_client = AsyncMock()
        mock_client.chat_completion.return_value = mock_response
        mock_client.provider.provider_type.value = "openai"
        mock_client.active_identifier = "gpt-4o"
        mock_gateway_class.return_value = mock_client

        await service.send_message(chat.id, "Hello")

    mock_audit.log_llm_call.assert_awaited_once()
    kwargs = mock_audit.log_llm_call.call_args.kwargs
    assert kwargs["status"] == "success"
    assert kwargs["provider"] == "openai"
    assert kwargs["model"] == "gpt-4o"
    assert kwargs["request_payload"]  # the prompt messages
    assert kwargs["response_payload"]["content"] == "Hi there"


@pytest.mark.asyncio
async def test_send_message_records_error_audit(
    async_db_session: AsyncSession,
    db: Session,
    async_sample_character: Any,
    async_sample_model: Any,
) -> None:
    chat = await _make_chat(async_db_session, async_sample_character.id, async_sample_model.id)
    service = _service(async_db_session, db)

    with (
        patch.object(Provider, "has_api_key", return_value=True),
        patch("src.chat_message.gateway_factory.ProviderGateway") as mock_gateway_class,
        patch("src.chat_message.llm_audit.audit_logger") as mock_audit,
    ):
        mock_audit.log_llm_call = AsyncMock()
        mock_client = AsyncMock()
        mock_client.chat_completion.side_effect = ProviderException("upstream down")
        mock_client.provider.provider_type.value = "openai"
        mock_client.active_identifier = "gpt-4o"
        mock_gateway_class.return_value = mock_client

        with pytest.raises(HTTPException):
            await service.send_message(chat.id, "Hello")

    mock_audit.log_llm_call.assert_awaited_once()
    kwargs = mock_audit.log_llm_call.call_args.kwargs
    assert kwargs["status"] == "provider_error"
    assert kwargs["error_message"] == "upstream down"
    assert kwargs["response_payload"] is None


@pytest.mark.asyncio
async def test_stream_records_success_audit(
    async_db_session: AsyncSession,
    db: Session,
    async_sample_character: Any,
    async_sample_model: Any,
) -> None:
    chat = await _make_chat(async_db_session, async_sample_character.id, async_sample_model.id)
    service = _service(async_db_session, db)

    async def mock_stream_gen(messages):
        yield StreamChunk(content="Hel")
        yield StreamChunk(content="lo")
        yield StreamChunk(finish_reason="stop", usage=TokenUsage(output_tokens=2))

    with (
        patch.object(Provider, "has_api_key", return_value=True),
        patch("src.chat_message.gateway_factory.ProviderGateway") as mock_gateway_class,
        patch("src.chat_message.llm_audit.audit_logger") as mock_audit,
    ):
        mock_audit.log_llm_call = AsyncMock()
        mock_client = AsyncMock()
        mock_client.chat_completion_stream = MagicMock(side_effect=mock_stream_gen)
        mock_client.provider.provider_type.value = "openai"
        mock_client.active_identifier = "gpt-4o"
        mock_gateway_class.return_value = mock_client

        events = [e async for e in service.send_message_stream(chat.id, "Hello")]

    assert any(e.type == "done" for e in events)
    mock_audit.log_llm_call.assert_awaited_once()
    kwargs = mock_audit.log_llm_call.call_args.kwargs
    assert kwargs["status"] == "success"
    assert kwargs["response_payload"]["content"] == "Hello"
    assert kwargs["response_payload"]["finish_reason"] == "stop"
