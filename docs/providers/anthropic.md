# Anthropic Messages API

> **Source:** Anthropic API docs (platform.claude.com), OpenAPI spec, Python SDK API reference
> **Endpoint:** `POST /v1/messages`
> **Goal:** Define exactly how the Anthropic API differs from OpenAI, and how the shipped
> `AnthropicAdapter` maps it onto the shared canonical types (`CompletionResponse`, `StreamChunk`,
> `TokenUsage`) defined in [OPENAI.md](/providers/openai#12-multi-provider-architecture).


## Table of Contents

1. [API Overview](#1-api-overview)
2. [Authentication — Completely Different from OpenAI](#2-authentication)
3. [Request Schema — Complete Reference](#3-request-schema)
4. [System Prompt — The Critical Difference](#4-system-prompt)
5. [Message Format & Content Blocks](#5-message-format)
6. [Response Schema — Fundamentally Different Structure](#6-response-schema)
7. [Streaming — Event-Based, Not Line-Based](#7-streaming)
8. [Extended Thinking](#8-extended-thinking)
9. [Tool Calling — Different Shape](#9-tool-calling)
10. [Prompt Caching](#10-prompt-caching)
11. [Token Counting Endpoint](#11-token-counting)
12. [Key Differences from OpenAI — Summary Table](#12-differences-from-openai)
13. [AnthropicAdapter Implementation Spec](#13-adapter-spec)
14. [Mapping: Shared Types ↔ Anthropic API](#14-type-mapping)
15. [Implementation Plan](#15-implementation-plan)


## 1. API Overview

| Property | OpenAI | Anthropic |
|---|---|---|
| **Base URL** | `https://api.openai.com/v1` | `https://api.anthropic.com/v1` |
| **Endpoint** | `POST /chat/completions` | `POST /messages` |
| **Auth header** | `Authorization: Bearer <key>` | `x-api-key: <key>` |
| **Version header** | None | `anthropic-version: 2023-06-01` (required) |
| **Beta header** | None | `anthropic-beta: <feature>` (optional) |
| **Message format** | `messages: [{role, content}]` | `messages: [{role, content}]` + `system` as **separate top-level field** |
| **Response format** | `{choices: [{message: {content}}]}` | `{content: [{type, text}]}` — content blocks, not choices |
| **Streaming format** | `data: {JSON}\n\n` lines | Named SSE events with typed event/data pairs |

**The Anthropic API is NOT OpenAI-compatible.** Every layer (auth, request shape, response shape,
streaming protocol) differs. A unified "OpenAI-compatible" client will not work.


## 2. Authentication

### Headers

```http
POST /v1/messages HTTP/1.1
Host: api.anthropic.com
Content-Type: application/json
x-api-key: sk-ant-api03-...
anthropic-version: 2023-06-01
```

| Header | Required | Description |
|---|---|---|
| `x-api-key` | **Yes** | API key. NOT Bearer token — raw key value. |
| `anthropic-version` | **Yes** | API version string. Must be `2023-06-01`. |
| `anthropic-beta` | No | Comma-separated beta feature flags (e.g., `prompt-caching-2024-07-31`). |
| `Content-Type` | Yes | `application/json` |

### Difference from OpenAI

| Aspect | OpenAI | Anthropic |
|---|---|---|
| Key header | `Authorization: Bearer sk-...` | `x-api-key: sk-ant-...` |
| Version header | Not required | **Required**: `anthropic-version: 2023-06-01` |
| Beta features | Not applicable | `anthropic-beta` header enables features |

**Impact on The Bannered Mare:** The `build_headers()` method in `AnthropicAdapter` must produce
completely different headers than `OpenAIAdapter`.


## 3. Request Schema

### 3.1 Complete Parameter Reference

#### Required Parameters

| Parameter | Type | Description |
|---|---|---|
| `model` | string | Model ID: `claude-opus-4-6`, `claude-sonnet-4-6`, `claude-haiku-4-5`, etc. |
| `messages` | array | Conversation messages. Only `user` and `assistant` roles. **No `system` role.** |
| `max_tokens` | integer | **Required** (unlike OpenAI where it's optional). Maximum output tokens. |

#### Generation Parameters

| Parameter | Type | Default | Constraints | Description |
|---|---|---|---|---|
| `temperature` | number | `1.0` | 0.0 to 1.0 | Sampling temperature. **Range is 0-1, NOT 0-2 like OpenAI.** |
| `top_p` | number | - | 0.0 to 1.0 | Nucleus sampling. Mutually exclusive with `top_k`. |
| `top_k` | integer | - | - | Sample from top K options. **OpenAI does not have this parameter.** |
| `stop_sequences` | string[] | - | - | Custom stop sequences. **Named differently from OpenAI's `stop`.** |

#### System Prompt (Critical Difference)

| Parameter | Type | Description |
|---|---|---|
| `system` | string \| TextBlockParam[] | **Top-level field, NOT a message.** See [Section 4](#4-system-prompt). |

#### Streaming

| Parameter | Type | Default | Description |
|---|---|---|---|
| `stream` | boolean | `false` | Enable SSE streaming. Different event format from OpenAI. |

#### Extended Thinking

| Parameter | Type | Description |
|---|---|---|
| `thinking` | object | Extended thinking config. See [Section 8](#8-extended-thinking). |

#### Tool Calling

| Parameter | Type | Description |
|---|---|---|
| `tools` | array | Tool definitions. Different shape from OpenAI. See [Section 9](#9-tool-calling). |
| `tool_choice` | object | How model uses tools. Different values from OpenAI. |

#### Platform / Caching

| Parameter | Type | Default | Description |
|---|---|---|---|
| `metadata` | object | - | Only `user_id` field (opaque identifier). |
| `service_tier` | string | `"auto"` | `"auto"` or `"standard_only"`. |
| `cache_control` | object | - | Prompt caching config. **OpenAI has no equivalent.** |

#### Output Control

| Parameter | Type | Description |
|---|---|---|
| `output_config` | object | Output format + effort. Contains `format` (json_schema) and `effort` (low/medium/high/max). |

### 3.2 Parameters OpenAI Has That Anthropic Does NOT Have

| OpenAI Parameter | Anthropic Equivalent | Notes |
|---|---|---|
| `frequency_penalty` | **None** | Not supported. Ignore when building Anthropic payload. |
| `presence_penalty` | **None** | Not supported. |
| `logit_bias` | **None** | Not supported. |
| `logprobs` | **None** | Not supported. |
| `top_logprobs` | **None** | Not supported. |
| `n` | **None** | Always generates exactly 1 response. No swiping via API. |
| `seed` | **None** | No deterministic sampling. |
| `max_completion_tokens` | `max_tokens` | Anthropic uses `max_tokens` (not deprecated). |
| `reasoning_effort` | `thinking.type` + `output_config.effort` | Different mechanism. See [Section 8](#8-extended-thinking). |
| `response_format` | `output_config.format` | Similar concept, different shape. |
| `user` | `metadata.user_id` | Different nesting. |
| `prediction` | **None** | No Predicted Outputs. |
| `web_search_options` | `tools` (web_search server tool) | Web search is a tool, not a parameter. |
| `parallel_tool_calls` | `tool_choice.disable_parallel_tool_use` | Inverted logic. |

### 3.3 Parameters Anthropic Has That OpenAI Does NOT Have

| Anthropic Parameter | Description |
|---|---|
| `top_k` | Sample from top K tokens. |
| `thinking` | Extended thinking with token budget, display control. |
| `cache_control` | Prompt caching for reduced costs. |
| `output_config.effort` | Output effort: `low`, `medium`, `high`, `max`. |
| `inference_geo` | Geographic region for inference. |
| `container` | Container reuse for code execution tools. |


## 4. System Prompt — The Critical Difference

### OpenAI: System Is a Message

```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello"}
  ]
}
```

### Anthropic: System Is a Top-Level Field

```json
{
  "system": "You are a helpful assistant.",
  "messages": [
    {"role": "user", "content": "Hello"}
  ]
}
```

Or with cache control:

```json
{
  "system": [
    {
      "type": "text",
      "text": "You are a helpful assistant.",
      "cache_control": {"type": "ephemeral"}
    }
  ],
  "messages": [
    {"role": "user", "content": "Hello"}
  ]
}
```

### Rules

1. The `messages` array can only contain `user` and `assistant` roles.
2. All `system` messages must be extracted and placed in the top-level `system` field.
3. If there are multiple system messages (from prompt builder), they must be concatenated
   or converted to an array of `TextBlockParam`.
4. Conversation must start with a `user` message (after system extraction).
5. Roles must alternate: `user` → `assistant` → `user` → ...
6. Consecutive same-role messages are auto-merged by the API.

### Impact on AnthropicAdapter

The shipped `build_payload()`:
1. Scans the incoming `messages` list for `system`-role messages (there is no `developer` role)
2. Joins their content and places it in the `system` top-level field (with an ephemeral cache block)
3. Passes the remaining `user`/`assistant` messages through as `{role, content}`
4. Does not itself enforce `user`/`assistant` alternation — it relies on the caller's ordering


## 5. Message Format & Content Blocks

### 5.1 Roles (Only Two)

| Role | Description |
|---|---|
| `user` | Human messages. Can contain text, images, documents, tool results. |
| `assistant` | Model responses. Can contain text, tool_use, thinking. Used for conversation replay. |

No `system`, `developer`, `tool`, or `function` roles in the messages array.

### 5.2 Content Block Types (Request)

**User messages can contain:**

| Block Type | Structure | Description |
|---|---|---|
| `text` | `{"type": "text", "text": "..."}` | Plain text |
| `image` | `{"type": "image", "source": {...}}` | Image (base64 or URL) |
| `document` | `{"type": "document", "source": {...}}` | PDF, plain text, URL |
| `tool_result` | `{"type": "tool_result", "tool_use_id": "...", "content": "..."}` | Tool call result |

**Image source formats:**

```json
// Base64
{"type": "base64", "media_type": "image/jpeg", "data": "..."}

// URL
{"type": "url", "url": "https://..."}
```

Supported image types: `image/jpeg`, `image/png`, `image/gif`, `image/webp`

**Assistant messages (for replay) can contain:**

| Block Type | Structure | Description |
|---|---|---|
| `text` | `{"type": "text", "text": "..."}` | Previous text response |
| `tool_use` | `{"type": "tool_use", "id": "...", "name": "...", "input": {...}}` | Previous tool call |
| `thinking` | `{"type": "thinking", "thinking": "...", "signature": "..."}` | Previous thinking block |

### 5.3 Content Block Types (Response)

The response `content` array contains these block types:

| Block Type | Fields | Description |
|---|---|---|
| `text` | `type`, `text` | Generated text |
| `tool_use` | `type`, `id`, `name`, `input` | Tool the model wants to call |
| `thinking` | `type`, `thinking`, `signature` | Extended thinking output |

### 5.4 Comparison with OpenAI

| Aspect | OpenAI | Anthropic |
|---|---|---|
| String shorthand | `content: "text"` | `content: "text"` (both support) |
| Multipart content | `content: [{type, ...}]` | `content: [{type, ...}]` (similar) |
| Image type name | `image_url` | `image` |
| Image URL field | `image_url.url` | `source.url` (inside `source` object) |
| Image base64 | `image_url.url: "data:..."` (data URI) | `source.type: "base64", source.data: "..."` (separate field) |
| Image detail | `detail: "auto"\|"low"\|"high"` | Not supported |
| Audio input | Supported | Not supported via Messages API |
| File input | `file` type | `document` type |
| Tool results | `role: "tool"` message | `type: "tool_result"` content block inside `user` message |


## 6. Response Schema — Fundamentally Different Structure

### 6.1 OpenAI Response vs Anthropic Response

**OpenAI:**
```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "Hello!"},
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
}
```

**Anthropic:**
```json
{
  "id": "msg_...",
  "type": "message",
  "role": "assistant",
  "content": [
    {"type": "text", "text": "Hello!"}
  ],
  "model": "claude-opus-4-6",
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 10,
    "output_tokens": 5,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0
  }
}
```

### 6.2 Structural Differences

| Aspect | OpenAI | Anthropic |
|---|---|---|
| **Wrapper** | `choices[]` array with index | Direct `content[]` array, no choices wrapper |
| **Content** | `message.content` (string) | `content[]` (array of typed blocks) |
| **Multiple responses** | `n > 1` → multiple choices | Not supported. Always 1 response. |
| **Stop reason field** | `finish_reason` | `stop_reason` |
| **Stop reason values** | `stop`, `length`, `tool_calls`, `content_filter` | `end_turn`, `max_tokens`, `stop_sequence`, `tool_use` |
| **Stop sequence value** | Not returned | `stop_sequence` field shows which sequence matched |
| **Content extraction** | `choices[0].message.content` | `content[0].text` (must find `text` type block) |
| **Object type** | `object: "chat.completion"` | `type: "message"` |
| **Refusal** | `message.refusal` field | Not a separate field |

### 6.3 Stop Reason Mapping

| Anthropic `stop_reason` | OpenAI `finish_reason` | Shared `FinishReason` |
|---|---|---|
| `end_turn` | `stop` | `STOP` |
| `max_tokens` | `length` | `LENGTH` |
| `stop_sequence` | `stop` | `STOP` |
| `tool_use` | `tool_calls` | `TOOL_CALLS` |
| (no equivalent) | `content_filter` | `CONTENT_FILTER` |

### 6.4 Usage Differences

| Field | OpenAI | Anthropic |
|---|---|---|
| Input tokens | `usage.prompt_tokens` | `usage.input_tokens` |
| Output tokens | `usage.completion_tokens` | `usage.output_tokens` |
| Total | `usage.total_tokens` | Not provided (must sum) |
| Cached tokens | `usage.prompt_tokens_details.cached_tokens` | `usage.cache_read_input_tokens` |
| Cache write | Not applicable | `usage.cache_creation_input_tokens` |
| Reasoning tokens | `usage.completion_tokens_details.reasoning_tokens` | Not broken out (included in `output_tokens`) |


## 7. Streaming — Event-Based, Not Line-Based

### 7.1 The Fundamental Difference

**OpenAI streaming** uses simple SSE lines:
```
data: {"id":"...","choices":[{"delta":{"content":"Hello"}}]}
data: {"id":"...","choices":[{"delta":{"content":"!"}}]}
data: [DONE]
```

**Anthropic streaming** uses named SSE events with a stateful lifecycle:
```
event: message_start
data: {"type":"message_start","message":{"id":"msg_...","role":"assistant","content":[],"usage":{"input_tokens":25,"output_tokens":1}}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"!"}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":15}}

event: message_stop
data: {"type":"message_stop"}
```

### 7.2 Event Types

| Event | Structure | Description |
|---|---|---|
| `message_start` | `{type, message: {id, role, content:[], model, usage}}` | Stream begins. Contains initial message with `input_tokens`. |
| `content_block_start` | `{type, index, content_block: {type, text:""}}` | New content block begins. |
| `content_block_delta` | `{type, index, delta: {type, text\|partial_json\|thinking}}` | Content fragment. |
| `content_block_stop` | `{type, index}` | Content block complete. |
| `message_delta` | `{type, delta: {stop_reason, stop_sequence}, usage: {output_tokens}}` | Final message metadata. **Usage is cumulative.** |
| `message_stop` | `{type}` | Stream complete. |
| `ping` | `{type: "ping"}` | Keep-alive. Ignore. |
| `error` | `{type: "error", error: {type, message}}` | Error mid-stream. |

### 7.3 Delta Types

| Delta Type | Inside Event | Fields | Description |
|---|---|---|---|
| `text_delta` | `content_block_delta` | `text` | Text content fragment |
| `input_json_delta` | `content_block_delta` | `partial_json` | Tool input argument fragment |
| `thinking_delta` | `content_block_delta` | `thinking` | Extended thinking fragment |
| `signature_delta` | `content_block_delta` | `signature` | Thinking block signature |

### 7.4 Stream Lifecycle

```
message_start                          ← input_tokens available here
  content_block_start (index=0)        ← thinking block (if enabled)
    content_block_delta (thinking)     ← thinking text fragments
    content_block_delta (signature)    ← thinking signature
  content_block_stop (index=0)
  content_block_start (index=1)        ← text block
    content_block_delta (text)         ← text fragments
    content_block_delta (text)
  content_block_stop (index=1)
  [optional: more content blocks for tool_use]
message_delta                          ← stop_reason + output_tokens
message_stop                           ← stream complete
```

### 7.5 Parsing Algorithm for AnthropicAdapter

> The sketch below shows the event handling conceptually. In the shipped code the adapter is
> stateless: it exposes `parse_stream_line(line) -> StreamChunk | None` (see §13.2) and the
> `ProviderGateway` owns the SSE loop. There is no adapter-owned `complete_stream`, no
> `CompletionChunk`/`ToolCallChunk` type, and tool-call streaming is not handled.

```python
async def complete_stream(self, request: CompletionRequest) -> AsyncIterator[CompletionChunk]:
    message_id = ""
    input_tokens = 0

    async for event_type, event_data in self._read_sse_events(response):
        match event_type:
            case "message_start":
                message_id = event_data["message"]["id"]
                input_tokens = event_data["message"]["usage"]["input_tokens"]

            case "content_block_delta":
                delta = event_data["delta"]
                if delta["type"] == "text_delta":
                    yield CompletionChunk(
                        id=message_id,
                        delta_content=delta["text"],
                    )
                elif delta["type"] == "thinking_delta":
                    pass  # Optionally yield thinking content
                elif delta["type"] == "input_json_delta":
                    yield CompletionChunk(
                        id=message_id,
                        tool_call_chunks=[ToolCallChunk(
                            index=event_data["index"],
                            arguments_delta=delta["partial_json"],
                        )],
                    )

            case "message_delta":
                delta = event_data["delta"]
                usage = TokenUsage(
                    prompt_tokens=input_tokens,
                    completion_tokens=event_data["usage"]["output_tokens"],
                    total_tokens=input_tokens + event_data["usage"]["output_tokens"],
                )
                yield CompletionChunk(
                    id=message_id,
                    finish_reason=self._map_stop_reason(delta.get("stop_reason")),
                    usage=usage,
                )

            case "message_stop":
                break  # Stream complete

            case "ping":
                continue  # Ignore

            case "error":
                raise ProviderException(event_data["error"]["message"])
```

### 7.6 Key Implementation Note: Named Events

Anthropic uses `event:` lines that OpenAI does not:

```
event: content_block_delta        ← THIS LINE EXISTS IN ANTHROPIC
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}
```

OpenAI only has:
```
data: {"choices":[{"delta":{"content":"Hello"}}]}
```

The SSE parser must handle the `event:` prefix to determine the event type.
The `data:` line contains the JSON payload.


## 8. Extended Thinking

Anthropic-exclusive feature. Allows Claude to "think" before responding.

### 8.1 Configuration

```json
{
  "thinking": {
    "type": "enabled",
    "budget_tokens": 4096
  }
}
```

| Type | Behavior |
|---|---|
| `enabled` | Thinking enabled with explicit token budget. Min 1024 tokens. |
| `disabled` | No thinking (default). |
| `adaptive` | Anthropic chooses whether to think. |

Additional options:
- `display`: `"summarized"` (default) or `"omitted"` — controls whether thinking text is returned.
- `budget_tokens`: Must be >= 1024 and < `max_tokens`.

### 8.2 Response with Thinking

```json
{
  "content": [
    {
      "type": "thinking",
      "thinking": "Let me analyze this step by step...",
      "signature": "EqQBCgIYAhIM..."
    },
    {
      "type": "text",
      "text": "The answer is 42."
    }
  ]
}
```

The thinking block appears **before** the text block in the content array.
The `signature` field is used for integrity verification and must be preserved
when replaying thinking blocks in subsequent messages.

### 8.3 Mapping to Shared Types

The shared `CompletionRequest.reasoning_effort` maps to Anthropic as follows:

| Shared `reasoning_effort` | Anthropic Mapping |
|---|---|
| `None` | `thinking: {"type": "disabled"}` or omit |
| `low` | `thinking: {"type": "enabled", "budget_tokens": 1024}` |
| `medium` | `thinking: {"type": "enabled", "budget_tokens": 4096}` |
| `high` | `thinking: {"type": "enabled", "budget_tokens": 16384}` |

Or alternatively, use `output_config.effort`:

| Shared `reasoning_effort` | `output_config.effort` |
|---|---|
| `low` | `"low"` |
| `medium` | `"medium"` |
| `high` | `"high"` |

The adapter should support both mechanisms. `thinking` gives direct budget control;
`output_config.effort` is simpler.


## 9. Tool Calling — Different Shape

### 9.1 Tool Definition

**OpenAI:**
```json
{
  "type": "function",
  "function": {
    "name": "get_weather",
    "description": "Get weather",
    "parameters": { "type": "object", ... }
  }
}
```

**Anthropic:**
```json
{
  "name": "get_weather",
  "description": "Get weather",
  "input_schema": { "type": "object", ... }
}
```

Or with explicit type:
```json
{
  "type": "custom",
  "name": "get_weather",
  "description": "Get weather",
  "input_schema": { "type": "object", ... },
  "strict": true,
  "cache_control": {"type": "ephemeral"}
}
```

| Difference | OpenAI | Anthropic |
|---|---|---|
| Wrapper | Wrapped in `{type: "function", function: {...}}` | Flat object with `name`, `description`, `input_schema` |
| Schema field | `parameters` | `input_schema` |
| Strict mode | `function.strict` | `strict` (top-level) |
| Caching | Not supported | `cache_control` field |

### 9.2 Tool Choice

**OpenAI:**
```json
"none" | "auto" | "required" | {"type": "function", "function": {"name": "..."}}
```

**Anthropic:**
```json
{"type": "none"} | {"type": "auto"} | {"type": "any"} | {"type": "tool", "name": "..."}
```

| Shared Value | OpenAI | Anthropic |
|---|---|---|
| No tools | `"none"` | `{"type": "none"}` |
| Model decides | `"auto"` | `{"type": "auto"}` |
| Must use tool | `"required"` | `{"type": "any"}` |
| Specific tool | `{"type": "function", "function": {"name": "X"}}` | `{"type": "tool", "name": "X"}` |

Note: Anthropic uses `disable_parallel_tool_use` (on `auto`/`any`), while OpenAI uses
`parallel_tool_calls` (inverted boolean).

### 9.3 Tool Call in Response

**OpenAI** (in `message.tool_calls`):
```json
{
  "id": "call_abc123",
  "type": "function",
  "function": {"name": "get_weather", "arguments": "{\"location\":\"NYC\"}"}
}
```

**Anthropic** (as content block):
```json
{
  "type": "tool_use",
  "id": "toolu_abc123",
  "name": "get_weather",
  "input": {"location": "NYC"}
}
```

| Difference | OpenAI | Anthropic |
|---|---|---|
| Location | Separate `tool_calls` array on message | Content block in `content[]` array |
| Arguments | `arguments` (JSON **string**) | `input` (parsed **object**) |
| ID prefix | `call_` | `toolu_` |

### 9.4 Tool Result

**OpenAI** (separate message):
```json
{"role": "tool", "tool_call_id": "call_abc123", "content": "72°F, sunny"}
```

**Anthropic** (content block inside user message):
```json
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_abc123",
      "content": "72°F, sunny"
    }
  ]
}
```

| Difference | OpenAI | Anthropic |
|---|---|---|
| Role | `tool` (dedicated role) | `user` (tool results go inside user messages) |
| ID field | `tool_call_id` | `tool_use_id` |
| Error handling | Not standardized | `is_error: true` field |

### 9.5 Server-Hosted Tools (Anthropic-Only)

Anthropic offers built-in server tools that OpenAI does not have:

| Tool | ID | Description |
|---|---|---|
| Web Search | `web_search_20250305` | Search the internet |
| Web Fetch | `web_fetch_20250910` | Fetch URL content |
| Code Execution | `code_execution_20250522` | Run Python code |
| Bash | `bash_20250124` | Run bash commands |
| Text Editor | `text_editor_20250124` | Edit files |
| Memory | `memory_20250818` | Persistent memory |

These are specified by type, not name:
```json
{"type": "web_search_20250305"}
```


## 10. Prompt Caching

Anthropic-exclusive feature that caches portions of the prompt for reuse.

### 10.1 How It Works

Add `cache_control` to any cacheable block (system, messages, tools):

```json
{
  "system": [
    {
      "type": "text",
      "text": "Very long system prompt...",
      "cache_control": {"type": "ephemeral", "ttl": "5m"}
    }
  ],
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Hello",
          "cache_control": {"type": "ephemeral"}
        }
      ]
    }
  ]
}
```

### 10.2 TTL Options

| TTL | Duration |
|---|---|
| `"5m"` | 5 minutes (default) |
| `"1h"` | 1 hour |

### 10.3 Usage Tracking

Response includes cache-specific token counts:

```json
{
  "usage": {
    "input_tokens": 100,
    "output_tokens": 50,
    "cache_creation_input_tokens": 500,
    "cache_read_input_tokens": 0
  }
}
```

### 10.4 Relevance to The Bannered Mare

System prompts + character descriptions are repeated identically across messages in the same
chat. Prompt caching could reduce costs by 90% for these repeated prefixes. The adapter should
support adding `cache_control` to the system prompt and initial context blocks.


## 11. Token Counting Endpoint

**Anthropic provides a dedicated token counting endpoint.** OpenAI does not.

### Endpoint

```
POST /v1/messages/count_tokens
```

### Request

Same body as `/v1/messages` but without generating a response:

```json
{
  "model": "claude-opus-4-6",
  "messages": [{"role": "user", "content": "Hello"}],
  "system": "You are helpful."
}
```

### Response

```json
{
  "input_tokens": 15
}
```

### Relevance to The Bannered Mare

This enables **accurate** token counting for Anthropic models without relying on tiktoken
estimates. The `TokenizerService` could use this endpoint for Claude models, providing exact
counts for:
- Prompt budget calculations
- World info budget enforcement
- History truncation decisions


## 12. Key Differences from OpenAI — Summary Table

| Aspect | OpenAI | Anthropic | Adapter Must Handle |
|---|---|---|---|
| **Auth** | `Authorization: Bearer` | `x-api-key` + `anthropic-version` | Different headers |
| **Endpoint** | `/v1/chat/completions` | `/v1/messages` | Different URL |
| **System prompt** | Message with `role: "system"` | Top-level `system` field | Extract from messages |
| **Message roles** | system, developer, user, assistant, tool | user, assistant only | Role mapping |
| **max_tokens** | Optional | **Required** | Must always include |
| **Temperature range** | 0-2 | 0-1 | Clamp values |
| **top_k** | Not supported | Supported | Pass through |
| **frequency_penalty** | Supported | Not supported | Drop from payload |
| **presence_penalty** | Supported | Not supported | Drop from payload |
| **logit_bias** | Supported | Not supported | Drop from payload |
| **n (multi-response)** | 1-128 | Always 1 | Cannot generate alternatives |
| **seed** | Supported | Not supported | Drop from payload |
| **Stop param name** | `stop` | `stop_sequences` | Rename field |
| **Response wrapper** | `choices[0].message.content` (string) | `content[0].text` (blocks array) | Different extraction |
| **Stop reason field** | `finish_reason` | `stop_reason` | Rename |
| **Stop reason values** | `stop`, `length`, `tool_calls` | `end_turn`, `max_tokens`, `tool_use` | Value mapping |
| **Usage field names** | `prompt_tokens`, `completion_tokens` | `input_tokens`, `output_tokens` | Rename |
| **Streaming format** | `data: {json}` lines + `[DONE]` | Named events (event: + data:) | Different parser |
| **Stream end signal** | `data: [DONE]` | `event: message_stop` | Different detection |
| **Tool definition** | `{type: "function", function: {name, parameters}}` | `{name, input_schema}` | Restructure |
| **Tool choice** | String or `{type, function: {name}}` | `{type}` or `{type, name}` | Restructure |
| **Tool call response** | `message.tool_calls[]` | `content[]` block with `type: "tool_use"` | Different extraction |
| **Tool result** | `role: "tool"` message | `tool_result` block in `user` message | Role + structure change |
| **Tool arguments** | JSON string (`arguments`) | Parsed object (`input`) | Parse/serialize |
| **Thinking** | Not supported | `thinking` param + content blocks | Anthropic-only |
| **Cache control** | Not supported | `cache_control` on blocks | Anthropic-only |
| **Token counting API** | Not available | `POST /v1/messages/count_tokens` | Anthropic-only |


## 13. AnthropicAdapter Implementation Spec

### 13.1 File Location

```
src/provider/adapters/anthropic.py
```

### 13.2 Core Implementation

The shipped `AnthropicAdapter` is stateless (the `ProviderGateway` owns the HTTP call) and works
from the shared hook signatures. It always attaches an ephemeral `cache_control` block to the
system prompt and sends the prompt-caching beta header. `thinking` is passed through only when the
caller supplies a `{"type": "enabled", ...}` config in `parameters` — it is not derived from a
`reasoning_effort` value.

```python
_STOP_REASON_MAP = {
    "end_turn": "stop", "max_tokens": "length",
    "stop_sequence": "stop", "tool_use": "tool_calls",
}
_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicAdapter(ProviderAdapter):
    """Adapter for the Anthropic Messages API."""

    def build_url(self, base_url, model, stream, api_key=None) -> str:
        return f"{base_url}/messages"

    def build_headers(self, api_key) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["x-api-key"] = api_key
        headers["anthropic-version"] = _ANTHROPIC_VERSION
        headers["anthropic-beta"] = "prompt-caching-2024-07-31"
        return headers

    def build_payload(self, messages, model, stream, parameters) -> dict[str, Any]:
        system_parts, chat_messages = [], []
        for msg in messages:
            if msg.get("role") == "system":
                system_parts.append(msg.get("content", ""))
            else:
                chat_messages.append({"role": msg["role"], "content": msg.get("content", "")})

        payload = {"model": model, "messages": chat_messages}
        if system_parts:
            payload["system"] = [{
                "type": "text",
                "text": "\n\n".join(system_parts),
                "cache_control": {"type": "ephemeral"},  # system prompt is always cached
            }]
        if stream:
            payload["stream"] = True

        payload["max_tokens"] = parameters.get("max_tokens", 4096)  # required by Anthropic
        temp = parameters.get("temperature")
        if temp is not None:
            payload["temperature"] = min(float(temp), 1.0)          # clamp to <= 1.0
        if parameters.get("top_p") is not None:
            payload["top_p"] = parameters["top_p"]
        if parameters.get("top_k") is not None:
            payload["top_k"] = parameters["top_k"]
        if parameters.get("stop_sequences"):
            payload["stop_sequences"] = parameters["stop_sequences"]
        thinking = parameters.get("thinking")
        if isinstance(thinking, dict) and thinking.get("type") == "enabled":
            payload["thinking"] = thinking
        return payload

    def parse_response(self, data) -> CompletionResponse:
        blocks = data.get("content", [])
        content = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        reasoning = "".join(b.get("thinking", "") for b in blocks if b.get("type") == "thinking") or None
        raw_reason = data.get("stop_reason") or "end_turn"
        usage = data.get("usage", {})
        return CompletionResponse(
            content=content,
            finish_reason=_STOP_REASON_MAP.get(raw_reason, raw_reason),
            usage=TokenUsage(
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                total_tokens=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                cache_read_tokens=usage.get("cache_read_input_tokens", 0),
                cache_creation_tokens=usage.get("cache_creation_input_tokens", 0),
            ),
            reasoning=reasoning,
            raw=data,
        )

    def parse_stream_line(self, line) -> StreamChunk | None:
        # "data: " SSE lines only. content_block_delta → text_delta / thinking_delta;
        # message_delta → finish_reason (+ output_tokens); message_stop → finish_reason="stop".
        ...
```

Not implemented: tool-call and image content-block formatting, a `reasoning_effort`→thinking
budget mapping, `output_config`/response-format, and metadata — Anthropic-only params such as
`frequency_penalty`/`n`/`seed` are simply never forwarded.


## 14. Mapping: Shared Types to Anthropic API

::: info Some rows describe unbuilt features
The shipped adapter forwards `messages`, `model`, `temperature` (clamped), `top_p`, `top_k`,
`stop_sequences`, and a pre-built `thinking` config, plus the always-on system-prompt cache. Rows
below for `reasoning_effort`→thinking, tools/tool_choice, response_format, and metadata describe a
design that is **not implemented**. Also note there is no `CompletionRequest`/`CompletionChunk`
object — requests are a `messages` list + `parameters` dict, and streaming yields `StreamChunk`.
:::

### 14.1 CompletionRequest → Anthropic Payload

| Shared Field | Anthropic Field | Transformation |
|---|---|---|
| `messages` (system role) | `system` (top-level) | Extract and separate |
| `messages` (user/assistant) | `messages` | Keep, reformat content blocks |
| `messages` (tool role) | User message with `tool_result` block | Restructure role |
| `messages` (developer role) | `system` (top-level) | Merge with system |
| `model` | `model` | Direct |
| `temperature` | `temperature` | Clamp to [0, 1] |
| `top_p` | `top_p` | Direct |
| `max_tokens` | `max_tokens` | Direct (but required) |
| `stop` | `stop_sequences` | Rename |
| `stream` | `stream` | Direct |
| `reasoning_effort` | `thinking` | Map to thinking config |
| `response_format` | `output_config.format` | Restructure |
| `tools` | `tools` | Restructure (remove wrapper, rename schema field) |
| `tool_choice` | `tool_choice` | Map values (required→any, named→tool) |
| `n` | *(dropped)* | Not supported |
| `frequency_penalty` | *(dropped)* | Not supported |
| `presence_penalty` | *(dropped)* | Not supported |
| `logit_bias` | *(dropped)* | Not supported |
| `logprobs` | *(dropped)* | Not supported |
| `seed` | *(dropped)* | Not supported |
| `extra.top_k` | `top_k` | Pass through |
| `extra.cache_control` | `cache_control` | Pass through |
| `extra.user_id` | `metadata.user_id` | Nest in metadata |

### 14.2 Anthropic Response → CompletionResponse

| Anthropic Field | Shared Field | Transformation |
|---|---|---|
| `id` | `id` | Direct |
| `content[].text` (type=text) | `content` | Concatenate all text blocks |
| `content[]` (type=tool_use) | `tool_calls` | Extract, serialize `input` to JSON string |
| `stop_reason` | `finish_reason` | Map values |
| `usage.input_tokens` | `usage.prompt_tokens` | Rename |
| `usage.output_tokens` | `usage.completion_tokens` | Rename |
| `usage.cache_read_input_tokens` | `usage.cached_tokens` | Rename |
| `model` | `model` | Direct |
| (full response) | `raw` | Preserve for debugging |

### 14.3 Anthropic Stream Events → CompletionChunk

| Anthropic Event | Shared CompletionChunk Field | Transformation |
|---|---|---|
| `message_start.message.id` | `id` | Extract from initial event |
| `content_block_delta.delta.text` (text_delta) | `delta_content` | Direct |
| `content_block_delta.delta.partial_json` | `tool_call_chunks[].arguments_delta` | Wrap in chunk |
| `message_delta.delta.stop_reason` | `finish_reason` | Map values |
| `message_delta.usage.output_tokens` | `usage.completion_tokens` | Combine with stored input_tokens |
| `message_stop` | *(stream end)* | Break iteration |


## 15. Implementation Status

### Delivered (`src/provider/adapters/anthropic.py`)

```
- build_headers(): x-api-key + anthropic-version + prompt-caching beta header
- build_url(): {base_url}/messages
- build_payload():
    a. Extract system messages → top-level system field (always cache_control: ephemeral)
    b. Pass user/assistant messages through as {role, content}
    c. Map params (temperature clamped to <=1.0, top_p, top_k, stop_sequences)
    d. thinking passed through when parameters["thinking"] = {type: "enabled", ...}
    e. Unsupported params (frequency_penalty, presence_penalty, n, seed, ...) simply not read
- parse_response(): text + thinking blocks, stop_reason mapping, cache-aware TokenUsage
- parse_stream_line(): content_block_delta (text_delta/thinking_delta), message_delta, message_stop
- Registered in the registry: ProviderType.ANTHROPIC → AnthropicAdapter
- Prompt caching: cache_control on system prompt; cache_read/creation tokens in TokenUsage
```

### Not Yet Built

```
- Tool calling: tool definition/choice formatting, tool_use parsing, tool_result messages
- reasoning_effort → thinking budget mapping (caller must supply the thinking config directly)
- response_format / output_config passthrough
- Multimodal (image/document content blocks)
- Token-counting endpoint (POST /v1/messages/count_tokens) integration
```


## Appendix: Anthropic Error Responses

### Error Format

```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "max_tokens: field required"
  }
}
```

### Error Types

| Error Type | HTTP Status | Description |
|---|---|---|
| `invalid_request_error` | 400 | Malformed request |
| `authentication_error` | 401 | Invalid API key |
| `permission_error` | 403 | Access denied |
| `not_found_error` | 404 | Resource not found |
| `rate_limit_error` | 429 | Too many requests |
| `api_error` | 500 | Internal error |
| `overloaded_error` | 529 | API overloaded |

### Mapping to The Bannered Mare Exceptions

The gateway (`ProviderGateway._handle_http_error`) maps by HTTP status only:

| Anthropic Error | The Bannered Mare Exception |
|---|---|
| `authentication_error` (401) | `ProviderAuthError` |
| `rate_limit_error` (429) | `ProviderRateLimitError` |
| `invalid_request_error` (400) | `ProviderInvalidRequestError` |
| `overloaded_error` (529) | `ProviderException` (all non-401/429/400 statuses) |
| All others | `ProviderException` |

### Streaming Errors

Errors can occur mid-stream:
```
event: error
data: {"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}}
```

The adapter must detect `event: error` and raise the appropriate exception, even during
an active stream.
