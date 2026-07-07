---
title: Knowledge & RAG
---

# Knowledge & RAG

The **data bank** is user-managed knowledge — notes, facts, background — that can be
retrieved into a prompt by meaning rather than by keyword. Writing an entry indexes it into
the vector store; **RAG search** queries that store. Retrieval draws on two sources: data
bank entries and past chat messages, both embedded into the same
[VectorChord](/architecture/backend/persistence) index. This is the semantic-search
counterpart to the keyword-triggered [World & Lore](/api/world-and-lore); the
retrieval design is discussed in the [RAG analysis](/sillytavern/analysis/rag).

## Data bank

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/data-bank/` | List entries (filterable; bare array). |
| `POST` | `/api/data-bank/` | Create an entry (indexed for RAG when enabled). |
| `GET` | `/api/data-bank/{id}` | Get one entry. |
| `PUT` | `/api/data-bank/{id}` | Update an entry (re-indexed when enabled). |
| `DELETE` | `/api/data-bank/{id}` | Delete an entry and purge its embeddings. |

### The data-bank resource

`DataBankResponse`:

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | 12-char nanoid. |
| `name` | string | **Required.** Display name. |
| `content` | string | **Required.** The knowledge text (chunked and embedded). |
| `scope` | string | `global` (default), `character`, or `chat`. |
| `character_id` | string \| null | Set for `character`-scoped entries. |
| `chat_id` | string \| null | Set for `chat`-scoped entries. |
| `created_at`, `updated_at` | string | ISO 8601 UTC. |

`scope` decides what an entry hangs off: `global` entries are always in scope, while
`character`- and `chat`-scoped entries carry the matching `*_id` and are owned by that
record (deleting the character or chat deletes them). Listing is a **bare array**
(unpaginated) and filters on `scope`, `character_id`, and `chat_id`.

Creating or updating an entry (re)indexes it into the vector store when RAG is enabled;
deleting one **purges its embeddings** so the index never points at gone content.

```bash
curl -X POST http://localhost:8000/api/data-bank/ \
  -H "Content-Type: application/json" \
  -d '{
        "name": "Whiterun politics",
        "content": "Jarl Balgruuf the Greater rules Whiterun and stays neutral in the civil war.",
        "scope": "character",
        "character_id": "V1StGXR8Z5jd"
      }'                                                                 # → 201 DataBankResponse
```

`DataBankUpdate` accepts `name`, `content`, and `scope` (all optional).

## RAG search

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/rag/search` | Run a manual semantic search across embeddings. |
| `GET` | `/api/rag/status` | Report RAG status and the active embedding provider. |

`POST /api/rag/search` takes a `RAGSearchRequest` and returns a **bare array** of
`RetrievedChunk` ranked by similarity. Only `query` is required; the rest scope and tune the
search:

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `query` | string | — | **Required.** The search text. |
| `chat_id` | string \| null | — | Restrict to a chat's context. |
| `character_id` | string \| null | — | Restrict to a character's context. |
| `max_results` | integer | `5` | Cap on returned chunks. |
| `threshold` | number | `0.3` | Minimum similarity score to include. |

Each `RetrievedChunk` carries the matched `content`, its `source_type` (`message` or
`data_bank`) and `source_id`, the similarity `score`, and the `chunk_index` within the
source.

```bash
curl -X POST http://localhost:8000/api/rag/search \
  -H "Content-Type: application/json" \
  -d '{ "query": "who rules Whiterun?", "max_results": 3, "threshold": 0.25 }'
# → [ { "content": "Jarl Balgruuf…", "source_type": "data_bank", "source_id": "…", "score": 0.82, "chunk_index": 0 }, … ]
```

`GET /api/rag/status` reports whether RAG is operational and which embedding provider and
model are in use — handy for confirming the vector extension and embedding backend are
wired up before relying on retrieval.
