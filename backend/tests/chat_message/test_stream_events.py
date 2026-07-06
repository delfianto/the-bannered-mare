"""Unit tests for StreamEvent dataclass and serialization."""

from src.chat_message.schemas import StreamEvent, stream_event_to_dict


class TestStreamEvent:
    def test_text_event_omits_none_fields(self):
        event = StreamEvent(type="text", content="Hello")
        d = stream_event_to_dict(event)
        assert d == {"type": "text", "content": "Hello"}
        assert "message_id" not in d
        assert "finish_reason" not in d

    def test_start_event(self):
        event = StreamEvent(type="start", message_id="abc123")
        d = stream_event_to_dict(event)
        assert d == {"type": "start", "message_id": "abc123"}

    def test_usage_event_includes_all_token_fields(self):
        event = StreamEvent(type="usage", input_tokens=100, output_tokens=50, total_tokens=150)
        d = stream_event_to_dict(event)
        assert d == {
            "type": "usage",
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
        }

    def test_done_event(self):
        event = StreamEvent(type="done", finish_reason="stop")
        d = stream_event_to_dict(event)
        assert d == {"type": "done", "finish_reason": "stop"}

    def test_error_event(self):
        event = StreamEvent(type="error", message="Rate limit hit", code="rate_limit")
        d = stream_event_to_dict(event)
        assert d == {"type": "error", "message": "Rate limit hit", "code": "rate_limit"}

    def test_reasoning_event(self):
        event = StreamEvent(type="reasoning", content="Let me think...")
        d = stream_event_to_dict(event)
        assert d == {"type": "reasoning", "content": "Let me think..."}
