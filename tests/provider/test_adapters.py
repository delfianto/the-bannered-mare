"""Unit tests for provider adapters — pure data transformation, no mocking needed."""

from src.provider.adapters.anthropic import AnthropicAdapter
from src.provider.adapters.base import TokenUsage
from src.provider.adapters.gemini import GeminiAdapter
from src.provider.adapters.ollama import OllamaAdapter
from src.provider.adapters.openai import OpenAIAdapter


class TestTokenUsage:
    def test_cache_fields_default_to_zero(self):
        usage = TokenUsage(input_tokens=10, output_tokens=5, total_tokens=15)
        assert usage.cache_read_tokens == 0
        assert usage.cache_creation_tokens == 0


class TestOpenAIAdapter:
    def setup_method(self):
        self.adapter = OpenAIAdapter()

    def test_build_url(self):
        url = self.adapter.build_url("https://api.openai.com/v1", "gpt-4o", False)
        assert url == "https://api.openai.com/v1/chat/completions"

    def test_build_headers_with_key(self):
        headers = self.adapter.build_headers("sk-test")
        assert headers["Authorization"] == "Bearer sk-test"
        assert headers["Content-Type"] == "application/json"

    def test_build_headers_without_key(self):
        headers = self.adapter.build_headers(None)
        assert "Authorization" not in headers

    def test_build_payload(self):
        messages = [{"role": "user", "content": "Hello"}]
        params = {"temperature": 0.8, "max_tokens": 100, "thinking": {"type": "disabled"}}
        payload = self.adapter.build_payload(messages, "gpt-4o", False, params)

        assert payload["model"] == "gpt-4o"
        assert payload["messages"] == messages
        assert payload["temperature"] == 0.8
        assert payload["max_tokens"] == 100
        assert "thinking" not in payload  # not in _OPENAI_PARAMS
        assert "stream" not in payload

    def test_build_payload_streaming(self):
        payload = self.adapter.build_payload([], "gpt-4o", True, {})
        assert payload["stream"] is True

    def test_parse_response(self):
        data = {
            "choices": [{"message": {"content": "Hi!"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
        }
        resp = self.adapter.parse_response(data)
        assert resp.content == "Hi!"
        assert resp.finish_reason == "stop"
        assert resp.usage.input_tokens == 5
        assert resp.usage.output_tokens == 2
        assert resp.usage.total_tokens == 7

    def test_parse_stream_line_content(self):
        line = 'data: {"choices":[{"delta":{"content":"Hello"},"finish_reason":null}]}'
        chunk = self.adapter.parse_stream_line(line)
        assert chunk is not None
        assert chunk.content == "Hello"
        assert chunk.finish_reason is None

    def test_parse_stream_line_done(self):
        chunk = self.adapter.parse_stream_line("data: [DONE]")
        assert chunk is not None
        assert chunk.finish_reason == "stop"

    def test_parse_stream_line_skip_event(self):
        assert self.adapter.parse_stream_line("event: message") is None
        assert self.adapter.parse_stream_line("") is None

    def test_parse_response_cached_tokens(self):
        data = {
            "choices": [{"message": {"content": "Hi"}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 10,
                "total_tokens": 110,
                "prompt_tokens_details": {"cached_tokens": 80},
            },
        }
        resp = self.adapter.parse_response(data)
        assert resp.usage.cache_read_tokens == 80
        assert resp.usage.cache_creation_tokens == 0

    def test_parse_response_no_cache_details(self):
        data = {
            "choices": [{"message": {"content": "Hi"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60},
        }
        resp = self.adapter.parse_response(data)
        assert resp.usage.cache_read_tokens == 0

    def test_parse_response_reasoning_content(self):
        data = {
            "choices": [
                {
                    "message": {
                        "content": "The answer is 42.",
                        "reasoning_content": "Let me think step by step...",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }
        resp = self.adapter.parse_response(data)
        assert resp.content == "The answer is 42."
        assert resp.reasoning == "Let me think step by step..."

    def test_parse_stream_reasoning_content(self):
        line = (
            'data: {"choices":[{"delta":{"reasoning_content":"thinking..."},"finish_reason":null}]}'
        )
        chunk = self.adapter.parse_stream_line(line)
        assert chunk is not None
        assert chunk.reasoning == "thinking..."
        assert chunk.content is None


class TestAnthropicAdapter:
    def setup_method(self):
        self.adapter = AnthropicAdapter()

    def test_build_url(self):
        url = self.adapter.build_url("https://api.anthropic.com/v1", "claude-sonnet-4-6", False)
        assert url == "https://api.anthropic.com/v1/messages"

    def test_build_headers(self):
        headers = self.adapter.build_headers("sk-ant-test")
        assert headers["x-api-key"] == "sk-ant-test"
        assert headers["anthropic-version"] == "2023-06-01"
        assert "Authorization" not in headers

    def test_system_extraction(self):
        messages = [
            {"role": "system", "content": "You are a pirate."},
            {"role": "system", "content": "Talk like a pirate."},
            {"role": "user", "content": "Hello"},
        ]
        payload = self.adapter.build_payload(messages, "claude-sonnet-4-6", False, {})

        # System is now a content block array with cache_control
        system = payload["system"]
        assert isinstance(system, list)
        assert len(system) == 1
        assert system[0]["type"] == "text"
        assert system[0]["text"] == "You are a pirate.\n\nTalk like a pirate."
        assert system[0]["cache_control"] == {"type": "ephemeral"}
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["role"] == "user"

    def test_max_tokens_required(self):
        payload = self.adapter.build_payload([], "claude-sonnet-4-6", False, {})
        assert payload["max_tokens"] == 4096  # default

        payload = self.adapter.build_payload([], "claude-sonnet-4-6", False, {"max_tokens": 8192})
        assert payload["max_tokens"] == 8192

    def test_temperature_clamped(self):
        payload = self.adapter.build_payload([], "claude-sonnet-4-6", False, {"temperature": 1.5})
        assert payload["temperature"] == 1.0

    def test_parse_response(self):
        data = {
            "content": [{"type": "text", "text": "Ahoy!"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 3},
        }
        resp = self.adapter.parse_response(data)
        assert resp.content == "Ahoy!"
        assert resp.finish_reason == "stop"
        assert resp.usage.input_tokens == 10

    def test_parse_response_with_thinking(self):
        data = {
            "content": [
                {"type": "thinking", "thinking": "Let me consider..."},
                {"type": "text", "text": "Here's my answer."},
            ],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }
        resp = self.adapter.parse_response(data)
        assert resp.content == "Here's my answer."
        assert resp.reasoning == "Let me consider..."

    def test_parse_stream_text_delta(self):
        line = 'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hi"}}'
        chunk = self.adapter.parse_stream_line(line)
        assert chunk is not None
        assert chunk.content == "Hi"

    def test_parse_stream_thinking_delta(self):
        line = 'data: {"type":"content_block_delta","index":0,"delta":{"type":"thinking_delta","thinking":"Let me think..."}}'
        chunk = self.adapter.parse_stream_line(line)
        assert chunk is not None
        assert chunk.reasoning == "Let me think..."
        assert chunk.content is None

    def test_parse_stream_message_stop(self):
        line = 'data: {"type":"message_stop"}'
        chunk = self.adapter.parse_stream_line(line)
        assert chunk is not None
        assert chunk.finish_reason == "stop"

    def test_parse_stream_skip_ping(self):
        line = 'data: {"type":"ping"}'
        assert self.adapter.parse_stream_line(line) is None

    def test_build_headers_includes_cache_beta(self):
        headers = self.adapter.build_headers("sk-ant-test")
        assert headers["anthropic-beta"] == "prompt-caching-2024-07-31"

    def test_parse_response_cache_tokens(self):
        data = {
            "content": [{"type": "text", "text": "Hi"}],
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 10,
                "cache_read_input_tokens": 80,
                "cache_creation_input_tokens": 20,
            },
        }
        resp = self.adapter.parse_response(data)
        assert resp.usage.cache_read_tokens == 80
        assert resp.usage.cache_creation_tokens == 20


class TestGeminiAdapter:
    def setup_method(self):
        self.adapter = GeminiAdapter()

    def test_build_url_non_streaming(self):
        url = self.adapter.build_url(
            "https://generativelanguage.googleapis.com",
            "gemini-2.5-flash",
            False,
            "AIza-test",
        )
        assert "v1beta/models/gemini-2.5-flash:generateContent" in url
        assert "key=AIza-test" in url
        assert "alt=" not in url

    def test_build_url_streaming(self):
        url = self.adapter.build_url(
            "https://generativelanguage.googleapis.com",
            "gemini-2.5-flash",
            True,
            "AIza-test",
        )
        assert "streamGenerateContent" in url
        assert "alt=sse" in url
        assert "key=AIza-test" in url

    def test_build_headers_no_auth(self):
        headers = self.adapter.build_headers("AIza-test")
        assert "Authorization" not in headers

    def test_system_extraction(self):
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        payload = self.adapter.build_payload(messages, "gemini-2.5-flash", False, {})

        assert "systemInstruction" in payload
        assert payload["systemInstruction"]["parts"][0]["text"] == "You are helpful."
        assert len(payload["contents"]) == 2
        assert payload["contents"][0]["role"] == "user"
        assert payload["contents"][1]["role"] == "model"

    def test_generation_config_nesting(self):
        params = {"temperature": 0.8, "top_p": 0.9, "max_output_tokens": 4096, "top_k": 40}
        payload = self.adapter.build_payload([], "gemini-2.5-flash", False, params)

        config = payload["generationConfig"]
        assert config["temperature"] == 0.8
        assert config["topP"] == 0.9
        assert config["maxOutputTokens"] == 4096
        assert config["topK"] == 40

    def test_max_tokens_fallback(self):
        params = {"max_tokens": 2048}
        payload = self.adapter.build_payload([], "gemini-2.5-flash", False, params)
        assert payload["generationConfig"]["maxOutputTokens"] == 2048

    def test_safety_settings(self):
        params = {
            "safety_settings": [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}]
        }
        payload = self.adapter.build_payload([], "gemini-2.5-flash", False, params)
        assert payload["safetySettings"] == params["safety_settings"]

    def test_parse_response(self):
        data = {
            "candidates": [
                {
                    "content": {"parts": [{"text": "Hello!"}], "role": "model"},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 5,
                "candidatesTokenCount": 3,
                "totalTokenCount": 8,
            },
        }
        resp = self.adapter.parse_response(data)
        assert resp.content == "Hello!"
        assert resp.finish_reason == "stop"
        assert resp.usage.total_tokens == 8

    def test_parse_stream_line(self):
        line = 'data: {"candidates":[{"content":{"parts":[{"text":"Hi"}]}}]}'
        chunk = self.adapter.parse_stream_line(line)
        assert chunk is not None
        assert chunk.content == "Hi"

    def test_parse_response_cached_tokens(self):
        data = {
            "candidates": [
                {
                    "content": {"parts": [{"text": "Hi"}], "role": "model"},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 100,
                "candidatesTokenCount": 5,
                "totalTokenCount": 105,
                "cachedContentTokenCount": 90,
            },
        }
        resp = self.adapter.parse_response(data)
        assert resp.usage.cache_read_tokens == 90
        assert resp.usage.cache_creation_tokens == 0

    def test_parse_response_thought_parts(self):
        data = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Let me think...", "thought": True},
                            {"text": "The answer is 42."},
                        ],
                        "role": "model",
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 20,
                "totalTokenCount": 30,
            },
        }
        resp = self.adapter.parse_response(data)
        assert resp.content == "The answer is 42."
        assert resp.reasoning == "Let me think..."


class TestOllamaAdapter:
    def setup_method(self):
        self.adapter = OllamaAdapter()

    def test_build_url(self):
        url = self.adapter.build_url("http://localhost:11434", "llama3", False)
        assert url == "http://localhost:11434/v1/chat/completions"

    def test_no_auth_headers(self):
        headers = self.adapter.build_headers("should-be-ignored")
        assert "Authorization" not in headers

    def test_timeout(self):
        assert self.adapter.get_timeout("llama3") == 300.0
