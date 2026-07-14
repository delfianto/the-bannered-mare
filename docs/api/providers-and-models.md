---
title: Providers & Models
---

# Providers & Models

This domain is the model infrastructure: a **provider** is a connection to an LLM API, a
**model** is a usable model configuration, and a **model family** is the shared capability
and parameter schema several models inherit. It also includes the live-management endpoints
for local providers (Ollama, LM Studio) — discovering, loading, and persisting models that
run on your own machine. For how these are wired into the completion loop, see
[LLM Integration](/architecture/backend/llm-integration) and the per-provider notes under
[LLM Providers](/providers/); for the relationships, see
[the data model](/architecture/backend/data-model#providers-models).

::: tip Two senses of "model"
A **`Model`** is a row in the database — a saved configuration you can chat with. A
**`DiscoveredModel`** is something the backend *found* by querying a local provider's live
API; it isn't persisted until you call **persist**. The provider `…/models/*` endpoints
deal in discovered models; the `/api/models` endpoints deal in saved ones.
:::

## Providers

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/providers` | List configured providers (paginated). |
| `POST` | `/api/providers` | Register a new provider. |
| `GET` | `/api/providers/{id}` | Get one provider. |
| `PUT` | `/api/providers/{id}` | Update a provider's configuration. |
| `PATCH` | `/api/providers/{id}/flags` | Enable or disable a provider. |
| `GET` | `/api/providers/{id}/models/available` | List models detected on a local provider (cache-aware). |
| `POST` | `/api/providers/{id}/models/sync` | Force a live refresh, bypassing the cache. |
| `GET` | `/api/providers/{id}/models/search` | Search the live model list by name. |
| `PUT` | `/api/providers/{id}/models/filter` | Set the curated allow-list of models. |
| `POST` | `/api/providers/{id}/models/load` | Load a model into memory (local). |
| `POST` | `/api/providers/{id}/models/unload` | Unload a model from memory (local). |
| `POST` | `/api/providers/{id}/models/persist` | Save a discovered model as a `Model` definition. |
| `DELETE` | `/api/providers/{id}/models` | Remove a model from a local provider's registry. |

### The provider resource

`ProviderResponse`:

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | 12-char nanoid. |
| `name` | string | Unique display name. |
| `provider_type` | enum | `openai` · `anthropic` · `google` · `openrouter` · `xai` · `ollama` · `lmstudio` · `opencode` · `opencode_go` · `custom`. |
| `base_url` | string \| null | Override endpoint; falls back to the type's default when null. |
| `enabled` | boolean | Whether it's usable. |
| `allowed_models` | string[] | Curated allow-list; empty means show all discovered models. |
| `api_key_configured` | boolean | Whether the expected API key is present **in the environment**. |
| `env_var_name` | string \| null | Which env var the key is read from. |
| `last_synced_at` | string \| null | When the model list was last refreshed. |
| `identifier_style` | string | Short label for this provider's model-identifier scheme (e.g. `vendor/model`). |
| `identifier_hint` | string | Human-friendly explanation of the identifier scheme, with an example. |
| `created_at`, `updated_at` | string | ISO 8601 UTC. |

The list is **paginated** — a `{ items, meta }` envelope. Note that API keys are **never** sent to or
stored by this API — a provider only records *which environment variable* holds its key,
and `api_key_configured` reports whether that variable is set on the server.

Register a provider with `ProviderCreate` (`name` and `provider_type` required; `base_url`
optional for known types; `api_key_env_var` only for `custom`). `ProviderUpdate` edits
`name`, `base_url`, `api_key_env_var`, and `enabled`; the dedicated `PATCH …/flags`
(`{ "enabled": false }`) is a lightweight enable/disable toggle.

```bash
curl -X POST http://localhost:8000/api/providers \
  -H "Content-Type: application/json" \
  -d '{ "name": "My Ollama", "provider_type": "ollama", "base_url": "http://localhost:11434" }'
# → 201 ProviderResponse
```

### Managing a local provider's models

For local providers, the backend can talk to the provider's own API to see what's
installed and control what's loaded. These endpoints return **discovered** models, not
saved ones:

- **`GET …/models/available`** → `AvailableModelsResponse` — `{ provider_id, models[],
  last_synced_at, from_cache }`. Cache-aware; `from_cache` tells you if it was served from
  the last sync. Each `DiscoveredModel` has an `identifier`, `display_name`, `state`, and
  optional `size_bytes`, `quantization`, and `max_context_length`.
- **`POST …/models/sync`** → the same shape, but forces a live refresh and updates
  `last_synced_at`.
- **`GET …/models/search?q=`** → `ModelSearchResponse` — substring matches against the live
  list, ignoring the allow-list.
- **`PUT …/models/filter`** with `{ "allowed_models": ["llama3.1:8b", …] }` sets the
  curated allow-list (empty shows all) and returns the newly filtered available models.
- **`POST …/models/load`** / **`…/models/unload`** with `{ "model_identifier": "…" }` load
  or unload a model in the provider's memory; both return a `ModelActionResponse`
  (`{ model_identifier, action }`).
- **`POST …/models/persist`** with `{ "model_identifier": "…" }` promotes a discovered model
  into a saved `Model` definition, returning the created `ModelResponse`.
- **`DELETE …/models?model_identifier=…`** removes a model from the local provider's
  registry/filesystem.

```bash
curl -X POST http://localhost:8000/api/providers/V1StGXR8Z5jd/models/sync          # refresh
curl -X POST http://localhost:8000/api/providers/V1StGXR8Z5jd/models/persist \
  -H "Content-Type: application/json" -d '{ "model_identifier": "llama3.1:8b" }'   # → ModelResponse
```

## Models

A **model** here is a *canonical model* (registry): a provider-independent identity that carries
N provider **routes** and one active route. `/api/models` operates on registries; routes are a
sub-resource. Chats and profiles bind to the registry, so flipping the active route redirects
every chat using it.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/models` | List canonical models (paginated, filterable). |
| `POST` | `/api/models` | Create a canonical model + its initial route(s). |
| `GET` | `/api/models/{id}` | Get a model (with its embedded family). |
| `PUT` | `/api/models/{id}` | Update model fields (not routes). |
| `DELETE` | `/api/models/{id}` | Delete a model (cascades to its routes). |
| `PATCH` | `/api/models/{id}/flags` | Toggle `enabled`. |
| `POST` | `/api/models/{id}/routes` | Add a provider route. |
| `DELETE` | `/api/models/{id}/routes/{route_id}` | Remove a route. |
| `PUT` | `/api/models/{id}/active-route` | Set which route the model resolves to. |

### The model resource

`ModelResponse` (and `ModelListResponse`, a lighter list-item variant):

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | 12-char nanoid. |
| `slug` | string | **Required.** Provider-independent identity (e.g. `deepseek-v4-pro`); unique. |
| `display_name` | string | **Required.** Friendly display name. |
| `original_identifier` | string | The lab's native/canonical identifier. |
| `model_family_id` | string | **Required.** Its capability family. |
| `template_id` | string \| null | Default prompt template. |
| `parameters` | object | Free-form sampling/generation overrides. |
| `enabled` | boolean | Available for use. |
| `active_route_id` | string \| null | The route the model currently resolves to. |
| `routes` | ModelRoute[] | Provider routes: `{id, model_registry_id, provider_id, model_identifier, enabled}`. |
| `provider_enabled` | boolean | *(derived)* Active route exists **and** it + its provider are enabled. |
| `created_at`, `updated_at` | string | ISO 8601 UTC. |

`GET /api/models/{id}` returns `ModelDetailResponse`, which additionally **embeds the full
`model_family`**. Listing is offset-paginated (`page`, `limit`) and filterable by `name__ilike`
(display name), `provider_id` (has a route on that provider), `model_family_id`, and `enabled`.
A route's provider must be one of the family's `provider_types`, and a model has at most one
route per provider.

```bash
# Create a canonical model with one route (slug/original_identifier derived from the route).
curl -X POST http://localhost:8000/api/models \
  -H "Content-Type: application/json" \
  -d '{
        "display_name": "DeepSeek V4 Pro",
        "model_family_id": "aB3dEf6hIjK0",
        "routes": [{ "provider_id": "V1StGXR8Z5jd", "model_identifier": "deepseek/deepseek-v4-pro" }],
        "parameters": { "temperature": 1.0, "max_tokens": 4096 }
      }'                                                                 # → 201 ModelResponse

# Add a second route (same model via OpenCode Go) and make it active.
curl -X POST http://localhost:8000/api/models/xY9zAb2cDe4f/routes \
  -H "Content-Type: application/json" \
  -d '{ "provider_id": "Op3nC0deG0id", "model_identifier": "deepseek-v4-pro" }'   # → ModelResponse

curl -X PUT http://localhost:8000/api/models/xY9zAb2cDe4f/active-route \
  -H "Content-Type: application/json" -d '{ "route_id": "rt_Ab12Cd34Ef56" }'      # → ModelResponse
```

## Model families

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/model-families` | List families (paginated, filterable). |
| `POST` | `/api/model-families` | Create a family. |
| `GET` | `/api/model-families/parameter-docs` | Documentation for all known model parameters. |
| `GET` | `/api/model-families/{id}` | Get a family. |
| `PUT` | `/api/model-families/{id}` | Update a family. |
| `DELETE` | `/api/model-families/{id}` | Delete a family (blocked while models use it). |

A **family** captures what a group of models has in common: which parameters they support,
their defaults and valid ranges, and which providers offer them. Because models depend on
their family (a [protected reference](/architecture/backend/data-model#_1-ownership-is-written-in-the-delete-rules)),
a family **cannot be deleted while any model still points at it**.

`ModelFamilyResponse`:

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | 12-char nanoid. |
| `name` | string | **Required.** Unique. |
| `family_identifier` | string | **Required.** URL-safe `provider/model-name` identifier. |
| `description` | string \| null | What the family is. |
| `provider_types` | string[] | Provider types that offer this family. |
| `parameters` | object | Per-parameter config — type, default, ranges. |
| `unsupported_parameters` | string[] | Parameters explicitly *not* supported. |
| `extra_metadata` | object \| null | Additional technical metadata. |
| `created_at`, `updated_at` | string | ISO 8601 UTC. |

The list uses the lighter `ModelFamilyListResponse` (omits the heavy `parameters` /
`extra_metadata`), is offset-paginated, and filters by `name__ilike`, `family_identifier`,
and `provider_type`.

`GET /api/model-families/parameter-docs` is a **static reference** endpoint (no path
params): it returns human-readable documentation — labels and descriptions — for every
known sampling parameter, which the UI uses to annotate parameter inputs. The frontend's
settings store lazy-loads and caches it.
