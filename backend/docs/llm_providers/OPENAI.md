# OpenAI Chat Completions API — Deep Analysis for Multi-Provider Architecture

> **Source:** OpenAI OpenAPI spec v2.3.0 (`openai/openai-openapi`, `manual_spec` branch)
> **Endpoint:** `POST /v1/chat/completions`
> **Goal:** Define what Candlekeep must implement to fully support the OpenAI API, and
> architect it so Anthropic, Google Gemini, and OpenRouter can be added modularly.

---

## Table of Contents

1. [API Overview](#1-api-overview)
2. [Authentication](#2-authentication)
3. [Request Schema — Complete Reference](#3-request-schema)
4. [Message Types — Complete Reference](#4-message-types)
5. [Response Schema — Complete Reference](#5-response-schema)
6. [Streaming Schema — Complete Reference](#6-streaming-schema)
7. [Tool Calling](#7-tool-calling)
8. [Response Formats (Structured Output)](#8-response-formats)
9. [Models Endpoint](#9-models-endpoint)
10. [What Candlekeep Currently Implements](#10-current-implementation)
11. [Gap Analysis](#11-gap-analysis)
12. [Multi-Provider Architecture Design](#12-multi-provider-architecture)
13. [OpenAI Adapter — Implementation Spec](#13-openai-adapter-spec)
14. [Shared Abstractions (Provider-Agnostic)](#14-shared-abstractions)
15. [Implementation Plan](#15-implementation-plan)

---

## 1. API Overview

**Base URL:** `https://api.openai.com/v1`

**Endpoint:** `POST /chat/completions`

**Purpose:** Given a list of messages (conversation history), generate a model response.
Supports text, vision (images), audio I/O, tool/function calling, structured output, streaming,
and reasoning models.

**Auth:** Bearer token via `Authorization: Bearer <API_KEY>` header.

---

## 2. Authentication

```
Authorization: Bearer sk-...
```

- API keys are confidential, never exposed client-side
- Organization header optional: `OpenAI-Organization: org-...`
- Project header optional: `OpenAI-Project: proj-...`

**For Candlekeep:** API keys are stored as environment variable names in the Provider model.
The current `ProviderClient` reads the key via `provider.get_api_key()`. This pattern works.

---

## 3. Request Schema

The `CreateChatCompletionRequest` is composed from two schemas:
- `ModelResponseProperties` (base: temperature, top_p, user, service_tier, metadata)
- Chat-specific properties (messages, model, stream, tools, etc.)

### 3.1 Complete Parameter Reference

#### Required Parameters

| Parameter | Type | Description |
|---|---|---|
| `model` | string | Model ID (e.g., `gpt-4o`, `o3`, `gpt-4o-mini`) |
| `messages` | array | Conversation messages (min 1 item). See [Section 4](#4-message-types). |

#### Generation Parameters

| Parameter | Type | Default | Constraints | Description |
|---|---|---|---|---|
| `temperature` | number \| null | `1` | 0 to 2 | Sampling temperature. Higher = more random. |
| `top_p` | number \| null | `1` | 0 to 1 | Nucleus sampling. 0.1 = top 10% probability mass. |
| `frequency_penalty` | number \| null | `0` | -2 to 2 | Penalize tokens by frequency in text so far. |
| `presence_penalty` | number \| null | `0` | -2 to 2 | Penalize tokens that appear in text so far. |
| `max_completion_tokens` | integer \| null | - | - | Upper bound for output tokens (includes reasoning tokens). **Preferred over `max_tokens`.** |
| `max_tokens` | integer \| null | - | - | **Deprecated.** Use `max_completion_tokens`. Not compatible with o-series models. |
| `n` | integer \| null | `1` | 1 to 128 | Number of completion choices to generate (for swiping). |
| `seed` | integer \| null | - | -2^63 to 2^63 | Deterministic sampling seed (beta). Best-effort, not guaranteed. |
| `stop` | string \| string[] \| null | `null` | Up to 4 sequences | Stop sequences. Not supported with o3/o4-mini. |
| `logit_bias` | object \| null | `null` | Values: -100 to 100 | Map of token IDs to bias values. |
| `logprobs` | boolean \| null | `false` | - | Return log probabilities of output tokens. |
| `top_logprobs` | integer \| null | - | 0 to 20 | Number of top logprobs per position. Requires `logprobs=true`. |

#### Reasoning Parameters (o-series models)

| Parameter | Type | Default | Enum Values | Description |
|---|---|---|---|---|
| `reasoning_effort` | string \| null | `"medium"` | `low`, `medium`, `high` | Constrain reasoning effort. Lower = faster + fewer reasoning tokens. |

#### Output Control

| Parameter | Type | Default | Description |
|---|---|---|---|
| `response_format` | object | - | Force output format: `text`, `json_object`, or `json_schema`. See [Section 8](#8-response-formats). |
| `modalities` | string[] \| null | `["text"]` | Output types: `["text"]` or `["text", "audio"]`. |
| `audio` | object \| null | - | Audio output config: `voice` (enum) + `format` (wav/aac/mp3/flac/opus/pcm16). Required when `modalities` includes `audio`. |
| `prediction` | object \| null | - | Predicted Output for fast regeneration of known content. |

#### Streaming

| Parameter | Type | Default | Description |
|---|---|---|---|
| `stream` | boolean \| null | `false` | Enable Server-Sent Events streaming. |
| `stream_options` | object \| null | `null` | Only when `stream=true`. Properties: `include_usage` (boolean) — adds a final chunk with token usage stats. |

#### Tool / Function Calling

| Parameter | Type | Description |
|---|---|---|
| `tools` | array | List of tools (max 128). Currently only `function` type. See [Section 7](#7-tool-calling). |
| `tool_choice` | string \| object | `none`, `auto`, `required`, or `{"type": "function", "function": {"name": "..."}}`. |
| `parallel_tool_calls` | boolean | Allow model to call multiple tools in parallel. |
| `functions` | array | **Deprecated.** Use `tools`. |
| `function_call` | string \| object | **Deprecated.** Use `tool_choice`. |

#### Platform / Billing

| Parameter | Type | Default | Description |
|---|---|---|---|
| `user` | string | - | End-user identifier for abuse monitoring. |
| `service_tier` | string \| null | `"auto"` | Latency tier: `auto`, `default`, `flex`. |
| `store` | boolean \| null | `false` | Store output for distillation/evals. |
| `metadata` | object \| null | - | Key-value metadata (max 16 pairs, key max 64 chars, value max 512 chars). |

#### Web Search (new)

| Parameter | Type | Description |
|---|---|---|
| `web_search_options` | object | Enable web search tool. Properties: `user_location` (object with `type: "approximate"`, `approximate`: lat/lng/etc), `search_context_size` (enum). |

---

## 4. Message Types

The `messages` array accepts 6 message types (discriminated by `role`):

### 4.1 System Message

```json
{
  "role": "system",
  "content": "string" | [{"type": "text", "text": "..."}],
  "name": "optional_participant_name"
}
```

Developer instructions the model should follow. For o-series models, use `developer` instead.

### 4.2 Developer Message

```json
{
  "role": "developer",
  "content": "string" | [{"type": "text", "text": "..."}],
  "name": "optional_participant_name"
}
```

Same as system but for o-series (o1, o3, o4-mini). These models don't accept `system` role.

### 4.3 User Message

```json
{
  "role": "user",
  "content": "string" | [content_part, ...],
  "name": "optional_participant_name"
}
```

**Content parts** (for multimodal):

| Type | Fields | Use |
|---|---|---|
| `text` | `type: "text"`, `text: string` | Text content |
| `image_url` | `type: "image_url"`, `image_url: {url, detail?}` | Vision input. `detail`: `auto`/`low`/`high` |
| `input_audio` | `type: "input_audio"`, `input_audio: {data, format}` | Audio input. Base64 encoded. Format: `wav`/`mp3` |
| `file` | `type: "file"`, `file: {file_id?, file_data?, filename?}` | File input (uploaded or base64) |

### 4.4 Assistant Message

```json
{
  "role": "assistant",
  "content": "string" | [content_part, ...] | null,
  "name": "optional_participant_name",
  "refusal": "string | null",
  "tool_calls": [tool_call, ...],
  "audio": {"id": "..."},
  "function_call": {...}  // deprecated
}
```

For conversation history replay — includes the model's previous responses including any
tool calls it made.

### 4.5 Tool Message

```json
{
  "role": "tool",
  "content": "string" | [{"type": "text", "text": "..."}],
  "tool_call_id": "call_abc123"
}
```

Result of a tool/function call. Must reference the `tool_call_id` from the assistant's tool call.

### 4.6 Function Message (Deprecated)

```json
{
  "role": "function",
  "content": "string",
  "name": "function_name"
}
```

Deprecated in favor of tool messages. Included for backwards compatibility.

---

## 5. Response Schema

### 5.1 `CreateChatCompletionResponse`

```json
{
  "id": "chatcmpl-B9MHD...",
  "object": "chat.completion",
  "created": 1741570283,
  "model": "gpt-4o-2024-08-06",
  "service_tier": "default",
  "system_fingerprint": "fp_44709d6fcb",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you?",
        "refusal": null,
        "annotations": [],
        "tool_calls": [],
        "audio": null
      },
      "logprobs": null,
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 8,
    "total_tokens": 20,
    "prompt_tokens_details": {
      "cached_tokens": 0,
      "audio_tokens": 0
    },
    "completion_tokens_details": {
      "reasoning_tokens": 0,
      "audio_tokens": 0,
      "accepted_prediction_tokens": 0,
      "rejected_prediction_tokens": 0
    }
  }
}
```

### 5.2 Field Reference

#### Top-Level Response

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique completion ID |
| `object` | `"chat.completion"` | yes | Always this value |
| `created` | integer | yes | Unix timestamp |
| `model` | string | yes | Model that generated the response |
| `choices` | array | yes | Completion choices (length = `n`) |
| `usage` | CompletionUsage | no | Token usage statistics |
| `service_tier` | string | no | Tier used for processing |
| `system_fingerprint` | string | no | Backend config fingerprint |

#### Choice Object

| Field | Type | Required | Description |
|---|---|---|---|
| `index` | integer | yes | Index in choices array |
| `message` | ChatCompletionResponseMessage | yes | The generated message |
| `finish_reason` | enum | yes | `stop`, `length`, `tool_calls`, `content_filter`, `function_call` |
| `logprobs` | object \| null | yes | Log probability info (if requested) |

#### Response Message

| Field | Type | Required | Description |
|---|---|---|---|
| `role` | `"assistant"` | yes | Always assistant |
| `content` | string \| null | yes | Generated text (null when tool_calls present) |
| `refusal` | string \| null | yes | Refusal message if model declined |
| `tool_calls` | array | no | Tool calls the model wants to make |
| `annotations` | array | no | Web search citations |
| `audio` | object \| null | no | Audio response data |
| `function_call` | object | no | Deprecated. Use tool_calls. |

#### CompletionUsage

| Field | Type | Required | Description |
|---|---|---|---|
| `prompt_tokens` | integer | yes | Input tokens |
| `completion_tokens` | integer | yes | Output tokens |
| `total_tokens` | integer | yes | Sum |
| `prompt_tokens_details.cached_tokens` | integer | no | Cached input tokens |
| `prompt_tokens_details.audio_tokens` | integer | no | Audio input tokens |
| `completion_tokens_details.reasoning_tokens` | integer | no | Reasoning tokens (o-series) |
| `completion_tokens_details.audio_tokens` | integer | no | Audio output tokens |
| `completion_tokens_details.accepted_prediction_tokens` | integer | no | Predicted tokens used |
| `completion_tokens_details.rejected_prediction_tokens` | integer | no | Predicted tokens rejected |

---

## 6. Streaming Schema

### 6.1 Format

When `stream=true`, the response is Server-Sent Events (SSE):

```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{"role":"assistant","content":""},"logprobs":null,"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{"content":"Hello"},"logprobs":null,"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{"content":"!"},"logprobs":null,"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{},"logprobs":null,"finish_reason":"stop"}]}

data: [DONE]
```

### 6.2 `CreateChatCompletionStreamResponse` (Chunk Object)

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Same ID across all chunks |
| `object` | `"chat.completion.chunk"` | yes | Always this value |
| `created` | integer | yes | Same timestamp across all chunks |
| `model` | string | yes | Model identifier |
| `choices` | array | yes | Chunk choices (can be empty on final usage-only chunk) |
| `usage` | CompletionUsage \| null | no | Only present on last chunk when `stream_options.include_usage=true` |
| `service_tier` | string | no | Tier used |
| `system_fingerprint` | string | no | Backend fingerprint |

### 6.3 Stream Delta Object

The `choices[].delta` replaces `choices[].message` in chunks:

| Field | Type | Description |
|---|---|---|
| `role` | string | Only in first chunk: `"assistant"` |
| `content` | string \| null | Text content delta |
| `refusal` | string \| null | Refusal content delta |
| `tool_calls` | array | Tool call chunks (streamed incrementally) |
| `function_call` | object | Deprecated |

### 6.4 Streaming Lifecycle

```
Chunk 1: delta = {role: "assistant", content: ""}     ← role announcement
Chunk 2: delta = {content: "Hello"}                    ← content token
Chunk 3: delta = {content: " world"}                   ← content token
...
Chunk N: delta = {}, finish_reason = "stop"            ← termination
[if include_usage]: Chunk N+1: choices=[], usage={...} ← usage stats
data: [DONE]                                           ← stream end signal
```

### 6.5 Tool Call Streaming

Tool calls stream incrementally:

```
Chunk 1: delta = {tool_calls: [{index: 0, id: "call_abc", type: "function", function: {name: "get_weather", arguments: ""}}]}
Chunk 2: delta = {tool_calls: [{index: 0, function: {arguments: '{"lo'}}]}
Chunk 3: delta = {tool_calls: [{index: 0, function: {arguments: 'cation'}}]}
Chunk 4: delta = {tool_calls: [{index: 0, function: {arguments: '":"NYC"}'}}]}
Chunk 5: delta = {}, finish_reason = "tool_calls"
```

---

## 7. Tool Calling

### 7.1 Tool Definition

```json
{
  "type": "function",
  "function": {
    "name": "get_weather",
    "description": "Get the current weather for a location",
    "parameters": {
      "type": "object",
      "properties": {
        "location": {"type": "string", "description": "City name"},
        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
      },
      "required": ["location"]
    },
    "strict": false
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | `"function"` | yes | Only function type supported |
| `function.name` | string | yes | Function name (a-z, A-Z, 0-9, underscores, dashes; max 64) |
| `function.description` | string | no | Used by model to decide when to call |
| `function.parameters` | JSON Schema object | no | Input parameters schema |
| `function.strict` | boolean \| null | no | Default `false`. If `true`, model strictly follows schema (Structured Outputs). |

### 7.2 Tool Choice

| Value | Behavior |
|---|---|
| `"none"` | Model won't call any tool |
| `"auto"` | Model decides (default when tools present) |
| `"required"` | Model must call at least one tool |
| `{"type": "function", "function": {"name": "..."}}` | Force specific function |

### 7.3 Tool Call Response Object

```json
{
  "id": "call_abc123",
  "type": "function",
  "function": {
    "name": "get_weather",
    "arguments": "{\"location\": \"NYC\"}"
  }
}
```

Note: `arguments` is a **string** (JSON-encoded), not an object. The model may produce invalid
JSON — callers must validate.

### 7.4 Relevance to Candlekeep

Tool calling is **not needed for core roleplay** but enables:
- Web search integration
- Dice rolling / game mechanics
- Character memory retrieval (RAG-as-a-tool)
- Dynamic world state queries

Lower priority, but the architecture should not prevent adding it later.

---

## 8. Response Formats

### 8.1 Text (Default)

```json
{"type": "text"}
```

Standard free-form text output.

### 8.2 JSON Object (Legacy)

```json
{"type": "json_object"}
```

Forces valid JSON output. Requires "JSON" mentioned in system/user message.

### 8.3 JSON Schema (Structured Outputs)

```json
{
  "type": "json_schema",
  "json_schema": {
    "name": "response_schema",
    "description": "A structured response",
    "schema": {
      "type": "object",
      "properties": {
        "action": {"type": "string"},
        "dialogue": {"type": "string"}
      },
      "required": ["action", "dialogue"]
    },
    "strict": true
  }
}
```

**Structured Outputs** — model output guaranteed to match the provided JSON Schema.

### 8.4 Relevance to Candlekeep

Response format control is useful for:
- Parsing structured RP actions (separate narration from dialogue)
- Extracting metadata from responses (mood, location changes)
- Integration with game engines

Not critical for MVP but the architecture should support passing it through.

---

## 9. Models Endpoint

### 9.1 List Models

```
GET /v1/models
Authorization: Bearer <key>
```

Response:
```json
{
  "object": "list",
  "data": [
    {
      "id": "gpt-4o",
      "object": "model",
      "created": 1686935002,
      "owned_by": "openai"
    }
  ]
}
```

### 9.2 Relevance to Candlekeep

This endpoint enables **auto-discovery** of available models. Instead of manually seeding
model definitions, Candlekeep could query the provider's model list and present available
options. This is particularly useful for:
- Ollama (models change as users pull/remove them)
- OpenRouter (aggregates hundreds of models)
- Custom providers (unknown model lineup)

---

## 10. Current Candlekeep Implementation

### 10.1 What `ProviderClient` Does Now

From `src/provider/client.py`:

```python
class ProviderClient:
    def __init__(self, provider, model, openrouter_provider=None):
        # Determines base_url and active_identifier
        # Handles OpenRouter routing

    def _get_effective_parameters(self) -> dict:
        # Merges model_family defaults with model overrides

    def _build_payload(self, messages, stream=False) -> dict:
        # Returns: {model, messages, stream?, **parameters}

    async def chat_completion(self, messages) -> dict:
        # POST {base_url}/chat/completions
        # Returns full response JSON

    async def chat_completion_stream(self, messages) -> AsyncIterator[str]:
        # POST {base_url}/chat/completions with stream=True
        # Yields content deltas as strings
```

### 10.2 What It Gets Right

1. **Bearer token auth** — correct
2. **POST to /chat/completions** — correct for OpenAI-compatible APIs
3. **SSE parsing** — handles `data: ` prefix and `[DONE]` signal
4. **Parameter merging** — family defaults + model overrides
5. **Error mapping** — HTTP status → custom exception types

### 10.3 What It Gets Wrong or Misses

| Issue | Current | Correct |
|---|---|---|
| **Hardcoded endpoint** | Always `/chat/completions` | Should vary by provider (Anthropic: `/v1/messages`, Gemini: different entirely) |
| **No `max_completion_tokens`** | Uses `max_tokens` from parameters | Should prefer `max_completion_tokens` for newer models |
| **No reasoning support** | No `reasoning_effort` | Required for o-series models |
| **No `developer` role** | Sends `system` messages | o-series models require `developer` role |
| **No response parsing** | Returns raw JSON dict | Should extract content, usage, finish_reason into typed objects |
| **No usage tracking** | Ignores `usage` in response | Should capture and return token counts |
| **No `n > 1` support** | Always generates 1 response | Needed for swipe feature |
| **No `stream_options`** | No `include_usage` support | Needed for streaming usage tracking |
| **No tool calling** | Not supported | Architecture should allow it |
| **No stop sequences** | Not passed | Should be configurable |
| **No response format** | Not supported | Should pass through |
| **No logprobs** | Not supported | Useful for debugging |
| **No multimodal** | Text-only messages | Should support image content parts |
| **No abort mechanism** | Stream runs to completion | Should support cancellation via signal |
| **Timeout too short** | 60 seconds | Some models (o3) take minutes for complex reasoning |
| **Single client per request** | Creates new `httpx.AsyncClient` per call | Should reuse connections |

---

## 11. Gap Analysis

### 11.1 Severity Levels

| Level | Meaning |
|---|---|
| **P0** | Breaks core functionality or produces incorrect results |
| **P1** | Missing feature that significantly impacts user experience |
| **P2** | Missing feature that would improve quality |
| **P3** | Nice-to-have, can be added later |

### 11.2 Gaps

| # | Gap | Severity | Reason |
|---|---|---|---|
| 1 | No typed response objects | P0 | Raw dict access is fragile — `response["choices"][0]["message"]["content"]` breaks if structure changes |
| 2 | No usage tracking returned to caller | P0 | ChatMessageService ignores actual token counts from the API, stores tiktoken estimates instead |
| 3 | No `max_completion_tokens` support | P0 | o-series models reject `max_tokens` |
| 4 | No `developer` role support | P0 | o-series models reject `system` role |
| 5 | Hardcoded `/chat/completions` path | P0 | Breaks for Anthropic (`/v1/messages`), Gemini, Ollama (`/api/chat`) |
| 6 | No abort/cancel mechanism | P1 | User cannot stop generation |
| 7 | No `n > 1` for swiping | P1 | Core RP feature (multiple alternatives) |
| 8 | No `reasoning_effort` | P1 | o-series models need this |
| 9 | No `stop` sequences | P1 | Important for formatting control |
| 10 | No `stream_options.include_usage` | P1 | Streaming calls lose usage data |
| 11 | Single-use httpx client | P2 | Connection overhead per request |
| 12 | No `response_format` passthrough | P2 | Cannot request JSON output |
| 13 | No `logprobs` | P2 | Useful for debugging/quality |
| 14 | No `logit_bias` | P2 | Token frequency control |
| 15 | No multimodal messages | P2 | Vision/image support |
| 16 | No tool calling | P3 | Not needed for core RP |
| 17 | No `seed` support | P3 | Reproducibility |
| 18 | No `service_tier` | P3 | Billing optimization |
| 19 | No `web_search_options` | P3 | New feature |

---

## 12. Multi-Provider Architecture Design

### 12.1 The Problem

Candlekeep currently has ONE client that assumes ALL providers speak the OpenAI protocol.
This is fundamentally broken because:

| Provider | Endpoint | Message Format | Auth | Key Differences |
|---|---|---|---|---|
| **OpenAI** | `POST /v1/chat/completions` | `messages: [{role, content}]` | Bearer token | Reference implementation |
| **Anthropic** | `POST /v1/messages` | `messages: [{role, content}]` but `system` is a **top-level field**, not a message | `x-api-key` header + `anthropic-version` header | Different payload shape entirely |
| **Google Gemini** | `POST /v1beta/models/{model}:generateContent` | `contents: [{role, parts: [{text}]}]` | `?key=` query param or OAuth | Completely different schema |
| **OpenRouter** | `POST /api/v1/chat/completions` | Same as OpenAI | Bearer token + extra headers (`HTTP-Referer`, `X-Title`) | OpenAI-compatible wrapper |
| **Ollama** | `POST /api/chat` | `messages: [{role, content}]` | None (local) | Similar but different path, no auth, different response shape |

### 12.2 Architecture: Strategy Pattern + Adapter Layer

```
                        ┌─────────────────────────┐
                        │   ChatMessageService     │
                        │   (business logic)       │
                        └──────────┬──────────────┘
                                   │
                                   │ uses
                                   ▼
                        ┌─────────────────────────┐
                        │   ProviderGateway        │  ← Facade
                        │   (route to adapter)     │
                        └──────────┬──────────────┘
                                   │
                    ┌──────────────┼──────────────────┐
                    │              │                   │
                    ▼              ▼                   ▼
           ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
           │ OpenAIAdapter│ │AnthropicAdapter│ │ GeminiAdapter│ ...
           └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
                  │                │                 │
                  ▼                ▼                 ▼
           ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
           │ OpenAI API   │ │ Anthropic API│ │ Gemini API   │
           └──────────────┘ └──────────────┘ └──────────────┘
```

### 12.3 Key Abstractions

```python
# ---- Shared types (provider-agnostic) ----

@dataclass
class CompletionRequest:
    """Provider-agnostic request. Adapters translate this to provider format."""
    messages: list[ChatMessage]
    model: str
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    stop: list[str] | None = None
    stream: bool = False
    stream_include_usage: bool = False
    n: int = 1
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    reasoning_effort: ReasoningEffort | None = None
    response_format: ResponseFormat | None = None
    seed: int | None = None
    tools: list[ToolDefinition] | None = None
    tool_choice: ToolChoice | None = None
    logit_bias: dict[str, int] | None = None
    logprobs: bool = False
    top_logprobs: int | None = None
    extra: dict[str, Any] | None = None  # Provider-specific overrides

@dataclass
class CompletionResponse:
    """Provider-agnostic response. Adapters translate provider response to this."""
    id: str
    content: str | None
    finish_reason: FinishReason
    usage: TokenUsage | None
    tool_calls: list[ToolCall] | None = None
    model: str | None = None
    refusal: str | None = None
    raw: dict[str, Any] | None = None  # Original provider response

@dataclass
class CompletionChunk:
    """Provider-agnostic streaming chunk."""
    id: str
    delta_content: str | None = None
    delta_role: str | None = None
    finish_reason: FinishReason | None = None
    usage: TokenUsage | None = None  # Only on final chunk
    tool_call_chunks: list[ToolCallChunk] | None = None

@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    reasoning_tokens: int = 0
    cached_tokens: int = 0

@dataclass
class ChatMessage:
    role: MessageRole  # system, developer, user, assistant, tool
    content: str | list[ContentPart]
    name: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None

class MessageRole(str, Enum):
    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

class FinishReason(str, Enum):
    STOP = "stop"
    LENGTH = "length"
    TOOL_CALLS = "tool_calls"
    CONTENT_FILTER = "content_filter"
    ERROR = "error"

class ReasoningEffort(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
```

### 12.4 The Adapter Protocol

```python
from abc import ABC, abstractmethod

class ProviderAdapter(ABC):
    """Base class for provider-specific API adapters."""

    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Send a completion request and return the response."""
        ...

    @abstractmethod
    async def complete_stream(
        self, request: CompletionRequest
    ) -> AsyncIterator[CompletionChunk]:
        """Send a streaming completion request and yield chunks."""
        ...

    @abstractmethod
    def build_headers(self) -> dict[str, str]:
        """Build provider-specific HTTP headers."""
        ...

    @abstractmethod
    def build_url(self, model: str) -> str:
        """Build the provider-specific endpoint URL."""
        ...

    @abstractmethod
    def build_payload(self, request: CompletionRequest) -> dict[str, Any]:
        """Transform CompletionRequest into provider-specific payload."""
        ...

    @abstractmethod
    def parse_response(self, raw: dict[str, Any]) -> CompletionResponse:
        """Transform provider response into CompletionResponse."""
        ...

    @abstractmethod
    def parse_stream_chunk(self, line: str) -> CompletionChunk | None:
        """Parse a single SSE line into a CompletionChunk."""
        ...
```

### 12.5 The Gateway (Router)

```python
class ProviderGateway:
    """Routes requests to the correct adapter based on provider type."""

    def __init__(self, http_client: httpx.AsyncClient):
        self._client = http_client
        self._adapters: dict[ProviderType, type[ProviderAdapter]] = {
            ProviderType.OPENAI: OpenAIAdapter,
            ProviderType.ANTHROPIC: AnthropicAdapter,
            ProviderType.GOOGLE: GeminiAdapter,
            ProviderType.OPENROUTER: OpenRouterAdapter,
            ProviderType.XAI: XAIAdapter,         # OpenAI-compatible
            ProviderType.OLLAMA: OllamaAdapter,
            ProviderType.CUSTOM: OpenAIAdapter,    # Default to OpenAI-compatible
        }

    def get_adapter(self, provider: Provider, model: Model) -> ProviderAdapter:
        adapter_class = self._adapters.get(provider.provider_type, OpenAIAdapter)
        return adapter_class(provider=provider, model=model, client=self._client)

    async def complete(
        self, provider: Provider, model: Model, request: CompletionRequest
    ) -> CompletionResponse:
        adapter = self.get_adapter(provider, model)
        return await adapter.complete(request)

    async def complete_stream(
        self, provider: Provider, model: Model, request: CompletionRequest
    ) -> AsyncIterator[CompletionChunk]:
        adapter = self.get_adapter(provider, model)
        async for chunk in adapter.complete_stream(request):
            yield chunk
```

---

## 13. OpenAI Adapter — Implementation Spec

### 13.1 File Location

```
src/provider/
  adapters/
    __init__.py
    base.py              ← ProviderAdapter ABC
    openai.py            ← OpenAIAdapter
    anthropic.py         ← (future) AnthropicAdapter
    gemini.py            ← (future) GeminiAdapter
    openrouter.py        ← (future) OpenRouterAdapter
    ollama.py            ← (future) OllamaAdapter
  gateway.py             ← ProviderGateway
  types.py               ← CompletionRequest, CompletionResponse, etc.
  client.py              ← (deprecated, replaced by gateway)
```

### 13.2 OpenAIAdapter Implementation

```python
class OpenAIAdapter(ProviderAdapter):
    """Adapter for OpenAI and OpenAI-compatible APIs."""

    def build_url(self, model: str) -> str:
        return f"{self.base_url}/chat/completions"

    def build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        api_key = self.provider.get_api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def build_payload(self, request: CompletionRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": self._format_messages(request.messages),
        }

        # Generation parameters (only include non-None)
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.max_tokens is not None:
            # Use max_completion_tokens for newer models
            if self._is_reasoning_model(request.model):
                payload["max_completion_tokens"] = request.max_tokens
            else:
                payload["max_completion_tokens"] = request.max_tokens
        if request.frequency_penalty is not None:
            payload["frequency_penalty"] = request.frequency_penalty
        if request.presence_penalty is not None:
            payload["presence_penalty"] = request.presence_penalty
        if request.stop:
            payload["stop"] = request.stop
        if request.n > 1:
            payload["n"] = request.n
        if request.seed is not None:
            payload["seed"] = request.seed
        if request.reasoning_effort is not None:
            payload["reasoning_effort"] = request.reasoning_effort.value
        if request.response_format:
            payload["response_format"] = request.response_format.to_dict()
        if request.logprobs:
            payload["logprobs"] = True
            if request.top_logprobs is not None:
                payload["top_logprobs"] = request.top_logprobs
        if request.logit_bias:
            payload["logit_bias"] = request.logit_bias
        if request.tools:
            payload["tools"] = [t.to_dict() for t in request.tools]
        if request.tool_choice:
            payload["tool_choice"] = request.tool_choice.to_dict()

        # Streaming
        if request.stream:
            payload["stream"] = True
            if request.stream_include_usage:
                payload["stream_options"] = {"include_usage": True}

        # Provider-specific overrides
        if request.extra:
            payload.update(request.extra)

        return payload

    def _format_messages(self, messages: list[ChatMessage]) -> list[dict]:
        result = []
        for msg in messages:
            m: dict[str, Any] = {"role": msg.role.value}

            if isinstance(msg.content, str):
                m["content"] = msg.content
            elif isinstance(msg.content, list):
                m["content"] = [self._format_content_part(p) for p in msg.content]

            if msg.name:
                m["name"] = msg.name
            if msg.tool_calls:
                m["tool_calls"] = [tc.to_dict() for tc in msg.tool_calls]
            if msg.tool_call_id:
                m["tool_call_id"] = msg.tool_call_id

            result.append(m)
        return result

    def _is_reasoning_model(self, model: str) -> bool:
        return any(model.startswith(p) for p in ("o1", "o3", "o4"))

    def parse_response(self, raw: dict[str, Any]) -> CompletionResponse:
        choice = raw["choices"][0]
        message = choice["message"]

        tool_calls = None
        if message.get("tool_calls"):
            tool_calls = [
                ToolCall(
                    id=tc["id"],
                    function_name=tc["function"]["name"],
                    arguments=tc["function"]["arguments"],
                )
                for tc in message["tool_calls"]
            ]

        usage = None
        if raw.get("usage"):
            u = raw["usage"]
            details = u.get("completion_tokens_details", {})
            usage = TokenUsage(
                prompt_tokens=u.get("prompt_tokens", 0),
                completion_tokens=u.get("completion_tokens", 0),
                total_tokens=u.get("total_tokens", 0),
                reasoning_tokens=details.get("reasoning_tokens", 0),
                cached_tokens=u.get("prompt_tokens_details", {}).get("cached_tokens", 0),
            )

        return CompletionResponse(
            id=raw["id"],
            content=message.get("content"),
            finish_reason=FinishReason(choice.get("finish_reason", "stop")),
            usage=usage,
            tool_calls=tool_calls,
            model=raw.get("model"),
            refusal=message.get("refusal"),
            raw=raw,
        )

    def parse_stream_chunk(self, data: dict[str, Any]) -> CompletionChunk | None:
        if not data.get("choices"):
            # Usage-only final chunk
            usage = self._parse_usage(data.get("usage")) if data.get("usage") else None
            return CompletionChunk(id=data["id"], usage=usage)

        choice = data["choices"][0]
        delta = choice.get("delta", {})

        usage = None
        if data.get("usage"):
            usage = self._parse_usage(data["usage"])

        tool_chunks = None
        if delta.get("tool_calls"):
            tool_chunks = [
                ToolCallChunk(
                    index=tc["index"],
                    id=tc.get("id"),
                    function_name=tc.get("function", {}).get("name"),
                    arguments_delta=tc.get("function", {}).get("arguments"),
                )
                for tc in delta["tool_calls"]
            ]

        finish = None
        if choice.get("finish_reason"):
            finish = FinishReason(choice["finish_reason"])

        return CompletionChunk(
            id=data["id"],
            delta_content=delta.get("content"),
            delta_role=delta.get("role"),
            finish_reason=finish,
            usage=usage,
            tool_call_chunks=tool_chunks,
        )
```

### 13.3 What OpenAI-Compatible Providers Get for Free

The `OpenAIAdapter` can be reused (or minimally subclassed) for:

| Provider | Reusable? | Customizations Needed |
|---|---|---|
| **xAI (Grok)** | Yes | Different `base_url` only |
| **OpenRouter** | Subclass | Extra headers: `HTTP-Referer`, `X-Title`. Different base URL. |
| **DeepSeek** | Yes | Different `base_url` only |
| **Groq** | Yes | Different `base_url` only |
| **Mistral** | Mostly | Different `base_url`, minor response format differences |
| **Ollama** | Subclass | Path: `/api/chat`. No auth. Different response shape for some fields. |
| **Custom** | Yes | User-provided `base_url` |

Providers that need entirely separate adapters:
- **Anthropic** — different payload, auth, and response format
- **Google Gemini** — completely different API structure

---

## 14. Shared Abstractions (Provider-Agnostic)

### 14.1 Content Parts (Multimodal)

```python
class ContentPart:
    """Base for multimodal content parts."""
    pass

@dataclass
class TextContent(ContentPart):
    text: str

@dataclass
class ImageContent(ContentPart):
    url: str                    # URL or base64 data URI
    detail: str = "auto"        # "auto", "low", "high"

@dataclass
class AudioContent(ContentPart):
    data: str                   # Base64 encoded
    format: str                 # "wav", "mp3"

@dataclass
class FileContent(ContentPart):
    file_id: str | None = None
    file_data: str | None = None
    filename: str | None = None
```

### 14.2 Response Format

```python
class ResponseFormat:
    pass

@dataclass
class TextFormat(ResponseFormat):
    def to_dict(self): return {"type": "text"}

@dataclass
class JsonObjectFormat(ResponseFormat):
    def to_dict(self): return {"type": "json_object"}

@dataclass
class JsonSchemaFormat(ResponseFormat):
    name: str
    schema: dict[str, Any]
    description: str | None = None
    strict: bool = False

    def to_dict(self):
        result = {
            "type": "json_schema",
            "json_schema": {"name": self.name, "schema": self.schema, "strict": self.strict}
        }
        if self.description:
            result["json_schema"]["description"] = self.description
        return result
```

### 14.3 Tool Definitions

```python
@dataclass
class ToolDefinition:
    name: str
    description: str | None = None
    parameters: dict[str, Any] | None = None
    strict: bool = False

    def to_dict(self):
        func = {"name": self.name}
        if self.description:
            func["description"] = self.description
        if self.parameters:
            func["parameters"] = self.parameters
        if self.strict:
            func["strict"] = True
        return {"type": "function", "function": func}

class ToolChoice:
    pass

@dataclass
class ToolChoiceAuto(ToolChoice):
    def to_dict(self): return "auto"

@dataclass
class ToolChoiceNone(ToolChoice):
    def to_dict(self): return "none"

@dataclass
class ToolChoiceRequired(ToolChoice):
    def to_dict(self): return "required"

@dataclass
class ToolChoiceFunction(ToolChoice):
    name: str
    def to_dict(self):
        return {"type": "function", "function": {"name": self.name}}

@dataclass
class ToolCall:
    id: str
    function_name: str
    arguments: str  # JSON string

    def to_dict(self):
        return {
            "id": self.id,
            "type": "function",
            "function": {"name": self.function_name, "arguments": self.arguments}
        }

@dataclass
class ToolCallChunk:
    index: int
    id: str | None = None
    function_name: str | None = None
    arguments_delta: str | None = None
```

---

## 15. Implementation Plan

### Phase 1: Foundation (Types + OpenAI Adapter)

```
1. Create src/provider/types.py
   - CompletionRequest, CompletionResponse, CompletionChunk
   - ChatMessage, MessageRole, FinishReason, ReasoningEffort
   - TokenUsage
   - ContentPart types (TextContent, ImageContent)

2. Create src/provider/adapters/base.py
   - ProviderAdapter ABC

3. Create src/provider/adapters/openai.py
   - OpenAIAdapter implementing all methods
   - Handles: headers, URL, payload, response parsing, stream parsing
   - Supports: all generation params, reasoning_effort, stream_options,
     developer role, max_completion_tokens

4. Create src/provider/gateway.py
   - ProviderGateway with shared httpx.AsyncClient
   - Route by ProviderType to adapter

5. Update src/chat_message/service.py
   - Use ProviderGateway instead of ProviderClient
   - Build CompletionRequest from PromptBuilder output
   - Extract TokenUsage from CompletionResponse
   - Store ACTUAL token counts (not tiktoken estimates)

6. Deprecate src/provider/client.py
   - Keep for backwards compatibility during transition
   - Mark all methods as deprecated
```

### Phase 2: OpenAI-Compatible Providers

```
7. Create src/provider/adapters/openrouter.py
   - Subclass OpenAIAdapter
   - Override build_headers() for extra headers
   - Override build_url() for OpenRouter base URL

8. Create src/provider/adapters/ollama.py
   - Subclass OpenAIAdapter
   - Override build_url() for /api/chat path
   - Override build_headers() (no auth)
   - Handle response shape differences

9. Verify xAI, DeepSeek, Groq work with base OpenAIAdapter
   - Only need different base_url (already in Provider model)
```

### Phase 3: Non-OpenAI Providers

```
10. Create src/provider/adapters/anthropic.py
    - Separate payload builder (system as top-level, different message format)
    - Different auth (x-api-key header, anthropic-version header)
    - Different response parsing

11. Create src/provider/adapters/gemini.py
    - Completely different API structure
    - Different auth (API key as query param)
    - Different message format (contents/parts)
    - Safety settings support
```

### Phase 4: Enhanced Features

```
12. Add abort/cancel support
    - Pass httpx CancelScope or asyncio Event to adapters
    - Allow ChatMessageService to signal cancellation

13. Add n > 1 support (swiping)
    - CompletionResponse returns list[Choice] instead of single
    - ChatMessageService stores multiple alternatives

14. Add response_format passthrough
    - PromptBuilder or ChatMessageService can set response format
    - Adapter passes it through

15. Add stream_options.include_usage
    - Return TokenUsage from streaming completions
    - Store actual usage data
```

---

## Appendix: OpenAI Parameter Quick Reference

For copy-paste reference when implementing the adapter.

### Request Parameters (Alphabetical)

| Parameter | Type | Default | Constraints |
|---|---|---|---|
| `audio` | `{voice, format}` \| null | null | Required when modalities includes audio |
| `frequency_penalty` | number \| null | 0 | [-2, 2] |
| `logit_bias` | `{token_id: bias}` \| null | null | bias: [-100, 100] |
| `logprobs` | boolean \| null | false | |
| `max_completion_tokens` | integer \| null | - | Preferred over max_tokens |
| `max_tokens` | integer \| null | - | **Deprecated** |
| `messages` | array | **required** | min 1 item |
| `metadata` | `{key: value}` \| null | null | max 16 pairs |
| `modalities` | string[] \| null | ["text"] | ["text"] or ["text", "audio"] |
| `model` | string | **required** | |
| `n` | integer \| null | 1 | [1, 128] |
| `parallel_tool_calls` | boolean | true | |
| `prediction` | object \| null | null | Predicted Outputs |
| `presence_penalty` | number \| null | 0 | [-2, 2] |
| `reasoning_effort` | string \| null | "medium" | low, medium, high (o-series only) |
| `response_format` | object | - | text, json_object, json_schema |
| `seed` | integer \| null | - | [-2^63, 2^63] |
| `service_tier` | string \| null | "auto" | auto, default, flex |
| `stop` | string \| string[] \| null | null | max 4 sequences |
| `store` | boolean \| null | false | |
| `stream` | boolean \| null | false | |
| `stream_options` | `{include_usage}` \| null | null | Only when stream=true |
| `temperature` | number \| null | 1 | [0, 2] |
| `tool_choice` | string \| object | - | none, auto, required, or named |
| `tools` | array | - | max 128 tools |
| `top_logprobs` | integer \| null | - | [0, 20], requires logprobs=true |
| `top_p` | number \| null | 1 | [0, 1] |
| `user` | string | - | End-user ID |
| `web_search_options` | object | - | Web search config |

### Finish Reasons

| Value | Meaning |
|---|---|
| `stop` | Natural stop or stop sequence hit |
| `length` | Max tokens reached |
| `tool_calls` | Model wants to call tool(s) |
| `content_filter` | Content filtered |
| `function_call` | Deprecated function call |

### Message Roles

| Role | Supported By | Description |
|---|---|---|
| `system` | All except o-series | Developer instructions |
| `developer` | o-series (o1, o3, o4-mini) | Same as system for reasoning models |
| `user` | All | End-user messages |
| `assistant` | All | Model responses (for history replay) |
| `tool` | All with tools | Tool call results |
| `function` | Deprecated | Use tool instead |
