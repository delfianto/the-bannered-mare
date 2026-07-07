# LLM Provider System Comparison: SillyTavern v1.17.0 vs The Bannered Mare

This page assumes the [Providers Analysis](/sillytavern/analysis/providers) for how
SillyTavern works internally, and focuses on where The Bannered Mare diverges and why.

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
    <text x="408" y="122">Coverage — 8 types via 5 adapter classes</text>
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

SillyTavern supports ~40+ provider integrations split across two independent subsystems — 23 chat
completion providers, 15 text completion backends, and 3 dedicated endpoints (KoboldAI, NovelAI,
AI Horde) ([Analysis §1 ›](/sillytavern/analysis/providers#_1-provider-registry)).

**The Bannered Mare** supports 8 provider types via the `ProviderType` enum:

| ProviderType  | Adapter Used       |
|---------------|--------------------|
| `openai`      | `OpenAIAdapter`    |
| `anthropic`   | `AnthropicAdapter` |
| `google`      | `GeminiAdapter`    |
| `xai`         | `OpenAIAdapter`    |
| `openrouter`  | `OpenAIAdapter`    |
| `ollama`      | `OllamaAdapter`    |
| `lmstudio`    | `LMStudioAdapter`  |
| `custom`      | `OpenAIAdapter`    |

Five concrete adapter classes (OpenAI, Anthropic, Gemini, Ollama, LM Studio) cover all
eight types. `OllamaAdapter` and `LMStudioAdapter` both subclass `OpenAIAdapter` (local
OpenAI-compatible servers), and xAI, OpenRouter, and Custom providers reuse the OpenAI
adapter directly since their APIs are OpenAI-compatible.

SillyTavern covers a far wider surface area, including legacy text-completion backends,
niche aggregators, and self-hosted inference engines. The Bannered Mare targets the major
cloud providers and local inference (Ollama and LM Studio, both with native
model discovery and load/unload), delegating long-tail provider access to OpenRouter. Both
systems treat OpenAI-compatible APIs as a shared baseline.


## 2. Architecture Pattern

SillyTavern routes through a single ~2,700-line file (`chat-completions.js`) with a two-tier
dispatch — a switch statement for 12 bespoke providers and a ~260-line if/else chain for the
OAI-compatible rest — where each standalone async handler owns the full request lifecycle; text
completions live in a second, fully separate dispatch file ([Analysis §2 ›](/sillytavern/analysis/providers#_2-backend-request-handlers)).

**The Bannered Mare** uses an adapter pattern with a gateway, split into three layers:

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

| Aspect                    | SillyTavern                                          | The Bannered Mare                                    |
|---------------------------|------------------------------------------------------|----------------------------------------------------|
| Dispatch mechanism        | Switch statement + if/else chain                     | Registry dict lookup + polymorphic adapter          |
| Request/response coupling | Handler owns HTTP call + response parsing            | Adapter transforms data; Gateway owns HTTP          |
| Adding a new provider     | Add switch case or if/else branch in monolithic file | Implement `ProviderAdapter` subclass, add to registry |
| Shared code reuse         | Implicit (OAI-compat providers share the else path)  | Explicit (Ollama extends OpenAIAdapter)             |
| Subsystem count           | Two (chat completions + text completions)            | One unified chat completions path                   |
| State in handlers         | Handlers receive mutable `(req, res)` pair           | Adapters are stateless; Gateway holds config        |


## 3. Authentication Handling

SillyTavern stores 40+ named secrets in a per-user JSON file (via `SecretManager`, with rotation
and masking) and spans five auth patterns — Bearer, `x-api-key`, `api-key`, `?key=` query param,
and a full Vertex AI JWT/OAuth2 flow — with per-provider reverse-proxy overrides ([Analysis §4 ›](/sillytavern/analysis/providers#_4-authentication)).

**The Bannered Mare** takes a leaner, environment-variable approach:

- **Storage**: Environment variables. Each `ProviderConfig` declares an `env_var_name`
  (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). Custom providers store their env var
  name in the database column `api_key_env_var`.
- **Key retrieval**: `Provider.get_api_key()` reads `os.getenv(env_var_name)` at
  call time. `Provider.has_api_key()` checks whether the env var is set.
- **Three auth patterns** across adapters:
  - `Authorization: Bearer <key>` (OpenAI, xAI, OpenRouter, Custom, and LM Studio when a
    token is configured)
  - `x-api-key: <key>` (Anthropic)
  - No auth (Ollama -- `build_headers` returns only Content-Type; LM Studio defaults to no
    auth but inherits Bearer from `OpenAIAdapter` when a token is set)
- **Google Gemini** uses API key as a query parameter (`?key=<apiKey>`), handled in
  `GeminiAdapter.build_url()`.
- **Base URL override**: Each Provider row can store a custom `base_url` that overrides
  the default from `PROVIDER_CONFIGS`.

| Aspect                | SillyTavern                              | The Bannered Mare                          |
|-----------------------|------------------------------------------|------------------------------------------|
| Key storage           | JSON file with rotation/masking          | Environment variables                    |
| Key count             | 40+ named secrets                        | 8 (one per ProviderConfig)               |
| Auth pattern variety  | 5+ patterns including JWT/OAuth2         | 3 patterns (Bearer, x-api-key, none)     |
| Reverse proxy support | Built-in per provider                    | Via base_url override on Provider model  |
| Vertex AI auth        | Full JWT/OAuth2 flow                     | Not implemented (Google AI Studio only)  |


## 4. Parameter Management

SillyTavern filters parameters through 8 constant allowlist arrays (`_.pickBy()`), assembles
provider-specific additions inline in each handler, and manages defaults/presets entirely in the
frontend, sending parameters as-is ([Analysis §5 ›](/sillytavern/analysis/providers#_5-parameter-management)).

**The Bannered Mare** manages parameters server-side:

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
  - `OpenAIAdapter`: Whitelists via `_OPENAI_PARAMS` set (19 keys including
    `reasoning_effort`, `max_completion_tokens`, `stream_options`).
  - `AnthropicAdapter`: Extracts `max_tokens`, `temperature` (clamped to 1.0), `top_p`,
    `top_k`, `stop_sequences`, `thinking`.
  - `GeminiAdapter`: Maps canonical names to Gemini names via `_GENERATION_CONFIG_MAP`
    (e.g., `top_p` -> `topP`, `max_output_tokens` -> `maxOutputTokens`), with a
    `max_tokens` -> `maxOutputTokens` fallback.
  - `OllamaAdapter` / `LMStudioAdapter`: Inherit OpenAI filtering.
- **Unsupported parameter tracking**: `ModelFamily.unsupported_parameters` column
  explicitly lists parameters the family does not support.

| Aspect                     | SillyTavern                           | The Bannered Mare                                |
|----------------------------|---------------------------------------|------------------------------------------------|
| Model configuration        | One model = one config                | Configured endpoint (N configs per upstream model via `template_id`) |
| Default management         | Frontend-side presets                 | Server-side three-tier cascade                 |
| Parameter filtering        | Allowlist arrays + `_.pickBy()`       | Per-adapter whitelist sets/maps                |
| Provider-specific mapping  | Inline in each handler                | Declarative maps in adapter classes            |
| Parameter schema storage   | Not stored server-side                | `ModelFamily.parameters` JSON column           |
| Unsupported tracking       | Not tracked                           | `ModelFamily.unsupported_parameters` column    |


## 5. Response Normalization

SillyTavern normalizes to the OpenAI `{ choices: [{ message: { content } }] }` shape — forwarding
OAI-compatible providers untouched and hand-wrapping non-OAI responses per handler (preserving the
original alongside), all as plain untyped JS objects ([Analysis §6 ›](/sillytavern/analysis/providers#_6-response-normalisation)).

**The Bannered Mare** normalizes into three typed dataclasses:

- `CompletionResponse`: `content: str`, `finish_reason: str`, `usage: TokenUsage`,
  `reasoning: str | None`, `raw: dict`.
- `StreamChunk`: `content: str | None`, `reasoning: str | None`,
  `finish_reason: str | None`, `usage: TokenUsage | None`.
- `TokenUsage`: `input_tokens`, `output_tokens`, `total_tokens`,
  `cache_read_tokens`, `cache_creation_tokens`.

Every adapter implements `parse_response()` and `parse_stream_line()` to produce these canonical
types. Finish reasons are normalized to a common vocabulary (`stop`, `length`, `content_filter`,
`tool_calls`) via explicit per-adapter maps:

- Anthropic: `end_turn` -> `stop`, `max_tokens` -> `length`.
- Gemini: `STOP` -> `stop`, `MAX_TOKENS` -> `length`, `SAFETY`/`RECITATION`/etc. ->
  `content_filter`.
- OpenAI: Pass-through (already canonical).

The unmodified provider JSON is retained in `CompletionResponse.raw`.

| Aspect                   | SillyTavern                               | The Bannered Mare                            |
|--------------------------|-------------------------------------------|--------------------------------------------|
| Canonical type           | Plain JS object (OAI shape)               | Typed dataclasses                          |
| Finish reason mapping    | Ad-hoc per handler                        | Explicit maps per adapter                  |
| Raw response access      | Preserved as extra fields                 | Stored in `CompletionResponse.raw`         |
| Type safety              | None (dynamic JS objects)                 | Full (dataclass fields)                    |


## 6. Streaming

SillyTavern's backend is a transparent SSE proxy — `forwardFetchResponse()` pipes upstream bytes
straight to the Express response (Ollama's JSONL being the one re-wrapped exception), with an
`AbortController` tied to socket `close` for cancellation ([Streaming Analysis ›](/sillytavern/analysis/streaming)).

**The Bannered Mare** parses the stream server-side:
`ProviderGateway.chat_completion_stream()` uses `httpx.AsyncClient` with
`client.stream("POST", ...)`, iterates `response.aiter_lines()`, calls
`adapter.parse_stream_line()` on each line, and yields `StreamChunk` objects. Each adapter
handles its own SSE format:

- OpenAI: Strips `data: ` prefix, handles `[DONE]` sentinel, extracts delta content and reasoning.
- Anthropic: Dispatches on `type` field (`content_block_delta` for text/thinking, `message_delta`
  for finish, `message_stop` as fallback).
- Gemini: Parses `candidates[0].content.parts`, separates `thought` parts from text.
- Ollama / LM Studio: Inherit OpenAI parsing (both use the `/v1/chat/completions` SSE format).

Chunks with `finish_reason` set signal end of stream; the generator returns after the final chunk.
HTTP errors during streaming are caught after `response.aread()` and mapped to typed exceptions.
The full streaming contrast has its own [Streaming Comparison](/sillytavern/comparison/streaming).

| Aspect                  | SillyTavern                                | The Bannered Mare                              |
|-------------------------|--------------------------------------------|----------------------------------------------|
| Streaming transport     | Direct SSE pipe (transparent proxy)        | Parsed SSE -> typed StreamChunk generator    |
| Per-line parsing        | Client-side (frontend)                     | Server-side (adapter `parse_stream_line`)    |
| Abort mechanism         | AbortController on socket close            | httpx context manager (implicit on scope exit)|
| Chunk type              | Raw SSE text                               | Typed `StreamChunk` dataclass                |


## 7. Prompt Caching

SillyTavern implements Anthropic prompt caching via `cachingAtDepthForClaude()`
(`cache_control: { type: 'ephemeral', ttl }` at a configurable depth), with parallel logic for
OpenRouter and NanoGPT Claude, cacheability detection through the OpenRouter `/models` API, and
the relevant beta headers ([Analysis §8 ›](/sillytavern/analysis/providers#_8-provider-specific-features)).

**The Bannered Mare** caches through the adapters:

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

| Aspect                   | SillyTavern                              | The Bannered Mare                           |
|--------------------------|------------------------------------------|-------------------------------------------|
| Anthropic system caching | Supported with configurable TTL          | Supported (ephemeral, no TTL config)      |
| Depth-based caching      | Configurable breakpoint depth            | Not implemented                           |
| Cache usage tracking     | Not tracked in normalized response       | Tracked in `TokenUsage` dataclass         |
| OpenRouter cache detect  | Runtime query to `/models` API           | Not implemented                           |
| Multi-provider tracking  | Anthropic only                           | Anthropic, OpenAI/xAI, Gemini            |


## 8. Reasoning / Extended Thinking Support

SillyTavern activates reasoning by model-name string matching per provider — Anthropic
enabled/adaptive modes with budget calculators, Gemini `thinkingConfig`, DeepSeek `-reasoner`,
xAI binary effort, OpenRouter/Moonshot/Z.AI toggles — and extracts it provider-specifically
([Analysis §8 ›](/sillytavern/analysis/providers#_8-provider-specific-features)).

**The Bannered Mare** drives reasoning through the parameter cascade rather than name matching:

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

| Aspect                     | SillyTavern                                | The Bannered Mare                              |
|----------------------------|--------------------------------------------|----------------------------------------------|
| Thinking mode activation   | Model-name string matching per provider    | Parameter cascade from ModelFamily/Preset     |
| Adaptive thinking          | Opus 4.6+ detection with effort levels     | Pass-through via parameters dict              |
| Budget calculation         | Provider-specific calculator functions      | Delegated to ModelFamily parameter defaults   |
| Reasoning response field   | Provider-specific extraction per handler    | Unified `reasoning` field on canonical types  |
| Streaming reasoning        | Provider-specific handling                  | All adapters yield `StreamChunk.reasoning`    |
| Provider coverage          | Claude, Gemini, DeepSeek, xAI, Moonshot, Z.AI, OpenRouter | Claude, Gemini, OpenAI-compat (xAI, DeepSeek via OpenRouter) |


## 9. Error Handling

SillyTavern wraps each handler's fetch in try/catch, mostly flattening non-OK responses to 500
(502 for `ECONNREFUSED`), special-casing `429` + `insufficient_quota` into a `quota_error` flag,
and guarding on `response.headersSent` before sending errors ([Analysis §7 ›](/sillytavern/analysis/providers#_7-error-handling)).

**The Bannered Mare** uses a typed exception hierarchy:

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
| Provider count           | ~40+ (23 chat + 15 text + 3 dedicated)     | 8 types, 5 adapter classes                  |
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
| Total provider code      | ~6,200 lines across 10 files               | ~2,000 lines across 17 files                |
