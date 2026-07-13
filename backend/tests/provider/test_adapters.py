"""Unit tests for provider adapters — pure data transformation, no mocking needed."""

from src.core.persistence.enums import ProviderType
from src.provider.adapters import get_adapter
from src.provider.adapters.anthropic import AnthropicAdapter
from src.provider.adapters.base import TokenUsage
from src.provider.adapters.gemini import GeminiAdapter
from src.provider.adapters.lmstudio import LMStudioAdapter, strip_v1_suffix
from src.provider.adapters.ollama import OllamaAdapter
from src.provider.adapters.openai import OpenAIAdapter
from src.provider.adapters.openrouter import OpenRouterAdapter


class TestTokenUsage:
    def test_cache_fields_default_to_zero(self):
        usage = TokenUsage(input_tokens=10, output_tokens=5, total_tokens=15)
        assert usage.cache_read_tokens == 0
        assert usage.cache_creation_tokens == 0

    def test_merge_none_returns_self(self):
        usage = TokenUsage(input_tokens=10, output_tokens=5)
        assert usage.merge(None) is usage

    def test_merge_takes_max_per_field(self):
        a = TokenUsage(input_tokens=10, output_tokens=5, cache_read_tokens=80)
        b = TokenUsage(input_tokens=12, output_tokens=3, cache_creation_tokens=20)
        merged = a.merge(b)
        assert merged.input_tokens == 12
        assert merged.output_tokens == 5
        assert merged.cache_read_tokens == 80
        assert merged.cache_creation_tokens == 20

    def test_merge_does_not_clobber_with_zeros(self):
        # message_delta carries output only (input=0); must not zero out input.
        a = TokenUsage(input_tokens=100, cache_read_tokens=80, cache_creation_tokens=20)
        b = TokenUsage(output_tokens=50)
        merged = a.merge(b)
        assert merged.input_tokens == 100
        assert merged.output_tokens == 50
        assert merged.cache_read_tokens == 80
        assert merged.cache_creation_tokens == 20


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

    def test_build_payload_forwards_extra_samplers(self):
        params = {
            "top_k": 40,
            "min_p": 0.05,
            "top_a": 0.2,
            "repetition_penalty": 1.1,
            "repeat_penalty": 1.15,
            "verbosity": "low",
            "agent_count": 4,
        }
        payload = self.adapter.build_payload([], "some/model", False, params)
        assert payload["top_k"] == 40
        assert payload["min_p"] == 0.05
        assert payload["top_a"] == 0.2
        assert payload["repetition_penalty"] == 1.1
        assert payload["repeat_penalty"] == 1.15
        assert payload["verbosity"] == "low"
        assert payload["agent_count"] == 4

    def test_thinking_maps_to_openrouter_reasoning(self):
        payload = self.adapter.build_payload(
            [], "z-ai/glm-4.7", False, {"thinking": {"type": "enabled"}}
        )
        assert payload["reasoning"] == {"enabled": True}
        assert "thinking" not in payload  # transformed, not passed raw

    def test_thinking_disabled_maps_to_reasoning(self):
        payload = self.adapter.build_payload(
            [], "minimax/minimax-m3", False, {"thinking": {"type": "disabled"}}
        )
        assert payload["reasoning"] == {"enabled": False}

    def test_reasoning_effort_suppresses_thinking_map(self):
        # When effort is set it already controls reasoning; don't also emit the object.
        params = {"reasoning_effort": "high", "thinking": {"type": "enabled"}}
        payload = self.adapter.build_payload([], "z-ai/glm-5", False, params)
        assert payload["reasoning_effort"] == "high"
        assert "reasoning" not in payload

    def test_minimize_reasoning_forces_effort_none(self):
        # Authoritative over any graded value/reasoning object the params carry.
        params = {"reasoning_effort": "high", "thinking": {"type": "enabled"}}
        payload = self.adapter.build_payload([], "gemma", False, params, minimize_reasoning=True)
        assert payload["reasoning_effort"] == "none"
        assert "reasoning" not in payload

    def test_empty_choices_normalized_to_content_filter(self):
        # A hard block can return 200 with choices:[] — must not IndexError, and
        # should surface a filter terminal for the completion classifier.
        resp = self.adapter.parse_response({"choices": [], "usage": {}})
        assert resp.content == ""
        assert resp.finish_reason == "content_filter"

    def test_null_content_preserved_as_empty(self):
        # DeepSeek soft-filter: content null, finish stop → empty string, stop.
        resp = self.adapter.parse_response(
            {"choices": [{"message": {"content": None}, "finish_reason": "stop"}]}
        )
        assert resp.content == ""
        assert resp.finish_reason == "stop"

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


class TestOpenRouterAdapter:
    def setup_method(self):
        self.adapter = OpenRouterAdapter()

    def test_registry_maps_openrouter_to_this_adapter(self):
        assert isinstance(get_adapter(ProviderType.OPENROUTER), OpenRouterAdapter)

    def test_minimize_reasoning_uses_reasoning_enabled_false(self):
        # OpenRouter's universal disable — NOT reasoning_effort "none" (which its
        # open-weight models like Kimi, that only accept low/med/high, would reject).
        params = {"reasoning_effort": "high", "temperature": 0.7}
        payload = self.adapter.build_payload(
            [], "moonshotai/kimi-k2.6", False, params, minimize_reasoning=True
        )
        assert payload["reasoning"] == {"enabled": False}
        assert "reasoning_effort" not in payload
        assert payload["temperature"] == 0.7  # other params still forwarded

    def test_inherits_openai_wire_format(self):
        # Sanity: still an OpenAI-compatible /chat/completions body.
        payload = self.adapter.build_payload([{"role": "user", "content": "hi"}], "m", False, {})
        assert payload["model"] == "m"
        assert payload["messages"] == [{"role": "user", "content": "hi"}]


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

    def test_temperature_and_top_p_mutually_exclusive(self):
        # Claude 400s if both are present — prefer temperature, drop top_p.
        payload = self.adapter.build_payload(
            [], "claude-haiku-4-5", False, {"temperature": 0.7, "top_p": 0.9}
        )
        assert payload["temperature"] == 0.7
        assert "top_p" not in payload

    def test_top_p_used_when_temperature_absent(self):
        payload = self.adapter.build_payload([], "claude-haiku-4-5", False, {"top_p": 0.9})
        assert payload["top_p"] == 0.9
        assert "temperature" not in payload

    def test_minimize_reasoning_disables_thinking(self):
        # Authoritative over a forwarded thinking mode and adaptive-effort config.
        params = {"thinking": {"type": "enabled"}, "effort": "high"}
        payload = self.adapter.build_payload(
            [], "claude-opus-4-8", False, params, minimize_reasoning=True
        )
        assert payload["thinking"] == {"type": "disabled"}
        assert "output_config" not in payload

    def test_refusal_stop_reason_normalized_to_content_filter(self):
        data = {
            "content": [{"type": "text", "text": "I can't help with that."}],
            "stop_reason": "refusal",
            "usage": {"input_tokens": 5, "output_tokens": 6},
        }
        assert self.adapter.parse_response(data).finish_reason == "content_filter"

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

    def test_build_headers_includes_beta_flags(self):
        headers = self.adapter.build_headers("sk-ant-test")
        betas = headers["anthropic-beta"].split(",")
        assert "prompt-caching-2024-07-31" in betas
        assert "effort-2025-11-24" in betas

    def test_effort_maps_to_output_config(self):
        payload = self.adapter.build_payload([], "claude-opus-4-6", False, {"effort": "high"})
        assert payload["output_config"] == {"effort": "high"}

    def test_metadata_forwarded(self):
        payload = self.adapter.build_payload(
            [], "claude-opus-4-5", False, {"metadata": {"user_id": "u1"}}
        )
        assert payload["metadata"] == {"user_id": "u1"}

    def test_thinking_adaptive_forwarded(self):
        payload = self.adapter.build_payload(
            [], "claude-sonnet-5", False, {"thinking": {"type": "adaptive"}}
        )
        assert payload["thinking"] == {"type": "adaptive"}

    def test_thinking_disabled_forwarded(self):
        payload = self.adapter.build_payload(
            [], "claude-opus-4-6", False, {"thinking": {"type": "disabled"}}
        )
        assert payload["thinking"] == {"type": "disabled"}

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

    def test_post_history_system_converted_to_user(self):
        """A system message after the first user/assistant turn becomes a user
        [System note] turn, not hoisted into the cached system block."""
        messages = [
            {"role": "system", "content": "You are a pirate."},
            {"role": "user", "content": "Hello"},
            {"role": "system", "content": "Relevant context from RAG."},
            {"role": "system", "content": "Stay in character."},
        ]
        payload = self.adapter.build_payload(messages, "claude-sonnet-4-6", False, {})

        system = payload["system"]
        assert len(system) == 1
        assert system[0]["text"] == "You are a pirate."
        assert system[0]["cache_control"] == {"type": "ephemeral"}

        msgs = payload["messages"]
        # Only one user turn + the [System note] content merged into it (consecutive
        # same-role after conversion). The last message gets the history breakpoint,
        # so its content is block form — extract the text.
        assert all(m["role"] == "user" for m in msgs)
        last_text = msgs[-1]["content"][0]["text"]
        assert "Hello" in last_text
        assert "[System note]\nRelevant context from RAG." in last_text
        assert "Stay in character." in last_text

    def test_leading_system_run_concatenated_and_cached(self):
        """Multiple leading system messages are joined into one cached system block."""
        messages = [
            {"role": "system", "content": "Rule one."},
            {"role": "system", "content": "Rule two."},
            {"role": "user", "content": "Hi"},
        ]
        payload = self.adapter.build_payload(messages, "claude-sonnet-4-6", False, {})
        assert payload["system"][0]["text"] == "Rule one.\n\nRule two."
        assert payload["system"][0]["cache_control"] == {"type": "ephemeral"}

    def test_consecutive_same_role_merged(self):
        """Adjacent user messages (e.g. user history + converted RAG) are merged —
        Anthropic requires alternating user/assistant roles."""
        messages = [
            {"role": "system", "content": "System."},
            {"role": "user", "content": "Question"},
            {"role": "system", "content": "RAG note."},
        ]
        payload = self.adapter.build_payload(messages, "claude-sonnet-4-6", False, {})
        msgs = payload["messages"]
        # All three non-system turns collapse into one user turn; the last message
        # gets the history breakpoint so its content is block form.
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        text = msgs[0]["content"][0]["text"]
        assert "Question" in text
        assert "[System note]" in text

    def test_last_message_has_history_breakpoint(self):
        """The last chat message is converted to block form with cache_control —
        the second cache breakpoint so prior turns are a cache read next turn."""
        messages = [
            {"role": "system", "content": "System."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        payload = self.adapter.build_payload(messages, "claude-sonnet-4-6", False, {})
        last = payload["messages"][-1]
        assert isinstance(last["content"], list)
        assert last["content"][0]["type"] == "text"
        assert last["content"][0]["text"] == "Hi there"
        assert last["content"][0]["cache_control"] == {"type": "ephemeral"}

    def test_breakpoint_count_under_limit(self):
        """Total cache_control breakpoints ≤ 4 (Anthropic limit): one on the
        system block + one on the last message."""
        messages = [
            {"role": "system", "content": "System."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "Bye"},
        ]
        payload = self.adapter.build_payload(messages, "claude-sonnet-4-6", False, {})

        count = 0
        if "system" in payload:
            for block in payload["system"]:
                if "cache_control" in block:
                    count += 1
        for msg in payload["messages"]:
            if isinstance(msg["content"], list):
                for block in msg["content"]:
                    if "cache_control" in block:
                        count += 1
        assert count <= 4

    def test_no_messages_no_breakpoint(self):
        """Empty messages list produces no breakpoint and doesn't error."""
        payload = self.adapter.build_payload([], "claude-sonnet-4-6", False, {})
        assert payload["messages"] == []

    def test_parse_stream_message_start_usage(self):
        """message_start carries input + cache usage — must be captured for
        streaming audit (was silently dropped before)."""
        line = (
            'data: {"type":"message_start","message":{"usage":'
            '{"input_tokens":100,"cache_read_input_tokens":80,'
            '"cache_creation_input_tokens":20,"output_tokens":0}}}'
        )
        chunk = self.adapter.parse_stream_line(line)
        assert chunk is not None
        assert chunk.usage is not None
        assert chunk.usage.input_tokens == 100
        assert chunk.usage.cache_read_tokens == 80
        assert chunk.usage.cache_creation_tokens == 20

    def test_parse_stream_message_start_no_usage(self):
        """message_start without a usage block returns None (skip)."""
        line = 'data: {"type":"message_start","message":{}}'
        assert self.adapter.parse_stream_line(line) is None


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

    def test_thinking_budget_forwarded(self):
        payload = self.adapter.build_payload([], "gemini-2.5-pro", False, {"thinking_budget": 2048})
        assert payload["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 2048}

    def test_thinking_level_forwarded(self):
        payload = self.adapter.build_payload([], "gemini-3-pro", False, {"thinking_level": "high"})
        assert payload["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "high"}

    def test_prompt_block_normalized_to_content_filter(self):
        # A prompt-level block returns no candidate; the reason is under
        # promptFeedback.blockReason and must surface as a filter terminal.
        data = {"candidates": [], "promptFeedback": {"blockReason": "SAFETY"}}
        resp = self.adapter.parse_response(data)
        assert resp.content == ""
        assert resp.finish_reason == "content_filter"

    def test_minimize_reasoning_uses_declared_control(self):
        # 2.5 disables via budget 0; 3.x drops to the minimal level. Authoritative
        # over whatever level/budget the params carry.
        budget = self.adapter.build_payload(
            [], "gemini-2.5-pro", False, {"thinking_budget": 2048}, minimize_reasoning=True
        )
        assert budget["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 0}
        level = self.adapter.build_payload(
            [], "gemini-3-pro", False, {"thinking_level": "high"}, minimize_reasoning=True
        )
        assert level["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "minimal"}

    def test_media_resolution_forwarded(self):
        payload = self.adapter.build_payload(
            [], "gemini-3-pro", False, {"media_resolution": "MEDIA_RESOLUTION_HIGH"}
        )
        assert payload["generationConfig"]["mediaResolution"] == "MEDIA_RESOLUTION_HIGH"

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


class TestLMStudioAdapter:
    def setup_method(self):
        self.adapter = LMStudioAdapter()

    def test_build_url_bare_host(self):
        url = self.adapter.build_url("http://localhost:1234", "llama-3", False)
        assert url == "http://localhost:1234/v1/chat/completions"

    def test_build_url_does_not_double_v1_suffix(self):
        url = self.adapter.build_url("http://localhost:1234/v1", "llama-3", False)
        assert url == "http://localhost:1234/v1/chat/completions"

    def test_build_url_strips_trailing_slash(self):
        url = self.adapter.build_url("http://localhost:1234/v1/", "llama-3", False)
        assert url == "http://localhost:1234/v1/chat/completions"

    def test_timeout(self):
        assert self.adapter.get_timeout("llama-3") == 300.0


class TestStripV1Suffix:
    def test_bare_host_unchanged(self):
        assert strip_v1_suffix("http://localhost:1234") == "http://localhost:1234"

    def test_strips_v1_suffix(self):
        assert strip_v1_suffix("http://localhost:1234/v1") == "http://localhost:1234"

    def test_strips_trailing_slash_and_v1(self):
        assert strip_v1_suffix("http://localhost:1234/v1/") == "http://localhost:1234"
