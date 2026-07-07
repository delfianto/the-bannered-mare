# Google Gemini API

> **Source:** Google AI for Developers API reference (`ai.google.dev/api`), REST API spec (v1beta)
> **Endpoint:** `POST /v1beta/models/{model}:generateContent`
> **Goal:** Define exactly how the Gemini API differs from OpenAI, and how the shipped
> `GeminiAdapter` maps it onto the shared canonical types (`CompletionResponse`, `StreamChunk`,
> `TokenUsage`) defined in [OPENAI.md](/providers/openai#12-multi-provider-architecture).


## Table of Contents

1. [API Overview](#1-api-overview)
2. [Authentication — Query Parameter, Not Header](#2-authentication)
3. [Request Schema — Complete Reference](#3-request-schema)
4. [System Instruction — Separate Field (Like Anthropic)](#4-system-instruction)
5. [Message Format — Contents with Parts](#5-message-format)
6. [Response Schema — Candidates Array](#6-response-schema)
7. [Streaming — streamGenerateContent](#7-streaming)
8. [Safety Settings — Unique to Gemini](#8-safety-settings)
9. [Tool Calling — Different Shape](#9-tool-calling)
10. [Context Caching](#10-context-caching)
11. [Token Counting Endpoint](#11-token-counting)
12. [Key Differences from OpenAI — Summary Table](#12-differences-from-openai)
13. [GeminiAdapter Implementation Spec](#13-adapter-spec)
14. [Mapping: Shared Types to Gemini API](#14-type-mapping)
15. [Implementation Plan](#15-implementation-plan)


## 1. API Overview

| Property | OpenAI | Gemini |
|---|---|---|
| **Base URL** | `https://api.openai.com/v1` | `https://generativelanguage.googleapis.com` |
| **Endpoint** | `POST /chat/completions` | `POST /v1beta/models/{model}:generateContent` |
| **Streaming endpoint** | Same endpoint with `stream: true` | `POST /v1beta/models/{model}:streamGenerateContent` |
| **Auth** | `Authorization: Bearer <key>` | `?key=<API_KEY>` query parameter (or OAuth Bearer token) |
| **Model location** | `model` field in request body | **URL path parameter** `{model}` |
| **Message format** | `messages: [{role, content}]` | `contents: [{role, parts: [{text}]}]` — different name, different structure |
| **System prompt** | Message with `role: "system"` | `systemInstruction` top-level field (like Anthropic's `system`) |
| **Response format** | `{choices: [{message: {content}}]}` | `{candidates: [{content: {parts: [{text}]}}]}` |
| **Streaming format** | `data: {JSON}\n\n` lines + `[DONE]` | JSON array streamed as SSE `data:` lines (no `[DONE]` signal) |

**The Gemini API is NOT OpenAI-compatible.** The endpoint structure, message format, response
shape, authentication, and streaming protocol all differ. Model is in the URL path, messages
are "contents" with "parts", the assistant role is "model", and generation parameters are
wrapped in a `generationConfig` object.


## 2. Authentication

### API Key (Primary Method)

```
POST /v1beta/models/gemini-2.5-flash:generateContent?key=AIza...
Content-Type: application/json
```

The API key is passed as a **query parameter** `?key=`, not in headers.

### OAuth 2.0 (Alternative)

```http
POST /v1beta/models/gemini-2.5-flash:generateContent
Authorization: Bearer ya29.a0...
Content-Type: application/json
```

OAuth tokens use the standard Bearer header, but this requires a full Google OAuth flow
and is typically used for Vertex AI, not the AI Studio API.

### Comparison

| Aspect | OpenAI | Anthropic | Gemini |
|---|---|---|---|
| Key location | `Authorization: Bearer` header | `x-api-key` header | `?key=` **query parameter** |
| Version header | Not required | `anthropic-version` required | Not required |
| OAuth support | No | No | Yes (alternative) |
| Key prefix | `sk-...` | `sk-ant-...` | `AIza...` |

**Impact on The Bannered Mare:** The `GeminiAdapter.build_headers()` method produces minimal headers
(just `Content-Type`). The API key is appended to the URL instead — which is why every adapter's
`build_url(base_url, model, stream, api_key)` hook accepts the API key. Gemini uses it as a
`?key=` query param; the OAuth Bearer alternative is not implemented.


## 3. Request Schema

### 3.1 Endpoint Structure

Unlike OpenAI/Anthropic where the model is in the body, Gemini puts it in the URL:

```
POST /v1beta/models/{model}:generateContent?key={API_KEY}
```

The request body does **not** contain a `model` field.

### 3.2 Complete Parameter Reference

#### Top-Level Fields

| Parameter | Type | Required | Description |
|---|---|---|---|
| `contents` | Content[] | **Yes** | Conversation history. Equivalent to OpenAI's `messages`. |
| `systemInstruction` | Content | No | System prompt. Separate field like Anthropic's `system`. |
| `generationConfig` | GenerationConfig | No | All generation parameters wrapped in this object. |
| `safetySettings` | SafetySetting[] | No | Content safety thresholds. **Unique to Gemini.** |
| `tools` | Tool[] | No | Tool/function declarations. |
| `toolConfig` | ToolConfig | No | Tool calling behavior configuration. |
| `cachedContent` | string | No | Resource name of a cached content resource. |

#### GenerationConfig — All Generation Parameters

Unlike OpenAI (flat body) and Anthropic (mostly flat body), Gemini wraps **all**
generation parameters inside a `generationConfig` object:

| Parameter | Type | Default | Constraints | Description |
|---|---|---|---|---|
| `temperature` | number | Model-dependent | 0.0 to 2.0 | Sampling temperature. **Same range as OpenAI (0-2).** |
| `topP` | number | Model-dependent | 0.0 to 1.0 | Nucleus sampling. |
| `topK` | integer | Model-dependent | - | Sample from top K tokens. **OpenAI does not have this.** Anthropic does. |
| `maxOutputTokens` | integer | Model-dependent | - | Maximum output tokens. **Named differently from both OpenAI and Anthropic.** |
| `stopSequences` | string[] | - | Up to 5 | Stop sequences. **Named differently from OpenAI's `stop` and Anthropic's `stop_sequences`.** |
| `candidateCount` | integer | `1` | 1-8 | Number of response candidates. Equivalent to OpenAI's `n`. |
| `responseMimeType` | string | `"text/plain"` | - | Output format: `"text/plain"`, `"application/json"`, `"text/x.enum"`. |
| `responseSchema` | Schema | - | - | JSON schema for structured output. Requires `responseMimeType: "application/json"`. |
| `presencePenalty` | number | `0` | -2.0 to 2.0 | Penalize tokens present in text. **Same as OpenAI.** |
| `frequencyPenalty` | number | `0` | -2.0 to 2.0 | Penalize tokens by frequency. **Same as OpenAI.** |
| `responseLogprobs` | boolean | `false` | - | Return log probabilities. |
| `logprobs` | integer | - | - | Number of top logprobs per token. Requires `responseLogprobs: true`. |
| `seed` | integer | - | - | Seed for deterministic output. |
| `audioTimestamp` | boolean | - | - | Enable audio timestamp for audio input. |
| `routingConfig` | RoutingConfig | - | - | Model routing configuration. |
| `thinkingConfig` | ThinkingConfig | - | - | Thinking/reasoning configuration (Gemini 2.5+). |

#### ThinkingConfig (Gemini 2.5 Models)

| Parameter | Type | Description |
|---|---|---|
| `thinkingBudget` | integer | Maximum tokens for the model's internal reasoning. 0 to disable, -1 for dynamic. |
| `includeThoughts` | boolean | Whether to include thinking content in the response. |

### 3.3 Parameters OpenAI Has That Gemini Does NOT Have

| OpenAI Parameter | Gemini Equivalent | Notes |
|---|---|---|
| `model` (in body) | URL path `{model}` | Fundamentally different location |
| `messages` | `contents` | Different name and structure |
| `max_completion_tokens` | `generationConfig.maxOutputTokens` | Different name, nested in config |
| `max_tokens` (deprecated) | `generationConfig.maxOutputTokens` | Different name |
| `n` | `generationConfig.candidateCount` | Different name, nested |
| `stop` | `generationConfig.stopSequences` | Different name, nested |
| `stream` (in body) | Separate endpoint | Not a body parameter — use different URL |
| `logit_bias` | **None** | Not supported |
| `reasoning_effort` | `generationConfig.thinkingConfig` | Different mechanism (Gemini 2.5+) |
| `response_format` | `responseMimeType` + `responseSchema` | Split into two fields |
| `user` | **None** | No user tracking field |
| `prediction` | **None** | No Predicted Outputs |
| `web_search_options` | `tools` (google_search tool) | Web search is a tool |

### 3.4 Parameters Gemini Has That OpenAI Does NOT Have

| Gemini Parameter | Description |
|---|---|
| `safetySettings` | Content safety category thresholds. See [Section 8](#8-safety-settings). |
| `toolConfig` | Fine-grained tool calling behavior control. |
| `cachedContent` | Reference to server-side cached content. |
| `generationConfig.topK` | Top-K sampling (also in Anthropic). |
| `generationConfig.responseMimeType` | Output MIME type control. |
| `generationConfig.audioTimestamp` | Audio timestamp support. |
| `systemInstruction` | System prompt as Content object (with parts). |


## 4. System Instruction — Separate Field (Like Anthropic)

### OpenAI: System Is a Message

```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello"}
  ]
}
```

### Gemini: System Is a Top-Level Field

```json
{
  "systemInstruction": {
    "parts": [
      {"text": "You are a helpful assistant."}
    ]
  },
  "contents": [
    {"role": "user", "parts": [{"text": "Hello"}]}
  ]
}
```

### Key Differences from Anthropic's `system`

| Aspect | Anthropic `system` | Gemini `systemInstruction` |
|---|---|---|
| Type | `string \| TextBlockParam[]` | `Content` object (same shape as a message) |
| Structure | String or array of `{type, text}` blocks | `{parts: [{text: "..."}]}` — uses the parts format |
| Role field | Not applicable | No `role` field needed (implied) |
| Cache control | Supports `cache_control` on blocks | Uses `cachedContent` reference instead |

### Rules

1. The `contents` array can only contain `user` and `model` roles.
2. All `system` messages must be extracted and placed in `systemInstruction`.
3. `systemInstruction` uses the same `Content` object format (with `parts`), but without `role`.
4. Conversation must start with a `user` message (after system extraction).
5. Roles must alternate: `user` → `model` → `user` → ...

### Impact on GeminiAdapter

The shipped `build_payload()`:
1. Scans the incoming `messages` list for `system`-role messages (there is no `developer` role)
2. Joins their content into a `systemInstruction` Content object (`{parts: [{text}]}`)
3. Maps the remaining messages to Gemini's `contents` format (`assistant`→`model`, `parts` array)


## 5. Message Format — Contents with Parts

### 5.1 Roles (Only Two in Contents)

| Role | OpenAI Equivalent | Description |
|---|---|---|
| `user` | `user` | Human messages. |
| `model` | `assistant` | **NOT "assistant".** Model responses. |

No `system`, `developer`, `tool`, or `function` roles in the `contents` array.

### 5.2 Content Object Structure

```json
{
  "role": "user",
  "parts": [
    {"text": "What is in this image?"},
    {
      "inlineData": {
        "mimeType": "image/jpeg",
        "data": "<base64-encoded-data>"
      }
    }
  ]
}
```

### 5.3 Part Types

| Part Type | Structure | Description |
|---|---|---|
| `text` | `{"text": "..."}` | Plain text content |
| `inlineData` | `{"inlineData": {"mimeType": "...", "data": "..."}}` | Base64 inline binary data (images, audio, video) |
| `fileData` | `{"fileData": {"mimeType": "...", "fileUri": "..."}}` | Reference to uploaded file via File API |
| `functionCall` | `{"functionCall": {"name": "...", "args": {...}}}` | Model requesting a function call |
| `functionResponse` | `{"functionResponse": {"name": "...", "response": {...}}}` | Result of a function call |
| `executableCode` | `{"executableCode": {"language": "...", "code": "..."}}` | Code execution request |
| `codeExecutionResult` | `{"codeExecutionResult": {"outcome": "...", "output": "..."}}` | Code execution result |

### 5.4 Comparison with OpenAI and Anthropic

| Aspect | OpenAI | Anthropic | Gemini |
|---|---|---|---|
| Array name | `messages` | `messages` | `contents` |
| Assistant role | `assistant` | `assistant` | `model` |
| String shorthand | `content: "text"` | `content: "text"` | **Not supported** — always use `parts` array |
| Multipart content | `content: [{type, ...}]` | `content: [{type, ...}]` | `parts: [{text}, {inlineData}]` — different keys |
| Part type indicator | `type` field | `type` field | **Key name** (text, inlineData, fileData) — no `type` field |
| Image format | `{type: "image_url", image_url: {url}}` | `{type: "image", source: {type, data}}` | `{inlineData: {mimeType, data}}` |
| Image URL | `image_url.url` | `source.url` | `fileData.fileUri` (must use File API for URLs) |
| Tool results | Separate `role: "tool"` message | `tool_result` block in `user` message | `functionResponse` part in `user` message |
| Tool calls | `message.tool_calls[]` | `tool_use` content block | `functionCall` part in `model` message |

### 5.5 Multi-Turn Conversation Example

```json
{
  "systemInstruction": {
    "parts": [{"text": "You are a pirate. Respond in pirate speak."}]
  },
  "contents": [
    {
      "role": "user",
      "parts": [{"text": "What is the weather like today?"}]
    },
    {
      "role": "model",
      "parts": [{"text": "Ahoy! The skies be clear, matey!"}]
    },
    {
      "role": "user",
      "parts": [{"text": "Tell me about treasure hunting."}]
    }
  ],
  "generationConfig": {
    "temperature": 0.9,
    "maxOutputTokens": 1024
  }
}
```


## 6. Response Schema — Candidates Array

### 6.1 Full Response Structure

```json
{
  "candidates": [
    {
      "content": {
        "parts": [
          {"text": "Hello! How can I help you today?"}
        ],
        "role": "model"
      },
      "finishReason": "STOP",
      "index": 0,
      "safetyRatings": [
        {
          "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
          "probability": "NEGLIGIBLE"
        },
        {
          "category": "HARM_CATEGORY_HATE_SPEECH",
          "probability": "NEGLIGIBLE"
        },
        {
          "category": "HARM_CATEGORY_HARASSMENT",
          "probability": "NEGLIGIBLE"
        },
        {
          "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
          "probability": "NEGLIGIBLE"
        }
      ]
    }
  ],
  "usageMetadata": {
    "promptTokenCount": 10,
    "candidatesTokenCount": 12,
    "totalTokenCount": 22
  },
  "modelVersion": "gemini-2.5-flash"
}
```

### 6.2 Candidate Object

| Field | Type | Description |
|---|---|---|
| `content` | Content | The generated content with `role: "model"` and `parts[]`. |
| `finishReason` | FinishReason | Why generation stopped. See below. |
| `index` | integer | Candidate index (for `candidateCount > 1`). |
| `safetyRatings` | SafetyRating[] | Safety evaluation per category. |
| `citationMetadata` | CitationMetadata | Citation information for grounded content. |
| `tokenCount` | integer | Token count for this candidate. |
| `groundingMetadata` | GroundingMetadata | Grounding information (when using Google Search). |
| `avgLogprobs` | number | Average log probability of the candidate. |
| `logprobsResult` | LogprobsResult | Log probability details per token. |

### 6.3 FinishReason Values

| Gemini `finishReason` | OpenAI `finish_reason` | Shared `FinishReason` | Description |
|---|---|---|---|
| `STOP` | `stop` | `STOP` | Natural stop or stop sequence hit |
| `MAX_TOKENS` | `length` | `LENGTH` | Hit `maxOutputTokens` limit |
| `SAFETY` | `content_filter` | `CONTENT_FILTER` | **Unique mapping** — blocked by safety settings |
| `RECITATION` | (no equivalent) | `CONTENT_FILTER` | Blocked due to recitation/copyright |
| `LANGUAGE` | (no equivalent) | `STOP` | Unsupported language |
| `OTHER` | (no equivalent) | `STOP` | Unspecified reason |
| `BLOCKLIST` | (no equivalent) | `CONTENT_FILTER` | Blocked by terminology blocklist |
| `PROHIBITED_CONTENT` | (no equivalent) | `CONTENT_FILTER` | Blocked — CSAM or similar |
| `SPII` | (no equivalent) | `CONTENT_FILTER` | Blocked — sensitive PII |
| `MALFORMED_FUNCTION_CALL` | (no equivalent) | `ERROR` | Model produced invalid function call |
| (no equivalent) | `tool_calls` | `TOOL_CALLS` | Gemini uses `STOP` even when returning function calls |

### 6.4 Structural Differences from OpenAI

| Aspect | OpenAI | Gemini |
|---|---|---|
| **Wrapper** | `choices[]` | `candidates[]` |
| **Content access** | `choices[0].message.content` (string) | `candidates[0].content.parts[0].text` (parts array) |
| **Response ID** | `id` field at top level | No explicit response ID |
| **Model in response** | `model` field | `modelVersion` field |
| **Stop reason field** | `finish_reason` (snake_case) | `finishReason` (camelCase) |
| **Stop reason values** | lowercase: `stop`, `length` | UPPERCASE: `STOP`, `MAX_TOKENS` |
| **Safety info** | Not in standard response | `safetyRatings` on each candidate |
| **Usage location** | `usage` | `usageMetadata` |
| **Multiple responses** | `n > 1` → multiple `choices` | `candidateCount > 1` → multiple `candidates` |

### 6.5 Usage Metadata Differences

| Field | OpenAI | Anthropic | Gemini |
|---|---|---|---|
| Input tokens | `usage.prompt_tokens` | `usage.input_tokens` | `usageMetadata.promptTokenCount` |
| Output tokens | `usage.completion_tokens` | `usage.output_tokens` | `usageMetadata.candidatesTokenCount` |
| Total | `usage.total_tokens` | Not provided (sum) | `usageMetadata.totalTokenCount` |
| Cached tokens | `usage.prompt_tokens_details.cached_tokens` | `usage.cache_read_input_tokens` | `usageMetadata.cachedContentTokenCount` |
| Reasoning tokens | `usage.completion_tokens_details.reasoning_tokens` | Not broken out | `usageMetadata.thoughtsTokenCount` (Gemini 2.5) |


## 7. Streaming — streamGenerateContent

### 7.1 The Fundamental Difference

Gemini uses a **separate endpoint** for streaming instead of a body parameter:

| Provider | How Streaming is Enabled |
|---|---|
| **OpenAI** | Same endpoint, add `"stream": true` to body |
| **Anthropic** | Same endpoint, add `"stream": true` to body |
| **Gemini** | **Different endpoint:** `:streamGenerateContent` instead of `:generateContent` |

```
POST /v1beta/models/{model}:streamGenerateContent?key={API_KEY}&alt=sse
```

The `alt=sse` query parameter enables Server-Sent Events format. Without it, the response
is a JSON array of response objects.

### 7.2 SSE Stream Format

With `alt=sse`:

```
data: {"candidates":[{"content":{"parts":[{"text":"Hello"}],"role":"model"},"finishReason":"STOP","index":0}],"usageMetadata":{"promptTokenCount":5,"candidatesTokenCount":1,"totalTokenCount":6}}

data: {"candidates":[{"content":{"parts":[{"text":"! How"}],"role":"model"},"index":0}]}

data: {"candidates":[{"content":{"parts":[{"text":" can I help?"}],"role":"model"},"finishReason":"STOP","index":0}],"usageMetadata":{"promptTokenCount":5,"candidatesTokenCount":8,"totalTokenCount":13}}

```

### 7.3 Key Streaming Differences

| Aspect | OpenAI | Anthropic | Gemini |
|---|---|---|---|
| **Activation** | `stream: true` in body | `stream: true` in body | Different endpoint URL |
| **Format** | `data: {json}` lines | Named events (`event:` + `data:`) | `data: {json}` lines (with `alt=sse`) |
| **End signal** | `data: [DONE]` | `event: message_stop` | **No explicit end signal** — stream simply ends |
| **Delta structure** | `choices[0].delta.content` | `content_block_delta.delta.text` | `candidates[0].content.parts[0].text` |
| **Usage in stream** | Final chunk (with `stream_options`) | `message_start` + `message_delta` | **Every chunk** can contain `usageMetadata` |
| **Response ID** | Every chunk has `id` | `message_start` has `id` | **No response ID** in stream |

### 7.4 Stream Chunk Structure

Each SSE `data:` line contains a full `GenerateContentResponse` object — the same schema
as the non-streaming response, but with partial content:

```json
{
  "candidates": [
    {
      "content": {
        "parts": [{"text": "partial text"}],
        "role": "model"
      },
      "index": 0
    }
  ],
  "usageMetadata": {
    "promptTokenCount": 10,
    "candidatesTokenCount": 3,
    "totalTokenCount": 13
  }
}
```

The `finishReason` only appears on the final chunk for each candidate.
The `usageMetadata` may appear on intermediate chunks with running totals.

### 7.5 Parsing Algorithm for GeminiAdapter

> The sketch below shows the SSE handling conceptually. In the shipped code the adapter is
> stateless: it exposes `parse_stream_line(line) -> StreamChunk | None` (see §13.2) and the
> `ProviderGateway` owns the loop. There is no adapter-owned `complete_stream` and no
> `CompletionChunk` type; `thought`-flagged parts are surfaced as `StreamChunk.reasoning`.

```python
async def complete_stream(self, request: CompletionRequest) -> AsyncIterator[CompletionChunk]:
    chunk_index = 0

    async for line in self._read_sse_lines(response):
        if not line.startswith("data: "):
            continue

        data = json.loads(line[6:])

        if not data.get("candidates"):
            continue

        candidate = data["candidates"][0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])

        text_delta = None
        tool_call_chunks = None

        for part in parts:
            if "text" in part:
                text_delta = (text_delta or "") + part["text"]
            elif "functionCall" in part:
                fc = part["functionCall"]
                if tool_call_chunks is None:
                    tool_call_chunks = []
                tool_call_chunks.append(ToolCallChunk(
                    index=chunk_index,
                    id=f"call_{chunk_index}",
                    function_name=fc["name"],
                    arguments_delta=json.dumps(fc["args"]),
                ))
                chunk_index += 1

        finish_reason = None
        if candidate.get("finishReason"):
            finish_reason = self._map_finish_reason(candidate["finishReason"])

        usage = None
        if data.get("usageMetadata") and finish_reason is not None:
            um = data["usageMetadata"]
            usage = TokenUsage(
                prompt_tokens=um.get("promptTokenCount", 0),
                completion_tokens=um.get("candidatesTokenCount", 0),
                total_tokens=um.get("totalTokenCount", 0),
            )

        yield CompletionChunk(
            id="",  # Gemini does not provide response IDs
            delta_content=text_delta,
            finish_reason=finish_reason,
            usage=usage,
            tool_call_chunks=tool_call_chunks,
        )
```


## 8. Safety Settings — Unique to Gemini

Safety settings are a **Gemini-exclusive feature** with no equivalent in OpenAI or Anthropic.
They allow per-request control over content filtering thresholds.

### 8.1 Request Configuration

```json
{
  "safetySettings": [
    {
      "category": "HARM_CATEGORY_HARASSMENT",
      "threshold": "BLOCK_ONLY_HIGH"
    },
    {
      "category": "HARM_CATEGORY_HATE_SPEECH",
      "threshold": "BLOCK_ONLY_HIGH"
    },
    {
      "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
      "threshold": "BLOCK_NONE"
    },
    {
      "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
      "threshold": "BLOCK_ONLY_HIGH"
    }
  ]
}
```

### 8.2 HarmCategory Enum

| Value | Description |
|---|---|
| `HARM_CATEGORY_HARASSMENT` | Harassment content |
| `HARM_CATEGORY_HATE_SPEECH` | Hate speech |
| `HARM_CATEGORY_SEXUALLY_EXPLICIT` | Sexually explicit content |
| `HARM_CATEGORY_DANGEROUS_CONTENT` | Dangerous content (weapons, drugs, etc.) |
| `HARM_CATEGORY_CIVIC_INTEGRITY` | Content affecting civic integrity |

### 8.3 HarmBlockThreshold Enum

| Value | Description |
|---|---|
| `BLOCK_NONE` | Always allow (no blocking) |
| `BLOCK_ONLY_HIGH` | Block only high-probability harmful content |
| `BLOCK_MEDIUM_AND_ABOVE` | Block medium and high probability harmful content |
| `BLOCK_LOW_AND_ABOVE` | Block low, medium, and high probability harmful content |
| `HARM_BLOCK_THRESHOLD_UNSPECIFIED` | Use default threshold |

### 8.4 Response Safety Ratings

Every candidate in the response includes safety ratings:

```json
{
  "safetyRatings": [
    {
      "category": "HARM_CATEGORY_HARASSMENT",
      "probability": "NEGLIGIBLE",
      "blocked": false
    }
  ]
}
```

HarmProbability values: `NEGLIGIBLE`, `LOW`, `MEDIUM`, `HIGH`.

### 8.5 Relevance to The Bannered Mare

For roleplay sessions, users will likely want to set `BLOCK_NONE` or `BLOCK_ONLY_HIGH` for
most categories (especially `SEXUALLY_EXPLICIT` and `DANGEROUS_CONTENT`) to avoid overzealous
filtering. The adapter should support passing safety settings via `CompletionRequest.extra`.

Default safety settings for The Bannered Mare RP use:

```python
DEFAULT_RP_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"},
]
```


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

**Gemini:**
```json
{
  "functionDeclarations": [
    {
      "name": "get_weather",
      "description": "Get weather",
      "parameters": {
        "type": "object",
        "properties": {
          "location": {"type": "string", "description": "City name"}
        },
        "required": ["location"]
      }
    }
  ]
}
```

| Difference | OpenAI | Anthropic | Gemini |
|---|---|---|---|
| Wrapper | `{type: "function", function: {...}}` | Flat `{name, input_schema}` | `{functionDeclarations: [...]}` — array inside `tools[]` |
| Schema field | `parameters` | `input_schema` | `parameters` (same name as OpenAI) |
| Nesting | One tool per object | One tool per object | **Multiple declarations per tool object** |
| Strict mode | `function.strict` | `strict` | Not supported |

### 9.2 Tool Config (Tool Choice Equivalent)

**OpenAI** uses `tool_choice`:
```json
"none" | "auto" | "required" | {"type": "function", "function": {"name": "..."}}
```

**Gemini** uses `toolConfig`:
```json
{
  "toolConfig": {
    "functionCallingConfig": {
      "mode": "AUTO"
    }
  }
}
```

| Shared Value | OpenAI | Anthropic | Gemini |
|---|---|---|---|
| No tools | `"none"` | `{"type": "none"}` | `{"mode": "NONE"}` |
| Model decides | `"auto"` | `{"type": "auto"}` | `{"mode": "AUTO"}` |
| Must use tool | `"required"` | `{"type": "any"}` | `{"mode": "ANY"}` |
| Specific tool | `{"type": "function", "function": {"name": "X"}}` | `{"type": "tool", "name": "X"}` | `{"mode": "ANY", "allowedFunctionNames": ["X"]}` |

### 9.3 Tool Call in Response

**OpenAI** (in `message.tool_calls`):
```json
{
  "id": "call_abc123",
  "type": "function",
  "function": {"name": "get_weather", "arguments": "{\"location\":\"NYC\"}"}
}
```

**Gemini** (as part in `content.parts`):
```json
{
  "functionCall": {
    "name": "get_weather",
    "args": {"location": "NYC"}
  }
}
```

| Difference | OpenAI | Anthropic | Gemini |
|---|---|---|---|
| Location | `message.tool_calls[]` | `content[]` block | `content.parts[]` — inside parts |
| Arguments | `arguments` (JSON **string**) | `input` (parsed object) | `args` (parsed **object**) |
| ID | `call_abc123` | `toolu_abc123` | **No ID** — identified by function name |
| Name field | `function.name` | `name` | `functionCall.name` |

### 9.4 Tool Result

**OpenAI** (separate message):
```json
{"role": "tool", "tool_call_id": "call_abc123", "content": "72F, sunny"}
```

**Gemini** (functionResponse part in user message):
```json
{
  "role": "user",
  "parts": [
    {
      "functionResponse": {
        "name": "get_weather",
        "response": {"result": "72F, sunny"}
      }
    }
  ]
}
```

| Difference | OpenAI | Anthropic | Gemini |
|---|---|---|---|
| Role | `tool` (dedicated) | `user` (tool_result inside) | `user` (functionResponse inside) |
| ID reference | `tool_call_id` | `tool_use_id` | `name` (function name, **not ID**) |
| Result format | String `content` | String `content` | Object `response` (must be dict) |

### 9.5 Built-In Tools (Gemini-Exclusive)

Gemini offers built-in tools specified by type:

| Tool | Declaration | Description |
|---|---|---|
| Google Search | `{"googleSearch": {}}` | Grounded search via Google |
| Code Execution | `{"codeExecution": {}}` | Execute Python code |
| Google Search Retrieval | `{"googleSearchRetrieval": {...}}` | Retrieve and ground from search |

These are placed directly in the `tools` array alongside `functionDeclarations`.


## 10. Context Caching

Gemini supports server-side context caching for reducing costs on repeated prompts.

### 10.1 How It Works

1. **Create** a cached content resource via the CachedContents API:

```
POST /v1beta/cachedContents?key={API_KEY}
```

```json
{
  "model": "models/gemini-2.5-flash",
  "contents": [...],
  "systemInstruction": {...},
  "ttl": "600s"
}
```

2. **Reference** the cached content in generateContent:

```json
{
  "cachedContent": "cachedContents/abc123",
  "contents": [
    {"role": "user", "parts": [{"text": "New question about the cached context"}]}
  ]
}
```

### 10.2 Comparison with Anthropic Caching

| Aspect | Anthropic | Gemini |
|---|---|---|
| Mechanism | `cache_control` on individual blocks | Separate CachedContents API |
| Granularity | Per-block | Entire conversation prefix |
| TTL options | 5m, 1h | Custom (seconds) |
| Reference | Implicit (matching prefix) | Explicit resource name |
| API call | Same endpoint | Separate create + reference |

### 10.3 Relevance to The Bannered Mare

System prompts + character contexts are repeated across an entire chat session. Gemini's
cached content could significantly reduce costs. The adapter should support creating and
referencing cached content via `CompletionRequest.extra["cached_content"]`.


## 11. Token Counting Endpoint

Like Anthropic, Gemini provides a dedicated token counting endpoint.

### Endpoint

```
POST /v1beta/models/{model}:countTokens?key={API_KEY}
```

### Request

```json
{
  "contents": [
    {"role": "user", "parts": [{"text": "Hello, how are you?"}]}
  ]
}
```

### Response

```json
{
  "totalTokens": 6
}
```

### Comparison

| Provider | Token Counting | Method |
|---|---|---|
| **OpenAI** | No dedicated endpoint | Use tiktoken library (client-side) |
| **Anthropic** | `POST /v1/messages/count_tokens` | Server-side, returns `input_tokens` |
| **Gemini** | `POST /v1beta/models/{model}:countTokens` | Server-side, returns `totalTokens` |


## 12. Key Differences from OpenAI — Summary Table

| Aspect | OpenAI | Gemini | Adapter Must Handle |
|---|---|---|---|
| **Auth** | `Authorization: Bearer` header | `?key=` **query parameter** | Append to URL, not headers |
| **Endpoint** | `/v1/chat/completions` | `/v1beta/models/{model}:generateContent` | Model in URL path |
| **Streaming endpoint** | Same endpoint | `:streamGenerateContent?alt=sse` | Different URL for streaming |
| **Model location** | `model` field in body | **URL path parameter** | Extract from request, put in URL |
| **System prompt** | Message with `role: "system"` | `systemInstruction` top-level field | Extract from messages |
| **Messages array name** | `messages` | `contents` | Rename |
| **Assistant role** | `assistant` | `model` | Role mapping |
| **Message roles** | system, developer, user, assistant, tool | user, model only | Role mapping + extraction |
| **Content format** | `{role, content: string}` or parts | `{role, parts: [{text: "..."}]}` | Always use parts array |
| **Generation params** | Flat in body | Nested in `generationConfig` | Wrap in config object |
| **max_tokens name** | `max_completion_tokens` / `max_tokens` | `maxOutputTokens` | Rename + nest |
| **stop param name** | `stop` | `stopSequences` | Rename + nest |
| **n param name** | `n` | `candidateCount` | Rename + nest |
| **topK** | Not supported | `topK` in `generationConfig` | Pass through |
| **frequency_penalty** | Supported (flat) | Supported (nested in config) | Move to config |
| **presence_penalty** | Supported (flat) | Supported (nested in config) | Move to config |
| **logit_bias** | Supported | **Not supported** | Drop from payload |
| **seed** | Supported (flat) | Supported (nested in config) | Move to config |
| **Safety settings** | Not available | `safetySettings` array | Gemini-only, pass via `extra` |
| **Response wrapper** | `choices[0].message.content` (string) | `candidates[0].content.parts[0].text` | Different extraction path |
| **Response ID** | `id` field | **Not provided** | Generate or leave empty |
| **Stop reason field** | `finish_reason` (snake_case) | `finishReason` (camelCase) | Rename |
| **Stop reason values** | `stop`, `length`, `tool_calls` | `STOP`, `MAX_TOKENS`, `SAFETY` | Value mapping (case + names) |
| **Usage field** | `usage` | `usageMetadata` | Different path |
| **Usage names** | `prompt_tokens`, `completion_tokens` | `promptTokenCount`, `candidatesTokenCount` | Rename |
| **Streaming activation** | `stream: true` in body | **Separate endpoint URL** | Use different URL |
| **Stream end signal** | `data: [DONE]` | **None** — stream ends | Different detection |
| **Stream chunk shape** | `delta.content` (string) | Full `candidates[0].content.parts` | Different extraction |
| **Tool definition** | `{type: "function", function: {name, parameters}}` | `{functionDeclarations: [{name, parameters}]}` | Restructure |
| **Tool choice** | `tool_choice` (string/object) | `toolConfig.functionCallingConfig.mode` | Restructure + rename |
| **Tool call response** | `message.tool_calls[].function.arguments` (string) | `content.parts[].functionCall.args` (object) | Different path + serialize |
| **Tool call ID** | `call_abc123` | **No ID** | Generate synthetic IDs |
| **Tool result** | `role: "tool"` message | `functionResponse` part in user message | Role + structure change |
| **Response format** | `response_format` object | `responseMimeType` + `responseSchema` | Split into two fields |
| **Thinking** | Not supported | `thinkingConfig` in `generationConfig` (2.5+) | Gemini-specific |
| **Caching** | Not supported | `cachedContent` resource reference | Gemini-specific |
| **Token counting API** | Not available | `POST /v1beta/models/{model}:countTokens` | Gemini-specific |
| **Naming convention** | snake_case | camelCase | Case conversion everywhere |


## 13. GeminiAdapter Implementation Spec

### 13.1 File Location

```
src/provider/adapters/gemini.py
```

### 13.2 Core Implementation

The shipped `GeminiAdapter` is stateless. A single `build_url()` handles both streaming and
non-streaming (choosing `streamGenerateContent` + `?alt=sse` when `stream` is true), and the API
key is always a `?key=` query param — there is no OAuth Bearer path. Sampling params map into
`generationConfig` via `_GENERATION_CONFIG_MAP`; Gemini 2.5+ "thinking" parts are detected in the
response (parts flagged `thought: true`), not requested via a `reasoning_effort` budget.

```python
_FINISH_REASON_MAP = {
    "STOP": "stop", "MAX_TOKENS": "length", "SAFETY": "content_filter",
    "RECITATION": "content_filter", "LANGUAGE": "content_filter",
    "BLOCKLIST": "content_filter", "PROHIBITED_CONTENT": "content_filter",
    "SPII": "content_filter", "MALFORMED_FUNCTION_CALL": "stop",
}
_GENERATION_CONFIG_MAP = {
    "temperature": "temperature", "top_p": "topP", "top_k": "topK",
    "max_output_tokens": "maxOutputTokens", "stop_sequences": "stopSequences",
    "frequency_penalty": "frequencyPenalty", "presence_penalty": "presencePenalty",
    "seed": "seed",
}
_ROLE_MAP = {"assistant": "model", "user": "user"}


class GeminiAdapter(ProviderAdapter):
    """Adapter for the Google Gemini generateContent API."""

    def build_url(self, base_url, model, stream, api_key=None) -> str:
        base = base_url.rstrip("/")
        if stream:
            action, params = "streamGenerateContent", {"alt": "sse"}
        else:
            action, params = "generateContent", {}
        if api_key:
            params["key"] = api_key
        url = f"{base}/v1beta/models/{model}:{action}"
        return f"{url}?{urlencode(params)}" if params else url

    def build_headers(self, api_key) -> dict[str, str]:
        return {"Content-Type": "application/json"}   # key is in the URL

    def build_payload(self, messages, model, stream, parameters) -> dict[str, Any]:
        system_parts, contents = [], []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_parts.append(content)
                continue
            contents.append({"role": _ROLE_MAP.get(role, role), "parts": [{"text": content}]})

        payload = {"contents": contents}
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}

        gen_config = {}
        for param_key, config_key in _GENERATION_CONFIG_MAP.items():
            value = parameters.get(param_key)
            if value is not None:
                gen_config[config_key] = value
        if "maxOutputTokens" not in gen_config and "max_tokens" in parameters:
            gen_config["maxOutputTokens"] = parameters["max_tokens"]   # fallback
        if gen_config:
            payload["generationConfig"] = gen_config

        if parameters.get("safety_settings"):
            payload["safetySettings"] = parameters["safety_settings"]
        return payload

    def parse_response(self, data) -> CompletionResponse:
        candidates = data.get("candidates", [{}])
        candidate = candidates[0] if candidates else {}
        parts = candidate.get("content", {}).get("parts", [])
        content = "".join(p.get("text", "") for p in parts if "text" in p and not p.get("thought"))
        reasoning = "".join(p.get("text", "") for p in parts if p.get("thought")) or None
        raw_reason = candidate.get("finishReason") or "STOP"
        usage = data.get("usageMetadata", {})
        return CompletionResponse(
            content=content,
            finish_reason=_FINISH_REASON_MAP.get(raw_reason, raw_reason.lower()),
            usage=TokenUsage(
                input_tokens=usage.get("promptTokenCount", 0),
                output_tokens=usage.get("candidatesTokenCount", 0),
                total_tokens=usage.get("totalTokenCount", 0),
                cache_read_tokens=usage.get("cachedContentTokenCount", 0),
            ),
            reasoning=reasoning,
            raw=data,
        )

    def parse_stream_line(self, line) -> StreamChunk | None:
        # "data: " SSE lines only (?alt=sse); same candidates/parts extraction as above,
        # returning content/reasoning/finish_reason/usage as a StreamChunk (None to skip).
        ...
```

Not implemented: tool/function-calling (`functionDeclarations`, `toolConfig`,
`functionResponse`), image/inline-data parts, `responseSchema`/JSON mode, logprobs config,
`candidateCount` (n), cached content, and a `reasoning_effort`→`thinkingConfig` mapping.


## 14. Mapping: Shared Types to Gemini API

::: info Some rows describe unbuilt features
The shipped adapter maps `temperature`, `top_p`→topP, `top_k`→topK,
`max_output_tokens`/`max_tokens`→maxOutputTokens, `stop_sequences`→stopSequences,
`frequency_penalty`/`presence_penalty`, and `seed` into `generationConfig`, plus `safety_settings`.
Rows for tools, `responseSchema`/JSON mode, logprobs, `candidateCount`, cached content, and
`reasoning_effort`→thinking are **not implemented**. There is no `CompletionRequest`/`CompletionChunk`
object — requests are a `messages` list + `parameters` dict, and streaming yields `StreamChunk`.
:::

### 14.1 CompletionRequest to Gemini Payload

| Shared Field | Gemini Field | Transformation |
|---|---|---|
| `messages` (system role) | `systemInstruction` (top-level) | Extract, wrap in Content object with `parts` |
| `messages` (user/assistant) | `contents` | Rename array, map `assistant` role to `model`, format as parts |
| `messages` (tool role) | `functionResponse` part in user message | Restructure entirely |
| `messages` (developer role) | `systemInstruction` (top-level) | Merge with system |
| `model` | URL path `{model}` | Remove from body, place in URL |
| `temperature` | `generationConfig.temperature` | Nest in config |
| `top_p` | `generationConfig.topP` | Nest + camelCase |
| `max_tokens` | `generationConfig.maxOutputTokens` | Rename + nest |
| `stop` | `generationConfig.stopSequences` | Rename + nest |
| `n` | `generationConfig.candidateCount` | Rename + nest |
| `frequency_penalty` | `generationConfig.frequencyPenalty` | Nest + camelCase |
| `presence_penalty` | `generationConfig.presencePenalty` | Nest + camelCase |
| `seed` | `generationConfig.seed` | Nest |
| `stream` | Separate URL (`:streamGenerateContent`) | Not a body field — change endpoint |
| `reasoning_effort` | `generationConfig.thinkingConfig` | Map to thinking budget |
| `response_format` | `generationConfig.responseMimeType` + `responseSchema` | Split into two config fields |
| `logprobs` | `generationConfig.responseLogprobs` | Rename + nest |
| `top_logprobs` | `generationConfig.logprobs` | Rename + nest |
| `tools` | `tools[].functionDeclarations[]` | Wrap all in single functionDeclarations object |
| `tool_choice` | `toolConfig.functionCallingConfig.mode` | Map values + restructure |
| `logit_bias` | *(dropped)* | Not supported |
| `extra.top_k` | `generationConfig.topK` | Move into config |
| `extra.safety_settings` | `safetySettings` | Pass through |
| `extra.cached_content` | `cachedContent` | Pass through |

### 14.2 Gemini Response to CompletionResponse

| Gemini Field | Shared Field | Transformation |
|---|---|---|
| *(not provided)* | `id` | Empty string (Gemini has no response ID) |
| `candidates[0].content.parts[].text` | `content` | Concatenate all text parts |
| `candidates[0].content.parts[].functionCall` | `tool_calls` | Extract, generate synthetic IDs, serialize `args` to JSON string |
| `candidates[0].finishReason` | `finish_reason` | Map UPPERCASE values to shared enum |
| `usageMetadata.promptTokenCount` | `usage.prompt_tokens` | Rename |
| `usageMetadata.candidatesTokenCount` | `usage.completion_tokens` | Rename |
| `usageMetadata.totalTokenCount` | `usage.total_tokens` | Rename |
| `usageMetadata.cachedContentTokenCount` | `usage.cached_tokens` | Rename |
| `modelVersion` | `model` | Rename |
| (full response) | `raw` | Preserve for debugging |

### 14.3 Gemini Stream Chunks to CompletionChunk

| Gemini Chunk Field | Shared CompletionChunk Field | Transformation |
|---|---|---|
| *(not provided)* | `id` | Empty string |
| `candidates[0].content.parts[0].text` | `delta_content` | Extract text from parts |
| `candidates[0].content.parts[].functionCall` | `tool_call_chunks[].arguments_delta` | Serialize `args`, generate IDs |
| `candidates[0].finishReason` | `finish_reason` | Map values (only on final chunk) |
| `usageMetadata` (on final chunk) | `usage` | Rename fields, only emit on finish |
| *(stream end)* | *(iteration end)* | No explicit signal — stream closes |


## 15. Implementation Status

### Delivered (`src/provider/adapters/gemini.py`)

```
- build_url(): {base_url}/v1beta/models/{model}:generateContent?key=...  (non-stream)
              and :streamGenerateContent?alt=sse&key=...                 (stream)
- build_headers(): Content-Type only (key is in the URL)
- build_payload():
    a. Extract system messages → systemInstruction (parts)
    b. Format remaining messages as contents (assistant → "model")
    c. Map sampling params into generationConfig (_GENERATION_CONFIG_MAP + max_tokens fallback)
    d. Pass safety_settings through when provided
- parse_response(): text vs thought parts, finishReason mapping, cache-aware TokenUsage
- parse_stream_line(): "data: " SSE lines from ?alt=sse; content/reasoning/finish/usage
- Registered in the registry: ProviderType.GOOGLE → GeminiAdapter
- Reasoning: thinking ("thought") parts are surfaced on CompletionResponse.reasoning
```

### Not Yet Built

```
- Tool/function calling (functionDeclarations, toolConfig, functionResponse)
- reasoning_effort → thinkingConfig.thinkingBudget mapping
- Structured output (responseMimeType / responseSchema)
- Image / inline-data multimodal parts
- candidateCount (n), logprobs config, cached content
- Token-counting endpoint (:countTokens) integration
```


## Appendix A: Gemini Error Responses

### Error Format

```json
{
  "error": {
    "code": 400,
    "message": "Invalid value at 'contents[0].parts[0]'",
    "status": "INVALID_ARGUMENT",
    "details": [...]
  }
}
```

### Error Codes

| HTTP Status | gRPC Status | Description |
|---|---|---|
| 400 | `INVALID_ARGUMENT` | Malformed request |
| 401 | `UNAUTHENTICATED` | Invalid or missing API key |
| 403 | `PERMISSION_DENIED` | API key lacks permissions |
| 404 | `NOT_FOUND` | Model not found |
| 429 | `RESOURCE_EXHAUSTED` | Rate limit exceeded |
| 500 | `INTERNAL` | Server error |
| 503 | `UNAVAILABLE` | Service temporarily unavailable |

### Mapping to The Bannered Mare Exceptions

The gateway (`ProviderGateway._handle_http_error`) maps by HTTP status only:

| Gemini Error | The Bannered Mare Exception |
|---|---|
| `UNAUTHENTICATED` (401) | `ProviderAuthError` |
| `RESOURCE_EXHAUSTED` (429) | `ProviderRateLimitError` |
| `INVALID_ARGUMENT` (400) | `ProviderInvalidRequestError` |
| `NOT_FOUND` (404) / `INTERNAL` (500) / `UNAVAILABLE` (503) | `ProviderException` (all other statuses) |


## Appendix B: Gemini Model Names

| Model | ID | Status | Context Window | Max Output |
|---|---|---|---|---|
| Gemini 3.1 Pro | `gemini-3.1-pro-preview` | Preview | 1M tokens | 65,536 |
| Gemini 3 Flash | `gemini-3-flash-preview` | Preview | 1M tokens | 65,536 |
| Gemini 2.5 Pro | `gemini-2.5-pro` | Stable | 1M tokens | 65,536 |
| Gemini 2.5 Flash | `gemini-2.5-flash` | Stable | 1M tokens | 65,536 |

Model names are used directly in the URL path: `/v1beta/models/gemini-2.5-flash:generateContent`.


## Appendix C: Complete Request/Response Examples

### Non-Streaming Request

```http
POST /v1beta/models/gemini-2.5-flash:generateContent?key=AIza... HTTP/1.1
Host: generativelanguage.googleapis.com
Content-Type: application/json

{
  "systemInstruction": {
    "parts": [{"text": "You are a pirate named Captain Blackbeard."}]
  },
  "contents": [
    {
      "role": "user",
      "parts": [{"text": "Tell me about your ship."}]
    }
  ],
  "generationConfig": {
    "temperature": 0.9,
    "topP": 0.95,
    "topK": 40,
    "maxOutputTokens": 2048,
    "stopSequences": ["END_SCENE"]
  },
  "safetySettings": [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"}
  ]
}
```

### Non-Streaming Response

```json
{
  "candidates": [
    {
      "content": {
        "parts": [
          {"text": "Arrr! Me ship, the Queen Anne's Revenge, be the finest vessel to sail the seven seas!"}
        ],
        "role": "model"
      },
      "finishReason": "STOP",
      "index": 0,
      "safetyRatings": [
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "probability": "NEGLIGIBLE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "probability": "NEGLIGIBLE"},
        {"category": "HARM_CATEGORY_HARASSMENT", "probability": "NEGLIGIBLE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "probability": "NEGLIGIBLE"}
      ]
    }
  ],
  "usageMetadata": {
    "promptTokenCount": 25,
    "candidatesTokenCount": 22,
    "totalTokenCount": 47
  },
  "modelVersion": "gemini-2.5-flash"
}
```

### Streaming Request

```http
POST /v1beta/models/gemini-2.5-flash:streamGenerateContent?key=AIza...&alt=sse HTTP/1.1
Host: generativelanguage.googleapis.com
Content-Type: application/json

{
  "contents": [
    {"role": "user", "parts": [{"text": "Tell me a story."}]}
  ],
  "generationConfig": {
    "temperature": 0.8,
    "maxOutputTokens": 1024
  }
}
```

### Streaming Response

```
data: {"candidates":[{"content":{"parts":[{"text":"Once upon"}],"role":"model"},"index":0}]}

data: {"candidates":[{"content":{"parts":[{"text":" a time,"}],"role":"model"},"index":0}]}

data: {"candidates":[{"content":{"parts":[{"text":" there was"}],"role":"model"},"index":0}]}

data: {"candidates":[{"content":{"parts":[{"text":" a brave knight."}],"role":"model"},"finishReason":"STOP","index":0}],"usageMetadata":{"promptTokenCount":6,"candidatesTokenCount":12,"totalTokenCount":18}}

```

### Tool Calling Request

```json
{
  "contents": [
    {"role": "user", "parts": [{"text": "What is the weather in New York?"}]}
  ],
  "tools": [
    {
      "functionDeclarations": [
        {
          "name": "get_weather",
          "description": "Get current weather for a city",
          "parameters": {
            "type": "object",
            "properties": {
              "city": {"type": "string", "description": "City name"}
            },
            "required": ["city"]
          }
        }
      ]
    }
  ],
  "toolConfig": {
    "functionCallingConfig": {
      "mode": "AUTO"
    }
  }
}
```

### Tool Calling Response

```json
{
  "candidates": [
    {
      "content": {
        "parts": [
          {
            "functionCall": {
              "name": "get_weather",
              "args": {"city": "New York"}
            }
          }
        ],
        "role": "model"
      },
      "finishReason": "STOP",
      "index": 0
    }
  ],
  "usageMetadata": {
    "promptTokenCount": 30,
    "candidatesTokenCount": 8,
    "totalTokenCount": 38
  }
}
```

### Tool Result Follow-Up

```json
{
  "contents": [
    {"role": "user", "parts": [{"text": "What is the weather in New York?"}]},
    {
      "role": "model",
      "parts": [{"functionCall": {"name": "get_weather", "args": {"city": "New York"}}}]
    },
    {
      "role": "user",
      "parts": [
        {
          "functionResponse": {
            "name": "get_weather",
            "response": {"temperature": "72F", "condition": "sunny"}
          }
        }
      ]
    }
  ]
}
```
