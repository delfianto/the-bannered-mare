# Provider Landscape & Gap Analysis

> **Scope:** How SillyTavern integrates 25+ LLM API providers vs The Bannered Mare's current
> abstraction layer. Focus on architectural patterns, not 1:1 feature parity.


## Table of Contents

1. [The Bannered Mare — Current Architecture](#1-the-bannered-mare--current-architecture)
2. [SillyTavern — Provider Landscape](#2-sillytavern-provider-landscape)
3. [Provider Format Differences](#3-provider-format-differences)
4. [Gap Analysis](#4-gap-analysis)
5. [Reimagined Architecture](#5-reimagined-architecture)


## 1. The Bannered Mare — Current Architecture

### Provider System

**Database Model** (`src/core/persistence/models/provider.py`):
- `Provider` ORM model with `name`, `provider_type`, `base_url`, `api_key_env_var`, `enabled`,
  `last_synced_at`, `allowed_models`
- `ProviderType` enum: XAI, GOOGLE, OPENAI, ANTHROPIC, OPENROUTER, OLLAMA, LMSTUDIO, CUSTOM (8 types)
- `PROVIDER_CONFIGS` dict maps each type to display name, env var, default URL, key requirement

**Adapter Layer** (`src/provider/adapters/`):
- The single-client design has been replaced by an adapter pattern. Adapters are **stateless
  data transformers** — the `ProviderGateway` owns the `httpx` client, timeouts, and error handling.
- `ProviderAdapter` ABC (`adapters/base.py`) defines the hooks: `build_url()`, `build_headers()`,
  `build_payload()`, `parse_response()`, `parse_stream_line()`, and `get_timeout()`.
- Concrete adapters: `OpenAIAdapter`, `AnthropicAdapter`, `GeminiAdapter`, `OllamaAdapter`,
  `LMStudioAdapter` (the last two subclass `OpenAIAdapter`). xAI, OpenRouter, and CUSTOM all
  reuse `OpenAIAdapter`.
- Canonical types (`adapters/base.py`): `CompletionResponse`, `StreamChunk`, `TokenUsage`.
  Requests are passed as an OpenAI-format `messages` list plus a merged `parameters` dict.

**Gateway** (`src/provider/gateway.py`):
- `ProviderGateway` selects the adapter via `get_adapter(provider_type)`, builds the request
  through the adapter's hooks, and performs the HTTP call.
- `chat_completion()`: Non-streaming, returns a typed `CompletionResponse`.
- `chat_completion_stream()`: SSE streaming via `httpx.AsyncClient.stream()`, yielding `StreamChunk`s.
- `_get_effective_parameters()`: merges ModelFamily defaults → Model overrides → preset overrides.

**Parameter System** (`src/model_family/`, `src/model/`):
- `ModelFamily` defines parameter schemas + defaults per family
- `Model` can override with instance-level parameters
- `ProviderGateway._get_effective_parameters()` merges family defaults + model overrides

**Key Insight:** The Bannered Mare no longer assumes every provider speaks OpenAI protocol. The
OpenAI-compatible baseline covers Ollama, LM Studio, vLLM, OpenRouter, xAI, and similar proxies,
while native Anthropic and Gemini APIs each get a dedicated adapter.


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

### Gaps — Resolved and Remaining

Most of the gaps identified in the original single-client design have since been closed by the
adapter layer (see §1). The remaining table tracks their status.

| Gap | Impact | Status |
|-----|--------|--------|
| **Provider-specific adapters** — Anthropic/Gemini APIs are NOT OpenAI-compatible | Native APIs now supported directly | Done (`AnthropicAdapter`, `GeminiAdapter`) |
| **Message format conversion** — messages translated per provider | Native Anthropic + Gemini integration | Done (each adapter's `build_payload`) |
| **Response normalization layer** | Native shapes parsed into `CompletionResponse` | Done (each adapter's `parse_response`) |
| **Provider-specific auth strategies** | Gemini uses `?key=`, Anthropic uses `x-api-key` + version header | Done (each adapter's `build_headers`/`build_url`) |
| **Parameter allowlists / selective mapping** — each adapter extracts only the params it understands | Avoids sending unknown params | Done (e.g. `OpenAIAdapter._OPENAI_PARAMS`, Gemini `_GENERATION_CONFIG_MAP`) |
| **Provider-specific features** — thinking mode, safety settings, prompt caching | Advanced Claude/Gemini features | Done (Anthropic `thinking`/`cache_control`, Gemini `safetySettings`) |
| **Streaming format adaptation** — per-provider SSE parsing | Anthropic and Gemini stream differently | Done (each adapter's `parse_stream_line`) |
| **Multi-value API key rotation** | Single key per provider, no fallback | Not implemented (Low priority) |


## 5. Architecture (As Built)

### Design: Adapter Pattern with Canonical Message Format

Rather than ST's giant switch statement with 25 handler functions, the implemented design is a
clean adapter pattern that keeps the single-client simplicity while supporting provider-specific
needs. The sections below describe what shipped.

### Layer 1: Canonical Types (`adapters/base.py`)

Requests are not wrapped in a `CompletionRequest` object — the gateway passes an OpenAI-format
`messages` list and a merged `parameters` dict straight to the adapter's `build_payload()`. The
canonical response/streaming types are dataclasses:

```
CompletionResponse:
  - content: str
  - finish_reason: str
  - usage: TokenUsage
  - reasoning: str | None          # For thinking / reasoning models
  - raw: dict[str, Any]            # Original provider response

StreamChunk:
  - content: str | None
  - reasoning: str | None          # For thinking mode
  - finish_reason: str | None
  - usage: TokenUsage | None       # Populated on the final chunk

TokenUsage:
  - input_tokens / output_tokens / total_tokens
  - cache_read_tokens / cache_creation_tokens
```

Tool calling is not yet part of the canonical types.

### Layer 2: Provider Adapter Interface

`ProviderAdapter` is an `abc.ABC`. Adapters are stateless — they receive everything they need as
arguments and never hold provider/HTTP state:

```python
class ProviderAdapter(ABC):
    def build_url(self, base_url: str, model: str, stream: bool, api_key: str | None = None) -> str: ...
    def build_headers(self, api_key: str | None) -> dict[str, str]: ...
    def build_payload(self, messages: list[dict], model: str, stream: bool, parameters: dict) -> dict: ...
    def parse_response(self, data: dict) -> CompletionResponse: ...
    def parse_stream_line(self, line: str) -> StreamChunk | None: ...
    def get_timeout(self, model: str) -> float: ...  # non-abstract, defaults to 120.0
```

There is no separate `filter_parameters` hook — each adapter's `build_payload()` selectively
extracts only the parameters it understands.

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

**OllamaAdapter** (subclasses `OpenAIAdapter` with local-server quirks):
- No auth header
- Endpoint under `/v1/chat/completions`, longer default timeout (300s)
- Model list/load/unload/pull handled separately by the discovery client, not the adapter

**LMStudioAdapter** (subclasses `OpenAIAdapter` for LM Studio's local server):
- Optional auth (Bearer sent only when configured), longer default timeout (300s)
- Strips a trailing `/v1` from the configured base URL before appending `/v1/chat/completions`

### Layer 4: Adapter Registry (`adapters/__init__.py`)

```python
_REGISTRY: dict[ProviderType, type[ProviderAdapter]] = {
    ProviderType.OPENAI: OpenAIAdapter,
    ProviderType.ANTHROPIC: AnthropicAdapter,
    ProviderType.GOOGLE: GeminiAdapter,
    ProviderType.XAI: OpenAIAdapter,          # OpenAI-compatible
    ProviderType.OPENROUTER: OpenAIAdapter,   # OpenAI-compatible
    ProviderType.OLLAMA: OllamaAdapter,
    ProviderType.LMSTUDIO: LMStudioAdapter,
    ProviderType.CUSTOM: OpenAIAdapter,       # Assume compatible
}
```

`get_adapter(provider_type)` looks up this registry (falling back to `OpenAIAdapter`) and
instantiates the class.

### Delivered Adapters

All of the following have shipped:

1. **AnthropicAdapter** — completely different protocol (Messages API)
2. **GeminiAdapter** — generateContent API with a distinct schema
3. **Per-adapter parameter selection** — each adapter maps only the params it understands
4. **OllamaAdapter** and **LMStudioAdapter** — thin subclasses of `OpenAIAdapter` for local servers
5. **Provider-specific features** — Anthropic thinking + prompt caching, Gemini safety settings

### What NOT to Build

- **25+ individual provider handlers** — Most providers are OpenAI-compatible. Only build
  dedicated adapters for genuinely different protocols (Anthropic, Gemini, Cohere).
- **Secret rotation / multi-key** — Over-engineering for a self-hosted app. Env vars are fine.
- **Azure OpenAI adapter** — Azure uses OpenAI protocol with different URL pattern; handle
  via `CUSTOM` provider type with configurable base URL.
- **Provider health checking** — Not needed for single-user local deployment.
