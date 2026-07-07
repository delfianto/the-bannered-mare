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

### 3.2 The `options` Object — Generation Parameters

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

### 3.4 The `format` Parameter — Structured Outputs

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

### 3.5 The `think` Parameter — Reasoning/Thinking Models

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

The shipped `TokenUsage` uses `input_tokens`/`output_tokens` (not `prompt_tokens`/
`completion_tokens`). Note: this native-API mapping is illustrative — the `OllamaAdapter`
actually reads OpenAI-shaped usage from the `/v1/*` endpoint via the inherited `parse_response`.

```python
TokenUsage(
    input_tokens=response["prompt_eval_count"],
    output_tokens=response["eval_count"],
    total_tokens=response["prompt_eval_count"] + response["eval_count"],
    cache_read_tokens=0,
    cache_creation_tokens=0,
)
```

### 4.4 Mapping to finish_reason

`CompletionResponse.finish_reason` is a plain string (there is no `FinishReason` enum). Via the
OpenAI-compatible endpoint the inherited parser reads `choices[0].finish_reason` directly.

| Ollama `done_reason` | Normalized `finish_reason` |
|---|---|
| `"stop"` | `"stop"` |
| (tool_calls present) | `"tool_calls"` |
| (truncated by `num_predict`) | `"length"` |

Ollama does not have explicit `"length"` or `"content_filter"` done reasons in its native API.


## 5. Native Streaming — NDJSON

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

### 7.1 GET /api/tags — List Local Models

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

### 7.2 POST /api/show — Model Information

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

### 7.3 POST /api/pull — Download Model

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

### 7.4 DELETE /api/delete — Remove Model

```json
// Request
{"model": "gemma3:latest"}

// Response: 200 OK (empty) or 404 Not Found
```

### 7.5 POST /api/generate — Text Completion (non-chat)

Similar to `/api/chat` but for single-turn text completion without message history.
Not directly relevant for The Bannered Mare's chat-based architecture.

### 7.6 GET /api/ps — Running Models

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

### 7.7 POST /api/embed — Embeddings

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

The shipped `OllamaAdapter` (`src/provider/adapters/ollama.py`) is a thin subclass of
`OpenAIAdapter` — it overrides only the URL, headers, and timeout. It does **not** override
`build_payload()`, so parameters pass through the inherited `_OPENAI_PARAMS` allowlist unchanged
(there is no field-popping or `keep_alive`/`num_ctx` handling):

```python
class OllamaAdapter(OpenAIAdapter):
    """Adapter for Ollama's OpenAI-compatible /v1/chat/completions endpoint."""

    def build_url(self, base_url, model, stream, api_key=None) -> str:
        return f"{base_url}/v1/chat/completions"

    def build_headers(self, api_key) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    def get_timeout(self, model: str) -> float:
        return 300.0  # local inference can be slow on first load / large models

    # build_payload(), parse_response(), parse_stream_line() inherited from OpenAIAdapter
```

Model management (list, load/unload, pull, delete) lives outside the adapter, in the
`ModelDiscoveryClient` protocol implemented by `OllamaDiscoveryClient`
(`src/provider/discovery.py`) — it is **not** part of the `ProviderAdapter` interface:

```python
class OllamaDiscoveryClient:
    """Ollama's native API: /api/tags (installed), /api/ps (loaded)."""

    def list_models(self, base_url, api_key=None) -> list[DiscoveredModel]:
        """GET /api/tags + GET /api/ps to mark which models are loaded."""
        ...

    def load_model(self, base_url, identifier) -> None:
        """POST /api/generate with keep_alive=-1 (unload uses keep_alive=0)."""
        ...

    def unload_model(self, base_url, identifier) -> None: ...

    def delete_model(self, base_url, identifier) -> None:
        """DELETE /api/delete"""
        ...
```

Note: there is no `pull`/`show` in the discovery client and no `num_ctx`/`keep_alive`
plumbing today; discovery results are cached in `ModelListCache` (`src/provider/model_cache.py`).

### 9.3 Provider Configuration

The `Provider` model stores no API key value and no per-provider `extra_config`/`keep_alive`.
Auth is by env-var name (`api_key_env_var`, which is `None` for Ollama since no key is required),
and Ollama is seeded from `PROVIDER_CONFIGS` with `requires_api_key=False`:

```python
Provider(
    name="Ollama",
    provider_type=ProviderType.OLLAMA,
    base_url="http://localhost:11434",   # or the OLLAMA_HOST override at seed time
    api_key_env_var=None,                # no auth needed
    enabled=True,
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

This is implemented by `OllamaDiscoveryClient.list_models()` (`src/provider/discovery.py`), which
calls `GET /api/tags` (installed) plus `GET /api/ps` (loaded) and returns typed `DiscoveredModel`
records — `identifier`, `display_name`, `state` (`loaded`/`not-loaded`), `size_bytes`, and
`quantization` (from `details.quantization_level`). `max_context_length` is left `None` because it
would require a per-model `/api/show` call, which the client does not make today.

```python
# Shape returned per model (DiscoveredModel), sync httpx.Client throughout:
DiscoveredModel(
    identifier=m["model"],
    display_name=m.get("name", m["model"]),
    state="loaded" if m["model"] in loaded_names else "not-loaded",
    size_bytes=m.get("size"),
    quantization=(m.get("details") or {}).get("quantization_level"),
    max_context_length=None,
)
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

### 11.1 Payload, response, and message mapping

Because `OllamaAdapter` inherits `build_payload()`, `parse_response()`, and `parse_stream_line()`
from `OpenAIAdapter` unchanged, the mapping is **identical to OpenAI** — see
[OPENAI.md §13.2](/providers/openai#13-openai-adapter-spec). In particular:

- Messages are passed through as OpenAI-shaped `{role, content}` dicts (no per-message reformatting).
- Any parameter in the `_OPENAI_PARAMS` allowlist is forwarded verbatim; everything else is dropped.
- The response is already OpenAI-shaped, so `content`, `finish_reason`, and `usage` parse directly
  into the canonical `CompletionResponse` / `TokenUsage`.

### 11.2 Fields and their real behavior

The earlier notion of a hand-tuned Ollama allowlist does not exist — the adapter simply reuses
`_OPENAI_PARAMS`. That changes what actually happens to several fields:

| Field | Real behavior | Notes |
|---|---|---|
| `n` | Forwarded | Only the first choice is parsed |
| `logit_bias`, `logprobs`, `top_logprobs` | Forwarded (in `_OPENAI_PARAMS`) | Ollama may ignore them |
| `tool_choice` / `tools` | Forwarded | Not parsed back into typed tool calls |
| `reasoning` | Surfaced via `reasoning_content`/`reasoning` in the response |
| `keep_alive`, `num_ctx`, `num_gpu`, `top_k`, `mirostat` | **Not sent** | Not in `_OPENAI_PARAMS`; would need the native API |
| `TokenUsage.cache_*` | Usually 0 | Not applicable to local models |

There is no `extra`/`keep_alive` passthrough — Ollama-specific options are simply not forwarded
through the OpenAI-compatible chat path today.


## 12. Implementation Status

### Delivered — chat via the OpenAI-compatible endpoint

```
1. src/provider/adapters/ollama.py
   - OllamaAdapter subclasses OpenAIAdapter
   - Overrides build_headers() (no auth), build_url() ({base_url}/v1/chat/completions),
     and get_timeout() (300s)
   - build_payload(), parse_response(), parse_stream_line() inherited unchanged
     (no field-stripping, no keep_alive injection)

2. Registered in the adapter registry
   - ProviderType.OLLAMA -> OllamaAdapter
```

### Delivered — model management via the discovery client

```
3. src/provider/discovery.py — OllamaDiscoveryClient (ModelDiscoveryClient protocol)
   - list_models(): GET /api/tags + GET /api/ps (marks loaded models)
   - load_model()/unload_model(): POST /api/generate with keep_alive=-1 / 0
   - delete_model(): DELETE /api/delete
   - get_discovery_client(ProviderType.OLLAMA) resolves it from a registry

4. src/provider/model_cache.py — ModelListCache (in-process TTL cache of DiscoveredModel lists)
```

### Not Yet Built

```
- Native /api/chat fallback for num_ctx / hardware options (chat always uses /v1/*)
- Model pull (POST /api/pull) and show (POST /api/show)
- Vision / tool-call parsing, capability auto-detection, performance metrics
```


## Appendix A: Quick Reference — Endpoint Cheat Sheet

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

## Appendix B: Quick Reference — Parameter Name Mapping

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
