# RAG Pipeline — SillyTavern v1.17.0 vs The Bannered Mare

This page assumes the [RAG Analysis](/sillytavern/analysis/rag) for how SillyTavern works
internally, and focuses on where The Bannered Mare diverges and why. Both systems now have
functional RAG pipelines, though on different architectural foundations — a file-system index
versus the application's own database:

<Figure tag="Figure 1" title="Vectra files vs VectorChord in Postgres" id="fig-cmp-rag">
<svg viewBox="0 0 760 262" role="img" aria-label="SillyTavern vs The Bannered Mare RAG" style="font-family:var(--vp-font-family-base)">
  <rect x="24" y="16" width="344" height="230" rx="12" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <rect x="392" y="16" width="344" height="230" rx="12" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <rect x="24" y="16" width="344" height="44" rx="12" fill="var(--tbm-dgm-provider-soft)"/><rect x="24" y="36" width="344" height="24" fill="var(--tbm-dgm-provider-soft)"/>
  <rect x="392" y="16" width="344" height="44" rx="12" fill="var(--tbm-dgm-backend-soft)"/><rect x="392" y="36" width="344" height="24" fill="var(--tbm-dgm-backend-soft)"/>
  <text x="196" y="44" text-anchor="middle" font-size="13" font-weight="800" fill="var(--tbm-dgm-ink)">SillyTavern v1.17.0</text>
  <text x="564" y="44" text-anchor="middle" font-size="13" font-weight="800" fill="var(--tbm-dgm-ink)">The Bannered Mare</text>
  <g font-size="10.5" fill="var(--tbm-dgm-ink)">
    <text x="40" y="90">Store — Vectra (file-system JSON index)</text>
    <text x="40" y="122">Embeddings — 19 sources (local + cloud)</text>
    <text x="40" y="154">Ingestion — PDF · HTML · EPUB · DOCX · …</text>
    <text x="40" y="186">Runs — client-side (browser)</text>
    <text x="40" y="222" fill="var(--tbm-dgm-ink-2)">Broad ingestion, portable files</text>
    <text x="408" y="90">Store — PostgreSQL + VectorChord (vchordrq)</text>
    <text x="408" y="122">Embeddings — 4 adapters (llama.cpp · OpenAI · Ollama · TEI)</text>
    <text x="408" y="154">Ingestion — text (Data Bank manual entry)</text>
    <text x="408" y="186">Runs — server-side async service</text>
    <text x="408" y="222" fill="var(--tbm-dgm-ink-2)">One store for data + vectors</text>
  </g>
</svg>
<template #caption>

**Same three-tier Data Bank, different substrate.** SillyTavern indexes into per-source Vectra
directories on disk; The Bannered Mare keeps embeddings in the same PostgreSQL database as
everything else, so a single query can span messages and Data Bank entries.

</template>
</Figure>

## 1. High-Level Status

| Capability | SillyTavern v1.17.0 | The Bannered Mare |
|------------|---------------------|-----------------|
| Vector database | Vectra (file-system JSON) | PostgreSQL + VectorChord (vchordrq index, on pgvector) |
| Embedding providers | 19 sources (local + cloud) | 4 adapters (llama.cpp, OpenAI-compatible, Ollama, HF TEI) |
| Asymmetric embeddings | Cohere only | Yes (query/document prompt prefixes; default EmbeddingGemma) |
| Reranking | Not built-in | Optional cross-encoder reranker over HF TEI (off by default) |
| Document ingestion | PDF, HTML, Markdown, EPUB, DOCX, XLSX, PPTX, ODT/ODP/ODS | Text-only (Data Bank manual entry) |
| Text chunking | Recursive delimiter-based with overlap | Recursive delimiter-based with overlap |
| Knowledge base (Data Bank) | Three-tier (global, character, chat) | Three-tier (global, character, chat) |
| Chat vectorization | Incremental hash-based sync | Hash-based dedup with async embedding |
| World Info vector activation | Semantic activation alongside keyword matching | Keyword-only activation engine (no vector path) |
| Prompt injection of RAG results | Two channels (chat memory + Data Bank) via extension prompts | Single `rag_context` component in prompt builder |
| Pipeline execution | Client-side (browser JavaScript) | Server-side (Python async service layer) |


## 2. Vector Storage

SillyTavern stores vectors in **Vectra** (`vectra` npm package), a file-system index that keeps
each collection as a directory of JSON files (`<user_data>/vectors/<source>/<collectionId>/<model>/`),
with no support for external vector databases ([Analysis §2 ›](/sillytavern/analysis/rag#_2-vector-storage-backend)).

**The Bannered Mare** uses **VectorChord** (the `vchord` extension, built on pgvector's `vector`
type), storing embeddings directly in the same database as all other application data.

- Table: `embeddings` (SQLAlchemy model at `src/core/persistence/models/rag.py`)
- Vector column: `pgvector.sqlalchemy.Vector(768)` — dimension pinned, since the vchordrq
  index requires a fixed-dimension column
- Index: `ix_embeddings_vchordrq` — a flat VectorChord **vchordrq** RaBitQ index, built via
  `vchordrq (embedding vector_cosine_ops)` with `residual_quantization = true`
- Similarity search: cosine distance (`<=>` operator) as `ORDER BY ... LIMIT` — the shape the
  vchordrq index accelerates — with a score-threshold floor
- Repository: `AsyncEmbeddingRepository` (`src/rag/repository_async.py`) with raw SQL for the
  vector query and standard SQLAlchemy for CRUD; optional `vchordrq.epsilon` /
  `vchordrq.max_scan_tuples` tuning is applied per search
- Metadata per row: `source_type`, `source_id`, `content_hash` (BigInteger for dedup),
  `content` (original text), `chunk_index`, `model_name`, `dimensions`
- Index scope filtering: queries filter on `source_type` and `source_id` arrays,
  allowing a single query to search across multiple collections (messages + data bank
  entries) simultaneously

The VectorChord approach has several structural advantages over Vectra:

- No separate service -- vectors live in the same PostgreSQL instance, managed by
  Alembic migrations, backed up with the rest of the database
- SQL-level filtering -- WHERE clauses narrow the result set alongside the vector scan,
  rather than post-filtering results in application code
- The flat RaBitQ index scales to IVF partitioning (`vchordrq` `lists`) for larger datasets
  without changing application code

| Aspect | ST (Vectra) | The Bannered Mare (VectorChord) |
|--------|-------------|----------------------|
| Storage format | JSON files on disk | PostgreSQL rows |
| Scaling | Single-user local files | Connection-pooled database |
| Multi-collection query | Sequential loop over collections | Single SQL query with array filters |
| Index types | Flat (brute-force) | Flat RaBitQ (vchordrq); upgradeable to IVF `lists` |
| Backup/migration | Manual file copy | Standard database backup tooling |
| Cross-model migration | None (separate dirs per model) | Delete + re-embed (tracked by `model_name`) |


## 3. Embedding Providers

SillyTavern offers 19 embedding sources — mostly OpenAI-compatible `/embeddings` wrappers, plus a
zero-config in-process ONNX option and two browser-side embedders — with per-source batching quirks
([Analysis §3 ›](/sillytavern/analysis/rag#_3-embedding-providers)).

**The Bannered Mare** exposes four embedding adapters in `EmbeddingService`
(`src/rag/embedding_service.py`), selected by the `provider` setting:

| Adapter | `provider` value | API endpoint | Auth | Notes |
|---------|------------------|--------------|------|-------|
| **llama.cpp** (default) | `llamacpp` | `POST {llamacpp_url}/v1/embeddings` | None (local) | Default provider; llama-server's OpenAI-compatible route |
| **OpenAI-compatible** | `openai` | `POST {openai_url}/embeddings` | Bearer token via env var | OpenAI, Mistral, TogetherAI, vLLM, LiteLLM, etc. |
| **Ollama** | `ollama` | `POST {ollama_url}/api/embed` | None (local) | Ollama's native embed endpoint |
| **HF TEI** | `huggingface` | `POST {huggingface_url}/embed` | None (local) | Text Embeddings Inference native dialect (`inputs` key, bare list response) |

The `llamacpp` and `openai` adapters both speak the standard `/v1/embeddings`
contract, so the four-adapter architecture covers substantially more than four
providers in practice.

**Asymmetric embeddings.** The default model is **EmbeddingGemma**, which is
asymmetric: queries and documents are embedded with different prompt prefixes.
`EmbeddingService` exposes `embed_query()` and `embed_documents()`, applying the
configured `query_prefix` / `document_prefix` respectively.

Configuration via `EmbeddingSettings` in `src/core/config.py`:
- `provider`: `"llamacpp"` (default), `"openai"`, `"ollama"`, or `"huggingface"`
- `model`: embedding model name (default `embeddinggemma`)
- `dimensions`: vector dimensions (default 768)
- `llamacpp_url`: llama.cpp server URL (default `http://localhost:8080`)
- `huggingface_url`: HF TEI server URL (default `http://localhost:8080`)
- `ollama_url`: Ollama server URL (default `http://localhost:11434`)
- `openai_url`: OpenAI-compatible base URL (default `https://api.openai.com/v1`)
- `openai_key_env`: environment variable name holding the API key
- `query_prefix` / `document_prefix`: asymmetric-embedding prompt prefixes

Batching: 10 items per batch for all adapters (constant `BATCH_SIZE` in
`embedding_service.py`).

| Aspect | ST | The Bannered Mare |
|--------|-----|-----------|
| Named providers | 19 | 4 (llama.cpp, OpenAI-compatible, Ollama, HF TEI) |
| Effective provider coverage | 19 | Most of the same providers via the OpenAI-compatible adapter |
| Zero-config local option | Yes (ONNX `all-mpnet-base-v2`) | Requires running llama.cpp, Ollama, or TEI |
| Browser-side embedding | Yes (WebLLM, KoboldCpp) | No (server-side only) |
| Asymmetric embedding support | Cohere only | Yes (query/document prompt prefixes; default EmbeddingGemma) |
| Provider-specific quirks | Handled per-adapter (9 backend files) | Minimal -- four clean adapters |

The breadth gap is real but narrow in practice: most of ST's 19 sources use the
OpenAI-compatible protocol, which The Bannered Mare's `llamacpp`/`openai` adapters
already handle. The main gap is the lack of a zero-config local option -- The Bannered
Mare requires running llama.cpp, Ollama, or a TEI server (or supplying an API key),
while ST can run ONNX embeddings in-process with no setup.


## 4. Document Processing and Text Chunking

SillyTavern ingests 10+ file formats (PDF, HTML, Markdown, EPUB, DOCX/XLSX/PPTX,
ODT/ODP/ODS, up to 350 MB) and chunks with `splitRecursive` — a recursive delimiter chain
(`\n\n`, `\n`, ` `, `""`) with sentence-trimmed symmetric overlap ([Analysis §4 ›](/sillytavern/analysis/rag#_4-document-processing)).

**The Bannered Mare's** document ingestion is **text-only**. Data Bank entries are created via
the REST API with plain text content -- there is no file upload or format conversion pipeline.
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

| Aspect | ST | The Bannered Mare |
|--------|-----|-----------|
| File format support | 10+ formats (PDF, EPUB, DOCX, etc.) | Text-only (no file processing) |
| Chunking algorithm | Recursive delimiter-based | Recursive delimiter-based |
| Delimiter chain | `\n\n`, `\n`, ` `, `""` | `\n\n`, `\n`, `. `, ` ` |
| Chunk overlap | Symmetric (prev tail + next head), sentence-trimmed | Previous-tail only, character-based |
| Max file size | 350 MB | N/A (text input only) |
| Translation before chunking | Yes (optional) | No |

The chunking algorithms are functionally equivalent. ST's sentence-boundary trimming
on overlaps is slightly more sophisticated, while The Bannered Mare's `. ` delimiter
provides a sentence-aware split step that ST lacks. The significant gap is document
ingestion: The Bannered Mare cannot process binary file formats.


## 5. Data Bank (Knowledge Base)

SillyTavern's Data Bank is a three-tier attachment system (global / character / chat, stored in
settings and chat metadata) fed by six ingestion sources — file upload, Fandom, MediaWiki, web
scraping, YouTube transcripts, and manual notepad entry — managed via `/db*` slash commands
([Analysis §5 ›](/sillytavern/analysis/rag#_5-data-bank)).

**The Bannered Mare** keeps the same three-tier scoping model, implemented as a relational entity:

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

| Aspect | ST | The Bannered Mare |
|--------|-----|-----------|
| Scope tiers | 3 (global, character, chat) | 3 (global, character, chat) |
| Storage | JSON settings files | PostgreSQL with foreign keys |
| Ingestion sources | 6 (file, Fandom, MediaWiki, web, YouTube, notepad) | 1 (API text entry) |
| Enable/disable without deletion | Yes | Not yet |
| Cascade delete on parent removal | No (orphaned metadata) | Yes (FK `ON DELETE CASCADE`) |
| Pydantic validation on input | No (JS object) | Yes (`DataBankCreate` schema) |

The scoping model is equivalent. The Bannered Mare's relational storage provides referential
integrity (cascade deletes, indexed foreign keys) that ST's JSON-in-settings approach
lacks. ST has far richer ingestion sources.


## 6. Chat Vectorization

SillyTavern's `synchronizeChat()` incrementally vectorizes chat messages for memory recall —
hash-diffing against the Vectra collection, optionally summarizing and chunking before embedding,
triggered on a debounced schedule with configurable query/insert/protect/threshold parameters
([Analysis §6 ›](/sillytavern/analysis/rag#_6-chat-vectorization-smart-context)).

**The Bannered Mare** vectorizes messages via `RetrievalService.vectorize_message()`
(`src/rag/retrieval_service.py`):

1. Compute a deterministic 63-bit SHA-256 hash of the message content (masked to fit the signed `BIGINT` column)
2. Check if an embedding with that hash already exists (`exists_by_hash`)
3. If new, embed the message text and store an `Embedding` row with
   `source_type='message'` and `source_id=message_id`

Retrieval via `RetrievalService.retrieve()`:
1. Embed the query text (with the asymmetric query prefix)
2. Run a VectorChord (vchordrq) cosine similarity search across `source_types=['message', 'data_bank']`
   and relevant `source_ids` (chat ID + data bank entry IDs for the active scopes)
3. Filter by `threshold` (default 0.3), return top-K results

**Optional reranking.** When `RerankSettings.enabled` is true (off by default), the
retriever casts a wider net -- it pulls up to `candidates` (default 30) vector hits
with the vector similarity floor dropped to 0.0, then a cross-encoder reranker
(`RerankService`, an HF TEI `/rerank` model such as `BAAI/bge-reranker-v2-m3`)
reorders them. Hits scoring at least the reranker `score_threshold` are kept and cut
to `max_results`. A slow or down reranker never breaks retrieval -- it falls back to
the raw vector ranking.

Configuration (`RAGSettings` in `src/core/config.py`):
- `vectorize_messages`: toggle message embedding (default True)
- `query_messages`: number of recent messages for query construction (default 2)
- `max_results`: top-K limit (default 5)
- `similarity_threshold`: cosine similarity cutoff (default 0.3)

| Aspect | ST | The Bannered Mare |
|--------|-----|-----------|
| Dedup strategy | Hash-based (string hash) | Hash-based (SHA-256 masked to 63 bits) |
| Orphan cleanup | Deletes vectors for removed messages | `delete_by_source` available, not auto-triggered |
| Pre-embed summarization | Yes (3 backends) | Not yet |
| Message chunking | Optional (400 char default) | Not yet (whole message embedded) |
| Query construction | Last N messages, configurable | Last N messages, configurable |
| Protected messages | Yes (last 5 exempt from rearrangement) | Not yet |
| Trigger mechanism | Debounced on every message event | Callable from service layer |

Both systems use hash-based dedup to avoid re-embedding unchanged messages.
ST's implementation is more mature with summarization, message chunking, and
protected-message handling. The Bannered Mare's version covers the core embed-store-retrieve
loop.


## 7. Query Pipeline and Prompt Injection

SillyTavern runs its query pipeline before every generation (via a `generate_interceptor` hook),
walking a four-step flow — Data Bank, message attachments, World Info, chat memory — and injecting
results through two configurable channels (`3_vectors` chat memory and `4_vectors_data_bank`) with
position and role controls ([Analysis §7 ›](/sillytavern/analysis/rag#_7-query-pipeline), [§8 ›](/sillytavern/analysis/rag#_8-prompt-injection)).

**The Bannered Mare** integrates RAG results via the `rag_context` component in
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

| Aspect | ST | The Bannered Mare |
|--------|-----|-----------|
| Injection channels | 2 (chat memory + Data Bank, separate templates) | 1 (unified `rag_context` component) |
| Injection position | Configurable (before/after main prompt, in-chat at depth) | Configurable via template component ordering |
| Role control | Configurable per channel (system/user/assistant) | System role only |
| Template customization | Per-channel templates with `{{text}}` placeholder | Fixed format in `_build_rag_context()` |
| Trigger | Automatic on every generation | Caller-driven (service layer passes results) |
| Manual search API | `/db-search` slash command | `POST /api/rag/search` REST endpoint |

ST's injection system is more configurable (per-channel templates, role selection,
depth control). The Bannered Mare's approach is simpler -- a single prompt component in the
template pipeline -- but benefits from the template system's existing component ordering
and enable/disable mechanism.


## 8. World Info Vector Activation

SillyTavern supports dual activation for World Info — keyword matching plus optional semantic
search that vectorizes entries into per-world collections and force-activates matches via
`WORLDINFO_FORCE_ACTIVATE`, supplementing (not replacing) keyword hits ([Analysis §9 ›](/sillytavern/analysis/rag#_9-world-info-vector-integration)).

**The Bannered Mare** does keyword/regex activation only. The lore activation engine
(`src/lore/activation_engine.py`) implements:
- Primary key matching (keyword or regex, with case sensitivity and whole-word options)
- Secondary key matching (AND/NOT logic)
- Priority-based ordering with token budget management
- No semantic search path

The RAG infrastructure (embedding service, VectorChord search) is now in place, so
adding a vector activation channel alongside the keyword engine would be an additive
change -- vectorize lore entries into the existing `embeddings` table with
`source_type='lore'`, query during activation, merge results with keyword matches.
The activation engine itself would not need reworking.


## 9. Configuration Surface

SillyTavern exposes a ~40-parameter settings object plus runtime slash commands, covering
embedding source, chat/file/Data Bank vectorization, World Info vectorization, and summarization
([Analysis §10 ›](/sillytavern/analysis/rag#_10-settings-configuration)).

**The Bannered Mare** uses three Pydantic settings models in `src/core/config.py`:

**`EmbeddingSettings`** (nested in `RAGSettings.embedding`):
- `provider` -- `"llamacpp"` (default), `"openai"`, `"ollama"`, or `"huggingface"`
- `model` -- embedding model name (default `embeddinggemma`)
- `dimensions` -- vector dimensions (default 768)
- `llamacpp_url` -- llama.cpp endpoint (default `http://localhost:8080`)
- `huggingface_url` -- HF TEI endpoint (default `http://localhost:8080`)
- `ollama_url` -- Ollama endpoint (default `http://localhost:11434`)
- `openai_url` -- OpenAI-compatible endpoint (default `https://api.openai.com/v1`)
- `openai_key_env` -- env var name for API key
- `query_prefix` / `document_prefix` -- asymmetric-embedding prompt prefixes

**`RerankSettings`** (nested in `RAGSettings.rerank`):
- `enabled` -- master toggle for reranking (default False)
- `huggingface_url` -- TEI rerank endpoint (default `http://localhost:8091`)
- `model` -- reranker model, informational (default `BAAI/bge-reranker-v2-m3`)
- `candidates` -- wide-net vector-hit count fed to the reranker (default 30)
- `score_threshold` -- reranker relevance floor (default 0.3)

**`RAGSettings`** (at `settings.rag`):
- `enabled` -- master toggle (default False)
- `embedding` -- nested `EmbeddingSettings`
- `rerank` -- nested `RerankSettings`
- `chunk_size` -- characters per chunk (default 500)
- `chunk_overlap` -- overlap characters (default 50)
- `similarity_threshold` -- cosine similarity cutoff (default 0.3)
- `max_results` -- top-K limit (default 5)
- `query_messages` -- recent messages for query construction (default 2)
- `vectorize_messages` -- toggle message embedding (default True)

All settings are configurable via environment variables using the
`env_nested_delimiter="__"` convention (e.g., `RAG__EMBEDDING__MODEL=text-embedding-3-small`).

Runtime status endpoint: `GET /api/rag/status` returns the active configuration.

| Aspect | ST | The Bannered Mare |
|--------|-----|-----------|
| Total parameters | ~40 | ~22 |
| Per-provider model config | Yes (13 provider-specific model fields) | Single `model` field |
| File processing settings | Yes (size threshold, chunk size/count, overlap) | N/A (no file processing) |
| World Info vectorization settings | Yes (enable, enable-for-all, max entries) | N/A (no WI vectorization) |
| Summarization settings | Yes (enable, source, prompt) | N/A (no summarization) |
| Configuration method | JSON settings file + slash commands | Environment variables + Pydantic validation |
| Type validation | JavaScript runtime checks | Pydantic model validation at startup |

The Bannered Mare's configuration surface is smaller because the feature set is smaller.
The Pydantic-based approach provides startup-time validation and type safety that
ST's plain JSON settings do not.


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
| Embedding provider breadth | 19 named sources vs. 4 adapters |
| Zero-config local embeddings | ONNX in-process, no external service needed |
| Document ingestion | 10+ file formats, web/wiki scraping, YouTube transcripts |
| World Info vector activation | Semantic search supplements keyword matching |
| Chat vectorization maturity | Summarization, message chunking, protected messages |
| Injection configurability | Per-channel templates, role selection, depth control |

### Where The Bannered Mare Leads

| Area | Detail |
|------|--------|
| Vector database | PostgreSQL + VectorChord (flat vchordrq RaBitQ index, SQL-level filtering, standard backups) vs. Vectra (flat JSON files) |
| Multi-collection search | Single SQL query across message + data bank vectors vs. sequential collection iteration |
| Pipeline architecture | Fully server-side (Python async) vs. split between browser JS and Express backend |
| Data integrity | Foreign keys with cascade deletes, Alembic-managed schema vs. JSON settings metadata |
| Type safety | Pydantic schemas + BasedPyright across the full pipeline vs. untyped JavaScript objects |
| Configuration validation | Pydantic model validation at startup vs. runtime JS checks |
| Reranking | Optional cross-encoder reranker over HF TEI (`BAAI/bge-reranker-v2-m3`) vs. no built-in reranking |
| Asymmetric embeddings | First-class query/document prompt prefixes (EmbeddingGemma) vs. Cohere-only `input_type` |

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
