# Candlekeep UI: Backend Integration and Streaming Client

Candlekeep UI connects to the FastAPI backend using a combination of a strongly-typed OpenAPI fetch client for standard CRUD queries, and a custom SSE streaming parser for real-time inference completions.

---

## 1. Type-Safe Client (`openapi-fetch`)

The frontend ensures type safety across all network exchanges:
*   **Schema Compilation**: The API specification [schema.d.ts](file:///srv/project/personal/candlekeep-ui/src/api/schema.d.ts) is compiled directly from the backend's `openapi.json` contract via:
    ```bash
    bun run api:gen
    ```
*   **Client Factory**: The client (defined in [client.ts](file:///srv/project/personal/candlekeep-ui/src/api/client.ts)) instantiates `openapi-fetch`, providing autocompletion and compile-time verification for path variables, query params, headers, and body structures.

### Standard Query Example
```typescript
const { data, error } = await client.GET("/api/providers/{provider_id}", {
  params: { path: { provider_id: id } },
});
```

---

## 2. Handling File Uploads (FormData)

Standard JSON clients do not handle multi-part file payloads (such as Character or Persona avatar images) well. For these operations, the frontend bypasses `openapi-fetch` and calls the browser's native `fetch` API directly:
*   Constructs a `FormData` object containing the file binary and metadata parameters.
*   Sends a standard POST/PUT request without setting a manual `Content-Type` header (allowing the browser to append the boundary boundary tags automatically).

---

## 3. Server-Side Streaming (SSE) Engine

Real-time roleplay responses are processed via Server-Sent Events (SSE). The streaming client is implemented inside `useChatMessages` (defined in [useChatMessages.ts](file:///srv/project/personal/candlekeep-ui/src/composables/useChatMessages.ts)):

```mermaid
graph TD
    Request[POST /api/chats/:id/messages?stream=true] --> Response{Response Ok?}
    Response -->|No| HandleError[Display Error Toast]
    Response -->|Yes| TempMsg[Create Local UUID Message in UI]
    TempMsg --> Stream[getReader: Read stream body]
    Stream --> Decode[Decode chunks with TextDecoder]
    Decode --> Split[Split line buffers by double newlines]
    Split --> Event[Parse each event prefix 'data: ']
    Event --> Done{data === '[DONE]'}
    Done -->|Yes| End[Close stream reader, flag isGenerating=false]
    Done -->|No| Append[Append data.text to active message content]
    Append --> Stream
```

### Buffer Reassembly & Parsing
In network connections, packets can arrive fragmented. The streaming parser implements a buffer system to reassemble events correctly:
1. Appends received raw chunks to a local string buffer.
2. Splits the buffer by double newlines (`\n\n`) to segment separate SSE entries.
3. Keeps the last incomplete line in the buffer to prepend to the next packet.
4. Checks each line:
   - If starting with `data: `, slices the payload and parses it to JSON.
   - If payload is `[DONE]`, ends parsing.
   - Appends text values to the active message's `content` property.
