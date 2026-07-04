"""Integration tests for real LLM provider APIs.

Each test makes a real HTTP call. Tests are skipped when the
corresponding API key is not present in the environment.

Run with: pytest tests/integration/ -v
"""

import pytest
from src.provider.adapters import CompletionResponse, StreamChunk

from tests.integration.conftest import (
    SIMPLE_MESSAGES,
    has_anthropic_key,
    has_google_key,
    has_lmstudio,
    has_ollama,
    has_openai_key,
    has_openrouter_key,
)

# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------


@has_openai_key
class TestOpenAI:
    @pytest.mark.asyncio
    async def test_completion(self, openai_gateway):
        response = await openai_gateway.chat_completion(SIMPLE_MESSAGES)

        assert isinstance(response, CompletionResponse)
        assert len(response.content) > 0
        assert response.finish_reason in ("stop", "end_turn")
        assert response.usage.input_tokens > 0
        assert response.usage.output_tokens > 0

    @pytest.mark.asyncio
    async def test_streaming(self, openai_gateway):
        chunks: list[StreamChunk] = []
        async for chunk in openai_gateway.chat_completion_stream(SIMPLE_MESSAGES):
            chunks.append(chunk)

        content_chunks = [c for c in chunks if c.content]
        assert len(content_chunks) > 0

        full_text = "".join(c.content for c in content_chunks if c.content)
        assert len(full_text) > 0

        final = chunks[-1]
        assert final.finish_reason is not None


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------


@has_anthropic_key
class TestAnthropic:
    @pytest.mark.asyncio
    async def test_completion(self, anthropic_gateway):
        response = await anthropic_gateway.chat_completion(SIMPLE_MESSAGES)

        assert isinstance(response, CompletionResponse)
        assert len(response.content) > 0
        assert response.finish_reason in ("stop", "end_turn")
        assert response.usage.input_tokens > 0
        assert response.usage.output_tokens > 0

    @pytest.mark.asyncio
    async def test_streaming(self, anthropic_gateway):
        chunks: list[StreamChunk] = []
        async for chunk in anthropic_gateway.chat_completion_stream(SIMPLE_MESSAGES):
            chunks.append(chunk)

        content_chunks = [c for c in chunks if c.content]
        assert len(content_chunks) > 0

        full_text = "".join(c.content for c in content_chunks if c.content)
        assert len(full_text) > 0

    @pytest.mark.asyncio
    async def test_system_prompt(self, anthropic_gateway):
        """Verify system prompt extraction works end-to-end."""
        messages = [
            {"role": "system", "content": "You are a pirate. Always say 'Arrr'."},
            {"role": "user", "content": "Say your catchphrase."},
        ]
        response = await anthropic_gateway.chat_completion(messages)

        assert isinstance(response, CompletionResponse)
        assert len(response.content) > 0


# ---------------------------------------------------------------------------
# Google Gemini
# ---------------------------------------------------------------------------


@has_google_key
class TestGemini:
    @pytest.mark.asyncio
    async def test_completion(self, gemini_gateway):
        response = await gemini_gateway.chat_completion(SIMPLE_MESSAGES)

        assert isinstance(response, CompletionResponse)
        assert len(response.content) > 0
        assert response.finish_reason == "stop"
        assert response.usage.total_tokens > 0

    @pytest.mark.asyncio
    async def test_streaming(self, gemini_gateway):
        chunks: list[StreamChunk] = []
        async for chunk in gemini_gateway.chat_completion_stream(SIMPLE_MESSAGES):
            chunks.append(chunk)

        content_chunks = [c for c in chunks if c.content]
        assert len(content_chunks) > 0

        full_text = "".join(c.content for c in content_chunks if c.content)
        assert len(full_text) > 0

    @pytest.mark.asyncio
    async def test_system_prompt(self, gemini_gateway):
        """Verify systemInstruction extraction works end-to-end."""
        messages = [
            {"role": "system", "content": "You are a pirate. Always say 'Arrr'."},
            {"role": "user", "content": "Say your catchphrase."},
        ]
        response = await gemini_gateway.chat_completion(messages)

        assert isinstance(response, CompletionResponse)
        assert len(response.content) > 0


# ---------------------------------------------------------------------------
# OpenRouter
# ---------------------------------------------------------------------------


@has_openrouter_key
class TestOpenRouter:
    @pytest.mark.asyncio
    async def test_completion(self, openrouter_gateway):
        response = await openrouter_gateway.chat_completion(SIMPLE_MESSAGES)

        assert isinstance(response, CompletionResponse)
        assert len(response.content) > 0

    @pytest.mark.asyncio
    async def test_streaming(self, openrouter_gateway):
        chunks: list[StreamChunk] = []
        async for chunk in openrouter_gateway.chat_completion_stream(SIMPLE_MESSAGES):
            chunks.append(chunk)

        content_chunks = [c for c in chunks if c.content]
        assert len(content_chunks) > 0

        full_text = "".join(c.content for c in content_chunks if c.content)
        assert len(full_text) > 0


# ---------------------------------------------------------------------------
# Ollama (local)
# ---------------------------------------------------------------------------


@has_ollama
class TestOllama:
    @pytest.mark.asyncio
    async def test_completion(self, ollama_gateway):
        response = await ollama_gateway.chat_completion(SIMPLE_MESSAGES)

        assert isinstance(response, CompletionResponse)
        assert len(response.content) > 0
        assert response.finish_reason in ("stop", "length")

    @pytest.mark.asyncio
    async def test_streaming(self, ollama_gateway):
        chunks: list[StreamChunk] = []
        async for chunk in ollama_gateway.chat_completion_stream(SIMPLE_MESSAGES):
            chunks.append(chunk)

        content_chunks = [c for c in chunks if c.content]
        assert len(content_chunks) > 0

        full_text = "".join(c.content for c in content_chunks if c.content)
        assert len(full_text) > 0

    @pytest.mark.asyncio
    async def test_system_prompt(self, ollama_gateway):
        """Verify system prompt works through OllamaAdapter (OpenAI-compat)."""
        messages = [
            {"role": "system", "content": "You are a pirate. Always say 'Arrr'."},
            {"role": "user", "content": "Say your catchphrase."},
        ]
        response = await ollama_gateway.chat_completion(messages)

        assert isinstance(response, CompletionResponse)
        assert len(response.content) > 0


# ---------------------------------------------------------------------------
# LM Studio (local)
# ---------------------------------------------------------------------------


@has_lmstudio
class TestLMStudio:
    @pytest.mark.asyncio
    async def test_completion(self, lmstudio_gateway):
        response = await lmstudio_gateway.chat_completion(SIMPLE_MESSAGES)

        assert isinstance(response, CompletionResponse)
        assert len(response.content) > 0
        assert response.finish_reason in ("stop", "length")

    @pytest.mark.asyncio
    async def test_streaming(self, lmstudio_gateway):
        chunks: list[StreamChunk] = []
        async for chunk in lmstudio_gateway.chat_completion_stream(SIMPLE_MESSAGES):
            chunks.append(chunk)

        content_chunks = [c for c in chunks if c.content]
        assert len(content_chunks) > 0

        full_text = "".join(c.content for c in content_chunks if c.content)
        assert len(full_text) > 0

    @pytest.mark.asyncio
    async def test_system_prompt(self, lmstudio_gateway):
        """Verify system prompt works through LMStudio (OpenAI-compat)."""
        messages = [
            {"role": "system", "content": "You are a pirate. Always say 'Arrr'."},
            {"role": "user", "content": "Say your catchphrase."},
        ]
        response = await lmstudio_gateway.chat_completion(messages)

        assert isinstance(response, CompletionResponse)
        assert len(response.content) > 0
