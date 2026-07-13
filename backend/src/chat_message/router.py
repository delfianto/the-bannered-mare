"""Message API endpoints (FULLY ASYNC)"""

import json

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from src.chat_message.dependencies import ChatMessageServiceDep
from src.chat_message.llm_audit import classify_error
from src.chat_message.schemas import (
    AlternativeResponse,
    ChatPromptPreviewResponse,
    MessageCreate,
    MessageListResponse,
    MessageResponse,
    MessageUpdate,
    StreamEvent,
    SuggestionRequest,
    SuggestionResponse,
    TitleResponse,
    stream_event_to_dict,
)
from src.chat_message.service import ChatMessageService
from src.core.exceptions import ProviderException, ValidationError
from src.core.logging.logger_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/chats/{chat_id}/messages", tags=["messages"])

# Chat-scoped (not message-scoped) endpoints served by the same async service.
preview_router = APIRouter(prefix="/api/chats/{chat_id}", tags=["chats"])


@preview_router.get("/prompt-preview", response_model=ChatPromptPreviewResponse)
async def get_prompt_preview(chat_id: str, service: ChatMessageServiceDep):
    """Resolved prompt scaffolding + effective sampler params for the chat.

    Read-only, no LLM call — powers the chat drawer's Session-info tab.
    """
    return await service.preview_prompt(chat_id)


@router.get("", response_model=MessageListResponse)
async def get_chat_messages(
    chat_id: str,
    service: ChatMessageServiceDep,
    limit: int = Query(default=20, ge=1, le=100, description="Number of messages to load"),
    cursor: str | None = Query(
        default=None, description="ISO datetime of the oldest loaded message"
    ),
):
    """
    Get chat messages (Cursor Pagination).
    Returns wrapped response: { items: [...], meta: { cursor: '...', has_more: true } }
    """
    return await service.get_messages(chat_id, limit=limit, cursor=cursor)


@router.post("", response_model=MessageResponse)
async def send_message(
    request: Request,
    chat_id: str,
    service: ChatMessageServiceDep,
    message_data: MessageCreate | None = None,
    stream: bool = Query(default=False, description="Stream the response"),
    regenerate: bool = Query(default=False, description="Regenerate the last assistant message"),
):
    """
    Send a message or regenerate the last response.
    Supports both blocking and streaming modes.
    - **stream=False** (default): Returns JSON MessageResponse.
    - **stream=True**: Returns Server-Sent Events (SSE) with typed events.
    """
    if not regenerate and message_data is None:
        raise ValidationError("Message content is required when not regenerating.")

    if stream:
        return _handle_streaming(request, chat_id, service, message_data, regenerate)

    return await _handle_blocking(chat_id, service, message_data, regenerate)


def _handle_streaming(
    request: Request,
    chat_id: str,
    service: ChatMessageService,
    message_data: MessageCreate | None,
    regenerate: bool,
) -> StreamingResponse:
    async def event_generator():
        try:
            stream_iterator = (
                service.regenerate_stream(chat_id)
                if regenerate
                else service.send_message_stream(chat_id, message_data.content)  # type: ignore (checked above)
            )

            async for event in stream_iterator:
                if await request.is_disconnected():
                    return
                yield f"data: {json.dumps(stream_event_to_dict(event))}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e!s}", exc_info=True)
            # Classify the code so the client can react (retry a rate-limit/timeout
            # vs surface a fault). Provider errors carry a user-facing message; for
            # an unexpected internal fault keep it generic (detail is logged above).
            code = classify_error(e)
            message = (
                str(e) if isinstance(e, ProviderException) else "An unexpected error occurred."
            )
            error_event = StreamEvent(type="error", message=message, code=code)
            yield f"data: {json.dumps(stream_event_to_dict(error_event))}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def _handle_blocking(
    chat_id: str,
    service: ChatMessageService,
    message_data: MessageCreate | None,
    regenerate: bool,
) -> MessageResponse:
    if regenerate:
        msg = await service.regenerate(chat_id)
        return MessageResponse.model_validate(msg)

    msg = await service.send_message(chat_id, message_data.content)  # type: ignore
    return MessageResponse.model_validate(msg)


@router.post("/suggestions", response_model=SuggestionResponse)
async def suggest_next_turn(
    chat_id: str,
    body: SuggestionRequest,
    service: ChatMessageServiceDep,
):
    """Generate next-turn suggestions for the user.

    - **reply**: several short candidate replies (rendered as clickable chips).
    - **impersonate**: one drafted user message in the user's voice, optionally
      steered by a `tone`.
    """
    suggestions = await service.generate_suggestions(
        chat_id, mode=body.mode, tone=body.tone, count=body.count
    )
    return SuggestionResponse(suggestions=suggestions)


@router.post("/title", response_model=TitleResponse)
async def generate_chat_title(chat_id: str, service: ChatMessageServiceDep):
    """Generate and persist a concise title for the chat, using the task model
    (falls back to the chat's main model when no task model is configured)."""
    title = await service.generate_title(chat_id)
    return TitleResponse(title=title)


@router.put("/{message_id}", response_model=MessageResponse)
async def edit_message(
    chat_id: str,
    message_id: str,
    body: MessageUpdate,
    service: ChatMessageServiceDep,
):
    """Edit a message's content. Recounts tokens."""
    msg = await service.edit_message(chat_id, message_id, body.content)
    return MessageResponse.model_validate(msg)


@router.get("/{message_id}/alternatives", response_model=list[AlternativeResponse])
async def list_alternatives(
    chat_id: str,
    message_id: str,
    service: ChatMessageServiceDep,
):
    """List all alternatives (swipes) for a message."""
    alts = await service.list_alternatives(chat_id, message_id)
    return [AlternativeResponse.model_validate(a) for a in alts]


@router.put("/{message_id}/alternatives/{alternative_id}/activate", response_model=MessageResponse)
async def activate_alternative(
    chat_id: str,
    message_id: str,
    alternative_id: str,
    service: ChatMessageServiceDep,
):
    """Switch the active alternative (swipe) for a message."""
    msg = await service.activate_alternative(chat_id, message_id, alternative_id)
    return MessageResponse.model_validate(msg)
