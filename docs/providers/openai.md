# OpenAI Chat Completions API

> **Source:** OpenAI OpenAPI spec v2.3.0 (`openai/openai-openapi`, `manual_spec` branch)
> **Endpoint:** `POST /v1/chat/completions`
> **Goal:** Define what The Bannered Mare must implement to fully support the OpenAI API, and
> architect it so Anthropic, Google Gemini, and OpenRouter can be added modularly.


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
10. [What The Bannered Mare Currently Implements](#10-current-implementation)
11. [Gap Analysis](#11-gap-analysis)
12. [Multi-Provider Architecture Design](#12-multi-provider-architecture)
13. [OpenAI Adapter — Implementation Spec](#13-openai-adapter-spec)
14. [Shared Abstractions (Provider-Agnostic)](#14-shared-abstractions)
15. [Implementation Plan](#15-implementation-plan)


## 1. API Overview

**Base URL:** `https://api.openai.com/v1`

**Endpoint:** `POST /chat/completions`

**Purpose:** Given a list of messages (conversation history), generate a model response.
Supports text, vision (images), audio I/O, tool/function calling, structured output, streaming,
and reasoning models.

**Auth:** Bearer token via `Authorization: Bearer <API_KEY>` header.


## 2. Authentication

```
Authorization: Bearer sk-...
```

- API keys are confidential, never exposed client-side
- Organization header optional: `OpenAI-Organization: org-...`
- Project header optional: `OpenAI-Project: proj-...`

**For The Bannered Mare:** API keys are stored as environment variable names in the Provider model.
The current `ProviderClient` reads the key via `provider.get_api_key()`. This pattern works.


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

### 7.4 Relevance to The Bannered Mare

Tool calling is **not needed for core roleplay** but enables:
- Web search integration
- Dice rolling / game mechanics
- Character memory retrieval (RAG-as-a-tool)
- Dynamic world state queries

Lower priority, but the architecture should not prevent adding it later.


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

### 8.4 Relevance to The Bannered Mare

Response format control is useful for:
- Parsing structured RP actions (separate narration from dialogue)
- Extracting metadata from responses (mood, location changes)
- Integration with game engines

Not critical for MVP but the architecture should support passing it through.


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

### 9.2 Relevance to The Bannered Mare

This endpoint enables **auto-discovery** of available models. Instead of manually seeding
model definitions, The Bannered Mare could query the provider's model list and present available
options. This is particularly useful for:
- Ollama (models change as users pull/remove them)
- OpenRouter (aggregates hundreds of models)
- Custom providers (unknown model lineup)


## 10. Current The Bannered Mare Implementation

The original single `ProviderClient` has been replaced by the adapter layer described in
[Section 12](#12-multi-provider-architecture). The `OpenAIAdapter` is now the baseline for all
OpenAI-compatible providers.

### 10.1 What `OpenAIAdapter` + `ProviderGateway` Do Now

The `ProviderGateway` (`src/provider/gateway.py`) owns the `httpx` client and calls into a
stateless adapter selected by provider type. For OpenAI, that is `OpenAIAdapter`
(`src/provider/adapters/openai.py`):

```python
class OpenAIAdapter(ProviderAdapter):
    def build_url(self, base_url, model, stream, api_key=None) -> str:
        return f"{base_url}/chat/completions"

    def build_headers(self, api_key) -> dict[str, str]:
        # Content-Type + optional "Authorization: Bearer <key>"

    def build_payload(self, messages, model, stream, parameters) -> dict:
        # {model, messages, stream?} plus every key in _OPENAI_PARAMS present in parameters

    def parse_response(self, data) -> CompletionResponse:
        # Extracts content, finish_reason, usage (incl. cached tokens), and reasoning_content

    def parse_stream_line(self, line) -> StreamChunk | None:
        # Parses "data: " SSE lines, [DONE], content/reasoning deltas, and usage
```

The gateway's `chat_completion()` returns a typed `CompletionResponse`; its
`chat_completion_stream()` yields typed `StreamChunk` objects. Parameters are merged by
`ProviderGateway._get_effective_parameters()` (ModelFamily defaults → Model overrides → preset
overrides).

### 10.2 What It Gets Right

1. **Bearer token auth** — correct (only sent when an API key is configured)
2. **POST to /chat/completions** — correct for OpenAI-compatible APIs
3. **SSE parsing** — handles `data: ` prefix and `[DONE]` signal
4. **Parameter merging** — family defaults + model overrides + preset overrides
5. **Error mapping** — HTTP status → custom exception types (in the gateway)
6. **Typed responses** — content, usage, finish_reason, and reasoning parsed into dataclasses
7. **Parameter selection** — only keys in `_OPENAI_PARAMS` (incl. `max_completion_tokens`,
   `reasoning_effort`, `stop`, `response_format`, `tools`, `stream_options`) are forwarded
8. **Reasoning capture** — `reasoning_content` / `reasoning` fields surfaced on the response

### 10.3 What It Still Misses

The adapter forwards these parameters if present but The Bannered Mare does not yet drive them
end-to-end, and some higher-level features remain unbuilt:

| Issue | Status |
|---|---|
| **`developer` role** | Adapter passes messages through unchanged; no automatic `system`→`developer` rewrite for o-series |
| **Typed tool-calling** | `tools`/`tool_choice` are forwarded, but tool calls are not parsed into canonical types |
| **Multimodal content parts** | Messages are OpenAI-shaped dicts; image/audio parts are passed through, not modeled |
| **`n > 1` (swiping)** | `n` is forwarded, but only the first choice is parsed |
| **Abort / cancellation** | Stream runs to completion; no cancellation signal |
| **Shared connection pool** | Each call opens a new `httpx.AsyncClient` |
| **Configurable timeout** | Fixed at 120s (`get_timeout`), not per-model tunable via config |


## 11. Gap Analysis

### 11.1 Severity Levels

| Level | Meaning |
|---|---|
| **P0** | Breaks core functionality or produces incorrect results |
| **P1** | Missing feature that significantly impacts user experience |
| **P2** | Missing feature that would improve quality |
| **P3** | Nice-to-have, can be added later |

### 11.2 Gaps

Most of the original P0/P1 gaps were closed by the adapter layer. The `Status` column reflects the
current `OpenAIAdapter` / `ProviderGateway` implementation.

| # | Gap | Severity | Status |
|---|---|---|---|
| 1 | Typed response objects | P0 | Done — `parse_response` returns `CompletionResponse` |
| 2 | Usage returned to caller | P0 | Done at the gateway (`CompletionResponse.usage`); downstream storage out of scope here |
| 3 | `max_completion_tokens` support | P0 | Done — in `_OPENAI_PARAMS`, forwarded when present |
| 4 | `developer` role support | P0 | Open — messages passed through as-is; no `system`→`developer` rewrite |
| 5 | Endpoint varies by provider | P0 | Done — each adapter builds its own URL |
| 6 | Abort/cancel mechanism | P1 | Open — stream runs to completion |
| 7 | `n > 1` for swiping | P1 | Partial — `n` is forwarded; only the first choice is parsed |
| 8 | `reasoning_effort` | P1 | Done — forwarded via `_OPENAI_PARAMS` |
| 9 | `stop` sequences | P1 | Done — forwarded via `_OPENAI_PARAMS` |
| 10 | `stream_options.include_usage` | P1 | Done — forwarded; usage parsed from the final chunk |
| 11 | Single-use httpx client | P2 | Open — a new `AsyncClient` per call |
| 12 | `response_format` passthrough | P2 | Done — forwarded via `_OPENAI_PARAMS` |
| 13 | `logprobs` / `top_logprobs` | P2 | Done — forwarded via `_OPENAI_PARAMS` |
| 14 | `logit_bias` | P2 | Done — forwarded via `_OPENAI_PARAMS` |
| 15 | Multimodal messages | P2 | Open — not modeled as typed content parts |
| 16 | Typed tool calling | P3 | Partial — `tools`/`tool_choice` forwarded; tool calls not parsed |
| 17 | `seed` support | P3 | Done — forwarded via `_OPENAI_PARAMS` |
| 18 | `service_tier` | P3 | Open — not in `_OPENAI_PARAMS` |
| 19 | `web_search_options` | P3 | Open — not in `_OPENAI_PARAMS` |


## 12. Multi-Provider Architecture Design

### 12.1 The Problem It Solves

The original design had ONE client that assumed ALL providers speak the OpenAI protocol. That was
fundamentally broken — hence the adapter layer described below, which is now the shipped design:

| Provider | Endpoint | Message Format | Auth | Key Differences |
|---|---|---|---|---|
| **OpenAI** | `POST /v1/chat/completions` | `messages: [{role, content}]` | Bearer token | Reference implementation |
| **Anthropic** | `POST /v1/messages` | `messages: [{role, content}]` but `system` is a **top-level field**, not a message | `x-api-key` header + `anthropic-version` header | Different payload shape entirely |
| **Google Gemini** | `POST /v1beta/models/{model}:generateContent` | `contents: [{role, parts: [{text}]}]` | `?key=` query param or OAuth | Completely different schema |
| **OpenRouter** | `POST /api/v1/chat/completions` | Same as OpenAI | Bearer token + extra headers (`HTTP-Referer`, `X-Title`) | OpenAI-compatible wrapper |
| **Ollama** | `POST /api/chat` | `messages: [{role, content}]` | None (local) | Similar but different path, no auth, different response shape |

### 12.2 Architecture: Strategy Pattern + Adapter Layer

<Figure tag="Figure 1" title="Strategy pattern — one gateway, many adapters" id="fig-adapter-strategy">
<svg viewBox="0 0 720 400" role="img" aria-label="Provider gateway routing to per-provider adapters" style="font-family:var(--vp-font-family-base)">
  <defs>
    <marker id="tbm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-arrow)"/>
    </marker>
  </defs>
  <rect x="260" y="16" width="200" height="52" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
  <text x="360" y="40" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">ChatMessageService</text>
  <text x="360" y="57" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">business logic</text>
  <rect x="250" y="104" width="220" height="56" rx="10" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/>
  <text x="360" y="128" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">ProviderGateway</text>
  <text x="360" y="145" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">facade · routes to an adapter</text>
  <g font-size="11.5" text-anchor="middle">
    <rect x="30" y="216" width="180" height="52" rx="9" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="120" y="247" fill="var(--tbm-dgm-ink)">OpenAIAdapter</text>
    <rect x="270" y="216" width="180" height="52" rx="9" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="360" y="247" fill="var(--tbm-dgm-ink)">AnthropicAdapter</text>
    <rect x="510" y="216" width="180" height="52" rx="9" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="600" y="247" fill="var(--tbm-dgm-ink)">GeminiAdapter</text>
  </g>
  <g font-size="11.5" text-anchor="middle">
    <rect x="30" y="324" width="180" height="52" rx="9" fill="var(--tbm-dgm-provider-soft)" stroke="var(--tbm-dgm-provider)"/><text x="120" y="355" fill="var(--tbm-dgm-ink)">OpenAI API</text>
    <rect x="270" y="324" width="180" height="52" rx="9" fill="var(--tbm-dgm-provider-soft)" stroke="var(--tbm-dgm-provider)"/><text x="360" y="355" fill="var(--tbm-dgm-ink)">Anthropic API</text>
    <rect x="510" y="324" width="180" height="52" rx="9" fill="var(--tbm-dgm-provider-soft)" stroke="var(--tbm-dgm-provider)"/><text x="600" y="355" fill="var(--tbm-dgm-ink)">Gemini API</text>
  </g>
  <text x="700" y="248" font-size="16" fill="var(--tbm-dgm-faint)">…</text>
  <g stroke="var(--tbm-dgm-arrow)" stroke-width="1.6" fill="none">
    <path d="M360 68 L360 102" marker-end="url(#tbm-ah)"/>
    <path d="M360 160 L360 190"/>
    <path d="M120 190 L600 190"/>
    <path d="M120 190 L120 214" marker-end="url(#tbm-ah)"/>
    <path d="M360 190 L360 214" marker-end="url(#tbm-ah)"/>
    <path d="M600 190 L600 214" marker-end="url(#tbm-ah)"/>
    <path d="M120 268 L120 322" marker-end="url(#tbm-ah)"/>
    <path d="M360 268 L360 322" marker-end="url(#tbm-ah)"/>
    <path d="M600 268 L600 322" marker-end="url(#tbm-ah)"/>
  </g>
  <text x="372" y="90" font-size="10" fill="var(--tbm-dgm-ink-2)">uses</text>
</svg>
<template #caption>

**One provider-agnostic call, translated per provider.** `ChatMessageService` speaks only to
the `ProviderGateway`; the gateway selects the adapter for the target model, and each adapter
translates the shared request into its provider's native API. Adding a provider means adding an
adapter — nothing above the gateway changes.

</template>
</Figure>

### 12.3 Key Abstractions

The canonical types live in `src/provider/adapters/base.py`. There is **no `CompletionRequest`
object** — the gateway passes an OpenAI-format `messages` list (list of `{role, content}` dicts)
and a merged `parameters` dict directly into each adapter's `build_payload()`. Only the response
and streaming shapes are typed:

```python
# ---- Shared types (provider-agnostic), src/provider/adapters/base.py ----

@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

@dataclass
class CompletionResponse:
    """Normalized non-streaming completion response."""
    content: str
    finish_reason: str
    usage: TokenUsage
    reasoning: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

@dataclass
class StreamChunk:
    """Single chunk from a streaming completion response."""
    content: str | None = None
    reasoning: str | None = None
    finish_reason: str | None = None
    usage: TokenUsage | None = None  # populated on the final chunk
```

Message roles come from the persistence layer's `MessageRole` enum (`user`, `assistant`,
`system` — no `developer` or `tool` role). `finish_reason` is a plain string that adapters
normalize toward the OpenAI vocabulary (`stop`, `length`, `tool_calls`, `content_filter`). There
are no `CompletionRequest`, `CompletionChunk`, `FinishReason`, or `ReasoningEffort` types, and
tool-call / content-part types are not yet modeled.

### 12.4 The Adapter Interface

Adapters are **stateless data transformers** — they do not make HTTP calls. The `ProviderGateway`
owns the `httpx` client, timeouts, and error handling, and calls these hooks:

```python
from abc import ABC, abstractmethod

class ProviderAdapter(ABC):
    """Transforms requests/responses between canonical format and a provider's native API."""

    @abstractmethod
    def build_url(
        self, base_url: str, model: str, stream: bool, api_key: str | None = None
    ) -> str:
        """Build the full request URL for this provider."""
        ...

    @abstractmethod
    def build_headers(self, api_key: str | None) -> dict[str, str]:
        """Build request headers (auth, content-type, version headers)."""
        ...

    @abstractmethod
    def build_payload(
        self, messages: list[dict[str, Any]], model: str, stream: bool, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Convert canonical messages + parameters into the provider's request body."""
        ...

    @abstractmethod
    def parse_response(self, data: dict[str, Any]) -> CompletionResponse:
        """Parse the provider's JSON response into a canonical CompletionResponse."""
        ...

    @abstractmethod
    def parse_stream_line(self, line: str) -> StreamChunk | None:
        """Parse a single SSE line into a StreamChunk (None to skip the line)."""
        ...

    def get_timeout(self, model: str) -> float:
        """HTTP timeout in seconds (non-abstract; defaults to 120.0)."""
        return 120.0
```

The adapter registry lives in `src/provider/adapters/__init__.py`, and `get_adapter()` resolves a
`ProviderType` to a concrete adapter class (falling back to `OpenAIAdapter`):

```python
_REGISTRY: dict[ProviderType, type[ProviderAdapter]] = {
    ProviderType.OPENAI: OpenAIAdapter,
    ProviderType.ANTHROPIC: AnthropicAdapter,
    ProviderType.GOOGLE: GeminiAdapter,
    ProviderType.XAI: OpenAIAdapter,          # OpenAI-compatible
    ProviderType.OPENROUTER: OpenAIAdapter,   # OpenAI-compatible
    ProviderType.OLLAMA: OllamaAdapter,
    ProviderType.LMSTUDIO: LMStudioAdapter,
    ProviderType.CUSTOM: OpenAIAdapter,       # Default to OpenAI-compatible
}
```

### 12.5 The Gateway (Router)

`ProviderGateway` (`src/provider/gateway.py`) is constructed per request with a `Provider` and
`Model` (plus an optional OpenRouter provider). It selects the adapter, builds the request through
the adapter's hooks, and owns the `httpx` call and error mapping:

```python
class ProviderGateway:
    """Routes requests to AI providers through the correct adapter."""

    def __init__(self, provider, model, openrouter_provider=None, preset_parameters=None):
        # model.use_openrouter routes through the OpenRouter provider with OpenAIAdapter;
        # otherwise get_adapter(provider.provider_type) picks the adapter.
        ...

    async def chat_completion(self, messages: list[dict[str, str]]) -> CompletionResponse:
        parameters = self._get_effective_parameters()
        url = self.adapter.build_url(self.base_url, self.active_identifier, False, self.api_key)
        headers = self.adapter.build_headers(self.api_key)
        payload = self.adapter.build_payload(messages, self.active_identifier, False, parameters)
        # httpx POST, raise_for_status → _handle_http_error, then adapter.parse_response(...)

    async def chat_completion_stream(
        self, messages: list[dict[str, str]]
    ) -> AsyncIterator[StreamChunk]:
        # streams SSE, calling adapter.parse_stream_line(line) per line
        ...
```


## 13. OpenAI Adapter — Implementation Spec

### 13.1 File Location

```
src/provider/
  adapters/
    __init__.py          ← registry (_REGISTRY) + get_adapter()
    base.py              ← ProviderAdapter ABC + CompletionResponse/StreamChunk/TokenUsage
    openai.py            ← OpenAIAdapter (also serves xAI, OpenRouter, CUSTOM)
    anthropic.py         ← AnthropicAdapter
    gemini.py            ← GeminiAdapter
    ollama.py            ← OllamaAdapter (subclass of OpenAIAdapter)
    lmstudio.py          ← LMStudioAdapter (subclass of OpenAIAdapter)
  gateway.py             ← ProviderGateway
  discovery.py           ← ModelDiscoveryClient implementations (local + cloud model listing)
  model_cache.py         ← ModelListCache (TTL cache of discovered models)
```

There is no separate `types.py` (canonical types live in `base.py`) and no `openrouter.py` —
OpenRouter reuses `OpenAIAdapter`. The old `client.py` has been removed.

### 13.2 OpenAIAdapter Implementation

The shipped `OpenAIAdapter` is a stateless transformer. `build_payload()` forwards only the keys
it recognizes (the `_OPENAI_PARAMS` allowlist), and it does **not** rename `max_tokens` — the
allowlist carries both `max_tokens` and `max_completion_tokens` as-is:

```python
_OPENAI_PARAMS = {
    "temperature", "top_p", "n", "stop", "max_tokens", "max_completion_tokens",
    "presence_penalty", "frequency_penalty", "logit_bias", "logprobs", "top_logprobs",
    "response_format", "seed", "tools", "tool_choice", "parallel_tool_calls",
    "reasoning_effort", "user", "stream_options",
}


class OpenAIAdapter(ProviderAdapter):
    """Adapter for OpenAI and OpenAI-compatible APIs (xAI, OpenRouter, vLLM, etc.)."""

    def build_url(self, base_url, model, stream, api_key=None) -> str:
        return f"{base_url}/chat/completions"

    def build_headers(self, api_key) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def build_payload(self, messages, model, stream, parameters) -> dict[str, Any]:
        payload = {"model": model, "messages": messages}
        if stream:
            payload["stream"] = True
        for key, value in parameters.items():
            if key in _OPENAI_PARAMS:
                payload[key] = value
        return payload

    def parse_response(self, data) -> CompletionResponse:
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage_data = data.get("usage", {})
        prompt_details = usage_data.get("prompt_tokens_details", {})
        # reasoning_content used by DeepSeek, xAI, OpenRouter reasoning models
        reasoning = message.get("reasoning_content") or message.get("reasoning") or None

        return CompletionResponse(
            content=message.get("content") or "",
            finish_reason=choice.get("finish_reason", "stop"),
            usage=TokenUsage(
                input_tokens=usage_data.get("prompt_tokens", 0),
                output_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
                cache_read_tokens=prompt_details.get("cached_tokens", 0),
            ),
            reasoning=reasoning,
            raw=data,
        )

    def parse_stream_line(self, line) -> StreamChunk | None:
        if not line.startswith("data: "):
            return None
        data_str = line[6:]
        if data_str == "[DONE]":
            return StreamChunk(finish_reason="stop")
        # json.loads(data_str) → extract choices[0].delta.content / reasoning_content,
        # finish_reason, and usage (with prompt_tokens_details.cached_tokens);
        # returns None for empty/keepalive lines.
        ...
```

Note: message roles/content are passed through as OpenAI-shaped dicts, so there is no
`_format_messages` step, no `max_tokens`→`max_completion_tokens` rewrite, and tool calls are not
parsed into typed objects.

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


## 15. Implementation Status

### Delivered (Foundation + all adapters)

```
1. src/provider/adapters/base.py
   - ProviderAdapter ABC + CompletionResponse, StreamChunk, TokenUsage
   - (no separate types.py; no CompletionRequest — messages+parameters are passed directly)

2. src/provider/adapters/openai.py
   - OpenAIAdapter: headers, URL, payload (via _OPENAI_PARAMS), response + stream parsing
   - Forwards reasoning_effort, stream_options, max_completion_tokens, etc.

3. src/provider/gateway.py
   - ProviderGateway routes by ProviderType via get_adapter(); returns typed responses
   - _get_effective_parameters() merges family defaults + model overrides + preset overrides

4. OpenAI-compatible providers
   - xAI, OpenRouter, and CUSTOM reuse OpenAIAdapter (no dedicated classes)
   - OllamaAdapter and LMStudioAdapter subclass OpenAIAdapter (local-server URL/auth/timeout)

5. Non-OpenAI providers
   - src/provider/adapters/anthropic.py — AnthropicAdapter (system top-level, x-api-key +
     anthropic-version, prompt caching, thinking, distinct response parsing)
   - src/provider/adapters/gemini.py — GeminiAdapter (contents/parts, key as query param,
     generationConfig, safetySettings, ?alt=sse streaming)

6. Model discovery
   - src/provider/discovery.py + model_cache.py provide live model listing (and load/unload
     for Ollama / LM Studio) with a TTL cache
```

### Not Yet Built

```
- Abort/cancel support (stream currently runs to completion)
- n > 1 parsing (n is forwarded, only the first choice is parsed)
- Typed tool calling and multimodal content parts
- Shared/pooled httpx client (a new AsyncClient is opened per call)
- system → developer role rewrite for o-series models
```


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
