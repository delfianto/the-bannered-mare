# Backend Connection

The frontend talks to the FastAPI backend two ways: a **strongly-typed `openapi-fetch`
client** for ordinary CRUD, and a **custom SSE parser** for real-time completions. Everyday
requests get compile-time safety from the generated schema; the streaming path drops down to
raw `fetch` because it needs the response body as a live byte stream.

## 1. Type-Safe Client (`openapi-fetch`)

The client keeps types honest end to end:

- **Schema compilation** — the API surface
  [schema.d.ts](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/api/schema.d.ts)
  is generated directly from the root `openapi.json` contract:
  ```bash
  bun run api:gen
  ```
- **Client factory** — the client
  ([client.ts](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/api/client.ts))
  wraps `openapi-fetch`, giving autocompletion and compile-time verification for path
  variables, query params, headers, and body shapes.

### Standard Query Example

```typescript
const { data, error } = await client.GET("/api/providers/{provider_id}", {
  params: { path: { provider_id: id } },
});
```

## 2. File Uploads (FormData)

Typed JSON clients don't handle multipart file payloads (Character or Persona avatar images)
well, so those operations bypass `openapi-fetch` and use the browser's native `fetch`:

- Build a `FormData` object with the file binary and metadata fields.
- Send a plain POST/PUT **without** setting `Content-Type` manually, so the browser appends
  the correct multipart boundary itself.

## 3. Server-Sent Streaming (SSE) Engine

Real-time roleplay replies arrive as Server-Sent Events. The streaming client lives inside
`useChatMessages`
([useChatMessages.ts](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/composables/useChatMessages.ts)),
shared by both `sendMessage` and `regenerate` via a `readStream(response)` helper. It creates a
placeholder assistant message in the UI, then reads the response body chunk by chunk, appending
decoded content to that message until the stream ends:

<Figure tag="Figure 1" title="The SSE read loop" id="fig-sse-loop">
<svg viewBox="0 0 640 700" role="img" aria-label="Server-sent events streaming loop" style="font-family:var(--vp-font-family-base)">
  <defs>
    <marker id="tbm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-arrow)"/>
    </marker>
  </defs>
  <!-- Start -->
  <rect x="110" y="14" width="420" height="44" rx="10" fill="var(--tbm-dgm-surface-3)" stroke="var(--tbm-dgm-border-strong)"/>
  <text x="320" y="41" text-anchor="middle" font-size="12" font-weight="700" fill="var(--tbm-dgm-ink)">POST /api/chats/:id/messages?stream=true</text>
  <!-- Decision: Response OK? -->
  <polygon points="320,76 398,110 320,144 242,110" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-accent)"/>
  <text x="320" y="114" text-anchor="middle" font-size="12" font-weight="600" fill="var(--tbm-dgm-ink)">Response OK?</text>
  <!-- Error branch -->
  <rect x="430" y="88" width="182" height="44" rx="10" fill="var(--tbm-dgm-danger-soft)" stroke="var(--tbm-dgm-danger)"/>
  <text x="521" y="115" text-anchor="middle" font-size="12" fill="var(--tbm-dgm-ink)">Display error toast</text>
  <!-- Process boxes -->
  <g font-size="12" text-anchor="middle" fill="var(--tbm-dgm-ink)">
    <rect x="160" y="170" width="320" height="44" rx="10" fill="var(--tbm-dgm-frontend-soft)" stroke="var(--tbm-dgm-frontend)"/>
    <text x="320" y="197">Create local UUID message in UI</text>
    <rect x="160" y="238" width="320" height="44" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <text x="320" y="265">getReader — read stream body</text>
    <rect x="160" y="306" width="320" height="44" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <text x="320" y="333">Decode chunks with TextDecoder</text>
    <rect x="160" y="374" width="320" height="44" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <text x="320" y="401">Split buffer on double newlines</text>
    <rect x="160" y="442" width="320" height="44" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <text x="320" y="469">Parse each “data: ” event</text>
  </g>
  <!-- Decision: DONE? -->
  <polygon points="320,506 402,540 320,574 238,540" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-accent)"/>
  <text x="320" y="544" text-anchor="middle" font-size="12" font-weight="600" fill="var(--tbm-dgm-ink)">data == “[DONE]”?</text>
  <!-- End box -->
  <rect x="430" y="518" width="182" height="44" rx="10" fill="var(--tbm-dgm-data-soft)" stroke="var(--tbm-dgm-data)"/>
  <text x="521" y="539" text-anchor="middle" font-size="11.5" fill="var(--tbm-dgm-ink)">Close reader ·</text>
  <text x="521" y="554" text-anchor="middle" font-size="11.5" fill="var(--tbm-dgm-ink)">isGenerating = false</text>
  <!-- Append box -->
  <rect x="160" y="616" width="320" height="44" rx="10" fill="var(--tbm-dgm-frontend-soft)" stroke="var(--tbm-dgm-frontend)"/>
  <text x="320" y="643" text-anchor="middle" font-size="12" fill="var(--tbm-dgm-ink)">Append event.content to active message</text>
  <!-- Arrows -->
  <g stroke="var(--tbm-dgm-arrow)" stroke-width="1.6" fill="none" marker-end="url(#tbm-ah)">
    <path d="M320 58 L320 74"/>
    <path d="M398 110 L428 110"/>
    <path d="M320 144 L320 168"/>
    <path d="M320 214 L320 236"/>
    <path d="M320 282 L320 304"/>
    <path d="M320 350 L320 372"/>
    <path d="M320 418 L320 440"/>
    <path d="M320 486 L320 504"/>
    <path d="M402 540 L428 540"/>
    <path d="M320 574 L320 614"/>
    <path d="M160 638 L110 638 L110 260 L158 260"/>
  </g>
  <g font-size="10.5" fill="var(--tbm-dgm-ink-2)">
    <text x="412" y="102">No</text>
    <text x="330" y="160">Yes</text>
    <text x="412" y="532">Yes</text>
    <text x="330" y="596">No</text>
    <text x="96" y="450" text-anchor="middle" transform="rotate(-90 96 450)">loop until [DONE]</text>
  </g>
</svg>
<template #caption>

**A placeholder, then a growing message.** The UI message is created immediately with a local
UUID so the user sees the reply forming; each decoded `data:` event appends its `content` and
loops back to read more, until the stream ends (`[DONE]` is skipped and the reader reports `done`).

</template>
</Figure>

### Buffer Reassembly & Parsing

Network packets can arrive fragmented, so the parser reassembles events from a running buffer:

1. Decode each raw chunk (`TextDecoder`, `{ stream: true }`) and append it to a local string buffer.
2. Split the buffer on double newlines (`\n\n`) to segment individual SSE entries.
3. `pop()` the last (possibly incomplete) segment back into the buffer, to prepend to the next packet.
4. For each complete line:
   - skip anything that doesn't start with `data: `;
   - slice off the `data: ` prefix; if the payload is `[DONE]`, skip it (`continue`);
   - otherwise parse the payload as JSON. Backend events are the typed `StreamEvent`
     shape `{ type, content?, message? }` — **not** `{ text }`.
5. Dispatch on `event.type`:
   - `text` → append `event.content` to the active message's `content`;
   - `reasoning` → append `event.content` to the message's `reasoning_content`;
   - `error` → capture `event.message` and stop; the empty placeholder is dropped so a failed
     generation never lingers as a blank reply.

Each append writes a **new** message object into the array so standard watchers fire and the UI
re-renders as text grows. When `reader.read()` reports `done`, the loop ends and
`isGenerating` is set back to `false`.
