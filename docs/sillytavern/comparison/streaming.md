# Streaming Architecture Comparison: SillyTavern v1.17.0 vs The Bannered Mare

How each system carries an SSE stream from the provider to the consumer (the browser
frontend in SillyTavern, an API client in The Bannered Mare). This page assumes the
[Streaming Analysis](/sillytavern/analysis/streaming) for how SillyTavern works internally,
and focuses on where The Bannered Mare diverges and why.

The split is where parsing happens — SillyTavern forwards raw bytes and parses in the browser;
The Bannered Mare parses server-side into a typed event protocol:

<Figure tag="Figure 1" title="Byte proxy vs typed event pipeline" id="fig-cmp-streaming">
<svg viewBox="0 0 760 262" role="img" aria-label="SillyTavern vs The Bannered Mare streaming" style="font-family:var(--vp-font-family-base)">
  <rect x="24" y="16" width="344" height="230" rx="12" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <rect x="392" y="16" width="344" height="230" rx="12" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <rect x="24" y="16" width="344" height="44" rx="12" fill="var(--tbm-dgm-provider-soft)"/><rect x="24" y="36" width="344" height="24" fill="var(--tbm-dgm-provider-soft)"/>
  <rect x="392" y="16" width="344" height="44" rx="12" fill="var(--tbm-dgm-backend-soft)"/><rect x="392" y="36" width="344" height="24" fill="var(--tbm-dgm-backend-soft)"/>
  <text x="196" y="44" text-anchor="middle" font-size="13" font-weight="800" fill="var(--tbm-dgm-ink)">SillyTavern v1.17.0</text>
  <text x="564" y="44" text-anchor="middle" font-size="13" font-weight="800" fill="var(--tbm-dgm-ink)">The Bannered Mare</text>
  <g font-size="10.5" fill="var(--tbm-dgm-ink)">
    <text x="40" y="90">Backend — transparent byte pipe, zero transform</text>
    <text x="40" y="122">Parsing — in the frontend, per provider</text>
    <text x="40" y="154">Output — raw provider SSE bytes</text>
    <text x="40" y="186">Ollama — JSONL transcoded to SSE</text>
    <text x="40" y="222" fill="var(--tbm-dgm-ink-2)">Trivial backend, heavy frontend parser</text>
    <text x="408" y="90">Backend — adapter.parse_stream_line → StreamChunk</text>
    <text x="408" y="122">Parsing — server-side, normalized</text>
    <text x="408" y="154">Output — typed StreamEvents (6 types)</text>
    <text x="408" y="186">Ollama — same adapter path as the rest</text>
    <text x="408" y="222" fill="var(--tbm-dgm-ink-2)">Uniform typed protocol to the client</text>
  </g>
</svg>
<template #caption>

**Who parses the stream.** SillyTavern's backend is one pass-through function and the browser
owns all provider parsing; The Bannered Mare parses each provider server-side into a fixed
`StreamEvent` protocol (`start · text · reasoning · usage · done · error`).

</template>
</Figure>

## 1. Stream Proxy vs Typed Event Pipeline

SillyTavern's backend is a transparent byte proxy — `forwardFetchResponse()` pipes raw
provider bytes to the browser with zero transformation, so a complete multi-provider parser
has to live in the frontend ([Analysis §1 ›](/sillytavern/analysis/streaming#_1-backend-stream-proxy)).

The Bannered Mare parses the stream **server-side** and emits a uniform typed event protocol.
The pipeline has three layers:

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

Every provider adapter implements `parse_stream_line()`, returning a `StreamChunk` or `None`;
the service layer maps chunks into a fixed six-event protocol. The API client receives a
single, provider-agnostic format and never needs to know which provider is generating — the
cost is that provider-specific parsing lives in the backend adapter layer.

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| Backend transformation | None (raw pipe) | Full parse + normalization |
| Provider parsing location | Frontend (JS) | Backend (Python adapters) |
| Client complexity | High (multi-provider parser) | Low (single event schema) |
| Event format to client | Raw provider SSE | `{"type": "text", "content": "..."}` |
| Intermediate types | None | `StreamChunk` -> `StreamEvent` |

## 2. Provider-Specific Stream Parsing

SillyTavern dispatches in the frontend: `parseStreamData()` is a cascading if/else that
sniffs JSON structure across seven providers (with eight OpenAI-compatible sub-paths), and a
second `getStreamingReply()` extracts by `chat_completion_source` enum — two partially
overlapping code paths ([Analysis §4 ›](/sillytavern/analysis/streaming#_4-provider-specific-stream-parsing)).

The Bannered Mare gives each provider its own adapter class implementing `parse_stream_line()`:

| Adapter | Class | Parsing strategy |
|---------|-------|-----------------|
| Anthropic | `AnthropicAdapter` | Matches `type` field: `content_block_delta` (text/thinking), `message_delta` (finish + usage), `message_stop` |
| OpenAI | `OpenAIAdapter` | Strips `data: ` prefix, handles `[DONE]` sentinel, extracts from `choices[0].delta` with `reasoning_content` / `reasoning` fallback |
| Gemini | `GeminiAdapter` | Extracts from `candidates[0].content.parts`, separates `thought: true` parts from text parts |
| Ollama | `OllamaAdapter` | Inherits from `OpenAIAdapter` unchanged (Ollama's `/v1/chat/completions` is OpenAI-compatible) |
| LM Studio | `LMStudioAdapter` | Inherits from `OpenAIAdapter` unchanged (LM Studio's `/v1/chat/completions` is OpenAI-compatible) |

All five return the same `StreamChunk(content, reasoning, finish_reason, usage)` dataclass;
the gateway iterates lines and delegates without knowing which adapter is active.

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| Dispatch mechanism | JSON structure sniffing + enum switch | Polymorphic class per provider |
| Number of parsing codepaths | ~15 (7 main + 8 OpenAI sub-paths) | 5 adapter classes (3 with distinct parsers; Ollama + LM Studio inherit OpenAI's) |
| Output type | Yields `{ data, chunk, reasoning }` | Returns `StreamChunk` dataclass |
| Extensibility | Add branches to if/else chain | Add new adapter class |
| Ollama handling | Custom JSONL-to-SSE transcoder | Inherits OpenAI adapter (Ollama serves `/v1/`) |

## 3. Abort / Cancellation Mechanism

SillyTavern aborts signal-based at two levels: the frontend `StreamingProcessor` calls
`AbortController.abort()` on Stop, and the Express socket's `close` event triggers a
matching backend `controller.abort()` on the upstream fetch (KoboldCpp additionally needs an
explicit `POST /api/extra/abort`) ([Analysis §2 ›](/sillytavern/analysis/streaming#_2-abort-mechanism)).

The Bannered Mare has no `AbortController` equivalent — cancellation is **cooperative**. The
router checks `request.is_disconnected()` between events:

```python
async for event in stream_iterator:
    if await request.is_disconnected():
        return
    yield f"data: {json.dumps(stream_event_to_dict(event))}\n\n"
```

When the generator returns, the `StreamingResponse` ends and the `httpx` async stream context
manager closes the upstream connection as part of normal cleanup. The trade-off: cancellation
happens between events rather than interrupting mid-chunk.

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| Frontend abort | `AbortController.abort()` | Client closes connection |
| Backend abort | Socket `close` -> `controller.abort()` | `request.is_disconnected()` polling |
| Upstream teardown | Explicit `body.destroy()` + `AbortError` | httpx context manager cleanup |
| Abort granularity | Immediate (signal-based) | Between events (cooperative) |
| Special provider handling | KoboldCpp explicit abort endpoint | None |

## 4. Reasoning / Thinking Content

SillyTavern handles reasoning across three frontend layers: stream parsing flags per-chunk
reasoning, `getStreamingReply()` accumulates it (gated by `show_thoughts`), and a
`ReasoningHandler` state machine tracks duration, auto-parses think blocks, detects
hidden-reasoning models (o1/o3), and stores reasoning signatures
([Analysis §5 ›](/sillytavern/analysis/streaming#_5-reasoning-thinking-content)).

The Bannered Mare uses a two-level pipeline:

1. **Adapter layer** (`parse_stream_line`): each adapter extracts reasoning into
   `StreamChunk.reasoning` — `AnthropicAdapter` from `thinking_delta` blocks, `OpenAIAdapter`
   from `delta.reasoning_content` / `delta.reasoning`, `GeminiAdapter` from `thought: true`
   parts.
2. **Service layer** (`_stream_completion`): accumulates reasoning and emits
   `StreamEvent(type="reasoning", …)`. If no API-level reasoning was found, after the stream
   `parse_reasoning_tags()` extracts `<think>…</think>` blocks from the content (covering
   local models like DeepSeek R1, QwQ, Qwen3). The result is persisted to
   `Message.reasoning_content` alongside the cleaned content.

The Bannered Mare deliberately skips SillyTavern's rendering-side reasoning features
(duration tracking, hidden-model lists, signatures) — those belong to a client.

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| Provider-specific extraction | Per-provider in frontend JS | Per-adapter `parse_stream_line()` |
| Think-tag auto-parsing | Configurable prefix/suffix in ReasoningHandler | `parse_reasoning_tags()` with `<think>`/`</think>` default |
| Duration tracking | `startTime`/`endTime` in ReasoningHandler | Not implemented |
| Hidden reasoning models | Explicit list (o1, o3, etc.) | Not implemented |
| Reasoning signatures | Stored for OpenRouter Claude, Gemini | Not implemented |
| Client receives | Raw reasoning text (client renders) | `{"type":"reasoning","content":"..."}` events |
| Persistence | `chat[messageId].extra.reasoning_duration` | `Message.reasoning_content` column |

## 5. Token Usage from Streams

SillyTavern does **not** read `usage` objects from the stream; it computes token counts on
the client with a tokenizer after the stream completes, and derives TPS from wall-clock time —
uniform across providers but approximate ([Analysis §7 ›](/sillytavern/analysis/streaming#_7-token-usage-from-streams)).

The Bannered Mare prefers **provider-reported** usage, extracted per adapter:

- **Anthropic**: `message_delta` carries `usage.output_tokens`
- **OpenAI**: `usage` object in the final chunk (when `stream_options` is set)
- **Gemini**: `usageMetadata` per frame (`promptTokenCount`, `candidatesTokenCount`,
  `totalTokenCount`, `cachedContentTokenCount`)

The service emits a dedicated `StreamEvent(type="usage", …)` and, when the provider omits
output tokens, falls back to `TokenizerService.count_tokens()`:

```python
token_count = (
    last_usage.output_tokens
    if last_usage and last_usage.output_tokens
    else self.tokenizer.count_tokens(full_content)
)
```

The non-streaming path also logs token drift between estimated and actual counts.

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| Primary source | Client-side tokenizer | Provider-reported `usage` objects |
| Fallback | None (tokenizer only) | Local tokenizer when provider omits usage |
| Cache token tracking | Not tracked | `cache_read_tokens`, `cache_creation_tokens` |
| Usage event to client | None (computed post-stream) | `StreamEvent(type="usage", ...)` |
| Token drift monitoring | Not tracked | Structured log comparing estimate vs actual |

## 6. Smooth Streaming

SillyTavern ships client-side smooth streaming: `SmoothEventSourceStream` splits each SSE
event into per-character events with punctuation-aware delays, and `stream_fade_in` uses
`morphdom` + `Intl.Segmenter` for word-level opacity transitions
([Analysis §6 ›](/sillytavern/analysis/streaming#_6-smooth-streaming)).

The Bannered Mare is a **headless API server**, so this is out of scope by design — it emits
raw `StreamEvent` objects with no rendering-level transformation. The typed protocol
(`text`, `reasoning`) gives a client the building blocks to implement smooth streaming
itself, at its own discretion.

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| Implementation | Built-in TransformStream | Not applicable (headless API) |
| Granularity | Per-character with punctuation-aware delays | Chunk-level events |
| Configuration | Speed slider (1-100), toggle, no-think option | N/A (client responsibility) |
| DOM rendering | morphdom + CSS fade-in | N/A |

## 7. Error Handling

SillyTavern forwards provider errors largely as-is: the backend passes through HTTP status +
body (500 on network error), and the frontend's `tryParseStreamingError()` heuristically
sniffs `data.error` / `message` / `detail` / `quota_error`, shows a toast, and preserves
partial text on recovery ([Analysis §8 ›](/sillytavern/analysis/streaming#_8-stream-error-handling)).

The Bannered Mare produces **structured, classified** error events. The gateway maps
`httpx.HTTPStatusError` to a typed exception hierarchy (401 → `ProviderAuthError`, 429 →
`ProviderRateLimitError`, 400 → `ProviderInvalidRequestError`, timeouts →
`ProviderTimeoutError`), and `_stream_completion()` turns any exception into a typed event:

```python
except Exception as e:
    yield StreamEvent(type="error", message=str(e), code=_classify_error(e))
```

The `code` is machine-readable (`rate_limit`, `auth_error`, `timeout`, `provider_error`,
`internal_error`), and a second guard in the router catches anything escaping the service.
The client receives a structured event:

```json
{"type": "error", "message": "Rate limit exceeded", "code": "rate_limit"}
```

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| Error format to client | Raw provider error JSON (passthrough) | `StreamEvent(type="error", code="...", message="...")` |
| Error classification | Client-side heuristic parsing | Backend exception hierarchy with typed codes |
| Partial content on error | Preserved (`this.result` returned) | Not emitted (stream ends with error event) |
| HTTP status forwarding | Yes (except 401 -> 400) | Mapped to typed exceptions before stream starts |
| Error during stream | Arrives as raw SSE data | Arrives as structured error event |

## 8. Overall Trade-offs

The two architectures (contrasted in [Figure 1](#fig-cmp-streaming) above) optimize for
different shapes. SillyTavern is a monolithic browser app: a thin relay backend and a
frontend that owns all intelligence. The Bannered Mare is a decoupled API server: the backend
owns provider abstraction, persistence, and error classification, exposing a clean contract to
any client.

| Dimension | SillyTavern | The Bannered Mare |
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
