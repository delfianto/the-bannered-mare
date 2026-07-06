# API Provider Integration — Gap Analysis

> **Scope:** How SillyTavern integrates 25+ LLM API providers vs The Bannered Mare's current
> abstraction layer. Focus on architectural patterns, not 1:1 feature parity.

---

## Table of Contents

1. [The Bannered Mare — Current Architecture](#1-the-bannered-mare--current-architecture)
2. [SillyTavern — Provider Landscape](#2-sillytavern-provider-landscape)
3. [Provider Format Differences](#3-provider-format-differences)
4. [Gap Analysis](#4-gap-analysis)
5. [Reimagined Architecture](#5-reimagined-architecture)

---

## 1. The Bannered Mare — Current Architecture

### Provider System

**Database Model** (`src/core/persistence/models.py:441-565`):
- `Provider` ORM model with `name`, `provider_type`, `base_url`, `api_key_env_var`, `enabled`
- `ProviderType` enum: OPENAI, ANTHROPIC, GOOGLE, OPENROUTER, XAI, OLLAMA, CUSTOM (7 types)
- `PROVIDER_CONFIGS` dict maps each type to display name, env var, default URL, key requirement

**Single Client** (`src/provider/client.py`):
- `ProviderClient` class handles ALL providers via OpenAI-compatible protocol
- `_build_payload()` (line 76): Constructs `{"model", "messages", "stream"}` + merged parameters
- `chat_completion()` (line 120): Non-streaming, returns full response
- `chat_completion_stream()` (line 157): SSE streaming via `httpx.AsyncClient.stream()`
- Auth: Always `Authorization: Bearer <key>` header (line 133)

**Parameter System** (`src/core/persistence/models.py:283-329`):
- `ModelFamily` defines parameter schemas + defaults per family
- `Model` can override with instance-level parameters
- `_get_effective_parameters()` merges family defaults + model overrides

**Key Insight:** The Bannered Mare assumes every provider speaks OpenAI protocol. This works for
Ollama, vLLM, OpenRouter, and LiteLLM proxies — but breaks for native Anthropic, Gemini,
and Cohere APIs.

---

## 2. SillyTavern — Provider Landscape

### Architecture: Giant Switch Statement

**File:** `st/src/endpoints/backends/chat-completions.js` (2675 lines)

25+ providers handled via `CHAT_COMPLETION_SOURCES` enum and per-provider handler functions:

```
OPENAI, CLAUDE, OPENROUTER, AI21, MAKERSUITE, VERTEXAI, MISTRALAI,
CUSTOM, COHERE, PERPLEXITY, GROQ, CHUTES, ELECTRONHUB, NANOGPT,
DEEPSEEK, AIMLAPI, XAI, POLLINATIONS, MOONSHOT, FIREWORKS,
COMETAPI, AZURE_OPENAI, ZAI, SILICONFLOW
```

Each provider gets a dedicated handler function (e.g., `sendClaudeRequest()`, `sendGoogleRequest()`)
with custom request building, auth, and response normalization.

### Prompt Converters

**File:** `st/src/prompt-converters.js`

Dedicated format converters per provider:
- `convertClaudeMessages()` — OpenAI format to Anthropic `{system, messages}` with content blocks
- `convertGooglePrompt()` — OpenAI format to Gemini `{contents[{role, parts}], systemInstruction}`
- `convertCohereMessages()` — OpenAI format to Cohere v2 `{preamble, messages}`
- `convertMistralMessages()` — Minor adjustments for Mistral
- `convertAI21Messages()`, `convertXAIMessages()` — Provider-specific tweaks

### Response Normalization

ALL providers normalize responses back to OpenAI format before returning to frontend:

```javascript
// Claude response → OpenAI shape
const reply = {
    choices: [{ message: { content: responseText } }],
    content: generateResponseJson.content  // preserve original
};
```

### API Key Management

**File:** `st/src/endpoints/secrets.js`

- `SecretManager` class with 50+ secret keys
- Multi-value secrets (array per key with active flag)
- Atomic file writes, secret masking

### Parameter Allowlists

**File:** `st/src/constants.js`

Per-provider parameter filtering:
- `OPENAI_KEYS`: 13 allowed params
- `VLLM_KEYS`: 40+ params
- `OLLAMA_KEYS`: 15 params
- `OPENROUTER_KEYS`: 18 params
- `AZURE_OPENAI_KEYS`: 17 params

---

## 3. Provider Format Differences

### Why a Single Client Isn't Enough

| Aspect | OpenAI | Anthropic | Gemini | Cohere |
|--------|--------|-----------|--------|--------|
| **Auth** | `Bearer` header | `x-api-key` header + `anthropic-version` | `?key=` query param | `Bearer` header |
| **Model location** | Body `model` field | Body `model` field | **URL path** parameter | Body `model` field |
| **System prompt** | `role: "system"` message | `system` top-level field | `systemInstruction` field | `preamble` field |
| **Message format** | `{role, content}` | `{role, content: [{type, text}]}` | `{role, parts: [{text}]}` | `{role, content}` |
| **Assistant role** | `"assistant"` | `"assistant"` | `"model"` | `"assistant"` |
| **Response shape** | `choices[0].message.content` | `content[0].text` | `candidates[0].content.parts[0].text` | `message.content[0].text` |
| **Streaming** | `data: {json}\n\n` + `[DONE]` | `event: content_block_delta` | JSON array as SSE (no `[DONE]`) | `event: text-generation` |
| **Endpoint** | `/v1/chat/completions` | `/v1/messages` | `/v1beta/models/{model}:generateContent` | `/v2/chat` |

### Provider-Specific Features (Not Handled by OpenAI Protocol)

**Anthropic:**
- System prompt caching (ephemeral TTL)
- Tool use with `tool_choice` and structured output via forced tools
- Thinking mode with `budget_tokens`
- Extended context (beta header: `max-tokens-3-5-sonnet-2025-04-14`)
- Web search capability
- Beta headers: `anthropic-beta` for feature flags

**Gemini:**
- Safety settings (harassment, hate speech, sexually explicit, dangerous content)
- `generationConfig` wrapper for all sampling params
- Function calling with `functionCallingConfig`
- Response MIME types (JSON mode)
- Thinking config with budget
- Image generation with aspect ratios

**OpenRouter:**
- Provider ordering/selection
- Quantization preferences
- `HTTP-Referer` and `X-Title` tracking headers
- Fallback routing

---

## 4. Gap Analysis

### What The Bannered Mare Has (Strong Foundation)

| Area | Status |
|------|--------|
| Provider database model with type enum | Done |
| Model → ModelFamily → Provider relationship | Done |
| Parameter merging (family defaults + model overrides) | Done |
| Custom exception hierarchy (Auth, RateLimit, InvalidRequest, Timeout) | Done |
| OpenAI-compatible streaming via httpx | Done |
| Environment variable-based API key storage | Done |
| Provider CRUD with validation | Done |

### What's Missing

| Gap | Impact | Priority |
|-----|--------|----------|
| **No provider-specific adapters** — Anthropic/Gemini/Cohere APIs are NOT OpenAI-compatible | Cannot use native APIs; must rely on proxy (LiteLLM/OpenRouter) | High |
| **No message format conversion** — All messages assumed OpenAI shape | Blocks native Anthropic, Gemini integration | High |
| **No response normalization layer** — Assumes `choices[0].message.content` | Breaks for native Anthropic (`content[0].text`), Gemini (`candidates[0]`) | High |
| **No provider-specific auth strategies** — Always uses Bearer header | Gemini needs query param, Anthropic needs `x-api-key` + version header | High |
| **No parameter allowlists** — Sends ALL params to every provider | Providers reject unknown params (Ollama rejects `top_p` sometimes) | Medium |
| **No provider-specific features** — No thinking mode, safety settings, caching | Users can't access advanced features of Claude/Gemini | Medium |
| **No streaming format adaptation** — Only parses OpenAI SSE format | Anthropic and Gemini stream differently | High |
| **No multi-value API key rotation** | Single key per provider, no fallback | Low |

---

## 5. Reimagined Architecture

### Design: Adapter Pattern with Canonical Message Format

Rather than ST's giant switch statement with 25 handler functions, use a clean adapter
pattern that keeps the single-client simplicity while supporting provider-specific needs.

### Layer 1: Canonical Types (Already Partially Exists)

```
CompletionRequest:
  - messages: list[Message]        # Canonical format
  - system_prompt: str | None      # Extracted, not inline
  - model: str
  - stream: bool
  - parameters: dict[str, Any]     # Merged family + model params
  - tools: list[Tool] | None       # For function calling

CompletionResponse:
  - content: str
  - finish_reason: str
  - usage: TokenUsage
  - tool_calls: list[ToolCall] | None

StreamChunk:
  - content: str | None
  - reasoning: str | None          # For thinking mode
  - finish_reason: str | None
```

### Layer 2: Provider Adapter Protocol

```python
class ProviderAdapter(Protocol):
    def build_url(self, model: str) -> str: ...
    def build_headers(self, api_key: str) -> dict[str, str]: ...
    def build_payload(self, request: CompletionRequest) -> dict[str, Any]: ...
    def parse_response(self, data: dict) -> CompletionResponse: ...
    def parse_stream_chunk(self, line: str) -> StreamChunk | None: ...
    def filter_parameters(self, params: dict) -> dict: ...
```

### Layer 3: Concrete Adapters

**OpenAIAdapter** (baseline — handles OpenAI, OpenRouter, Groq, DeepSeek, vLLM, XAI, etc.):
- Most providers are OpenAI-compatible; this is the default
- Parameter allowlist filtering
- Standard `Bearer` auth

**AnthropicAdapter:**
- `x-api-key` + `anthropic-version` headers
- System prompt → top-level `system` field
- Messages → content blocks `[{type: "text", text: "..."}]`
- Response → `content[0].text`
- Stream → event-based (`content_block_delta`)
- Thinking mode support
- Beta header management

**GeminiAdapter:**
- API key as query parameter
- Model in URL path, not body
- System prompt → `systemInstruction` field
- Messages → `contents[{role, parts: [{text}]}]`
- Response → `candidates[0].content.parts[0].text`
- Safety settings injection
- `generationConfig` wrapper for params
- Stream → `?alt=sse` endpoint variant

**OllamaAdapter** (extends OpenAI but with local quirks):
- No auth required
- Parameter filtering (Ollama-specific keys only)
- Model pull/status checking

### Layer 4: Adapter Registry

```python
ADAPTER_REGISTRY: dict[ProviderType, type[ProviderAdapter]] = {
    ProviderType.OPENAI: OpenAIAdapter,
    ProviderType.ANTHROPIC: AnthropicAdapter,
    ProviderType.GOOGLE: GeminiAdapter,
    ProviderType.OPENROUTER: OpenAIAdapter,  # OpenAI-compatible
    ProviderType.XAI: OpenAIAdapter,         # OpenAI-compatible
    ProviderType.OLLAMA: OllamaAdapter,
    ProviderType.CUSTOM: OpenAIAdapter,      # Assume compatible
}
```

### Implementation Priority

1. **AnthropicAdapter** — High demand, completely different protocol
2. **GeminiAdapter** — Second most different, large user base
3. **Parameter filtering** — Quick win, prevents provider errors
4. **OllamaAdapter** — Minor tweaks to OpenAI adapter
5. **Provider-specific features** — Thinking mode, safety settings, caching (iterative)

### What NOT to Build

- **25+ individual provider handlers** — Most providers are OpenAI-compatible. Only build
  dedicated adapters for genuinely different protocols (Anthropic, Gemini, Cohere).
- **Secret rotation / multi-key** — Over-engineering for a self-hosted app. Env vars are fine.
- **Azure OpenAI adapter** — Azure uses OpenAI protocol with different URL pattern; handle
  via `CUSTOM` provider type with configurable base URL.
- **Provider health checking** — Not needed for single-user local deployment.
