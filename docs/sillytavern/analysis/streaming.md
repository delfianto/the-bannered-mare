# SillyTavern v1.17.0 -- Streaming Handler Architecture

Analysis of the full streaming pipeline: provider API to backend proxy to SSE to
frontend parser to UI rendering.

---

## 1. Backend Stream Proxy

**File:** `src/util.js` (lines 708-744)

The backend acts as a transparent SSE proxy. The core function is
`forwardFetchResponse()`, which pipes the raw byte stream from a provider's HTTP
response directly through to the Express response:

```js
export function forwardFetchResponse(from, to) {
    let statusCode = from.status;
    let statusText = from.statusText;

    // Avoid sending 401 to the browser -- it resets Basic auth
    if (statusCode === 401) {
        statusCode = 400;
    }

    to.statusCode = statusCode;
    to.statusMessage = statusText;

    if (from.body && to.socket) {
        from.body.pipe(to);                          // Node stream pipe

        to.socket.on('close', function () {
            if (from.body instanceof Readable) from.body.destroy();
            to.end();
        });

        from.body.on('end', function () {
            console.info('Streaming request finished');
            to.end();
        });
    } else {
        to.end();
    }
}
```

Key design choices:

- **Zero transformation**: The backend does not parse, reformat, or buffer SSE
  events. It uses Node's `Readable.pipe()` to forward raw bytes with minimal
  memory overhead.
- **Status code forwarding**: The provider's HTTP status is forwarded verbatim
  (except 401 is mapped to 400 to prevent browser Basic auth prompts).
- **Connection cleanup**: When the Express socket closes (browser tab closed, stop
  button), the remote stream is destroyed via `from.body.destroy()`.

This single function is used by every streaming provider handler (Claude,
Gemini, OpenAI, OpenRouter, Cohere, Mistral, DeepSeek, xAI, AI21, etc.) in
`src/endpoints/backends/chat-completions.js`, `text-completions.js`,
`novelai.js`, and `kobold.js`.

### Exception: Ollama

Ollama uses a non-standard JSONL (newline-delimited JSON) format instead of SSE.
The backend has a dedicated `parseOllamaStream()` function
(`src/endpoints/backends/text-completions.js`, lines 29-71) that transcodes
Ollama's JSONL into SSE:

```js
async function parseOllamaStream(jsonStream, request, response) {
    let partialData = '';
    jsonStream.body.on('data', (data) => {
        const chunk = data.toString();
        partialData += chunk;
        while (true) {
            let json;
            try { json = JSON.parse(partialData); } catch (e) { break; }
            const text = json.response || '';
            const thinking = json.thinking || '';
            const chunk = { choices: [{ text, thinking }] };
            response.write(`data: ${JSON.stringify(chunk)}\n\n`);
            partialData = '';
        }
    });

    jsonStream.body.on('end', () => {
        response.write('data: [DONE]\n\n');
        response.end();
    });
}
```

This converts each Ollama JSON frame into an OpenAI-compatible SSE event with
`choices[0].text` and `choices[0].thinking`, then emits a `[DONE]` sentinel.

---

## 2. Abort Mechanism

Every provider handler in `src/endpoints/backends/chat-completions.js` follows
the identical abort pattern (shown here from the Claude handler, lines 220-223;
repeated at lines 615-618, 752-755, 834-837, 915-918, 1022-1025, 1132-1135,
1238-1241, 1343-1346, 1455-1458, 1595-1597, 2351-2354):

```js
const controller = new AbortController();
request.socket.removeAllListeners('close');
request.socket.on('close', function () {
    controller.abort();
});

// ... later, passed to fetch:
const generateResponse = await fetch(apiUrl, {
    signal: controller.signal,
    // ...
});
```

The flow:

1. A fresh `AbortController` is created per request.
2. Any previous `close` listeners are removed (`removeAllListeners('close')`) to
   avoid double-abort from prior request handlers.
3. When the browser disconnects (user navigates away, presses Stop, or closes
   the tab), the Express socket emits `'close'`.
4. The handler calls `controller.abort()`, which causes the in-flight
   `node-fetch` request to throw an `AbortError`.
5. For `forwardFetchResponse`, the socket `close` event separately calls
   `from.body.destroy()` to tear down the upstream stream.

### Special case: KoboldCpp

KoboldCpp requires an explicit HTTP abort endpoint. The text-completions
backend (`src/endpoints/backends/text-completions.js`, lines 80-90) sends
`POST /api/extra/abort` to the KoboldCpp server before calling
`controller.abort()`:

```js
request.socket.on('close', async function () {
    if (request.body.api_type === TEXTGEN_TYPES.KOBOLDCPP && !response.writableEnded) {
        await abortKoboldCppRequest(request, trimV1(baseUrl));
    }
    controller.abort();
});
```

### Frontend abort

The frontend `StreamingProcessor` (in `public/script.js`, line 3488) also has its
own `AbortController`:

```js
this.abortController = new AbortController();
```

The signal from this controller is passed to the `fetch()` call for the backend
API endpoint. When the user presses the Stop button, `onStopStreaming()` is
called (line 3768), which calls `this.abortController.abort()`. This aborts the
frontend fetch, which closes the HTTP connection, which triggers the backend
socket `close` handler, which aborts the upstream provider request.

---

## 3. Frontend SSE Parser

**File:** `public/scripts/sse-stream.js` (lines 10-81)

`EventSourceStream` is a Web Streams API `TransformStream` pipeline that converts
raw binary fetch response bytes into `MessageEvent` objects:

```
[fetch response body (ReadableStream<Uint8Array>)]
    |
    v
[TextDecoderStream('utf-8')]          -- bytes to string
    |
    v
[TransformStream (SSE parser)]        -- string to MessageEvent
    |
    v
[ReadableStream<MessageEvent>]        -- consumer reads events
```

The SSE parsing logic:

1. **Buffering**: Incoming text chunks are appended to `streamBuffer`.
2. **Event splitting**: The buffer is split on double newlines
   (`/\r\n\r\n|\r\r|\n\n/g`). The last element (incomplete event) stays in the
   buffer.
3. **Field parsing**: Each event block is split on single newlines. Each line is
   parsed with `/([^:]+)(?:: ?(.*))?/` to extract field name and value.
4. **Supported fields**: `event` (sets event type), `data` (appended with `\n`
   separator), `id` (sets `lastEventId`, rejecting null characters).
5. **Event dispatch**: Events with empty data are skipped. A trailing newline is
   trimmed from data. A `MessageEvent` is created and enqueued.

This is a faithful implementation of the
[WHATWG SSE specification](https://html.spec.whatwg.org/multipage/server-sent-events.html#dispatchMessage).

### Usage pattern (common across all frontends)

```js
const eventStream = getEventSourceStream();  // returns EventSourceStream or SmoothEventSourceStream
response.body.pipeThrough(eventStream);
const reader = eventStream.readable.getReader();

while (true) {
    const { done, value } = await reader.read();
    if (done) return;
    const data = value.data;  // MessageEvent.data
    if (data === '[DONE]') return;
    const parsed = JSON.parse(data);
    // ... extract text from parsed JSON
}
```

---

## 4. Provider-Specific Stream Parsing

**File:** `public/scripts/sse-stream.js`, `parseStreamData()` (lines 113-335)

This is an async generator that takes a parsed JSON object and yields individual
characters. It exists solely for the `SmoothEventSourceStream` to split
multi-character chunks into single-character events for smooth rendering.

### Provider dispatch order (checked top to bottom)

| Priority | Condition | Provider | Content path |
|----------|-----------|----------|-------------|
| 1 | `json.delta.message` object + type `content-delta` or `tool-plan-delta` | **Cohere** | `json.delta.message.content.text` |
| 2 | `json.delta.text` string | **Claude** (text) | `json.delta.text` |
| 3 | `json.delta.thinking` string | **Claude** (reasoning) | `json.delta.thinking` (yields `reasoning: true`) |
| 4 | `json.candidates` array | **Google Gemini / Vertex AI** | `json.candidates[i].content.parts[j].text`; reasoning via `parts[j].thought` flag |
| 5 | `json.token` string | **NovelAI / KoboldCpp Classic** | `json.token` |
| 6 | `json.content` string (non-chat.completion.chunk) | **llama.cpp** | `json.content` |
| 7 | `json.choices` array | **OpenAI-compatible** | Multiple sub-paths (see below) |
| fallback | None matched | -- | Throws `'Unknown event data format'` |

### OpenAI-compatible sub-paths (within `json.choices`)

| Sub-condition | Use case | Content path | Reasoning? |
|---------------|----------|-------------|------------|
| `choices[0].text` | Text completion | `choices[0].text` | No |
| `choices[0].thinking` | Text completion reasoning | `choices[0].thinking` | Yes |
| `choices[0].delta.text` | Chat delta text | `choices[0].delta.text` | No |
| `choices[0].delta.reasoning_content` | DeepSeek / xAI reasoning | `choices[0].delta.reasoning_content` | Yes |
| `choices[0].delta.reasoning` | OpenRouter reasoning | `choices[0].delta.reasoning` | Yes |
| `choices[0].delta.content` (string) | Standard chat content | `choices[0].delta.content` | No |
| `choices[0].delta.content` (array with `thinking`) | Mistral thinking | `choices[0].delta.content[0].thinking[0].text` | Yes |
| `choices[0].message.content` | Full message in stream | `choices[0].message.content` | No |

For non-primary swipes (`index > 0`), the parser throws an error with the
`NOT_PRIMARY` symbol cause, which is caught silently by the smooth stream handler.

### Reply extraction: `getStreamingReply()`

**File:** `public/scripts/openai.js` (lines 2988-3071)

This function runs in the main stream consumption loop (not in
`parseStreamData`) and extracts text and reasoning on a per-provider basis. The
dispatch is by `chat_completion_source`:

| Source | Text extraction | Reasoning extraction |
|--------|----------------|---------------------|
| `CLAUDE` | `data.delta.text` | `data.delta.thinking` |
| `MAKERSUITE` / `VERTEXAI` | `candidates[0].content.parts` (non-thought) | parts with `thought: true` |
| `COHERE` | `data.delta.message.content.text` or `tool_plan` | -- |
| `DEEPSEEK` | `choices[0].delta.content` | `choices[0].delta.reasoning_content` |
| `XAI` | `choices[0].delta.content` | `choices[0].delta.reasoning_content` |
| `OPENROUTER` | `choices[0].delta.content` or `.message.content` or `.text` | `delta.reasoning` or `delta.reasoning_content` or `message.reasoning` / `message.reasoning_content` |
| `MISTRALAI` | array content joined | `delta.content[0].thinking[0].text` |
| Generic/Custom/etc. | `choices[0].delta.content` or `.message.content` or `.text` | `delta.reasoning_content` or `delta.reasoning` |

---

## 5. Reasoning / Thinking Content

SillyTavern has a comprehensive reasoning system spread across three layers.

### 5.1 Stream-level parsing (`parseStreamData`)

The `parseStreamData` generator yields `{ reasoning: true }` for reasoning
chunks. This flag tells `SmoothEventSourceStream` whether to apply the
character-level delay (configurable with `smooth_streaming_no_think`).

### 5.2 Reply-level extraction (`getStreamingReply`)

Each provider has explicit logic to accumulate reasoning text into
`state.reasoning`. The `show_thoughts` flag (from
`oai_settings.show_thoughts`) gates whether reasoning is collected at all.

### 5.3 The ReasoningHandler class

**File:** `public/scripts/reasoning.js` (lines 255-532)

This class manages the full lifecycle of reasoning during streaming:

- **States**: `None` -> `Thinking` -> `Done` or `Hidden`
- **Types**: `Model` (from API), `Parsed` (extracted from message text), `Manual`,
  `Edited`
- **Hidden reasoning models**: o1, o3, gpt-4.5, gemini-2.0-flash-thinking-exp,
  gemini-2.0-pro-exp -- these models produce reasoning but do not expose it.
  The handler tracks duration without content.
- **Auto-parse**: For providers that embed thinking in XML-like blocks within the
  message text (lines 459-506), the handler uses configurable
  `power_user.reasoning.prefix` / `suffix` to extract reasoning from the
  streamed message content at parse time.
- **DOM updates**: The handler maintains references to `.mes_reasoning_details`,
  `.mes_reasoning`, and `.mes_reasoning_header_title` DOM elements and updates
  them during streaming.
- **Duration tracking**: `startTime` is set when reasoning begins; `endTime` when
  the first non-reasoning content arrives. Duration is persisted to
  `chat[messageId].extra.reasoning_duration`.

### 5.4 Reasoning signature support

For OpenRouter Claude models, encrypted reasoning signatures are extracted from
`reasoning_details` (lines 3039-3053 of `openai.js`) and stored as
`state.signature`. Gemini uses `thoughtSignature` on content parts. These are
persisted to `message.extra.reasoning_signature` for multi-turn context.

---

## 6. Smooth Streaming

**File:** `public/scripts/sse-stream.js`, `SmoothEventSourceStream` (lines
340-378)

`SmoothEventSourceStream` extends `EventSourceStream` by piping through an
additional `TransformStream` that splits each SSE event into per-character
events with configurable delays:

```js
for await (const parsed of parseStreamData(json)) {
    !(power_user.smooth_streaming_no_think && parsed.reasoning)
        && hasFocus
        && await delay(getDelay(lastStr));
    controller.enqueue(new MessageEvent(event.type, {
        data: JSON.stringify(parsed.data)
    }));
    lastStr = parsed.chunk;
}
```

### Delay calculation (`getDelay`, lines 88-106)

```js
function getDelay(s) {
    const speedFactor = Math.max(100 - power_user.smooth_streaming_speed, 1);
    const defaultDelayMs = speedFactor * 0.4;
    const punctuationDelayMs = defaultDelayMs * 25;

    if ([',', '\n'].includes(s)) return punctuationDelayMs / 2;
    if (['.', '!', '?'].includes(s)) return punctuationDelayMs;
    return defaultDelayMs;
}
```

With the default `smooth_streaming_speed` of 50:

| Character type | speedFactor | Delay |
|---------------|-------------|-------|
| Regular character | 50 | 20ms |
| Comma, newline | 50 | 250ms |
| Period, `!`, `?` | 50 | 500ms |

At max speed (100): speedFactor = 1, regular = 0.4ms, period = 10ms.
At min speed (1): speedFactor = 99, regular = 39.6ms, period = 990ms.

### Conditions that skip delay

- `smooth_streaming_no_think` is true AND the chunk is reasoning content
- The document does not have focus (`!document.hasFocus()`)

### Selection logic (`getEventSourceStream`, lines 381-387)

```js
export function getEventSourceStream() {
    if (power_user.smooth_streaming) {
        return new SmoothEventSourceStream();
    }
    return new EventSourceStream();
}
```

---

## 7. Token Usage from Streams

SillyTavern does **not** extract `usage` objects from streaming responses. Token
counts during streaming are computed client-side using the tokenizer:

```js
// StreamingProcessor.onProgressStreaming (script.js, lines 3617-3624)
const tokenCountText = this.reasoningHandler.reasoning + processedText;
const currentTokenCount = isFinal && power_user.message_token_count_enabled
    ? await getTokenCountAsync(tokenCountText, 0) : 0;
if (currentTokenCount) {
    chat[messageId].extra.token_count = currentTokenCount;
}
```

This only runs on the final progress call (`isFinal = true`) and only when
`power_user.message_token_count_enabled` is active. The token count is stored in
`chat[messageId].extra.token_count` and displayed in the message's
`.tokenCounterDisplay` element.

For non-streaming responses, the same client-side tokenizer approach is used
post-response (e.g., `script.js` line 5800).

The generation timer (`formatGenerationTimer`, `script.js` lines 2666-2689)
computes TPS as `tokenCount / seconds` using the client-side token count and
wall-clock elapsed time.

---

## 8. Stream Error Handling

### 8.1 Backend errors

In `forwardFetchResponse()`, if the upstream provider returns a non-200 status,
the status code is forwarded to the browser. The stream body is still piped -- this
means error JSON from providers arrives as stream data, which the frontend must
parse.

If the fetch itself fails (network error), each provider handler catches the
error and returns 500 if headers have not been sent:

```js
// chat-completions.js, typical pattern
} catch (error) {
    console.error('Error communicating with Claude:', error);
    if (!response.headersSent) {
        return response.status(500).send({ error: true });
    }
}
```

### 8.2 Frontend error parsing

Each frontend stream consumer calls `tryParseStreamingError()` at two points:

1. **On non-OK initial response** (before starting the stream reader):
   ```js
   if (!response.ok) {
       tryParseStreamingError(response, await response.text());
       throw new Error(`Got response status ${response.status}`);
   }
   ```

2. **On each SSE event** (during the read loop):
   ```js
   tryParseStreamingError(response, value.data);
   ```

The Chat Completions version (`public/scripts/openai.js`, lines 1604-1635) tries
to parse the data as JSON and checks for `data.error`, `data.message`,
`data.detail`, and `data.quota_error`. If found, it displays a toast and throws.

The Text Completions version (`public/scripts/textgen-settings.js`, lines
1429-1444) similarly checks for `data.error.message`, `data.error`, `data.message`,
or `data.detail`.

### 8.3 StreamingProcessor error recovery

In `StreamingProcessor.generate()` (`script.js`, lines 3821-3828):

```js
} catch (err) {
    if (!this.isFinished) {
        console.error(err);
        this.onErrorStreaming();
    }
    return this.result;
}
```

`onErrorStreaming()` (lines 3741-3752) aborts the controller, marks the processor
as stopped, unlocks the UI, and emits the `MESSAGE_RECEIVED` and
`CHARACTER_MESSAGE_RENDERED` events. The partial result is preserved -- whatever
text was accumulated before the error is kept in `this.result` and returned.

### 8.4 SmoothEventSourceStream error handling

In the smooth streaming transform (lines 368-374):

```js
} catch (error) {
    if (error instanceof Error && error.cause !== NOT_PRIMARY) {
        console.debug('Smooth Streaming parsing error', error);
    }
    controller.enqueue(event);  // pass through the raw event on error
}
```

If `parseStreamData` throws for an unrecognized format, the raw event is passed
through unmodified. Errors from non-primary swipes (`NOT_PRIMARY`) are silently
swallowed.

---

## 9. Text Completion Streaming

Text completion streaming (`public/scripts/textgen-settings.js`, lines
1305-1341) follows the same `EventSourceStream` pipeline as chat completions but
with a simpler data extraction:

```js
const eventStream = getEventSourceStream();
response.body.pipeThrough(eventStream);
const reader = eventStream.readable.getReader();

return async function* streamData() {
    let text = '';
    while (true) {
        const { done, value } = await reader.read();
        if (done) return;
        if (value.data === '[DONE]') return;

        let data = JSON.parse(value.data);

        // Standard OpenAI-compatible text completion
        const newText = data?.choices?.[0]?.text || data?.content || '';
        text += newText;

        // llama.cpp streaming swipe
        if (data?.index > 0) {
            swipes[data.index - 1] = (swipes[data.index - 1] || '') + data.content;
        }

        // Reasoning (Ollama)
        state.reasoning += data?.choices?.[0]?.reasoning
                        ?? data?.choices?.[0]?.thinking ?? '';

        yield { text, swipes, logprobs, toolCalls, state };
    }
};
```

Key differences from chat completions:
- Text is extracted from `choices[0].text` or `content` (not `delta.content`)
- llama.cpp swipes use `data.index` directly (not `choices[0].index`)
- Reasoning uses both `reasoning` and `thinking` fields (Ollama support)
- Logprobs have a dedicated `parseTextgenLogprobs` function (lines 1352-1401)
  with specific handling for KoboldCpp, TabbyAPI, vLLM, Aphrodite, llama.cpp

---

## 10. Frontend Stream Consumer

### 10.1 The StreamingProcessor class

**File:** `public/script.js` (lines 3461-3833)

This is the central orchestrator for all streaming on the frontend.

**Lifecycle:**

```
[sendStreamingRequest()] -> returns async generator
        |
        v
StreamingProcessor.generator = generator
        |
        v
StreamingProcessor.generate()
    |
    |-- onStartStreaming() -> creates message DOM, saves placeholder reply
    |
    |-- [main loop: for await (... of this.generator())]
    |       |
    |       |-- accumulates text, swipes, logprobs, reasoning
    |       |-- calls onProgressStreaming() throttled by Stopwatch
    |       |       |-- cleanUpMessage()
    |       |       |-- updates chat[messageId].mes
    |       |       |-- reasoningHandler.process()
    |       |       |-- messageFormatting() -> HTML
    |       |       |-- DOM update (innerHTML or stream fade-in)
    |       |       |-- timer update
    |       |       |-- scrollChatToBottom()
    |       |
    |       v
    |-- (loop ends)
    |
    |-- onFinishStreaming() -> final processing, save chat, play sound
```

### 10.2 Frame rate throttling

The main loop uses a `Stopwatch` class (`public/scripts/utils.js`, lines
1405-1435) to throttle DOM updates:

```js
const sw = new Stopwatch(1000 / power_user.streaming_fps);
for await (const { text, swipes, logprobs, toolCalls, state } of this.generator()) {
    // ...
    await sw.tick(async () => await this.onProgressStreaming(this.messageId, this.continueMessage + text));
}
```

The `Stopwatch.tick()` method only executes the callback if
`Date.now() - lastAction >= interval`. With the default `streaming_fps` of 30,
DOM updates happen at most every ~33ms regardless of how fast tokens arrive.

### 10.3 Stream statistics

After the loop, TPS is calculated and logged:

```js
const seconds = (timestamps[timestamps.length - 1] - timestamps[0]) / 1000;
console.warn(`Stream stats: ${timestamps.length} tokens, ${seconds.toFixed(2)} seconds, rate: ${Number(timestamps.length / seconds).toFixed(2)} TPS`);
```

### 10.4 Time to first token

Measured on the first iteration of the generator loop:

```js
if (!this.timeToFirstToken) {
    this.timeToFirstToken = now - this.createdAt.getTime();
}
```

Persisted to `chat[messageId].extra.time_to_first_token`.

### 10.5 Stream fade-in

**File:** `public/scripts/util/stream-fadein.js`

When `power_user.stream_fade_in` is enabled, instead of replacing `innerHTML`
directly, the system uses `morphdom` (a DOM-diffing library) plus
`Intl.Segmenter` to split text into word-level `<span class="text_segment">`
elements. CSS transitions then animate the opacity of new segments:

```js
export function applyStreamFadeIn(messageTextElement, htmlContent) {
    const targetElement = messageTextElement.cloneNode();
    segmentTextInElement(targetElement, htmlContent);
    morphdom(messageTextElement, targetElement);
}
```

This is applied to both the main message text and reasoning content.

---

## 11. Streaming Settings

### Per-API streaming toggles

| Setting | Location | Default | Description |
|---------|----------|---------|-------------|
| `stream_openai` | `openai.js` (line 399) | `false` | Streaming for Chat Completions API |
| `streaming_novel` | `nai-settings.js` (line 55) | `false` | Streaming for NovelAI |
| `streaming_kobold` | `kai-settings.js` (line 39) | `false` | Streaming for KoboldAI |
| `streaming` (textgen) | `textgen-settings.js` | varies | Streaming for text generation backends |

### Global streaming settings (power_user)

| Setting | Location | Default | Description |
|---------|----------|---------|-------------|
| `streaming_fps` | `power-user.js` (line 143) | `30` | Max DOM update rate (frames per second) |
| `smooth_streaming` | `power-user.js` (line 144) | `false` | Enable character-by-character smooth streaming |
| `smooth_streaming_no_think` | `power-user.js` (line 145) | `false` | Skip smooth delay for reasoning tokens |
| `smooth_streaming_speed` | `power-user.js` (line 146) | `50` | Speed slider (1-100) for smooth streaming |
| `stream_fade_in` | `power-user.js` (line 147) | `false` | Enable word-level CSS fade-in transitions |

### Streaming eligibility logic

**File:** `public/script.js`, `isStreamingEnabled()` (lines 3438-3447)

```js
export function isStreamingEnabled() {
    return (
        (main_api == 'openai' &&
            oai_settings.stream_openai &&
            // o1-2024-12-17 and o1 do not support streaming
            !(oai_settings.chat_completion_source == chat_completion_sources.OPENAI
              && ['o1-2024-12-17', 'o1'].includes(oai_settings.openai_model))
        )
        || (main_api == 'kobold' && kai_settings.streaming_kobold && kai_flags.can_use_streaming)
        || (main_api == 'novel' && nai_settings.streaming_novel)
        || (main_api == 'textgenerationwebui' && textgen_settings.streaming));
}
```

Additionally, `quiet` type generations always disable streaming regardless of
settings.

---

## 12. Architecture Summary

### Data flow diagram

```
Provider API (Claude/OpenAI/Gemini/etc.)
    |
    | SSE byte stream (or JSONL for Ollama)
    v
Backend (Express.js)
    |
    | forwardFetchResponse() -- pipe() with no transformation
    | (Ollama: parseOllamaStream() transcodes JSONL -> SSE)
    v
Frontend fetch() response.body
    |
    | pipeThrough(EventSourceStream)
    |     TextDecoderStream -> SSE TransformStream
    |     [optional: SmoothEventSourceStream adds per-char delay]
    v
ReadableStream<MessageEvent>
    |
    | reader.read() loop in generator function
    | (sendOpenAIRequest / generateTextGenWithStreaming / etc.)
    | getStreamingReply() extracts text per provider
    v
StreamingProcessor.generate()
    |
    | Stopwatch-throttled DOM updates
    | ReasoningHandler processes thinking content
    | cleanUpMessage() + messageFormatting()
    v
DOM innerHTML (or morphdom with stream-fadein)
```

### Key architectural patterns

1. **Transparent proxy**: The backend never parses or transforms SSE data (except
   Ollama). This means provider-specific parsing happens entirely on the frontend.

2. **Uniform generator interface**: All APIs (OpenAI, text completion, NovelAI,
   KoboldAI) return the same async generator shape:
   `AsyncGenerator<{ text, swipes, logprobs, toolCalls, state }>`.
   The `StreamingProcessor` consumes them identically.

3. **Two-level abort**: Frontend `AbortController` aborts the fetch, which closes
   the socket, which triggers the backend's `AbortController` to cancel the
   upstream request. This ensures clean teardown at every layer.

4. **Client-side tokenization**: Token counts are computed on the client using a
   tokenizer, not from provider `usage` objects. This works across all providers
   but is approximate.

5. **Frame-rate independence**: The `Stopwatch` decouples token arrival rate from
   DOM update rate. Smooth streaming adds artificial per-character delays on top
   of this.
