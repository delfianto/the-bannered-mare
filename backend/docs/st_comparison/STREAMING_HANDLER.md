# Streaming Architecture Comparison: SillyTavern v1.17.0 vs Candlekeep Core

Side-by-side analysis of how each system handles SSE streaming from provider
APIs to the consumer (browser frontend in ST, API client in Candlekeep).

---

## 1. Stream Proxy vs Typed Event Pipeline

### SillyTavern: Transparent Byte Proxy

ST's backend is a pass-through relay. `forwardFetchResponse()` uses Node's
`Readable.pipe()` to forward the raw byte stream from the provider directly to
the Express response with zero transformation:

```
Provider SSE bytes  -->  pipe()  -->  Browser
```

The backend never parses, validates, or restructures SSE data. All
provider-specific parsing happens on the JavaScript frontend. The one exception
is Ollama, where `parseOllamaStream()` transcodes JSONL into OpenAI-compatible
SSE events before piping.

**Implication:** The backend is trivially simple (one function serves all
providers), but the frontend must contain a complete multi-provider parser.

### Candlekeep Core: Adapter-Parsed Typed Events

Candlekeep parses the stream server-side and emits a uniform typed event
protocol. The pipeline has three layers:

```
Provider SSE bytes
    |
    v
ProviderGateway (httpx async line iteration)
    |  calls adapter.parse_stream_line(line) per provider
    v
AsyncIterator[StreamChunk]     (canonical: content, reasoning, finish_reason, usage)
    |
    v
ChatMessageService._stream_completion()
    |  maps StreamChunks to StreamEvents
    v
AsyncIterator[StreamEvent]     (typed: start, text, reasoning, usage, done, error)
    |
    v
Router serializes to SSE:  data: {"type":"text","content":"Hello"}\n\n
```

Every provider adapter implements `parse_stream_line()` that returns a
`StreamChunk` or `None`. The service layer then maps chunks into a fixed
`StreamEvent` protocol with six event types: `start`, `text`, `reasoning`,
`usage`, `done`, `error`.

**Implication:** The API client receives a single, provider-agnostic event
format. The client never needs to know which provider is generating the response.
The cost is that provider-specific parsing logic lives in the backend adapter
layer.

### Summary

| Aspect | SillyTavern | Candlekeep Core |
|--------|-------------|-----------------|
| Backend transformation | None (raw pipe) | Full parse + normalization |
| Provider parsing location | Frontend (JS) | Backend (Python adapters) |
| Client complexity | High (multi-provider parser) | Low (single event schema) |
| Event format to client | Raw provider SSE | `{"type": "text", "content": "..."}` |
| Intermediate types | None | `StreamChunk` -> `StreamEvent` |

---

## 2. Provider-Specific Stream Parsing

### SillyTavern: Frontend Dispatch Chain

`parseStreamData()` in `sse-stream.js` is a cascading if/else that checks JSON
structure to determine the provider. It tests seven conditions in priority order
(Cohere, Claude, Gemini, NovelAI/KoboldCpp, llama.cpp, OpenAI-compatible) and
falls through to an exception for unknown formats. Within the OpenAI-compatible
branch, there are eight sub-conditions for different content paths
(`delta.content`, `delta.reasoning_content`, `delta.reasoning`, Mistral thinking
arrays, etc.).

A separate `getStreamingReply()` function in `openai.js` performs a parallel
extraction keyed by `chat_completion_source` enum rather than by JSON structure.
These two functions partially overlap in responsibility.

### Candlekeep Core: Polymorphic Adapter Methods

Each provider has its own adapter class implementing `parse_stream_line()`:

| Adapter | Class | Parsing strategy |
|---------|-------|-----------------|
| Anthropic | `AnthropicAdapter` | Matches `type` field: `content_block_delta` (text/thinking), `message_delta` (finish + usage), `message_stop` |
| OpenAI | `OpenAIAdapter` | Strips `data: ` prefix, handles `[DONE]` sentinel, extracts from `choices[0].delta` with `reasoning_content` / `reasoning` fallback |
| Gemini | `GeminiAdapter` | Extracts from `candidates[0].content.parts`, separates `thought: true` parts from text parts |
| Ollama | `OllamaAdapter` | Inherits from `OpenAIAdapter` unchanged (Ollama's `/v1/chat/completions` is OpenAI-compatible) |

All four return the same `StreamChunk(content, reasoning, finish_reason, usage)`
dataclass. The gateway layer iterates lines and delegates without knowing which
adapter is active.

### Summary

| Aspect | SillyTavern | Candlekeep Core |
|--------|-------------|-----------------|
| Dispatch mechanism | JSON structure sniffing + enum switch | Polymorphic class per provider |
| Number of parsing codepaths | ~15 (7 main + 8 OpenAI sub-paths) | 4 adapter classes |
| Output type | Yields `{ data, chunk, reasoning }` | Returns `StreamChunk` dataclass |
| Extensibility | Add branches to if/else chain | Add new adapter class |
| Ollama handling | Custom JSONL-to-SSE transcoder | Inherits OpenAI adapter (Ollama serves `/v1/`) |

---

## 3. Abort / Cancellation Mechanism

### SillyTavern: Two-Level AbortController Chain

ST implements abort at both frontend and backend:

1. **Frontend:** `StreamingProcessor` creates an `AbortController`. The Stop
   button calls `controller.abort()`, which terminates the `fetch()`.
2. **Backend:** Each provider handler creates its own `AbortController`. When
   the Express socket emits `close` (triggered by the frontend abort), the
   handler calls `controller.abort()` on the upstream `fetch()` to the provider.
3. **Stream teardown:** `forwardFetchResponse()` separately calls
   `from.body.destroy()` on socket close.

Special case: KoboldCpp requires an explicit `POST /api/extra/abort` HTTP call
before aborting the controller.

### Candlekeep Core: Disconnection Polling

The router checks `request.is_disconnected()` on each event iteration:

```python
async for event in stream_iterator:
    if await request.is_disconnected():
        return
    yield f"data: {json.dumps(stream_event_to_dict(event))}\n\n"
```

When disconnection is detected, the generator returns, which causes the
`StreamingResponse` to end. The underlying `httpx` async stream context manager
closes the HTTP connection to the provider as part of normal cleanup when the
async iterator exits scope.

There is no explicit `AbortController` equivalent. Cancellation is cooperative:
the generator checks between events rather than interrupting mid-chunk.

### Summary

| Aspect | SillyTavern | Candlekeep Core |
|--------|-------------|-----------------|
| Frontend abort | `AbortController.abort()` | Client closes connection |
| Backend abort | Socket `close` -> `controller.abort()` | `request.is_disconnected()` polling |
| Upstream teardown | Explicit `body.destroy()` + `AbortError` | httpx context manager cleanup |
| Abort granularity | Immediate (signal-based) | Between events (cooperative) |
| Special provider handling | KoboldCpp explicit abort endpoint | None |

---

## 4. Reasoning / Thinking Content

### SillyTavern: Three-Layer Reasoning System

Reasoning is handled across three independent layers:

1. **Stream parsing** (`parseStreamData`): Yields `{ reasoning: true }` flag per
   chunk. Supports Claude `delta.thinking`, Gemini `thought: true` parts,
   DeepSeek/xAI `reasoning_content`, OpenRouter `reasoning`, Mistral thinking
   arrays.

2. **Reply extraction** (`getStreamingReply`): Accumulates reasoning text into
   `state.reasoning`, gated by the `show_thoughts` setting.

3. **ReasoningHandler class**: Manages the full lifecycle with state machine
   (`None` -> `Thinking` -> `Done`/`Hidden`), duration tracking, DOM updates,
   auto-parsing of XML-like think blocks from message text, hidden-reasoning
   model detection (o1, o3, etc.), and reasoning signature storage for
   OpenRouter Claude models.

### Candlekeep Core: Two-Level Reasoning Pipeline

1. **Adapter layer** (`parse_stream_line`): Each adapter extracts reasoning into
   `StreamChunk.reasoning`:
   - `AnthropicAdapter`: `thinking_delta` blocks
   - `OpenAIAdapter`: `delta.reasoning_content` or `delta.reasoning`
   - `GeminiAdapter`: Parts with `thought: true`

2. **Service layer** (`_stream_completion`): Accumulates `full_reasoning` from
   chunks and emits `StreamEvent(type="reasoning", content=...)`. After the
   stream completes, if no API-level reasoning was found, `parse_reasoning_tags()`
   extracts `<think>...</think>` blocks from the content (covering local models
   like DeepSeek R1, QwQ, Qwen3 that embed reasoning in output text).

   The extracted reasoning is persisted to `Message.reasoning_content` in the
   database alongside the cleaned message content.

### Summary

| Aspect | SillyTavern | Candlekeep Core |
|--------|-------------|-----------------|
| Provider-specific extraction | Per-provider in frontend JS | Per-adapter `parse_stream_line()` |
| Think-tag auto-parsing | Configurable prefix/suffix in ReasoningHandler | `parse_reasoning_tags()` with `<think>`/`</think>` default |
| Duration tracking | `startTime`/`endTime` in ReasoningHandler | Not implemented |
| Hidden reasoning models | Explicit list (o1, o3, etc.) | Not implemented |
| Reasoning signatures | Stored for OpenRouter Claude, Gemini | Not implemented |
| Client receives | Raw reasoning text (client renders) | `{"type":"reasoning","content":"..."}` events |
| Persistence | `chat[messageId].extra.reasoning_duration` | `Message.reasoning_content` column |

---

## 5. Token Usage from Streams

### SillyTavern: Client-Side Tokenizer

ST does **not** extract `usage` objects from streaming responses. Token counts
are computed on the client using a tokenizer after the stream completes:

```js
const currentTokenCount = isFinal && power_user.message_token_count_enabled
    ? await getTokenCountAsync(tokenCountText, 0) : 0;
```

TPS (tokens per second) is calculated from wall-clock time and the client-side
token count. This approach works uniformly across all providers but produces
approximate counts.

### Candlekeep Core: Provider-Reported Usage with Fallback

Each adapter extracts `TokenUsage` from stream data when the provider includes
it:

- **Anthropic**: `message_delta` event carries `usage.output_tokens`
- **OpenAI**: `usage` object in the final chunk (when `stream_options` is set)
- **Gemini**: `usageMetadata` in each stream frame with `promptTokenCount`,
  `candidatesTokenCount`, `totalTokenCount`, `cachedContentTokenCount`

The service accumulates the last usage and emits a dedicated event:

```python
yield StreamEvent(
    type="usage",
    input_tokens=last_usage.input_tokens,
    output_tokens=last_usage.output_tokens,
    cache_read_tokens=last_usage.cache_read_tokens,
    cache_creation_tokens=last_usage.cache_creation_tokens,
)
```

If the provider does not report output tokens, the service falls back to
`TokenizerService.count_tokens()`:

```python
token_count = (
    last_usage.output_tokens
    if last_usage and last_usage.output_tokens
    else self.tokenizer.count_tokens(full_content)
)
```

The non-streaming path also tracks token drift between estimated and actual
counts via structured logging.

### Summary

| Aspect | SillyTavern | Candlekeep Core |
|--------|-------------|-----------------|
| Primary source | Client-side tokenizer | Provider-reported `usage` objects |
| Fallback | None (tokenizer only) | Local tokenizer when provider omits usage |
| Cache token tracking | Not tracked | `cache_read_tokens`, `cache_creation_tokens` |
| Usage event to client | None (computed post-stream) | `StreamEvent(type="usage", ...)` |
| Token drift monitoring | Not tracked | Structured log comparing estimate vs actual |

---

## 6. Smooth Streaming

### SillyTavern: Character-Level Delay Transform

`SmoothEventSourceStream` extends the base `EventSourceStream` by piping
through an additional `TransformStream` that splits each SSE event into
per-character events with configurable delays:

- Regular characters: `speedFactor * 0.4ms` (default 20ms at speed 50)
- Commas/newlines: half the punctuation delay (default 250ms)
- Periods/exclamation/question: full punctuation delay (default 500ms)

Delays are skipped when the document is not focused or when
`smooth_streaming_no_think` is enabled for reasoning content.

Additionally, `stream_fade_in` uses `morphdom` (DOM diffing) with
`Intl.Segmenter` to create word-level `<span>` elements with CSS opacity
transitions.

### Candlekeep Core: Not Implemented (Backend Design)

Candlekeep Core is a headless API server. It emits raw `StreamEvent` objects
over SSE without any rendering-level transformation. Smooth streaming, character
splitting, and animation delays are the responsibility of whatever frontend
client consumes the API.

The typed event protocol (`text`, `reasoning`) provides the building blocks for
a client to implement smooth streaming: each text chunk can be split and delayed
at the client's discretion.

### Summary

| Aspect | SillyTavern | Candlekeep Core |
|--------|-------------|-----------------|
| Implementation | Built-in TransformStream | Not applicable (headless API) |
| Granularity | Per-character with punctuation-aware delays | Chunk-level events |
| Configuration | Speed slider (1-100), toggle, no-think option | N/A (client responsibility) |
| DOM rendering | morphdom + CSS fade-in | N/A |

---

## 7. Error Handling

### SillyTavern: Multi-Layer Error Passthrough

**Backend:** Provider HTTP errors are forwarded as-is (status code + body).
Network errors return 500 if headers have not been sent. The backend never
constructs structured error events in the stream.

**Frontend:** `tryParseStreamingError()` runs at two points:
1. On non-OK initial HTTP response (before the stream reader starts)
2. On each SSE event during the read loop

It parses the raw data as JSON and checks for `data.error`, `data.message`,
`data.detail`, or `data.quota_error`. If found, a toast is displayed and an
exception is thrown.

**Recovery:** `StreamingProcessor.onErrorStreaming()` aborts the controller,
unlocks the UI, emits lifecycle events, and preserves whatever partial text was
accumulated. The partial result is returned rather than discarded.

**Smooth streaming:** Unrecognized event formats in `SmoothEventSourceStream`
pass through the raw event unmodified rather than crashing the stream.

### Candlekeep Core: Structured Error Events

**Gateway layer:** `ProviderGateway` catches `httpx.HTTPStatusError` and maps
status codes to a typed exception hierarchy:
- 401 -> `ProviderAuthError`
- 429 -> `ProviderRateLimitError`
- 400 -> `ProviderInvalidRequestError`
- Others -> `ProviderException`
- Timeouts -> `ProviderTimeoutError`

**Service layer:** `_stream_completion()` wraps the entire streaming loop in
try/except and maps exceptions to a typed error event:

```python
except Exception as e:
    yield StreamEvent(type="error", message=str(e), code=_classify_error(e))
```

The `code` field contains a machine-readable classification: `rate_limit`,
`auth_error`, `timeout`, `provider_error`, or `internal_error`.

**Router layer:** A second try/except in `event_generator()` catches any
exception that escapes the service (e.g., from event serialization) and emits a
final error event before closing the stream.

**Client receives:** A structured JSON error event:
```json
{"type": "error", "message": "Rate limit exceeded", "code": "rate_limit"}
```

### Summary

| Aspect | SillyTavern | Candlekeep Core |
|--------|-------------|-----------------|
| Error format to client | Raw provider error JSON (passthrough) | `StreamEvent(type="error", code="...", message="...")` |
| Error classification | Client-side heuristic parsing | Backend exception hierarchy with typed codes |
| Partial content on error | Preserved (`this.result` returned) | Not emitted (stream ends with error event) |
| HTTP status forwarding | Yes (except 401 -> 400) | Mapped to typed exceptions before stream starts |
| Error during stream | Arrives as raw SSE data | Arrives as structured error event |

---

## 8. Overall Architecture Comparison

```
                    SillyTavern v1.17.0
                    ====================
                    
  Provider API  ──(SSE bytes)──>  Express Backend  ──(raw pipe)──>  Browser
                                  [no transformation]               [heavy JS parser]
                                  
  Ollama        ──(JSONL)──────>  parseOllamaStream ──(SSE)──────>  Browser
                                  [JSONL -> SSE transcoder]


                    Candlekeep Core
                    ===============
                    
  Provider API  ──(SSE bytes)──>  httpx async lines
                                      |
                                  adapter.parse_stream_line()     [per-provider]
                                      |
                                  StreamChunk                     [canonical]
                                      |
                                  _stream_completion()            [business logic]
                                      |
                                  StreamEvent                     [API contract]
                                      |
                                  SSE JSON  ──────────────────>   Any client
```

### Architectural Trade-offs

| Dimension | SillyTavern | Candlekeep Core |
|-----------|-------------|-----------------|
| Backend complexity | Minimal (pipe + abort) | Higher (parse + normalize + persist) |
| Client complexity | High (full provider parser) | Low (single event schema) |
| Client coupling | Client must know all provider formats | Client is provider-agnostic |
| Adding a provider | Frontend parser branches | New adapter class (backend only) |
| Streaming overhead | Near-zero (byte forwarding) | Line-by-line parse + JSON serialize |
| Message persistence | Client-side (IndexedDB / localStorage) | Server-side (PostgreSQL, async) |
| Token usage | Client tokenizer estimate | Provider-reported with tokenizer fallback |
| Rendering features | Smooth streaming, fade-in, FPS throttle | None (headless API) |
| Error semantics | Raw passthrough | Typed, classified events |
| Abort mechanism | Signal-based (immediate) | Polling-based (cooperative) |

ST optimizes for a monolithic browser application where the backend is a thin
relay and the frontend owns all intelligence. Candlekeep optimizes for a
decoupled API server where the backend owns provider abstraction, persistence,
and error classification, exposing a clean contract to any client.
