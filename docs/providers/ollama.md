# Ollama API

> **Sources:** Ollama OpenAPI spec v0.1.0 (`ollama/ollama`, `main` branch), official docs
> **Endpoints:** Native API (`/api/*`) + OpenAI-compatible API (`/v1/*`)
> **Goal:** Define what The Bannered Mare must implement to support Ollama as a local model
> provider, and how the OllamaAdapter integrates into the multi-provider architecture
> defined in the OpenAI analysis (Sections 12 and 14).


## Table of Contents

1. [API Overview](#1-api-overview)
2. [Authentication](#2-authentication)
3. [Native Chat API -- POST /api/chat](#3-native-chat-api)
4. [Native Response Format](#4-native-response-format)
5. [Native Streaming -- NDJSON](#5-native-streaming)
6. [OpenAI-Compatible API -- POST /v1/chat/completions](#6-openai-compatible-api)
7. [Model Management Endpoints](#7-model-management-endpoints)
8. [Key Differences from OpenAI](#8-key-differences-from-openai)
9. [OllamaAdapter Implementation Spec](#9-ollamaadapter-implementation-spec)
10. [Model Discovery](#10-model-discovery)
11. [Mapping: Shared Types to Ollama API](#11-mapping-shared-types-to-ollama-api)
12. [Implementation Plan](#12-implementation-plan)


## 1. API Overview

**What is Ollama:** A local model server that downloads, manages, and runs LLMs on
the user's own hardware (CPU/GPU). No cloud dependency, no usage costs, no rate limits.

**Base URL:** `http://localhost:11434`

**Two API Modes:**

| Mode | Base Path | Format | Streaming Format | Best For |
|------|-----------|--------|------------------|----------|
| **Native API** | `/api/*` | Ollama-specific JSON | NDJSON (newline-delimited JSON) | Full feature access, model management |
| **OpenAI-compatible API** | `/v1/*` | OpenAI-compatible JSON | SSE (`text/event-stream`) | Drop-in replacement for OpenAI clients |

**Key Insight for The Bannered Mare:** The OpenAI-compatible endpoint handles chat completions
with the same request/response shape as OpenAI. The native API is needed exclusively
for model management operations (list, pull, show, delete). This means the OllamaAdapter
for chat can largely reuse OpenAI adapter logic.


## 2. Authentication

```
None.
```

- Ollama runs locally. No API keys, no bearer tokens, no headers required.
- The OpenAI-compatible endpoint accepts an `api_key` field (e.g. `"ollama"`) but
  **ignores it entirely**. This exists solely for compatibility with OpenAI client
  libraries that require a non-empty key.
- No rate limiting, no usage quotas, no billing.

**Adapter Impact:** `build_headers()` returns an empty dict (or minimal
`Content-Type: application/json`). No secrets to manage.


## 3. Native Chat API

**Endpoint:** `POST /api/chat`

### 3.1 Request Schema

```json
{
  "model": "string (required)",
  "messages": [
    {
      "role": "system | user | assistant | tool",
      "content": "string",
      "images": ["base64-encoded-string"],
      "thinking": "string (for assistant messages with thinking)",
      "tool_calls": [
        {
          "function": {
            "name": "string",
            "arguments": {}
          }
        }
      ],
      "tool_name": "string (for tool role messages)"
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "string",
        "description": "string",
        "parameters": { "JSON Schema" }
      }
    }
  ],
  "format": "json | { JSON Schema object }",
  "options": { "...generation params, see 3.2..." },
  "stream": true,
  "think": true,
  "keep_alive": "5m",
  "logprobs": false,
  "top_logprobs": null
}
```

**Critical:** `stream` defaults to **`true`**. This is the OPPOSITE of OpenAI where
`stream` defaults to `false`. The Bannered Mare must explicitly set `stream: false` for
non-streaming requests to the native API.

### 3.2 The `options` Object -- Generation Parameters

Unlike OpenAI where generation params are top-level fields, Ollama nests them inside
an `options` object. This is the single most important structural difference.

```json
{
  "options": {
    "temperature": 0.8,
    "top_p": 0.9,
    "top_k": 40,
    "min_p": 0.0,
    "seed": 42,
    "num_predict": 128,
    "num_ctx": 4096,
    "stop": ["<|end|>", "\n\n"],

    "repeat_penalty": 1.1,
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
    "repeat_last_n": 64,
    "penalize_newline": true,

    "mirostat": 0,
    "mirostat_tau": 5.0,
    "mirostat_eta": 0.1,

    "num_gpu": -1,
    "main_gpu": 0,
    "num_thread": 0,
    "num_batch": 512,
    "num_keep": 0,
    "use_mmap": true,
    "numa": false
  }
}
```

#### Parameter Reference

**Sampling Parameters (map to shared types):**

| Ollama Param | Type | Default | OpenAI Equivalent | Notes |
|---|---|---|---|---|
| `temperature` | float | model-dependent | `temperature` | Direct 1:1 mapping |
| `top_p` | float | model-dependent | `top_p` | Direct 1:1 mapping |
| `top_k` | int | model-dependent | -- | No OpenAI equivalent |
| `min_p` | float | 0.0 | -- | No OpenAI equivalent |
| `seed` | int | -- | `seed` | Direct 1:1 mapping |
| `num_predict` | int | -1 (unlimited) | `max_tokens` | **Different name.** -1 = unlimited, -2 = fill context |
| `stop` | string[] | -- | `stop` | Direct 1:1 mapping |

**Penalty Parameters:**

| Ollama Param | Type | Default | OpenAI Equivalent | Notes |
|---|---|---|---|---|
| `repeat_penalty` | float | 1.1 | `frequency_penalty` | **Different name, different scale.** Ollama uses a multiplier (1.0 = no penalty), OpenAI uses an additive value (0.0 to 2.0) |
| `presence_penalty` | float | 0.0 | `presence_penalty` | Direct 1:1 mapping |
| `frequency_penalty` | float | 0.0 | `frequency_penalty` | Also available directly in Ollama |
| `repeat_last_n` | int | 64 | -- | Window size for repetition detection |
| `penalize_newline` | bool | true | -- | No OpenAI equivalent |

**Context/Runtime Parameters (Ollama-specific):**

| Ollama Param | Type | Default | Purpose |
|---|---|---|---|
| `num_ctx` | int | 2048 | Context window size in tokens. Critical for local models. |
| `num_batch` | int | 512 | Prompt processing batch size |
| `num_keep` | int | 0 | Tokens to keep from initial prompt |

**Hardware Parameters (Ollama-specific):**

| Ollama Param | Type | Default | Purpose |
|---|---|---|---|
| `num_gpu` | int | -1 (auto) | Number of layers to offload to GPU. 0 = CPU only. |
| `main_gpu` | int | 0 | Primary GPU index for multi-GPU |
| `num_thread` | int | 0 (auto) | CPU threads for computation |
| `use_mmap` | bool | true | Memory-mapped file access |
| `numa` | bool | false | NUMA optimization |

**Mirostat Sampling (Ollama-specific, advanced):**

| Ollama Param | Type | Default | Purpose |
|---|---|---|---|
| `mirostat` | int | 0 | 0 = disabled, 1 = Mirostat, 2 = Mirostat 2.0 |
| `mirostat_tau` | float | 5.0 | Target entropy (perplexity) |
| `mirostat_eta` | float | 0.1 | Learning rate |

### 3.3 The `keep_alive` Parameter

Controls how long a model stays loaded in GPU/CPU memory after a request.

- Default: `"5m"` (5 minutes)
- `"0"` or `0`: Unload immediately after response
- `"-1"` or `-1`: Keep loaded indefinitely
- Duration strings: `"10m"`, `"1h"`, `"30s"`

**Relevance for The Bannered Mare:** For roleplay sessions, setting `keep_alive` to a longer
duration (e.g. `"30m"` or `"-1"`) avoids the latency of reloading the model between
messages. This should be configurable per-provider in The Bannered Mare settings.

### 3.4 The `format` Parameter -- Structured Outputs

Two modes:

```json
"format": "json"
```
Forces JSON output (equivalent to OpenAI `response_format: {"type": "json_object"}`).

```json
"format": {
  "type": "object",
  "properties": {
    "name": {"type": "string"},
    "age": {"type": "integer"}
  },
  "required": ["name", "age"]
}
```
Provides a full JSON schema, constraining the model output to match the schema.
This is more powerful than OpenAI's basic `json_object` mode and closer to OpenAI's
`json_schema` response format.

### 3.5 The `think` Parameter -- Reasoning/Thinking Models

Controls whether thinking-capable models (e.g. QwQ, DeepSeek-R1) emit their
reasoning trace.

- `true`: Enable thinking output
- `false`: Disable thinking
- `"high"`, `"medium"`, `"low"`: Granular thinking effort control

When enabled, responses include a `thinking` field alongside `content`.

### 3.6 Tool Calling

Tool definition format is identical to OpenAI:

```json
{
  "type": "function",
  "function": {
    "name": "get_weather",
    "description": "Get weather for a location",
    "parameters": {
      "type": "object",
      "properties": {
        "location": {"type": "string"}
      },
      "required": ["location"]
    }
  }
}
```

**Key differences from OpenAI tool calling:**

1. Tool call responses use `tool_name` field (not matched by `tool_call_id`):
   ```json
   {"role": "tool", "tool_name": "get_weather", "content": "22C sunny"}
   ```
2. Tool calls in assistant messages include an `index` field inside `function`:
   ```json
   {
     "tool_calls": [{
       "type": "function",
       "function": {"index": 0, "name": "get_weather", "arguments": {"location": "Paris"}}
     }]
   }
   ```
3. No `tool_call_id` field -- tools are correlated by name and order, not by ID.
4. `tool_choice` is NOT supported (model always decides autonomously).
5. Parallel tool calling is supported (multiple tool_calls in one response).

### 3.7 Vision / Image Support

Images are passed as base64 strings in the `images` array within a message:

```json
{
  "role": "user",
  "content": "What is in this image?",
  "images": ["iVBORw0KGgo..."]
}
```

This differs from OpenAI's content-parts approach. The native API uses a flat `images`
array, not structured content parts. The OpenAI-compatible endpoint, however, accepts
the standard OpenAI multipart content format.


## 4. Native Response Format

### 4.1 Non-Streaming Response (stream: false)

```json
{
  "model": "gemma3",
  "created_at": "2025-10-17T23:14:07.414671Z",
  "message": {
    "role": "assistant",
    "content": "The sky is blue because...",
    "thinking": "Let me reason about this...",
    "tool_calls": [],
    "images": []
  },
  "done": true,
  "done_reason": "stop",
  "total_duration": 174560334,
  "load_duration": 101397084,
  "prompt_eval_count": 11,
  "prompt_eval_duration": 13074791,
  "eval_count": 18,
  "eval_duration": 52479709
}
```

### 4.2 Response Field Reference

| Field | Type | Description |
|---|---|---|
| `model` | string | Model name used |
| `created_at` | string | ISO 8601 timestamp |
| `message` | object | The assistant message |
| `message.role` | string | Always `"assistant"` |
| `message.content` | string | Generated text |
| `message.thinking` | string | Reasoning trace (when `think` enabled) |
| `message.tool_calls` | array | Tool invocation requests |
| `done` | bool | Whether generation is complete |
| `done_reason` | string | `"stop"`, `"load"`, or `"unload"` |
| `total_duration` | int | Total time in **nanoseconds** |
| `load_duration` | int | Model load time in nanoseconds |
| `prompt_eval_count` | int | Input token count (equivalent to `prompt_tokens`) |
| `prompt_eval_duration` | int | Prompt evaluation time in nanoseconds |
| `eval_count` | int | Output token count (equivalent to `completion_tokens`) |
| `eval_duration` | int | Generation time in nanoseconds |

**Performance Metrics:** Ollama provides detailed timing breakdowns that OpenAI does
not. These are useful for monitoring local model performance but are not part of the
shared `TokenUsage` abstraction. Store in `CompletionResponse.raw` for observability.

### 4.3 Mapping to TokenUsage

```python
TokenUsage(
    prompt_tokens=response["prompt_eval_count"],
    completion_tokens=response["eval_count"],
    total_tokens=response["prompt_eval_count"] + response["eval_count"],
    reasoning_tokens=0,
    cached_tokens=0,
)
```

### 4.4 Mapping to FinishReason

| Ollama `done_reason` | Shared `FinishReason` |
|---|---|
| `"stop"` | `FinishReason.STOP` |
| (tool_calls present) | `FinishReason.TOOL_CALLS` |
| (no done_reason, eval_count == num_predict) | `FinishReason.LENGTH` |

Ollama does not have explicit `"length"` or `"content_filter"` done reasons.
The adapter must infer `LENGTH` when the generation was truncated by `num_predict`.


## 5. Native Streaming -- NDJSON

**Format:** Newline-Delimited JSON (NDJSON), NOT Server-Sent Events (SSE).

This is the most critical protocol difference from OpenAI. Each line in the response
body is a complete, self-contained JSON object terminated by `\n`.

### 5.1 Stream Format

```
{"model":"gemma3","created_at":"2025-10-17T23:14:07.414671Z","message":{"role":"assistant","content":"The"},"done":false}
{"model":"gemma3","created_at":"2025-10-17T23:14:07.415000Z","message":{"role":"assistant","content":" sky"},"done":false}
{"model":"gemma3","created_at":"2025-10-17T23:14:07.415500Z","message":{"role":"assistant","content":" is"},"done":false}
...
{"model":"gemma3","created_at":"2025-10-17T23:14:08.000000Z","message":{"role":"assistant","content":""},"done":true,"done_reason":"stop","total_duration":174560334,"load_duration":101397084,"prompt_eval_count":11,"prompt_eval_duration":13074791,"eval_count":18,"eval_duration":52479709}
```

### 5.2 Key Differences from SSE

| Aspect | Ollama NDJSON | OpenAI SSE |
|---|---|---|
| Line prefix | None | `data: ` |
| Line terminator | `\n` | `\n\n` |
| End signal | `"done": true` in JSON | `data: [DONE]` |
| Content-Type | `application/x-ndjson` | `text/event-stream` |
| Parsing | `json.loads(line)` | Strip `data: ` prefix, then `json.loads()` |

### 5.3 Streaming with Tool Calls

When streaming, tool calls arrive in chunks. The client must accumulate the partial
`tool_calls` array across chunks. The final chunk with `done: true` contains the
complete call data.

### 5.4 Streaming with Thinking

When `think: true`, chunks alternate between `thinking` and `content` fields:

```json
{"message": {"thinking": "Let me "}, "done": false}
{"message": {"thinking": "consider..."}, "done": false}
{"message": {"content": "The answer"}, "done": false}
{"message": {"content": " is 42."}, "done": true, ...}
```


## 6. OpenAI-Compatible API

**Endpoint:** `POST /v1/chat/completions`

This is the recommended endpoint for The Bannered Mare chat completions. It speaks the
OpenAI protocol, which means the OpenAI adapter logic can be largely reused.

### 6.1 Supported Features

- [x] Chat completions
- [x] Streaming (SSE, same format as OpenAI)
- [x] JSON mode (`response_format`)
- [x] Reproducible outputs (`seed`)
- [x] Vision (base64 images via content parts)
- [x] Tools / function calling
- [x] Reasoning / thinking control (`reasoning_effort`)
- [ ] Logprobs (not supported)

### 6.2 Supported Request Fields

| Field | Supported | Notes |
|---|---|---|
| `model` | Yes | |
| `messages` | Yes | Text, image (base64 only, not URL), content part arrays |
| `temperature` | Yes | |
| `top_p` | Yes | |
| `max_tokens` | Yes | Mapped internally to `num_predict` |
| `stop` | Yes | |
| `stream` | Yes | Defaults to `false` (OpenAI convention) |
| `stream_options.include_usage` | Yes | |
| `seed` | Yes | |
| `frequency_penalty` | Yes | |
| `presence_penalty` | Yes | |
| `response_format` | Yes | `json_object` type supported |
| `tools` | Yes | |
| `reasoning_effort` | Yes | `"high"`, `"medium"`, `"low"`, `"none"` |
| `tool_choice` | **No** | Always model-decided |
| `logit_bias` | **No** | |
| `n` | **No** | Always generates 1 completion |
| `user` | **No** | |
| `logprobs` | **No** | |
| `top_logprobs` | **No** | |

### 6.3 Unsupported OpenAI Features

These features exist in the OpenAI API but are NOT available through Ollama's
compatible endpoint:

1. **`tool_choice`** -- Cannot force a specific tool or "none"/"required" mode.
2. **`n`** -- Cannot request multiple completions. Always 1.
3. **`logit_bias`** -- No token-level probability manipulation.
4. **`logprobs` / `top_logprobs`** -- No log probability output.
5. **`user`** -- No user tracking field.
6. **Image URLs** -- Only base64-encoded images. Cannot pass HTTP URLs.
7. **Audio content** -- Not supported.
8. **`max_completion_tokens`** -- Use `max_tokens` instead.
9. **Structured output (`json_schema`)** -- Use `"json"` format or the native API's
   schema-based `format` field.

### 6.4 Response Format

Identical to OpenAI. Example:

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gemma3",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "The sky is blue because..."
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 11,
    "completion_tokens": 18,
    "total_tokens": 29
  }
}
```

### 6.5 Streaming Format

Standard SSE, identical to OpenAI:

```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gemma3","choices":[{"index":0,"delta":{"role":"assistant","content":"The"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gemma3","choices":[{"index":0,"delta":{"content":" sky"},"finish_reason":null}]}

data: [DONE]
```

### 6.6 Context Size Limitation

The OpenAI-compatible API has no parameter for `num_ctx` (context window size).
To control context size, you must either:

1. Create a custom Modelfile with `PARAMETER num_ctx <size>` and use that model name
2. Use the native `/api/chat` endpoint with `options.num_ctx`

This is a notable gap. For roleplay sessions with long context requirements, the
native API or pre-configured models may be necessary.


## 7. Model Management Endpoints

These endpoints have NO OpenAI equivalent and must use the native API directly.

### 7.1 GET /api/tags -- List Local Models

```json
// Response
{
  "models": [
    {
      "name": "gemma3:latest",
      "model": "gemma3:latest",
      "modified_at": "2025-01-15T10:30:00Z",
      "size": 4661224676,
      "digest": "sha256:abc123...",
      "details": {
        "format": "gguf",
        "family": "gemma",
        "families": ["gemma"],
        "parameter_size": "4B",
        "quantization_level": "Q4_K_M"
      }
    }
  ]
}
```

Also available as OpenAI-compatible: `GET /v1/models` (returns OpenAI-format model list).

### 7.2 POST /api/show -- Model Information

```json
// Request
{"model": "gemma3", "verbose": false}

// Response
{
  "parameters": "stop \"<|end|>\"\nnum_ctx 4096",
  "license": "...",
  "template": "{{ .System }}\n{{ .Prompt }}",
  "details": {
    "format": "gguf",
    "family": "gemma",
    "parameter_size": "4B",
    "quantization_level": "Q4_K_M"
  },
  "capabilities": ["completion", "vision"],
  "model_info": {"...architecture metadata..."},
  "modified_at": "2025-01-15T10:30:00Z"
}
```

**Key field:** `capabilities` -- tells us if a model supports vision, tool calling, etc.
Useful for The Bannered Mare to auto-detect model features.

### 7.3 POST /api/pull -- Download Model

```json
// Request
{"model": "gemma3:latest", "stream": true}

// Response (streaming NDJSON)
{"status": "pulling manifest"}
{"status": "pulling sha256:abc123", "digest": "sha256:abc123", "total": 4661224676, "completed": 1048576}
{"status": "pulling sha256:abc123", "digest": "sha256:abc123", "total": 4661224676, "completed": 2097152}
...
{"status": "verifying sha256 digest"}
{"status": "writing manifest"}
{"status": "removing any unused layers"}
{"status": "success"}
```

### 7.4 DELETE /api/delete -- Remove Model

```json
// Request
{"model": "gemma3:latest"}

// Response: 200 OK (empty) or 404 Not Found
```

### 7.5 POST /api/generate -- Text Completion (non-chat)

Similar to `/api/chat` but for single-turn text completion without message history.
Not directly relevant for The Bannered Mare's chat-based architecture.

### 7.6 GET /api/ps -- Running Models

Lists models currently loaded in memory:

```json
{
  "models": [
    {
      "name": "gemma3:latest",
      "model": "gemma3:latest",
      "size": 4661224676,
      "digest": "sha256:abc123",
      "expires_at": "2025-01-15T10:35:00Z",
      "size_vram": 3221225472,
      "context_length": 4096
    }
  ]
}
```

**Useful for The Bannered Mare:** Can check if a model is already loaded before sending a
request, and display VRAM usage to the user.

### 7.7 POST /api/embed -- Embeddings

```json
// Request
{"model": "nomic-embed-text", "input": "Hello world"}

// Response
{
  "model": "nomic-embed-text",
  "embeddings": [[0.123, -0.456, ...]],
  "total_duration": 50000000,
  "load_duration": 10000000,
  "prompt_eval_count": 3
}
```

### 7.8 GET /api/version

```json
{"version": "0.6.2"}
```


## 8. Key Differences from OpenAI

### 8.1 Summary Table

| Aspect | OpenAI | Ollama (Native) | Ollama (OpenAI-compat) |
|---|---|---|---|
| **Base URL** | `https://api.openai.com/v1` | `http://localhost:11434/api` | `http://localhost:11434/v1` |
| **Port** | 443 (HTTPS) | 11434 (HTTP) | 11434 (HTTP) |
| **Auth** | Bearer token | None | None (accepts dummy key) |
| **Chat endpoint** | `POST /v1/chat/completions` | `POST /api/chat` | `POST /v1/chat/completions` |
| **stream default** | `false` | **`true`** | `false` |
| **Streaming format** | SSE | **NDJSON** | SSE |
| **Param placement** | Top-level fields | Nested in `options` | Top-level fields |
| **max_tokens param** | `max_tokens` / `max_completion_tokens` | `options.num_predict` | `max_tokens` |
| **Context window** | Model-determined | `options.num_ctx` | Not configurable |
| **Tool result ID** | `tool_call_id` | `tool_name` | `tool_call_id` (OpenAI format) |
| **Image input** | Content parts with `image_url` | `images` array (base64) | Content parts (base64 only) |
| **Model management** | N/A (cloud) | Full CRUD (pull, delete, show, list) | `GET /v1/models` (list only) |
| **Hardware params** | N/A | `num_gpu`, `num_thread`, etc. | N/A |
| **Finish reasons** | `stop`, `length`, `tool_calls`, `content_filter` | `stop`, `load`, `unload` | `stop`, `length`, `tool_calls` |
| **Token usage** | `usage.prompt_tokens`, `usage.completion_tokens` | `prompt_eval_count`, `eval_count` | `usage.prompt_tokens`, `usage.completion_tokens` |
| **Timing metrics** | None | `total_duration`, `load_duration`, etc. (nanoseconds) | None |
| **Multi-completion (n)** | Supported | Not supported | Not supported |
| **tool_choice** | Supported | Not supported | Not supported |
| **logprobs** | Supported | Supported (native only) | Not supported |

### 8.2 Critical Behavioral Differences

1. **Stream defaults to TRUE (native API).** Every non-streaming call to the native
   API must explicitly pass `"stream": false`. Forgetting this will return NDJSON
   chunks instead of a single response object.

2. **Options nesting.** Generation params go INSIDE the `options` object on the native
   API, not as top-level fields. The OpenAI-compatible API uses top-level fields.

3. **No tool_call_id.** The native API uses `tool_name` to correlate tool results
   with tool calls, not a unique ID. The OpenAI-compatible endpoint wraps this in
   the standard `tool_call_id` format.

4. **Model cold-start latency.** Unlike cloud APIs, the first request to a model
   incurs model loading time (can be seconds to minutes depending on model size
   and hardware). The `load_duration` field reports this. Subsequent requests
   within the `keep_alive` window are fast.

5. **No content filtering.** Ollama models have no built-in content filter. The
   `content_filter` finish reason never occurs. This is relevant for The Bannered Mare's
   roleplay use case where content filtering would be undesirable.


## 9. OllamaAdapter Implementation Spec

### 9.1 Strategy Decision

**Two implementation strategies:**

| Strategy | Approach | Pros | Cons |
|---|---|---|---|
| **Option A** | Use OpenAI-compatible `/v1/*` for chat | Reuse OpenAIAdapter logic, same SSE parsing, same response format | Cannot set `num_ctx`, no hardware params, fewer features |
| **Option B** | Use native `/api/*` for everything | Full feature access, `num_ctx`, hardware params, performance metrics | Must implement NDJSON parser, different response mapping |

**Recommendation: Option A for chat completions, native API for model management.**

The OllamaAdapter should subclass or delegate to the OpenAIAdapter for chat
operations, with a separate `OllamaModelManager` component for native API operations.

Rationale:
- Chat completions via `/v1/chat/completions` work identically to OpenAI, so the
  parsing, streaming, and response mapping code is reusable.
- Model management (list, pull, delete, show) has no OpenAI equivalent and must
  use the native API regardless.
- The main feature lost by using the compat endpoint is `num_ctx` configuration,
  which can be worked around with Modelfiles or could be added as a hybrid call
  to the native API when needed.

### 9.2 Class Design

```python
class OllamaAdapter(OpenAIAdapter):
    """
    Uses the OpenAI-compatible endpoint for chat completions.
    Overrides connection params (no auth, local URL).
    """

    def build_headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    def build_url(self, model: str) -> str:
        # provider.base_url = "http://localhost:11434"
        return f"{self.provider.base_url}/v1/chat/completions"

    def build_payload(self, request: CompletionRequest) -> dict[str, Any]:
        payload = super().build_payload(request)
        # Ollama does not support these fields
        payload.pop("logit_bias", None)
        payload.pop("user", None)
        payload.pop("logprobs", None)
        payload.pop("top_logprobs", None)

        # If extra contains Ollama-specific options, handle them
        if request.extra:
            if "keep_alive" in request.extra:
                payload["keep_alive"] = request.extra["keep_alive"]
            if "num_ctx" in request.extra:
                # num_ctx not supported on /v1/, would need native API
                pass

        return payload

    # parse_response() inherited from OpenAIAdapter (same format)
    # parse_stream_chunk() inherited from OpenAIAdapter (same SSE format)


class OllamaModelManager:
    """
    Handles Ollama-specific model management via the native API.
    NOT part of the ProviderAdapter interface.
    """

    def __init__(self, base_url: str, client: httpx.AsyncClient):
        self.base_url = base_url
        self.client = client

    async def list_models(self) -> list[OllamaModelInfo]:
        """GET /api/tags"""
        ...

    async def show_model(self, model: str) -> OllamaModelDetail:
        """POST /api/show"""
        ...

    async def pull_model(self, model: str) -> AsyncIterator[PullProgress]:
        """POST /api/pull (streaming NDJSON)"""
        ...

    async def delete_model(self, model: str) -> bool:
        """DELETE /api/delete"""
        ...

    async def list_running(self) -> list[OllamaRunningModel]:
        """GET /api/ps"""
        ...
```

### 9.3 Provider Configuration

```python
# In the Provider model / config
Provider(
    name="Local Ollama",
    provider_type=ProviderType.OLLAMA,
    base_url="http://localhost:11434",
    api_key=None,           # No auth needed
    extra_config={
        "keep_alive": "30m",     # Keep models loaded for roleplay sessions
        "default_num_ctx": 8192, # Default context window
    }
)
```

### 9.4 NDJSON Parser (for model management streaming)

Required only for `POST /api/pull` and other native streaming endpoints:

```python
async def parse_ndjson_stream(
    response: httpx.Response,
) -> AsyncIterator[dict[str, Any]]:
    async for line in response.aiter_lines():
        line = line.strip()
        if not line:
            continue
        yield json.loads(line)
```


## 10. Model Discovery

### 10.1 Auto-Discovery via GET /api/tags

Ollama can report all locally available models. This is critical for The Bannered Mare's
UX -- users should see which models are available without manual configuration.

```python
async def discover_models(base_url: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{base_url}/api/tags")
        data = resp.json()
        return [
            {
                "id": m["name"],
                "name": m["name"],
                "family": m["details"]["family"],
                "parameter_size": m["details"]["parameter_size"],
                "quantization": m["details"]["quantization_level"],
                "size_bytes": m["size"],
                "capabilities": [],  # Use /api/show for this
            }
            for m in data.get("models", [])
        ]
```

### 10.2 Capability Detection via POST /api/show

The `capabilities` field in the show response indicates what a model can do:

```json
{"capabilities": ["completion", "vision", "tools"]}
```

This allows The Bannered Mare to:
- Only show vision models when image input is needed
- Only offer tool calling for models that support it
- Filter models by capability in the UI

### 10.3 Model Naming Convention

Format: `name:tag` with optional namespace.

- `llama3.2:latest` -- name with default tag
- `llama3.2:70b` -- name with size tag
- `llama3.2:70b-q4_K_M` -- name with size and quantization
- `myuser/custom-model:v1` -- namespaced model

Tag defaults to `latest` if omitted.

### 10.4 OpenAI-Compatible Model Listing

`GET /v1/models` returns the same models in OpenAI format:

```json
{
  "object": "list",
  "data": [
    {
      "id": "gemma3:latest",
      "object": "model",
      "created": 1737000000,
      "owned_by": "library"
    }
  ]
}
```

Note: `owned_by` defaults to `"library"` for Ollama Hub models, or the namespace
for custom models.


## 11. Mapping: Shared Types to Ollama API

This section maps the provider-agnostic types from the OpenAI analysis (Section 14)
to the Ollama-specific values. Since we use the OpenAI-compatible endpoint for chat,
most mappings are identical to the OpenAI adapter.

### 11.1 CompletionRequest to Ollama /v1/chat/completions

```python
def build_payload(request: CompletionRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": request.model,
        "messages": [format_message(m) for m in request.messages],
        "stream": request.stream,
    }

    # Direct 1:1 mappings (same as OpenAI)
    if request.temperature is not None:
        payload["temperature"] = request.temperature
    if request.top_p is not None:
        payload["top_p"] = request.top_p
    if request.max_tokens is not None:
        payload["max_tokens"] = request.max_tokens
    if request.stop:
        payload["stop"] = request.stop
    if request.seed is not None:
        payload["seed"] = request.seed
    if request.frequency_penalty is not None:
        payload["frequency_penalty"] = request.frequency_penalty
    if request.presence_penalty is not None:
        payload["presence_penalty"] = request.presence_penalty

    # Reasoning effort mapping
    if request.reasoning_effort is not None:
        payload["reasoning_effort"] = request.reasoning_effort.value

    # Stream options
    if request.stream and request.stream_include_usage:
        payload["stream_options"] = {"include_usage": True}

    # Response format
    if request.response_format:
        payload["response_format"] = request.response_format.to_dict()

    # Tools
    if request.tools:
        payload["tools"] = [t.to_dict() for t in request.tools]
    # Note: tool_choice NOT supported, skip even if set

    # Ollama-specific extras
    if request.extra:
        if "keep_alive" in request.extra:
            payload["keep_alive"] = request.extra["keep_alive"]

    # Unsupported fields intentionally omitted:
    # - n (always 1)
    # - logit_bias
    # - logprobs / top_logprobs
    # - user

    return payload
```

### 11.2 Ollama Response to CompletionResponse

Via the OpenAI-compatible endpoint, the response is already in OpenAI format.
The `parse_response()` method inherited from `OpenAIAdapter` works as-is:

```python
# Inherited from OpenAIAdapter -- no override needed
def parse_response(self, raw: dict[str, Any]) -> CompletionResponse:
    choice = raw["choices"][0]
    message = choice["message"]
    usage_data = raw.get("usage")

    return CompletionResponse(
        id=raw["id"],
        content=message.get("content"),
        finish_reason=self._map_finish_reason(choice.get("finish_reason")),
        usage=TokenUsage(
            prompt_tokens=usage_data["prompt_tokens"],
            completion_tokens=usage_data["completion_tokens"],
            total_tokens=usage_data["total_tokens"],
        ) if usage_data else None,
        tool_calls=self._parse_tool_calls(message.get("tool_calls")),
        model=raw.get("model"),
        raw=raw,
    )
```

### 11.3 ChatMessage to Ollama Message

Via the OpenAI-compatible endpoint, message format is standard:

```python
def format_message(msg: ChatMessage) -> dict[str, Any]:
    result: dict[str, Any] = {"role": msg.role.value}

    if isinstance(msg.content, str):
        result["content"] = msg.content
    elif isinstance(msg.content, list):
        # Content parts -- supported for vision
        result["content"] = [format_content_part(p) for p in msg.content]

    if msg.tool_calls:
        result["tool_calls"] = [tc.to_dict() for tc in msg.tool_calls]
    if msg.tool_call_id:
        result["tool_call_id"] = msg.tool_call_id

    return result
```

### 11.4 Fields NOT Mappable

| Shared Type Field | Status | Reason |
|---|---|---|
| `CompletionRequest.n` | Ignored | Ollama always generates 1 |
| `CompletionRequest.logit_bias` | Ignored | Not supported |
| `CompletionRequest.logprobs` | Ignored | Not supported via compat endpoint |
| `CompletionRequest.top_logprobs` | Ignored | Not supported via compat endpoint |
| `CompletionRequest.tool_choice` | Ignored | Not supported |
| `CompletionResponse.refusal` | Always None | No content filtering |
| `TokenUsage.reasoning_tokens` | Always 0 | Not reported separately |
| `TokenUsage.cached_tokens` | Always 0 | Not applicable to local models |

### 11.5 Ollama-Specific Fields (via `extra`)

Fields unique to Ollama that may be passed through `CompletionRequest.extra`:

```python
request = CompletionRequest(
    model="gemma3:latest",
    messages=[...],
    temperature=0.8,
    extra={
        "keep_alive": "30m",
        "num_ctx": 8192,        # Only effective via native API
        "num_gpu": -1,          # Only effective via native API
        "top_k": 40,            # Only effective via native API
        "mirostat": 2,          # Only effective via native API
    }
)
```


## 12. Implementation Plan

### Phase 1: OllamaAdapter for Chat (via OpenAI-compatible endpoint)

```
1. Create src/provider/adapters/ollama.py
   - OllamaAdapter subclassing OpenAIAdapter
   - Override build_headers() -- no auth
   - Override build_url() -- http://localhost:11434/v1/chat/completions
   - Override build_payload() -- strip unsupported fields, add keep_alive
   - Inherit parse_response() and parse_stream_chunk() from OpenAIAdapter

2. Register in ProviderGateway
   - ProviderType.OLLAMA -> OllamaAdapter

3. Test with local Ollama instance
   - Non-streaming chat completion
   - Streaming chat completion
   - Tool calling (if model supports it)
   - Vision (if model supports it)
```

### Phase 2: Model Management

```
4. Create src/provider/ollama/model_manager.py
   - OllamaModelManager class
   - list_models() -- GET /api/tags
   - show_model() -- POST /api/show
   - list_running() -- GET /api/ps

5. Create src/provider/ollama/schemas.py
   - OllamaModelInfo (Pydantic model for /api/tags response)
   - OllamaModelDetail (Pydantic model for /api/show response)
   - OllamaRunningModel (Pydantic model for /api/ps response)

6. Expose model management in router
   - GET /api/providers/ollama/models -- list available models
   - GET /api/providers/ollama/models/{model} -- show model info
   - GET /api/providers/ollama/models/running -- list loaded models
```

### Phase 3: Model Pull/Delete (Optional, nice-to-have)

```
7. Add pull/delete support
   - POST /api/providers/ollama/models/pull -- download a model
     - Stream progress via SSE to frontend
     - Parse NDJSON from Ollama, re-emit as SSE
   - DELETE /api/providers/ollama/models/{model} -- remove a model

8. Create NDJSON stream parser utility
   - parse_ndjson_stream() in src/core/streaming.py
   - Reusable for any NDJSON source
```

### Phase 4: Enhanced Ollama Features (Future)

```
9. Native API fallback for advanced features
   - When num_ctx is specified, use /api/chat instead of /v1/chat/completions
   - Build native API payload with options object
   - Parse NDJSON stream into CompletionChunk

10. Capability auto-detection
    - On provider connection, call /api/tags + /api/show for each model
    - Cache capabilities (vision, tools, etc.)
    - Surface in model selection UI

11. Performance dashboard
    - Expose timing metrics (load_duration, eval_duration, etc.)
    - Tokens/second calculation: eval_count / (eval_duration / 1e9)
    - VRAM usage from /api/ps
```


## Appendix A: Quick Reference -- Endpoint Cheat Sheet

| Operation | Method | Path | Body |
|---|---|---|---|
| Chat (OpenAI compat) | POST | `/v1/chat/completions` | OpenAI format |
| Chat (native) | POST | `/api/chat` | Ollama format |
| Text completion | POST | `/api/generate` | `{model, prompt, ...}` |
| List models | GET | `/api/tags` | -- |
| List models (OpenAI) | GET | `/v1/models` | -- |
| Show model info | POST | `/api/show` | `{model}` |
| Pull model | POST | `/api/pull` | `{model}` |
| Delete model | DELETE | `/api/delete` | `{model}` |
| List running | GET | `/api/ps` | -- |
| Embeddings | POST | `/api/embed` | `{model, input}` |
| Embeddings (OpenAI) | POST | `/v1/embeddings` | OpenAI format |
| Version | GET | `/api/version` | -- |

## Appendix B: Quick Reference -- Parameter Name Mapping

| Shared / OpenAI Name | Ollama Native Name | Placement |
|---|---|---|
| `temperature` | `temperature` | `options.temperature` |
| `top_p` | `top_p` | `options.top_p` |
| `max_tokens` | `num_predict` | `options.num_predict` |
| `stop` | `stop` | `options.stop` |
| `seed` | `seed` | `options.seed` |
| `frequency_penalty` | `frequency_penalty` | `options.frequency_penalty` |
| `presence_penalty` | `presence_penalty` | `options.presence_penalty` |
| -- | `top_k` | `options.top_k` |
| -- | `min_p` | `options.min_p` |
| -- | `num_ctx` | `options.num_ctx` |
| -- | `repeat_penalty` | `options.repeat_penalty` |
| -- | `num_gpu` | `options.num_gpu` |
| -- | `num_thread` | `options.num_thread` |
| -- | `mirostat` | `options.mirostat` |
| `stream` | `stream` | Top-level |
| -- | `keep_alive` | Top-level |
| `response_format` | `format` | Top-level |
| `tools` | `tools` | Top-level |
