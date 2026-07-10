# LLM Integration

The Bannered Mare speaks to many LLM backends — cloud APIs like OpenAI and Anthropic,
aggregators like OpenRouter and OpenCode, and local servers like Ollama and LM Studio —
through one uniform internal interface. The design
splits two concerns that are usually tangled together: **what a provider's wire format looks
like** (owned by stateless adapters) and **how a call is actually made** (owned by a single
stateful gateway). Connection configuration lives in the database, separate from both.

## 1. Provider, Model, and ModelFamily

Three core database models describe LLM connectivity:

1. **Provider** — an API service instance (e.g., "Ollama Local" or "OpenAI Production").
   Holds the base URL, an `enabled` toggle, the `last_synced_at` timestamp, and a curated
   `allowed_models` allow-list. Credentials are read from an environment variable: for most
   provider types the variable name is fixed by static `PROVIDER_CONFIGS` (e.g.
   `OPENAI_API_KEY`), while a `custom` provider names its own via `api_key_env_var`.
2. **ModelFamily** — a grouping of similar models that defines default parameters
   (temperature, frequency penalty, and so on) and configuration such as prompt-structure
   templates.
3. **Model** — a concrete, selectable model (e.g., `gpt-4o` or `llama3`) linked to one
   Provider and one ModelFamily. It inherits parameters from its family and supports per-model
   overrides. Its Provider is chosen from the family's `provider_types` and is the route — the
   *same* base model reachable through several providers (DeepSeek V4 via OpenRouter or OpenCode)
   is one Model row per provider. See [Provider selection](#provider-selection).

## 2. The Stateless Adapter Pattern

So that transport logic is never duplicated per provider, each provider format is expressed
as a stateless adapter. The abstract `ProviderAdapter`
([base.py](https://github.com/delfianto/the-bannered-mare/blob/main/backend/src/provider/adapters/base.py))
exposes five hooks — the complete surface a provider must implement:

- `build_url` — assembles the full API endpoint URL.
- `build_headers` — assembles authentication headers (API keys, custom agents, org headers).
- `build_payload` — converts OpenAI-formatted system/user messages plus merged generation
  parameters into the provider's native JSON request body.
- `parse_response` — transforms the native JSON response into a normalized `CompletionResponse`.
- `parse_stream_line` — parses a single Server-Sent Events (SSE) line from a streaming
  connection into a normalized `StreamChunk`.

### Supported Adapters

- **OpenAI** — the standard format for OpenAI, xAI, OpenRouter, OpenCode Zen/Go, and other
  OpenAI-compatible systems.
- **Anthropic** — formats requests using Anthropic's message schema.
- **Google AI (Gemini)** — formats requests using Gemini's native client structure.
- **Ollama** — talks to local Ollama `/api/chat` endpoints.
- **LM Studio** — maps directly to LM Studio endpoints.

## 3. The Centralized Gateway (`ProviderGateway`)

Where adapters are stateless format-translators, the `ProviderGateway`
([gateway.py](https://github.com/delfianto/the-bannered-mare/blob/main/backend/src/provider/gateway.py))
is the stateful execution coordinator. It owns the asynchronous HTTP connection
(`httpx.AsyncClient`), enforces timeouts, and maps connection failures to normalized internal
exceptions. A caller never picks an adapter or touches HTTP directly — it hands work to the
gateway, which selects the right adapter and drives the call:

<Figure tag="Figure 1" title="Caller → gateway → adapter / provider" id="fig-gateway">
<svg viewBox="0 0 760 300" role="img" aria-label="ProviderGateway coordinating adapter and provider API" style="font-family:var(--vp-font-family-base)">
  <defs>
    <marker id="tbm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-arrow)"/>
    </marker>
  </defs>
  <!-- Caller -->
  <rect x="24" y="110" width="160" height="70" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
  <text x="104" y="140" text-anchor="middle" font-size="13" font-weight="700" fill="var(--tbm-dgm-ink)">Service /</text>
  <text x="104" y="158" text-anchor="middle" font-size="13" font-weight="700" fill="var(--tbm-dgm-ink)">chat job</text>
  <!-- Gateway -->
  <rect x="256" y="70" width="216" height="150" rx="12" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/>
  <text x="364" y="98" text-anchor="middle" font-size="14" font-weight="800" fill="var(--tbm-dgm-ink)">ProviderGateway</text>
  <text x="364" y="120" text-anchor="middle" font-size="11" fill="var(--tbm-dgm-ink-2)">stateful coordinator</text>
  <line x1="278" y1="132" x2="450" y2="132" stroke="var(--tbm-dgm-border)"/>
  <text x="364" y="150" text-anchor="middle" font-size="11" fill="var(--tbm-dgm-ink-2)">owns httpx.AsyncClient</text>
  <text x="364" y="168" text-anchor="middle" font-size="11" fill="var(--tbm-dgm-ink-2)">per-model timeouts</text>
  <text x="364" y="186" text-anchor="middle" font-size="11" fill="var(--tbm-dgm-ink-2)">exception normalization</text>
  <text x="364" y="204" text-anchor="middle" font-size="11" fill="var(--tbm-dgm-ink-2)">parameter resolution</text>
  <!-- Adapter -->
  <rect x="544" y="28" width="196" height="110" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
  <text x="642" y="50" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">ProviderAdapter</text>
  <text x="642" y="67" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-faint)">stateless · per-format</text>
  <text x="642" y="87" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">build_url · build_headers</text>
  <text x="642" y="103" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">build_payload</text>
  <text x="642" y="119" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">parse_response · parse_stream_line</text>
  <!-- Provider API -->
  <rect x="544" y="196" width="196" height="72" rx="10" fill="var(--tbm-dgm-provider-soft)" stroke="var(--tbm-dgm-provider)"/>
  <text x="642" y="226" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">Provider API endpoint</text>
  <text x="642" y="245" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">OpenAI · Anthropic · Gemini · Ollama · …</text>
  <!-- Arrows -->
  <g stroke="var(--tbm-dgm-arrow)" stroke-width="1.6" fill="none" marker-end="url(#tbm-ah)">
    <path d="M184 145 H254"/>
    <path d="M472 145 H508 V83 H542"/>
    <path d="M472 145 H508 V232 H542"/>
  </g>
  <text x="219" y="138" text-anchor="middle" font-size="10" fill="var(--tbm-dgm-ink-2)">hand off</text>
  <text x="526" y="78" text-anchor="middle" font-size="10" fill="var(--tbm-dgm-ink-2)">select</text>
  <text x="506" y="248" text-anchor="middle" font-size="10" fill="var(--tbm-dgm-ink-2)">HTTPS · SSE</text>
</svg>
<template #caption>

**The gateway is the only stateful piece.** Callers hand it a request; it looks up the
adapter for the target format, uses the adapter's pure functions to shape the payload and
parse the reply, and owns the one real HTTP connection to the provider — including timeouts
and failure mapping.

</template>
</Figure>

### Parameter Resolution Pipeline

When a request is initiated, the gateway merges generation parameters in a fixed priority
order, each layer overriding the one before it:

1. **ModelFamily parameters** — global defaults (only params whose `default` is set).
2. **Model parameters** — per-model overrides.
3. **Preset parameters** — user-specified overrides for the chat session.

### Provider selection

A model runs on exactly one provider (`provider_id`) using `model_identifier` — the id that
provider knows it by. **The provider _is_ the route:** the gateway uses that provider's base URL
and API key, sends `model_identifier`, and selects the adapter from the provider's type via the
registry. Nothing is special-cased — OpenRouter, OpenCode Zen/Go, and any other aggregator are
just OpenAI-compatible providers a model can point at.

A model's provider must be one of its family's `provider_types` (enforced on create/update), so
a model can never point at a provider its family can't run on. Because a base model (the family)
has no single "home", the *same* model reachable via several providers is simply several Model
rows — e.g. "DeepSeek V4 Flash" on OpenRouter and on OpenCode Go — sharing one family, hence one
parameter schema. (There is deliberately no separate "route override": a native provider plus an
override provider produced nonsensical states like OpenRouter-routed-to-HuggingFace; the single
provider selection is the whole story.)

**Adding a new aggregator** (e.g. Hugging Face Inference) is a configuration change, not a
gateway change: add the `ProviderType`, a `PROVIDER_CONFIGS` entry (default base URL + env var),
and a discovery-client registration, then add the new type to the relevant families'
`provider_types`. Models can then be created on it — and no new adapter is needed when it speaks
the OpenAI wire format.

### Exception Normalization

The gateway catches HTTP status errors and maps them to clean system exceptions:

- `401` → `ProviderAuthError`
- `429` → `ProviderRateLimitError`
- `400` → `ProviderInvalidRequestError`
- any other status → `ProviderException`

Timeouts are caught separately and raised as `ProviderTimeoutError`; any other unexpected
error is wrapped in `ProviderException`.

## 4. Model Discovery and Syncing

To make connecting a local backend painless, The Bannered Mare auto-discovers models:

- **ModelDiscoveryClient**
  ([discovery.py](https://github.com/delfianto/the-bannered-mare/blob/main/backend/src/provider/discovery.py))
  — a `Protocol` with per-provider implementations, chosen from a registry keyed by
  provider type. Each queries that provider's native listing endpoint (Ollama's `/api/tags`
  plus `/api/ps` for load state, LM Studio's `/api/v1/models`, the OpenAI-compatible
  `/models`, Anthropic's `/models`, Gemini's `/v1beta/models`) and normalizes the results
  into `DiscoveredModel` items. The local clients (Ollama, LM Studio) additionally support
  `load_model` / `unload_model`; cloud clients raise `NotImplementedError` for those.
- **ModelListCache**
  ([model_cache.py](https://github.com/delfianto/the-bannered-mare/blob/main/backend/src/provider/model_cache.py))
  — a process-local, in-memory TTL cache keyed by provider ID that avoids hammering network
  backends while a user browses available models. It is lost on restart by design.
- **Model Synchronizer** — merges discovered models into the database, creating new `Model`
  rows automatically while preserving user modifications to existing ones.
