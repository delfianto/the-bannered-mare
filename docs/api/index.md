---
title: API Reference
---

# API Reference

The backend exposes a single REST API — the same contract the frontend consumes and the
one described by the repo-root [`openapi.json`](https://github.com/delfianto/the-bannered-mare/blob/main/openapi.json).
This section documents **every endpoint**, grouped by the [domain](/architecture/backend/data-model)
it belongs to. Read this overview first: it covers the conventions that hold across the
whole API — base URL, the response envelope, pagination, filtering, and errors — so the
per-domain pages can stay focused on what's specific to each.

::: tip The spec is the source of truth
This reference is written and curated for reading. For the exhaustive, always-current,
machine-readable view, a running backend serves interactive **Swagger UI** at
`http://localhost:8000/docs` and the raw spec at `http://localhost:8000/openapi.json`.
Anything here and the spec disagree on, the spec wins.
:::

## Base URL and structure

There is no version prefix and no gateway — the service is addressed directly. In local
development that is `http://localhost:8000`.

| Prefix | Holds |
|--------|-------|
| `/api/…` | Everything application-facing — characters, chats, providers, prompts, RAG, and so on. |
| `/health` | Liveness/readiness probe. |
| `/admin/…` | Read-only operational log queries. |
| `/`, `/demo` | The API root banner and a minimal built-in HTML chat page for manual testing. |

## Authentication

**There is none.** The Bannered Mare is designed to be **self-hosted and run locally**, so
the API is unauthenticated and every endpoint is open to whoever can reach the port. The
credentials that matter — your LLM provider API keys — never travel over this API and are
never stored in the database; the backend reads them from server-side **environment
variables** (see [LLM Providers](/providers/)). Do not expose this service directly to an
untrusted network. If you need remote access, put it behind your own authenticating proxy
or an SSH tunnel.

## Content types

Requests and responses are **`application/json`** unless noted. Three kinds of endpoint
differ:

- **File uploads** use `multipart/form-data`: creating or updating a character or persona
  (the avatar is an uploaded file alongside the fields), and the character / preset
  **import** endpoints.
- **Binary downloads** return the raw bytes: avatar images (`image/*`) and the character
  PNG export.
- **Streaming** responses use Server-Sent Events (`text/event-stream`) — only when sending
  a message with `?stream=true` (see [Streaming](#streaming-completions)).

## Identifiers and timestamps

Every resource is keyed by a **12-character nanoid** string (e.g. `"V1StGXR8Z5jd"`) — not a
sequential integer or a UUID. IDs are URL-safe and appear both in paths
(`/api/characters/{character_id}`) and as `*_id` fields in bodies. All timestamps
(`created_at`, `updated_at`, and friends) are **ISO 8601 in UTC**, e.g.
`"2026-07-07T14:32:10.512Z"`.

## The response envelope

Single resources are returned bare — the object *is* the body:

```json
{
  "id": "V1StGXR8Z5jd",
  "name": "Lydia",
  "created_at": "2026-07-07T14:32:10.512Z",
  "updated_at": "2026-07-07T14:32:10.512Z"
}
```

**Paginated** list endpoints wrap their results in a consistent envelope — an `items`
array plus a `meta` object — so a client can page without special-casing each resource:

```json
{
  "items": [ { "id": "…", "name": "…" }, … ],
  "meta": { "limit": 10, "has_more": true, "total": 42, "page": 1 }
}
```

Not every list is paginated. Small, bounded collections (a message's alternatives, RAG
search hits) return a **bare JSON array**. Each per-domain page states which style an
endpoint uses.

## Pagination

Two strategies share the one `meta` envelope; which fields are populated tells you which
one an endpoint uses.

**Offset (page-based)** — the default for most catalog-style lists (characters, models,
personas, presets, profiles, templates, fragments). Request a `page` (1-based) and a
`limit`; the response's `meta` carries `total` and `page` so you can render numbered pages.

```bash
curl "http://localhost:8000/api/characters?page=2&limit=10"
```

**Cursor (infinite scroll)** — used where new rows arrive at the head and stable paging
matters: **chats** and a chat's **messages**. Pass `limit` and, for the next page, the
`cursor` from the previous `meta`; `has_more` tells you when to stop.

```bash
# first page
curl "http://localhost:8000/api/chats?limit=20"
# next page, using meta.cursor from the previous response
curl "http://localhost:8000/api/chats?limit=20&cursor=eyJpZCI6…"
```

## Filtering

List endpoints accept filters as query parameters using a **`field__operator`** convention.
The operator suffix maps to a SQL comparison:

| Suffix | Meaning | Example |
|--------|---------|---------|
| *(none)* / `__eq` | equals | `?provider_id=V1StGXR8Z5jd` |
| `__ilike` | case-insensitive substring | `?name__ilike=lydia` |
| `__ge` / `__le` | ≥ / ≤ (great for dates) | `?created_at__ge=2026-01-01` |
| `__in` | in a set | `?gender__in=female,non-binary` |

The available filters differ per endpoint and are listed on each domain page.

## Status codes

The API uses standard HTTP semantics:

| Code | When |
|------|------|
| `200 OK` | Successful read or update. |
| `201 Created` | A resource was created (most `POST`s). |
| `204 No Content` | A successful `DELETE` — empty body. |
| `404 Not Found` | The addressed resource doesn't exist. |
| `409 Conflict` | A uniqueness or state conflict — a duplicate name/slug, or a delete blocked by a dependent resource. |
| `422 Unprocessable Entity` | Request validation failed (bad/missing fields, wrong types). |

## Errors

A plain error carries a `detail` string:

```json
{ "detail": "Character not found" }
```

Validation errors (`422`) come from FastAPI/Pydantic and list exactly what failed, each
with a `loc` path into the request, a human `msg`, and a machine `type`:

```json
{
  "detail": [
    { "loc": ["body", "name"], "msg": "Field required", "type": "missing" }
  ]
}
```

## Streaming completions

Sending a message is the one endpoint with two response modes. `POST
/api/chats/{chat_id}/messages` returns a normal JSON `MessageResponse` by default; add
**`?stream=true`** and it returns a Server-Sent Event stream instead, emitting typed events
as the model generates so the UI can render tokens live. The frontend's parser for this
stream is described in
[Backend Connection](/architecture/frontend/backend-connection); the mechanics of the
completion loop are in [LLM Integration](/architecture/backend/llm-integration).

## The domains

The API's ~110 operations divide into seven areas, mirroring the
[data model](/architecture/backend/data-model):

| Domain | Covers |
|--------|--------|
| [Characters & Personas](/api/characters-personas) | Character cards (CRUD, import/export, avatars) and user personas. |
| [Conversations](/api/conversations) | Chats, messages, streaming, swipes, and bookmarks. |
| [World & Lore](/api/world-and-lore) | Lorebooks and their keyword-triggered entries. |
| [Knowledge & RAG](/api/knowledge-and-rag) | The data bank and semantic search. |
| [Providers & Models](/api/providers-and-models) | Provider connections, model definitions, families, and live model management. |
| [Prompt Building](/api/prompt-building) | Profiles (loadouts), presets, templates, and fragments. |
| [System & Admin](/api/system) | Health, the operational log queries, and the built-ins. |
