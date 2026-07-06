# RAG Pipeline -- SillyTavern v1.17.0 vs Candlekeep Core

This document compares RAG (Retrieval-Augmented Generation) capabilities between
SillyTavern v1.17.0 and Candlekeep Core. Both systems now have functional RAG
pipelines, though with different architectural foundations and scope.

Source analysis: `docs/st_analysis/RAG_PIPELINE.md`

---

## 1. High-Level Status

| Capability | SillyTavern v1.17.0 | Candlekeep Core |
|------------|---------------------|-----------------|
| Vector database | Vectra (file-system JSON) | PostgreSQL + pgvector (upgradeable to vchord) |
| Embedding providers | 19 sources (local + cloud) | 2 adapters (Ollama + OpenAI-compatible) |
| Document ingestion | PDF, HTML, Markdown, EPUB, DOCX, XLSX, PPTX, ODT/ODP/ODS | Text-only (Data Bank manual entry) |
| Text chunking | Recursive delimiter-based with overlap | Recursive delimiter-based with overlap |
| Knowledge base (Data Bank) | Three-tier (global, character, chat) | Three-tier (global, character, chat) |
| Chat vectorization | Incremental hash-based sync | Hash-based dedup with async embedding |
| World Info vector activation | Semantic activation alongside keyword matching | Keyword-only activation engine (no vector path) |
| Prompt injection of RAG results | Two channels (chat memory + Data Bank) via extension prompts | Single `rag_context` component in prompt builder |
| Pipeline execution | Client-side (browser JavaScript) | Server-side (Python async service layer) |

---

## 2. Vector Storage

### SillyTavern

ST uses **Vectra** (`vectra` npm package v0.2.2), a lightweight file-system-based
vector index that stores collections as directories of JSON files on disk.

- Directory layout: `<user_data>/vectors/<source>/<collectionId>/<model>/`
- Switching embedding source or model creates a separate index (no automatic migration)
- Operations: upsert, query (top-K with score threshold), list, delete, purge
- Metadata per item: `{ hash, text, index }` (hash for dedup, text for retrieval, index for ordering)
- Corrupted index recovery: detects JSON parse errors, deletes index, retries with redirect

No support for external vector databases (Pinecone, Chroma, Weaviate, pgvector, etc.).

### Candlekeep Core

Candlekeep uses **pgvector**, the PostgreSQL vector extension, storing embeddings
directly in the same database as all other application data.

- Table: `embeddings` (SQLAlchemy model at `src/core/persistence/models/rag.py`)
- Vector column: `pgvector.sqlalchemy.Vector` with configurable dimensions
- Similarity search: cosine distance (`<=>` operator) with score threshold filtering
- Repository: `AsyncEmbeddingRepository` (`src/rag/repository_async.py`) with raw SQL
  for the vector query, standard SQLAlchemy for CRUD
- Metadata per row: `source_type`, `source_id`, `content_hash` (BigInteger for dedup),
  `content` (original text), `chunk_index`, `model_name`, `dimensions`
- Index scope filtering: queries filter on `source_type` and `source_id` arrays,
  allowing a single query to search across multiple collections (messages + data bank
  entries) simultaneously

The pgvector approach has several structural advantages over Vectra:

- No separate service -- vectors live in the same PostgreSQL instance, managed by
  Alembic migrations, backed up with the rest of the database
- SQL-level filtering -- WHERE clauses narrow the search space before the vector scan,
  rather than post-filtering results in application code
- Upgrade path to **vchord** (or other pgvector-compatible extensions) for HNSW/IVFFlat
  indexing without changing application code

### Comparison

| Aspect | ST (Vectra) | Candlekeep (pgvector) |
|--------|-------------|----------------------|
| Storage format | JSON files on disk | PostgreSQL rows |
| Scaling | Single-user local files | Connection-pooled database |
| Multi-collection query | Sequential loop over collections | Single SQL query with array filters |
| Index types | Flat (brute-force) | Flat; upgradeable to HNSW/IVFFlat |
| Backup/migration | Manual file copy | Standard database backup tooling |
| Cross-model migration | None (separate dirs per model) | Delete + re-embed (tracked by `model_name`) |

---

## 3. Embedding Providers

### SillyTavern

19 embedding sources, most wrapping OpenAI-compatible `/embeddings` endpoints:

| Category | Providers |
|----------|-----------|
| Local (zero-config) | `transformers` (ONNX via sillytavern-transformers, default `Xenova/all-mpnet-base-v2`) |
| Local (user-hosted) | `ollama`, `llamacpp`, `vllm`, `koboldcpp` |
| Cloud (API key) | `openai`, `mistral`, `togetherai`, `cohere`, `nomicai`, `palm`, `vertexai`, `electronhub`, `openrouter`, `chutes`, `nanogpt`, `siliconflow` |
| Browser-side | `webllm` (WebLLM WASM), `koboldcpp` (client fetch) |
| Legacy | `extras` (ST-Extras server) |

Notable details:
- Batching: 10 items server-side, 5 client-side (1 for transformers/ollama)
- Cohere passes `input_type` for asymmetric embeddings (search_query vs. search_document)
- Two providers compute embeddings in-browser and send pre-computed vectors to backend

### Candlekeep Core

Two embedding adapters in `EmbeddingService` (`src/rag/embedding_service.py`):

| Adapter | API endpoint | Auth | Default model |
|---------|-------------|------|---------------|
| **Ollama** | `POST {ollama_url}/api/embed` | None (local) | `nomic-embed-text` |
| **OpenAI-compatible** | `POST {openai_url}/embeddings` | Bearer token via env var | User-configured |

The OpenAI-compatible adapter works with any provider that implements the standard
`/v1/embeddings` contract (OpenAI, Mistral, TogetherAI, vLLM, LiteLLM, etc.),
meaning the 2-adapter architecture covers substantially more than 2 providers in
practice.

Configuration via `EmbeddingSettings` in `src/core/config.py`:
- `provider`: `"ollama"` or `"openai"` (selects the adapter)
- `model`: embedding model name
- `dimensions`: vector dimensions (default 768)
- `ollama_url`: Ollama server URL (default `http://localhost:11434`)
- `openai_url`: OpenAI-compatible base URL (default `https://api.openai.com/v1`)
- `openai_key_env`: environment variable name holding the API key

Batching: 10 items per batch for both adapters (constant `BATCH_SIZE` in
`embedding_service.py`).

### Comparison

| Aspect | ST | Candlekeep |
|--------|-----|-----------|
| Named providers | 19 | 2 (Ollama + OpenAI-compatible) |
| Effective provider coverage | 19 | Most of the same providers via OpenAI-compatible adapter |
| Zero-config local option | Yes (ONNX `all-mpnet-base-v2`) | Requires running Ollama |
| Browser-side embedding | Yes (WebLLM, KoboldCpp) | No (server-side only) |
| Asymmetric embedding support | Cohere only | Not yet |
| Provider-specific quirks | Handled per-adapter (9 backend files) | Minimal -- two clean adapters |

The breadth gap is real but narrow in practice: most of ST's 19 sources use the
OpenAI-compatible protocol, which Candlekeep's single OpenAI adapter already handles.
The main gap is the lack of a zero-config local option -- Candlekeep requires either
Ollama or an API key, while ST can run ONNX embeddings in-process with no setup.

---

## 4. Document Processing and Text Chunking

### SillyTavern

Supported file types via client-side and server-side converters:

| Format | Converter |
|--------|-----------|
| PDF | pdf.js (client-side) |
| HTML | DOMParser + DOMPurify |
| Markdown | Simple text post-processing |
| EPUB | epub.js (client-side) |
| DOCX, XLSX, PPTX | Server plugin (`/api/plugins/office/probe`) |
| ODT, ODP, ODS | Server plugin |
| Plain text (.txt, .json, .csv) | Stored as-is |

Max file size: 350 MB.

**Text chunking** uses `splitRecursive`, a recursive delimiter-based algorithm:
- Delimiter chain: `['\n\n', '\n', ' ', '']` (paragraph, line, word, character)
- Custom chunk boundary delimiter can be prepended
- Chunk overlap: symmetric, trimmed to sentence boundaries
- Overlap formula: `chunk_size * overlap_percent / 100`, split evenly between prev/next chunk tails

Optional: translate files to English before chunking (via Chat Translation extension).

### Candlekeep Core

**Document ingestion is text-only.** Data Bank entries are created via the REST API
with plain text content -- there is no file upload or format conversion pipeline.
Adding file processing (PDF, EPUB, etc.) is a future enhancement.

**Text chunking** uses `chunk_text()` (`src/rag/chunker.py`), a recursive
delimiter-based splitter structurally similar to ST's `splitRecursive`:
- Delimiter chain: `['\n\n', '\n', '. ', ' ']` (paragraph, line, sentence, word)
- Character-level fallback for text that cannot be split by any delimiter
- Small-chunk merging: adjacent chunks that fit within `max_size` are combined
- Overlap: tail of previous chunk prepended to current chunk

Configurable parameters (via `RAGSettings`):
- `chunk_size`: max characters per chunk (default 500)
- `chunk_overlap`: overlap characters from previous chunk (default 50)

### Comparison

| Aspect | ST | Candlekeep |
|--------|-----|-----------|
| File format support | 10+ formats (PDF, EPUB, DOCX, etc.) | Text-only (no file processing) |
| Chunking algorithm | Recursive delimiter-based | Recursive delimiter-based |
| Delimiter chain | `\n\n`, `\n`, ` `, `""` | `\n\n`, `\n`, `. `, ` ` |
| Chunk overlap | Symmetric (prev tail + next head), sentence-trimmed | Previous-tail only, character-based |
| Max file size | 350 MB | N/A (text input only) |
| Translation before chunking | Yes (optional) | No |

The chunking algorithms are functionally equivalent. ST's sentence-boundary trimming
on overlaps is slightly more sophisticated, while Candlekeep's `. ` delimiter
provides a sentence-aware split step that ST lacks. The significant gap is document
ingestion: Candlekeep cannot process binary file formats.

---

## 5. Data Bank (Knowledge Base)

### SillyTavern

Three-tier attachment system with different scopes:

| Scope | Availability | Storage location |
|-------|-------------|-----------------|
| Global | All characters, all chats | `extension_settings.attachments` |
| Character | One character, all its chats | `extension_settings.character_attachments[avatar]` |
| Chat | Current chat only | `chat_metadata.attachments` |

Ingestion sources:
- Direct file upload (drag & drop or file picker)
- Fandom wiki scraping (all articles, with regex filtering)
- MediaWiki scraping (any instance)
- Web scraping (arbitrary URLs)
- YouTube transcripts (by URL or video ID)
- Manual text entry (Notepad)

Files can be individually enabled/disabled without deletion. Managed via slash commands
(`/db`, `/db-list`, `/db-get`, `/db-add`, `/db-update`, `/db-delete`, `/db-search`, etc.).

### Candlekeep Core

Three-tier Data Bank with the same scoping model, implemented as a relational entity:

| Scope | Availability | Storage |
|-------|-------------|---------|
| Global | All characters, all chats | `DataBankEntry` row with `scope='global'` |
| Character | One character, all its chats | `DataBankEntry` row with `scope='character'`, FK to `characters.id` |
| Chat | Current chat only | `DataBankEntry` row with `scope='chat'`, FK to `chats.id` |

Model: `DataBankEntry` (`src/core/persistence/models/rag.py`)
- Fields: `id`, `name`, `content`, `scope`, `character_id` (nullable FK),
  `chat_id` (nullable FK), `created_at`, `updated_at`
- Cascade deletes: deleting a character or chat removes associated entries

CRUD via REST API (`src/rag/router.py`, prefix `/api/data-bank`):
- `GET /` -- list entries with optional `scope`, `character_id`, `chat_id` filters
- `POST /` -- create entry
- `GET /{id}` -- get by ID
- `PUT /{id}` -- update
- `DELETE /{id}` -- delete

Service layer: `DataBankService` (`src/rag/service.py`) -- standard CRUD with
synchronous database access through `DataBankRepository` (`src/rag/repository.py`).

Ingestion: text content only, supplied via the API. No file upload, web scraping,
wiki scraping, or YouTube transcript extraction.

### Comparison

| Aspect | ST | Candlekeep |
|--------|-----|-----------|
| Scope tiers | 3 (global, character, chat) | 3 (global, character, chat) |
| Storage | JSON settings files | PostgreSQL with foreign keys |
| Ingestion sources | 6 (file, Fandom, MediaWiki, web, YouTube, notepad) | 1 (API text entry) |
| Enable/disable without deletion | Yes | Not yet |
| Cascade delete on parent removal | No (orphaned metadata) | Yes (FK `ON DELETE CASCADE`) |
| Pydantic validation on input | No (JS object) | Yes (`DataBankCreate` schema) |

The scoping model is equivalent. Candlekeep's relational storage provides referential
integrity (cascade deletes, indexed foreign keys) that ST's JSON-in-settings approach
lacks. ST has far richer ingestion sources.

---

## 6. Chat Vectorization

### SillyTavern

Incremental chat message vectorization for "memory recall" -- retrieving semantically
relevant past messages that have scrolled out of the context window.

Process (`synchronizeChat()`):
1. Hash each non-system message text
2. Compare hashes against Vectra collection (keyed by chat ID)
3. Insert new messages, delete orphaned ones
4. Optional: summarize messages before embedding (via Main API, Extras, or WebLLM)
5. Optional: chunk messages by `message_chunk_size` (default 400 chars)

Triggered on a debounced schedule whenever messages are sent, received, edited,
deleted, or swiped. "Vectorize All" button available for full re-indexing.

Configurable parameters:
- `query`: number of recent messages to form the search query (default 2)
- `insert`: number of past messages to retrieve (default 3)
- `protect`: last N messages exempt from rearrangement (default 5)
- `score_threshold`: cosine similarity cutoff (default 0.25)

### Candlekeep Core

Message vectorization via `RetrievalService.vectorize_message()`
(`src/rag/retrieval_service.py`):

1. Compute a deterministic 64-bit SHA-256 hash of the message content
2. Check if an embedding with that hash already exists (`exists_by_hash`)
3. If new, embed the message text and store an `Embedding` row with
   `source_type='message'` and `source_id=message_id`

Retrieval via `RetrievalService.retrieve()`:
1. Embed the query text
2. Run a pgvector cosine similarity search across `source_types=['message', 'data_bank']`
   and relevant `source_ids` (chat ID + data bank entry IDs for the active scopes)
3. Filter by `threshold` (default 0.3), return top-K results

Configuration (`RAGSettings` in `src/core/config.py`):
- `vectorize_messages`: toggle message embedding (default True)
- `query_messages`: number of recent messages for query construction (default 2)
- `max_results`: top-K limit (default 5)
- `similarity_threshold`: cosine similarity cutoff (default 0.3)

### Comparison

| Aspect | ST | Candlekeep |
|--------|-----|-----------|
| Dedup strategy | Hash-based (string hash) | Hash-based (SHA-256 truncated to 64 bits) |
| Orphan cleanup | Deletes vectors for removed messages | `delete_by_source` available, not auto-triggered |
| Pre-embed summarization | Yes (3 backends) | Not yet |
| Message chunking | Optional (400 char default) | Not yet (whole message embedded) |
| Query construction | Last N messages, configurable | Last N messages, configurable |
| Protected messages | Yes (last 5 exempt from rearrangement) | Not yet |
| Trigger mechanism | Debounced on every message event | Callable from service layer |

Both systems use hash-based dedup to avoid re-embedding unchanged messages.
ST's implementation is more mature with summarization, message chunking, and
protected-message handling. Candlekeep's version covers the core embed-store-retrieve
loop.

---

## 7. Query Pipeline and Prompt Injection

### SillyTavern

Triggered before every LLM generation (except quiet prompts) via the
`generate_interceptor` manifest hook.

Full flow:
1. Process Data Bank files -- ingest any un-vectorized attachments, query all
   Data Bank collections, inject results via `setExtensionPrompt(TAG_DB)`
2. Process message attachments -- vectorize inline file attachments, prepend
   retrieved chunks to the message text
3. Activate World Info -- vectorize WI entries per-world, query, emit
   `WORLDINFO_FORCE_ACTIVATE` for matches
4. Chat memory retrieval -- build query from last N messages, query chat collection,
   filter out protected messages, inject via `setExtensionPrompt(TAG)`

Two injection channels:
- `3_vectors` -- chat memory results (default template: `"Past events:\n{{text}}"`)
- `4_vectors_data_bank` -- Data Bank results (default template: `"Related information:\n{{text}}"`)

Injection position is configurable: before main prompt, after main prompt, or
in-chat at a specific depth. Role configurable for Data Bank (system/user/assistant).

### Candlekeep Core

RAG results are integrated into the prompt via the `rag_context` component in
`PromptBuilder.build_api_messages()` (`src/prompt_template/prompt_builder.py`).

Flow:
1. Caller passes `rag_results` (list of `RetrievedChunk` objects) to `build_api_messages()`
2. `_build_rag_context()` formats results as a system message:
   `"Relevant context from previous conversations and knowledge:\n"` followed by
   chunk contents joined with `\n---\n` separators
3. The `rag_context` component is placed in the prompt's component order, positioned
   after example dialogues and before chat history by default

The component order is configurable per `PromptTemplate` via `component_order` and
`components_enabled`, allowing `rag_context` to be repositioned or disabled.

Additionally, manual semantic search is exposed via the REST API:
- `POST /api/rag/search` -- query with text, optional scope filters, configurable
  threshold and max results
- `GET /api/rag/status` -- returns current RAG configuration (provider, model,
  dimensions, chunk settings, threshold)

### Comparison

| Aspect | ST | Candlekeep |
|--------|-----|-----------|
| Injection channels | 2 (chat memory + Data Bank, separate templates) | 1 (unified `rag_context` component) |
| Injection position | Configurable (before/after main prompt, in-chat at depth) | Configurable via template component ordering |
| Role control | Configurable per channel (system/user/assistant) | System role only |
| Template customization | Per-channel templates with `{{text}}` placeholder | Fixed format in `_build_rag_context()` |
| Trigger | Automatic on every generation | Caller-driven (service layer passes results) |
| Manual search API | `/db-search` slash command | `POST /api/rag/search` REST endpoint |

ST's injection system is more configurable (per-channel templates, role selection,
depth control). Candlekeep's approach is simpler -- a single prompt component in the
template pipeline -- but benefits from the template system's existing component ordering
and enable/disable mechanism.

---

## 8. World Info Vector Activation

### SillyTavern

Dual activation: keyword matching AND optional semantic search. When "Enable for
World Info" is checked:

1. WI entries are vectorized into per-world collections (`world_<hash(name)>`)
2. Chat text is used as query against all world collections
3. Matching entries are force-activated via `WORLDINFO_FORCE_ACTIVATE` event
4. Configurable: activate all entries or only entries marked "vectorized"
5. Max entries cap (default 5)

This runs alongside the standard keyword activation -- semantic matches supplement
keyword matches rather than replacing them.

### Candlekeep Core

Keyword/regex activation only. The lore activation engine
(`src/lore/activation_engine.py`) implements:
- Primary key matching (keyword or regex, with case sensitivity and whole-word options)
- Secondary key matching (AND/NOT logic)
- Priority-based ordering with token budget management
- No semantic search path

The RAG infrastructure (embedding service, pgvector search) is now in place, so
adding a vector activation channel alongside the keyword engine would be an additive
change -- vectorize lore entries into the existing `embeddings` table with
`source_type='lore'`, query during activation, merge results with keyword matches.
The activation engine itself would not need reworking.

---

## 9. Configuration Surface

### SillyTavern

Extensive settings object with ~40 parameters covering:
- Embedding source selection and per-source model names
- Chat vectorization (enable, query count, insert count, protect count, chunk size, threshold)
- File vectorization (enable, size threshold, chunk size/count, overlap percent)
- Data Bank files (size threshold, chunk size/count, overlap, template, position, depth, role)
- World Info vectorization (enable, enable-for-all, max entries)
- Summarization (enable, source, prompt)
- Runtime slash commands for threshold, query count, max entries, and feature toggles

### Candlekeep Core

Two Pydantic settings models in `src/core/config.py`:

**`EmbeddingSettings`** (nested in `RAGSettings.embedding`):
- `provider` -- `"ollama"` or `"openai"`
- `model` -- embedding model name (default `nomic-embed-text`)
- `dimensions` -- vector dimensions (default 768)
- `ollama_url` -- Ollama endpoint (default `http://localhost:11434`)
- `openai_url` -- OpenAI-compatible endpoint (default `https://api.openai.com/v1`)
- `openai_key_env` -- env var name for API key

**`RAGSettings`** (at `settings.rag`):
- `enabled` -- master toggle (default False)
- `embedding` -- nested `EmbeddingSettings`
- `chunk_size` -- characters per chunk (default 500)
- `chunk_overlap` -- overlap characters (default 50)
- `similarity_threshold` -- cosine similarity cutoff (default 0.3)
- `max_results` -- top-K limit (default 5)
- `query_messages` -- recent messages for query construction (default 2)
- `vectorize_messages` -- toggle message embedding (default True)

All settings are configurable via environment variables using the
`env_nested_delimiter="__"` convention (e.g., `RAG__EMBEDDING__MODEL=text-embedding-3-small`).

Runtime status endpoint: `GET /api/rag/status` returns the active configuration.

### Comparison

| Aspect | ST | Candlekeep |
|--------|-----|-----------|
| Total parameters | ~40 | ~12 |
| Per-provider model config | Yes (13 provider-specific model fields) | Single `model` field |
| File processing settings | Yes (size threshold, chunk size/count, overlap) | N/A (no file processing) |
| World Info vectorization settings | Yes (enable, enable-for-all, max entries) | N/A (no WI vectorization) |
| Summarization settings | Yes (enable, source, prompt) | N/A (no summarization) |
| Configuration method | JSON settings file + slash commands | Environment variables + Pydantic validation |
| Type validation | JavaScript runtime checks | Pydantic model validation at startup |

Candlekeep's configuration surface is smaller because the feature set is smaller.
The Pydantic-based approach provides startup-time validation and type safety that
ST's plain JSON settings do not.

---

## 10. Summary

### What Both Systems Have

- Recursive delimiter-based text chunking with overlap
- Three-tier Data Bank scoping (global, character, chat)
- Hash-based dedup for message vectorization
- Configurable similarity threshold and top-K retrieval
- RAG context injection into the LLM prompt

### Where SillyTavern Leads

| Area | Detail |
|------|--------|
| Embedding provider breadth | 19 named sources vs. 2 adapters |
| Zero-config local embeddings | ONNX in-process, no external service needed |
| Document ingestion | 10+ file formats, web/wiki scraping, YouTube transcripts |
| World Info vector activation | Semantic search supplements keyword matching |
| Chat vectorization maturity | Summarization, message chunking, protected messages |
| Injection configurability | Per-channel templates, role selection, depth control |

### Where Candlekeep Core Leads

| Area | Detail |
|------|--------|
| Vector database | PostgreSQL + pgvector (SQL-level filtering, HNSW-upgradeable, standard backups) vs. Vectra (flat JSON files) |
| Multi-collection search | Single SQL query across message + data bank vectors vs. sequential collection iteration |
| Pipeline architecture | Fully server-side (Python async) vs. split between browser JS and Express backend |
| Data integrity | Foreign keys with cascade deletes, Alembic-managed schema vs. JSON settings metadata |
| Type safety | Pydantic schemas + BasedPyright across the full pipeline vs. untyped JavaScript objects |
| Configuration validation | Pydantic model validation at startup vs. runtime JS checks |

### Remaining Gaps

| Component | Status | Notes |
|-----------|--------|-------|
| File format processing | Not implemented | PDF, EPUB, DOCX ingestion would require adding extraction libraries |
| Web/wiki scraping | Not implemented | ST's Fandom, MediaWiki, and URL scraping have no equivalent |
| World Info vector activation | Not implemented | Infrastructure is in place; requires wiring lore entries into the embedding pipeline |
| Pre-embed summarization | Not implemented | Would reduce embedding costs for long messages |
| Message chunking | Not implemented | Long messages are embedded whole rather than chunked |
| Entry enable/disable toggle | Not implemented | Data Bank entries can only be created or deleted |
| Browser-side embedding | N/A | Server-side architecture by design; not a gap, a different model |
