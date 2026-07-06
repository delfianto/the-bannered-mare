# LLM Provider System Comparison: SillyTavern v1.17.0 vs The Bannered Mare

The two systems reach the same providers by opposite means — a big branching dispatcher versus
a small adapter interface:

<Figure tag="Figure 1" title="if/else dispatch vs the adapter pattern" id="fig-cmp-providers">
<svg viewBox="0 0 760 262" role="img" aria-label="SillyTavern vs The Bannered Mare provider architecture" style="font-family:var(--vp-font-family-base)">
  <rect x="24" y="16" width="344" height="230" rx="12" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <rect x="392" y="16" width="344" height="230" rx="12" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <rect x="24" y="16" width="344" height="44" rx="12" fill="var(--tbm-dgm-provider-soft)"/><rect x="24" y="36" width="344" height="24" fill="var(--tbm-dgm-provider-soft)"/>
  <rect x="392" y="16" width="344" height="44" rx="12" fill="var(--tbm-dgm-backend-soft)"/><rect x="392" y="36" width="344" height="24" fill="var(--tbm-dgm-backend-soft)"/>
  <text x="196" y="44" text-anchor="middle" font-size="13" font-weight="800" fill="var(--tbm-dgm-ink)">SillyTavern v1.17.0</text>
  <text x="564" y="44" text-anchor="middle" font-size="13" font-weight="800" fill="var(--tbm-dgm-ink)">The Bannered Mare</text>
  <g font-size="10.5" fill="var(--tbm-dgm-ink)">
    <text x="40" y="90">Dispatch — switch + if/else, one ~2,700-line file</text>
    <text x="40" y="122">Coverage — ~40+ providers across 2 subsystems</text>
    <text x="40" y="154">Abstraction — none; a branch per provider</text>
    <text x="40" y="186">Text vs chat — a second, separate dispatch file</text>
    <text x="40" y="222" fill="var(--tbm-dgm-ink-2)">Widest surface area, most coupling</text>
    <text x="408" y="90">Dispatch — ProviderGateway selects an adapter</text>
    <text x="408" y="122">Coverage — 7 types via 4 adapter classes</text>
    <text x="408" y="154">Abstraction — one ProviderAdapter interface</text>
    <text x="408" y="186">Reuse — xAI/OpenRouter/Custom → OpenAIAdapter</text>
    <text x="408" y="222" fill="var(--tbm-dgm-ink-2)">Fewer providers, uniform shape</text>
  </g>
</svg>
<template #caption>

**Same baseline, opposite structure.** Both treat OpenAI-compatible APIs as the common
denominator, but SillyTavern dispatches through one large branching file while The Bannered Mare
routes every call through a small, uniform `ProviderAdapter` interface.

</template>
</Figure>

## 1. Provider Count and Scope

### SillyTavern

Supports ~40+ distinct provider integrations split across two independent subsystems:

- **Chat Completions**: 23 providers (OpenAI, Claude, OpenRouter, Gemini, Vertex AI,
  MistralAI, Cohere, DeepSeek, xAI, Groq, Perplexity, Azure OpenAI, AI21, Chutes,
  ElectronHub, NanoGPT, AI/ML API, Pollinations, Moonshot, Fireworks, CometAPI, Z.AI,
  SiliconFlow).
- **Text Completions**: 15 providers (Ooba, Mancer, vLLM, Aphrodite, TabbyAPI,
  KoboldCpp, TogetherAI, LlamaCpp, Ollama, InfermaticAI, DreamGen, OpenRouter,
  Featherless, HuggingFace, Generic).
- **Dedicated backends**: KoboldAI, NovelAI, AI Horde (separate endpoint files).

### The Bannered Mare

Supports 7 provider types via `ProviderType` enum:

| ProviderType  | Adapter Used       |
|---------------|--------------------|
| `openai`      | `OpenAIAdapter`    |
| `anthropic`   | `AnthropicAdapter` |
| `google`      | `GeminiAdapter`    |
| `xai`         | `OpenAIAdapter`    |
| `openrouter`  | `OpenAIAdapter`    |
| `ollama`      | `OllamaAdapter`    |
| `custom`      | `OpenAIAdapter`    |

Four concrete adapter classes (OpenAI, Anthropic, Gemini, Ollama) cover all seven
types. xAI, OpenRouter, and Custom providers reuse the OpenAI adapter since their APIs
are OpenAI-compatible.

### Comparison

SillyTavern covers a far wider surface area, including legacy text-completion backends,
niche aggregators, and self-hosted inference engines. The Bannered Mare targets the major
cloud providers and local inference (Ollama), delegating long-tail provider access to
OpenRouter. Both systems treat OpenAI-compatible APIs as a shared baseline.


## 2. Architecture Pattern

### SillyTavern: Switch/If-Else Dispatch

Routing lives in a single ~2,700-line file (`chat-completions.js`) with a two-tier
dispatch:

1. **Tier 1 -- Switch statement**: 12 providers with bespoke request formats are
   dispatched to dedicated `async` handler functions (`sendClaudeRequest`,
   `sendMakerSuiteRequest`, etc.).
2. **Tier 2 -- If/else chain**: The remaining 11 providers fall through to a ~260-line
   if/else block that configures `apiUrl`, `apiKey`, `headers`, and `bodyParams`, then
   merges them into a single OpenAI-compatible request body.

Text completions use a second, fully separate dispatch file (`text-completions.js`,
646 lines) with its own switch statement and parameter filtering.

Handler functions are standalone async functions that receive the raw Express
`(request, response)` pair. Each handler owns the full lifecycle: URL construction,
auth, payload building, HTTP call, streaming/non-streaming response handling, and
error handling.

### The Bannered Mare: Adapter Pattern with Gateway

The system is split into three layers:

1. **`ProviderAdapter` (ABC)**: Defines five abstract methods -- `build_url`,
   `build_headers`, `build_payload`, `parse_response`, `parse_stream_line` -- plus a
   default `get_timeout`. Adapters are stateless data transformers that produce
   request/response shapes but never make HTTP calls.
2. **Adapter Registry** (`adapters/__init__.py`): A `dict[ProviderType, type[ProviderAdapter]]`
   mapping resolved by `get_adapter()`.
3. **`ProviderGateway`**: Owns the `httpx.AsyncClient`, timeout handling, error mapping,
   and the streaming iteration loop. Calls adapter methods to build requests and parse
   responses.

```
Router -> Service -> ProviderGateway -> ProviderAdapter (stateless)
                          |
                     httpx.AsyncClient -> Provider API
```

### Comparison

| Aspect                    | SillyTavern                                          | The Bannered Mare                                    |
|---------------------------|------------------------------------------------------|----------------------------------------------------|
| Dispatch mechanism        | Switch statement + if/else chain                     | Registry dict lookup + polymorphic adapter          |
| Request/response coupling | Handler owns HTTP call + response parsing            | Adapter transforms data; Gateway owns HTTP          |
| Adding a new provider     | Add switch case or if/else branch in monolithic file | Implement `ProviderAdapter` subclass, add to registry |
| Shared code reuse         | Implicit (OAI-compat providers share the else path)  | Explicit (Ollama extends OpenAIAdapter)             |
| Subsystem count           | Two (chat completions + text completions)            | One unified chat completions path                   |
| State in handlers         | Handlers receive mutable `(req, res)` pair           | Adapters are stateless; Gateway holds config        |


## 3. Authentication Handling

### SillyTavern

- **Storage**: JSON file on disk per user, managed by `SecretManager` class. Supports
  multi-secret per key with rotation and masked display.
- **40+ secret keys** defined in `SECRET_KEYS` (one per provider/service).
- **Five auth patterns** across providers:
  - `Authorization: Bearer <key>` (majority of providers)
  - `x-api-key: <key>` (Anthropic)
  - `api-key: <key>` (Azure OpenAI)
  - `?key=<apiKey>` query parameter (Google AI Studio, Vertex AI Express)
  - JWT/OAuth2 flow (Vertex AI Full -- service account JSON to JWT to access token)
  - No auth (local backends: KoboldCpp, LlamaCpp, Ollama)
- **Reverse proxy**: Nearly every cloud provider supports a `reverse_proxy` URL
  override with `proxy_password` as the credential.

### The Bannered Mare

- **Storage**: Environment variables. Each `ProviderConfig` declares an `env_var_name`
  (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). Custom providers store their env var
  name in the database column `api_key_env_var`.
- **Key retrieval**: `Provider.get_api_key()` reads `os.getenv(env_var_name)` at
  call time. `Provider.has_api_key()` checks whether the env var is set.
- **Three auth patterns** across adapters:
  - `Authorization: Bearer <key>` (OpenAI, xAI, OpenRouter, Custom)
  - `x-api-key: <key>` (Anthropic)
  - No auth (Ollama -- `build_headers` returns only Content-Type)
- **Google Gemini** uses API key as a query parameter (`?key=<apiKey>`), handled in
  `GeminiAdapter.build_url()`.
- **Base URL override**: Each Provider row can store a custom `base_url` that overrides
  the default from `PROVIDER_CONFIGS`.

### Comparison

| Aspect                | SillyTavern                              | The Bannered Mare                          |
|-----------------------|------------------------------------------|------------------------------------------|
| Key storage           | JSON file with rotation/masking          | Environment variables                    |
| Key count             | 40+ named secrets                        | 7 (one per ProviderConfig)               |
| Auth pattern variety  | 5+ patterns including JWT/OAuth2         | 3 patterns (Bearer, x-api-key, none)     |
| Reverse proxy support | Built-in per provider                    | Via base_url override on Provider model  |
| Vertex AI auth        | Full JWT/OAuth2 flow                     | Not implemented (Google AI Studio only)  |


## 4. Parameter Management

### SillyTavern

- **Parameter allowlists**: 8 constant arrays (`OLLAMA_KEYS`, `OPENAI_KEYS`,
  `VLLM_KEYS`, `OPENROUTER_KEYS`, `AZURE_OPENAI_KEYS`, etc.) defined in
  `constants.js`. Filtering is applied via `_.pickBy()`.
- **Common set**: `model, messages, temperature, max_tokens, top_p, stream,
  presence_penalty, frequency_penalty, stop, seed`.
- **Provider additions** are assembled inline within each handler or if/else branch
  (e.g., Claude gets `top_k`, `thinking`, `output_config`; Gemini gets `topK`,
  `safetySettings`, `thinkingConfig`).
- **No cascade**: Parameters are sent as-is from the frontend. The frontend UI manages
  defaults, presets, and overrides.

### The Bannered Mare

- **Model as configured endpoint**: A `Model` entry is not a 1:1 mapping to an upstream
  model. The same upstream model (identified by `model_identifier`) can have multiple
  `Model` rows, each with a different `template_id` and parameter overrides -- similar
  to OpenWebUI's custom model concept. Prompt configuration is handled entirely by the
  template + fragment system (`Model.template_id` -> `PromptTemplate`);
  `Model.system_prompt` was removed.
- **Three-tier cascade** in `ProviderGateway._get_effective_parameters()`:
  1. **ModelFamily defaults**: `ModelFamily.parameters` JSON column stores a schema with
     default values per parameter key.
  2. **Model overrides**: `Model.parameters` JSON column merges on top.
  3. **Preset overrides**: `Preset.parameters` JSON column (from chat session) merges
     last.
- **Adapter-level filtering**: Each adapter selectively extracts parameters it
  understands from the merged dict:
  - `OpenAIAdapter`: Whitelists via `_OPENAI_PARAMS` set (20 keys including
    `reasoning_effort`, `max_completion_tokens`, `stream_options`).
  - `AnthropicAdapter`: Extracts `max_tokens`, `temperature` (clamped to 1.0), `top_p`,
    `top_k`, `stop_sequences`, `thinking`.
  - `GeminiAdapter`: Maps canonical names to Gemini names via `_GENERATION_CONFIG_MAP`
    (e.g., `top_p` -> `topP`, `max_output_tokens` -> `maxOutputTokens`), with a
    `max_tokens` -> `maxOutputTokens` fallback.
  - `OllamaAdapter`: Inherits OpenAI filtering.
- **Unsupported parameter tracking**: `ModelFamily.unsupported_parameters` column
  explicitly lists parameters the family does not support.

### Comparison

| Aspect                     | SillyTavern                           | The Bannered Mare                                |
|----------------------------|---------------------------------------|------------------------------------------------|
| Model configuration        | One model = one config                | Configured endpoint (N configs per upstream model via `template_id`) |
| Default management         | Frontend-side presets                 | Server-side three-tier cascade                 |
| Parameter filtering        | Allowlist arrays + `_.pickBy()`       | Per-adapter whitelist sets/maps                |
| Provider-specific mapping  | Inline in each handler                | Declarative maps in adapter classes            |
| Parameter schema storage   | Not stored server-side                | `ModelFamily.parameters` JSON column           |
| Unsupported tracking       | Not tracked                           | `ModelFamily.unsupported_parameters` column    |


## 5. Response Normalization

### SillyTavern

- **Target format**: OpenAI-compatible `{ choices: [{ message: { content } }] }`.
- **OAI-compat providers**: Forwarded without transformation (OpenRouter, Groq,
  Fireworks, Perplexity, etc.).
- **Non-OAI providers**: Each handler wraps its response into the OAI shape manually.
  The original provider response is preserved alongside (e.g., Claude's `content` array,
  Gemini's `responseContent` parts).
- **No typed response model**: Normalized responses are plain JS objects.

### The Bannered Mare

- **Target format**: Three typed dataclasses:
  - `CompletionResponse`: `content: str`, `finish_reason: str`, `usage: TokenUsage`,
    `reasoning: str | None`, `raw: dict`.
  - `StreamChunk`: `content: str | None`, `reasoning: str | None`,
    `finish_reason: str | None`, `usage: TokenUsage | None`.
  - `TokenUsage`: `input_tokens`, `output_tokens`, `total_tokens`,
    `cache_read_tokens`, `cache_creation_tokens`.
- **Every adapter** implements `parse_response()` and `parse_stream_line()` to produce
  these canonical types.
- **Finish reason mapping**: Each adapter normalizes provider-specific stop reasons to a
  common vocabulary (`stop`, `length`, `content_filter`, `tool_calls`):
  - Anthropic: `end_turn` -> `stop`, `max_tokens` -> `length`.
  - Gemini: `STOP` -> `stop`, `MAX_TOKENS` -> `length`, `SAFETY`/`RECITATION`/etc. ->
    `content_filter`.
  - OpenAI: Pass-through (already canonical).
- **Raw preservation**: `CompletionResponse.raw` stores the unmodified provider JSON.

### Comparison

| Aspect                   | SillyTavern                               | The Bannered Mare                            |
|--------------------------|-------------------------------------------|--------------------------------------------|
| Canonical type           | Plain JS object (OAI shape)               | Typed dataclasses                          |
| Finish reason mapping    | Ad-hoc per handler                        | Explicit maps per adapter                  |
| Raw response access      | Preserved as extra fields                 | Stored in `CompletionResponse.raw`         |
| Type safety              | None (dynamic JS objects)                 | Full (dataclass fields)                    |


## 6. Streaming

### SillyTavern

- **Mechanism**: `forwardFetchResponse()` from `src/util.js` pipes the upstream SSE
  stream directly to the Express HTTP response. The server acts as a transparent proxy
  for SSE data.
- **Ollama exception**: Text-completion Ollama uses newline-delimited JSON, rewrapped
  into SSE format via `parseOllamaStream()`.
- **Abort handling**: Each handler creates an `AbortController` tied to the socket
  `close` event. When the client disconnects, the upstream request is aborted.
  KoboldCpp additionally sends an explicit `/api/extra/abort` request.
- **Header-sent safety**: All handlers check `response.headersSent` before sending
  error responses to avoid crashes during active streams.

### The Bannered Mare

- **Mechanism**: `ProviderGateway.chat_completion_stream()` uses `httpx.AsyncClient`
  with `client.stream("POST", ...)`. The gateway iterates `response.aiter_lines()`,
  calls `adapter.parse_stream_line()` on each line, and yields `StreamChunk` objects.
- **Adapter parsing**: Each adapter implements `parse_stream_line()` to handle its SSE
  format:
  - OpenAI: Strips `data: ` prefix, handles `[DONE]` sentinel, extracts delta content
    and reasoning.
  - Anthropic: Dispatches on `type` field (`content_block_delta` for text/thinking,
    `message_delta` for finish, `message_stop` as fallback).
  - Gemini: Parses `candidates[0].content.parts`, separates `thought` parts from text.
  - Ollama: Inherits OpenAI parsing (uses `/v1/chat/completions` SSE format).
- **Stream termination**: Chunks with `finish_reason` set signal end of stream; the
  generator returns after yielding the final chunk.
- **Error handling**: HTTP errors during streaming are caught after `response.aread()`
  and mapped to typed exceptions.

### Comparison

| Aspect                  | SillyTavern                                | The Bannered Mare                              |
|-------------------------|--------------------------------------------|----------------------------------------------|
| Streaming transport     | Direct SSE pipe (transparent proxy)        | Parsed SSE -> typed StreamChunk generator    |
| Per-line parsing        | Client-side (frontend)                     | Server-side (adapter `parse_stream_line`)    |
| Abort mechanism         | AbortController on socket close            | httpx context manager (implicit on scope exit)|
| Chunk type              | Raw SSE text                               | Typed `StreamChunk` dataclass                |


## 7. Prompt Caching

### SillyTavern

- **Anthropic caching**: `cachingAtDepthForClaude()` adds
  `cache_control: { type: 'ephemeral', ttl }` to messages at a configurable depth from
  the end. System prompt caching adds `cache_control` to the last system block and
  last tool definition.
- **OpenRouter Claude caching**: `cachingAtDepthForOpenRouterClaude()` and
  `cachingSystemPromptForOpenRouter()` adapt the same logic for OpenRouter's message
  format (handles string vs array content).
- **NanoGPT Claude caching**: Passes `cache_control.enabled` and `ttl` when model
  matches a Claude pattern.
- **Beta header**: `prompt-caching-2024-07-31` included in Claude's beta headers array
  alongside `extended-cache-ttl-2025-04-11`.
- **Cacheable detection**: `isOpenRouterModelCacheable()` queries the OpenRouter
  `/models` API to check for `pricing.input_cache_write`.

### The Bannered Mare

- **Anthropic caching**: `AnthropicAdapter.build_payload()` wraps the system prompt
  (assembled from the template + fragment system, not stored on the Model entity) in a
  content block with `cache_control: { type: 'ephemeral' }`:
  ```python
  payload["system"] = [{
      "type": "text",
      "text": system_text,
      "cache_control": {"type": "ephemeral"},
  }]
  ```
- **Beta header**: `anthropic-beta: prompt-caching-2024-07-31` is set unconditionally
  in `AnthropicAdapter.build_headers()`.
- **Cache token tracking**: `TokenUsage` includes `cache_read_tokens` and
  `cache_creation_tokens` fields populated from Anthropic's `cache_read_input_tokens`
  and `cache_creation_input_tokens` response fields.
- **OpenAI/xAI caching**: `OpenAIAdapter.parse_response()` extracts
  `prompt_tokens_details.cached_tokens` into `TokenUsage.cache_read_tokens`.
- **Gemini caching**: `GeminiAdapter.parse_response()` extracts
  `usageMetadata.cachedContentTokenCount` into `cache_read_tokens`.
- **No depth-based caching**: No configurable depth parameter for cache breakpoint
  placement.

### Comparison

| Aspect                   | SillyTavern                              | The Bannered Mare                           |
|--------------------------|------------------------------------------|-------------------------------------------|
| Anthropic system caching | Supported with configurable TTL          | Supported (ephemeral, no TTL config)      |
| Depth-based caching      | Configurable breakpoint depth            | Not implemented                           |
| Cache usage tracking     | Not tracked in normalized response       | Tracked in `TokenUsage` dataclass         |
| OpenRouter cache detect  | Runtime query to `/models` API           | Not implemented                           |
| Multi-provider tracking  | Anthropic only                           | Anthropic, OpenAI/xAI, Gemini            |


## 8. Reasoning / Extended Thinking Support

### SillyTavern

- **Anthropic**: Detects thinking-capable models by string matching (`claude-3-7`,
  `claude-opus-4`, `claude-sonnet-4`, etc.). Two modes:
  - `thinking.type = 'enabled'` with numeric `budget_tokens` (pre-Opus 4.6).
  - `thinking.type = 'adaptive'` with `output_config.effort` levels
    (low/medium/high/max) for Opus 4.6+/Sonnet 4.6.
  - Budget calculation via `calculateClaudeBudgetTokens()`.
- **Gemini**: `thinkingConfig` with either numeric `thinkingBudget` or string
  `thinkingLevel` depending on model generation. Separate calculator functions per
  model sub-family (Flash, Pro, Gemini 3).
- **DeepSeek**: Detects `-reasoner` suffix, adds `reasoning_content` to tool calls.
- **xAI**: Binary reasoning effort -- `high` stays `high`, everything else maps to
  `low`.
- **OpenRouter**: `reasoning.exclude` flag and `reasoning.effort` level pass-through.
- **Moonshot / Z.AI**: `thinking.type: 'enabled'/'disabled'` toggle.
- **Response extraction**: Provider-specific. Claude thinking blocks, Gemini thought
  parts, DeepSeek `reasoning_content` fields.

### The Bannered Mare

- **Anthropic**: `AnthropicAdapter.build_payload()` passes through a `thinking` dict
  from parameters when `thinking.type == 'enabled'`. No model-name detection or
  adaptive mode handling -- the parameter cascade supplies the correct config per
  ModelFamily.
- **Gemini**: `GeminiAdapter.parse_response()` separates `thought: true` parts from
  content parts. Thinking budget is not assembled at the adapter level -- it would
  come through the parameter cascade as `thinkingConfig` in `safety_settings` or
  generation config.
- **OpenAI/xAI**: `OpenAIAdapter` supports `reasoning_effort` as a pass-through
  parameter (in `_OPENAI_PARAMS`). Response parsing extracts `reasoning_content` or
  `reasoning` from the message.
- **Streaming**: All three adapter families handle reasoning in streaming:
  - Anthropic: `thinking_delta` event type yields `StreamChunk(reasoning=...)`.
  - OpenAI: `delta.reasoning_content` or `delta.reasoning` yields reasoning chunks.
  - Gemini: `thought: true` parts in stream chunks yield reasoning.
- **Canonical field**: Both `CompletionResponse.reasoning` and `StreamChunk.reasoning`
  normalize reasoning content across all providers.

### Comparison

| Aspect                     | SillyTavern                                | The Bannered Mare                              |
|----------------------------|--------------------------------------------|----------------------------------------------|
| Thinking mode activation   | Model-name string matching per provider    | Parameter cascade from ModelFamily/Preset     |
| Adaptive thinking          | Opus 4.6+ detection with effort levels     | Pass-through via parameters dict              |
| Budget calculation         | Provider-specific calculator functions      | Delegated to ModelFamily parameter defaults   |
| Reasoning response field   | Provider-specific extraction per handler    | Unified `reasoning` field on canonical types  |
| Streaming reasoning        | Provider-specific handling                  | All adapters yield `StreamChunk.reasoning`    |
| Provider coverage          | Claude, Gemini, DeepSeek, xAI, Moonshot, Z.AI, OpenRouter | Claude, Gemini, OpenAI-compat (xAI, DeepSeek via OpenRouter) |


## 9. Error Handling

### SillyTavern

- **Pattern**: Each handler wraps its fetch call in try/catch. Non-OK responses are
  logged and returned as `response.status(500).send(errorJson)`. The original status
  code is not always preserved.
- **Rate limiting**: Detected specifically for the OAI-compat path via
  `status === 429 && error.type === 'insufficient_quota'`. A `quota_error` flag is
  sent to the frontend for UI-specific messaging.
- **Connection errors**: `ECONNREFUSED` is detected and returned as 502.
- **Abort handling**: `AbortController` tied to socket close on every handler.
- **Header-sent guard**: All handlers check `response.headersSent` before sending
  error responses.

### The Bannered Mare

- **Typed exception hierarchy**: `ProviderException` base class with four subclasses:
  - `ProviderAuthError` (HTTP 401)
  - `ProviderRateLimitError` (HTTP 429)
  - `ProviderInvalidRequestError` (HTTP 400)
  - `ProviderTimeoutError` (httpx timeout)
- **Centralized mapping**: `ProviderGateway._handle_http_error()` maps HTTP status
  codes to the appropriate exception type. Error detail is extracted from the
  provider's JSON error response.
- **Single error path**: Both `chat_completion()` and `chat_completion_stream()` use
  the same error handling: `HTTPStatusError` -> `_handle_http_error()`,
  `TimeoutException` -> `ProviderTimeoutError`, catch-all -> `ProviderException`.
- **Exception propagation**: Provider exceptions bubble up to the router layer, where
  they are mapped to HTTP responses per the project's layered architecture.

### Comparison

| Aspect                 | SillyTavern                                | The Bannered Mare                             |
|------------------------|--------------------------------------------|---------------------------------------------|
| Error typing           | Plain objects with `error: true` flag      | Typed exception hierarchy                   |
| Status code mapping    | Mostly flattened to 500/502                | Preserved (401, 429, 400, timeout)          |
| Error detail extraction| Inline per handler                         | Centralized in `_handle_http_error()`       |
| Rate limit detection   | Special-cased for OAI path                 | HTTP 429 -> `ProviderRateLimitError`        |
| Abort/cancel           | AbortController per handler                | httpx async context manager                 |


## 10. Summary Table

| Dimension                | SillyTavern v1.17.0                        | The Bannered Mare                             |
|--------------------------|--------------------------------------------|---------------------------------------------|
| Provider count           | ~40+ (23 chat + 15 text + 3 dedicated)     | 7 types, 4 adapter classes                  |
| Architecture             | Switch/if-else in monolithic handlers      | Adapter pattern + Gateway                   |
| Language / Runtime       | Node.js / Express                          | Python 3.14+ / FastAPI                      |
| HTTP client              | node-fetch                                 | httpx (async)                               |
| Auth storage             | Per-user JSON file with rotation           | Environment variables                       |
| Auth patterns            | 5+ (Bearer, x-api-key, api-key, query, JWT)| 3 (Bearer, x-api-key, query param)         |
| Prompt configuration     | Frontend-managed per model               | Template + fragment system (`Model.template_id`) |
| Parameter defaults       | Frontend-managed presets                   | Server-side 3-tier cascade                  |
| Parameter filtering      | Allowlist arrays (`_.pickBy`)              | Per-adapter whitelist sets/maps             |
| Response format          | Plain JS objects (OAI shape)               | Typed dataclasses                           |
| Streaming model          | SSE pipe-through (transparent proxy)       | Parsed SSE -> typed generator               |
| Prompt caching           | Anthropic depth-based + OpenRouter detect  | Anthropic system-level + multi-provider tracking |
| Reasoning support        | 7 providers with model-name detection      | 3 adapter families with parameter cascade   |
| Error handling           | Per-handler try/catch, flat status codes   | Typed exception hierarchy, centralized mapping |
| Text completions         | Separate subsystem (15 providers)          | Not implemented (chat completions only)     |
| Total provider code      | ~6,200 lines across 10 files               | ~550 lines across 6 files                   |
