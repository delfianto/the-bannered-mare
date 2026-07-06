# SillyTavern v1.17.0 -- RAG Pipeline Analysis

This document analyzes SillyTavern's complete RAG (Retrieval-Augmented Generation) pipeline,
covering vector storage, embedding providers, document processing, the Data Bank, Smart Context
(chat vectorization), file attachments, and prompt injection.

Source revision: SillyTavern v1.17.0, tag `1.17.0`.


## 1. Architecture Overview

SillyTavern's RAG system is implemented as a **built-in extension** called "Vector Storage"
(`public/scripts/extensions/vectors/`). It is composed of:

| Layer | Location | Role |
|-------|----------|------|
| Frontend extension | `public/scripts/extensions/vectors/index.js` | Orchestration, chunking, prompt injection, UI |
| Backend API router | `src/endpoints/vectors.js` | Express router with CRUD + query endpoints |
| Embedding providers | `src/vectors/*.js` (9 files) | Adapters for embedding APIs |
| Local embeddings | `src/vectors/embedding.js` + `src/transformers.js` | ONNX-based local inference |
| Vector database | `vectra` npm package (v0.2.2) | File-system-based local vector index |
| Data Bank | `public/scripts/extensions/attachments/index.js` + `public/scripts/chats.js` | Knowledge base management |

The extension hooks into prompt generation via the manifest's `generate_interceptor` mechanism.
Before every LLM call, the framework calls `vectors_rearrangeChat(chat, contextSize, abort, type)`
which triggers the full RAG pipeline.

```
manifest.json:8  ->  "generate_interceptor": "vectors_rearrangeChat"
```


## 2. Vector Storage Backend

### 2.1 Vectra -- The Only Vector Database

SillyTavern uses exactly **one** vector database engine: **Vectra** (`vectra` npm package, `^0.2.2`).
There is no support for Pinecone, Chroma, Weaviate, pgvector, or any other external vector DB.

Vectra is a lightweight, file-system-based vector index written in JavaScript. Each collection is
stored as a directory of JSON files on disk.

**Index creation** (`src/endpoints/vectors.js`, lines 285-295):

```js
async function getIndex(directories, collectionId, source, sourceSettings) {
    const model = getModelScope(sourceSettings);
    const pathToFile = path.join(directories.vectors, sanitize(source), sanitize(collectionId), sanitize(model));
    const store = new vectra.LocalIndex(pathToFile);

    if (!await store.isIndexCreated()) {
        await store.createIndex();
    }

    return store;
}
```

The directory structure on disk is:

```
<user_data>/vectors/<source>/<collectionId>/<model>/
```

For example: `vectors/openai/file_abc123/text-embedding-3-small/`.

This means **switching embedding sources or models creates separate indexes** -- there is no
automatic migration between providers.

### 2.2 Operations

| Operation | Backend method | Vectra call |
|-----------|---------------|-------------|
| Insert | `insertVectorItems()` | `store.upsertItem({ vector, metadata: { hash, text, index } })` |
| Query | `queryCollection()` | `store.queryItems(vector, topK)` with post-filter on score threshold |
| Multi-query | `multiQueryCollection()` | Iterates collections, merges results, sorts by score descending |
| List hashes | `getSavedHashes()` | `store.listItems()` then extract `metadata.hash` |
| Delete | `deleteVectorItems()` | `store.listItemsByMetadata({ hash: { '$in': hashes } })` then delete |
| Purge collection | `/api/vector/purge` | `fs.promises.rm(sourcePath, { recursive: true })` |
| Purge all | `/api/vector/purge-all` | Deletes all source directories |

### 2.3 Metadata Schema

Every stored vector item carries this metadata:

```js
{
    hash: number,   // Hash of the original text (used as dedup key)
    text: string,   // The original chunk text
    index: number   // Position index (message index for chats, chunk index for files)
}
```

### 2.4 Corrupted Index Recovery

If a `SyntaxError` is caught during any vector operation, the backend assumes the Vectra JSON
index is corrupted. It deletes the index and redirects the request (HTTP 307) to retry with
`?regenerated=true` to prevent infinite loops (`src/endpoints/vectors.js`, lines 432-453).


## 3. Embedding Providers

SillyTavern supports **19 distinct embedding sources**. Most are thin wrappers around OpenAI-compatible
`/embeddings` endpoints.

### 3.1 Source Registry

Defined in `src/endpoints/vectors.js`, lines 22-42:

```js
const SOURCES = [
    'transformers', 'mistral', 'openai', 'extras', 'palm',
    'togetherai', 'nomicai', 'cohere', 'ollama', 'llamacpp',
    'vllm', 'webllm', 'koboldcpp', 'vertexai', 'electronhub',
    'openrouter', 'chutes', 'nanogpt', 'siliconflow',
];
```

### 3.2 Provider Details

| Source | Backend file | API type | Default model | Auth |
|--------|-------------|----------|---------------|------|
| **transformers** | `embedding.js` + `transformers.js` | Local ONNX (sillytavern-transformers) | `Xenova/all-mpnet-base-v2` | None |
| **openai** | `openai-vectors.js` | OpenAI `/v1/embeddings` | `text-embedding-ada-002` | API key |
| **mistral** | `openai-vectors.js` | OpenAI-compatible | `mistral-embed` | API key |
| **togetherai** | `openai-vectors.js` | OpenAI-compatible | `togethercomputer/m2-bert-80M-32k-retrieval` | API key |
| **cohere** | `cohere-vectors.js` | Cohere `/v2/embed` | `embed-english-v3.0` | API key |
| **nomicai** | `nomicai-vectors.js` | Nomic Atlas API | `nomic-embed-text-v1.5` | API key |
| **ollama** | `ollama-vectors.js` | Ollama `/api/embed` | User-configured (e.g. `mxbai-embed-large`) | None (local) |
| **llamacpp** | `llamacpp-vectors.js` | OpenAI-compatible `/v1/embeddings` | Server's loaded model | None (local) |
| **vllm** | `vllm-vectors.js` | OpenAI-compatible `/v1/embeddings` | User-configured | None (local) |
| **palm** (Google AI Studio) | `google-vectors.js` | Google `batchEmbedContents` | `text-embedding-005` | API key |
| **vertexai** | `google-vectors.js` | Vertex AI `predict` | `text-embedding-005` | Service account |
| **extras** | `extras-vectors.js` | ST-Extras `/api/embeddings/compute` | Server-configured | Optional API key |
| **webllm** | Client-side (WebLLM extension) | In-browser WASM | User-selected | None |
| **koboldcpp** | Client-side via `/api/backends/kobold/embed` | KoboldCpp native | Server's loaded model | None (local) |
| **electronhub** | `openai-vectors.js` | OpenAI-compatible | `text-embedding-3-small` | API key |
| **openrouter** | `openai-vectors.js` | OpenAI-compatible | `openai/text-embedding-3-large` | API key |
| **chutes** | `openai-vectors.js` | OpenAI-compatible | `chutes-qwen-qwen3-embedding-8b` | API key |
| **nanogpt** | `openai-vectors.js` | OpenAI-compatible | `text-embedding-3-small` | API key |
| **siliconflow** | `openai-vectors.js` | OpenAI-compatible | `Qwen/Qwen3-Embedding-0.6B` | API key |

### 3.3 Local Embeddings (Transformers)

The default and zero-config option. Uses `sillytavern-transformers` (a fork of Xenova/transformers.js)
running ONNX Runtime with WASM backend.

`src/transformers.js`, lines 32-37:

```js
'feature-extraction': {
    defaultModel: 'Xenova/all-mpnet-base-v2',
    pipeline: null,
    configField: 'extensions.models.embedding',
    quantized: true,
},
```

The model is downloaded on first use and cached to `<DATA_ROOT>/_cache/`. The pipeline is
initialized lazily and reused across requests. Mean pooling with normalization is applied
(`src/vectors/embedding.js`, line 11):

```js
const result = await pipe(text, { pooling: 'mean', normalize: true });
```

The model can be overridden in `config.yaml` via `extensions.models.embedding`.

### 3.4 Client-Side Providers

Two sources compute embeddings **in the browser**, not on the server:

- **WebLLM**: Uses the SillyTavern WebLLM third-party extension. The frontend computes
  embeddings via `SillyTavern.llm.generateEmbedding(texts)` and sends them to the server
  as pre-computed dictionaries (`public/scripts/extensions/vectors/webllm.js`).

- **KoboldCpp**: Embeddings are fetched client-side from the KoboldCpp server and passed
  through to the backend as pre-computed values.

In both cases, the vector items sent to `/api/vector/insert` already contain the embeddings
in the `sourceSettings.embeddings` field, and the backend simply stores them.

### 3.5 Batching

Batch embeddings are sent in groups of **10** on the backend (`src/endpoints/vectors.js`, line 106):

```js
const batchSize = 10;
const batches = Array(Math.ceil(texts.length / batchSize))
    .fill(undefined)
    .map((_, i) => texts.slice(i * batchSize, i * batchSize + batchSize));
```

The frontend uses a separate batch size of **5** (or **1** for `transformers` and `ollama`):

```js
const getBatchSize = () => ['transformers', 'ollama'].includes(settings.source) ? 1 : 5;
```

### 3.6 Cohere-Specific: Query vs. Document Distinction

The Cohere provider is the only one that passes an `isQuery` boolean to differentiate between
`input_type: 'search_query'` and `input_type: 'search_document'` (`src/vectors/cohere-vectors.js`,
line 30). This follows Cohere's API requirement for asymmetric embeddings.


## 4. Document Processing

### 4.1 Supported File Types

Files are converted to plain text before vectorization. The converter registry is in
`public/scripts/chats.js`, lines 86-97:

| MIME Type | Format | Converter function | Implementation |
|-----------|--------|-------------------|----------------|
| `application/pdf` | PDF | `extractTextFromPDF` | pdf.js (client-side) |
| `text/html` | HTML | `extractTextFromHTML` | DOMParser + DOMPurify |
| `text/markdown` | Markdown | `extractTextFromMarkdown` | Simple postProcessText |
| `application/epub+zip` | EPUB | `extractTextFromEpub` | epub.js (client-side) |
| `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | DOCX | `extractTextFromOffice` | Server plugin (`/api/plugins/office/probe`) |
| `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | XLSX | `extractTextFromOffice` | Server plugin |
| `application/vnd.openxmlformats-officedocument.presentationml.presentation` | PPTX | `extractTextFromOffice` | Server plugin |
| `application/vnd.oasis.opendocument.text` | ODT | `extractTextFromOffice` | Server plugin |
| `application/vnd.oasis.opendocument.presentation` | ODP | `extractTextFromOffice` | Server plugin |
| `application/vnd.oasis.opendocument.spreadsheet` | ODS | `extractTextFromOffice` | Server plugin |

Plain text files (`.txt`, `.json`, `.csv`, etc.) are stored as-is without conversion.
Binary files that are not media and not convertible are rejected at upload time. The maximum
file size is **350 MB** (`public/scripts/chats.js`, line 76).

### 4.2 Text Chunking Algorithm

All text chunking uses the `splitRecursive` function (`public/scripts/utils.js`, lines 1157-1190).
This is a recursive delimiter-based splitter:

```js
export function splitRecursive(input, length, delimiters = ['\n\n', '\n', ' ', '']) {
    if (length <= 0) return [input];
    const delim = delimiters[0] ?? '';
    const parts = input.split(delim);
    const flatParts = parts.flatMap(p => {
        if (p.length < length) return p;
        return splitRecursive(p, length, delimiters.slice(1));
    });
    // Merge short chunks back together up to `length`
    const result = [];
    let currentChunk = '';
    for (let i = 0; i < flatParts.length;) {
        currentChunk = flatParts[i];
        let j = i + 1;
        while (j < flatParts.length) {
            const nextChunk = flatParts[j];
            if (currentChunk.length + nextChunk.length + delim.length <= length) {
                currentChunk += delim + nextChunk;
            } else break;
            j++;
        }
        i = j;
        result.push(currentChunk);
    }
    return result;
}
```

**Algorithm**: Split on the first delimiter (`\n\n`). If any part exceeds `length`, recursively
split on the next delimiter (`\n`, then ` `, then empty string as char-level fallback). After
splitting, merge consecutive short chunks back together, respecting the length limit.

The default delimiter chain is `['\n\n', '\n', ' ', '']`. A custom "Chunk boundary" delimiter
can be prepended via settings.

### 4.3 Chunk Overlap

For file chunks, overlap is implemented by `overlapChunks` (`index.js`, lines 739-749):

```js
function overlapChunks(chunk, index, chunks, overlapSize) {
    const halfOverlap = Math.floor(overlapSize / 2);
    const nextChunk = chunks[index + 1];
    const prevChunk = chunks[index - 1];
    const nextOverlap = trimToEndSentence(nextChunk?.substring(0, halfOverlap)) || '';
    const prevOverlap = trimToStartSentence(prevChunk?.substring(prevChunk.length - halfOverlap)) || '';
    const overlappedChunk = [prevOverlap, chunk, nextOverlap].filter(x => x).join(' ');
    return overlappedChunk;
}
```

The overlap text is **trimmed to sentence boundaries** to avoid mid-sentence fragments. The overlap
is split evenly: half from the tail of the previous chunk, half from the head of the next chunk.
The overlap size is computed as `chunk_size * overlap_percent / 100`. The effective chunk size is
reduced by the overlap size so that the total (chunk + overlap) stays approximately at the
configured size.

### 4.4 Optional Translation Before Vectorization

An experimental feature (`settings.translate_files`) can translate file content to English before
chunking, using the Chat Translation extension's API (`index.js`, lines 591-594):

```js
if (settings.translate_files && typeof globalThis.translate === 'function') {
    const translatedText = await globalThis.translate(fileText, 'en');
    fileText = translatedText;
}
```


## 5. Data Bank

The Data Bank is SillyTavern's knowledge base system. It is managed through the **Attachments
extension** (`public/scripts/extensions/attachments/`).

### 5.1 Three-Tier Attachment Sources

Attachments are organized into three scopes (`public/scripts/chats.js`, lines 77-81):

| Source | Scope | Storage |
|--------|-------|---------|
| `global` | Available to all characters, all chats | `extension_settings.attachments` |
| `character` | Available to one character across all chats | `extension_settings.character_attachments[avatar]` |
| `chat` | Available only in current chat | `chat_metadata.attachments` |

The `getDataBankAttachments()` function (`chats.js`, lines 1779-1786) aggregates all three:

```js
export function getDataBankAttachments(includeDisabled = false) {
    const globalAttachments = extension_settings.attachments ?? [];
    const chatAttachments = chat_metadata.attachments ?? [];
    const characterAttachments = extension_settings.character_attachments?.[characters[this_chid]?.avatar] ?? [];
    return [...globalAttachments, ...chatAttachments, ...characterAttachments]
        .filter(x => includeDisabled || !isAttachmentDisabled(x));
}
```

### 5.2 Attachment Object Shape

Each attachment is a `FileAttachment` object (`chats.js`, lines 62-68):

```ts
{
    url: string,    // Server-relative URL to the stored file
    size: number,   // File size in bytes
    name: string,   // Display name
    created: number // Timestamp
}
```

### 5.3 Data Bank Ingestion Sources

The Data Bank manager UI (`attachments/manager.html`) supports adding files through:

1. **Direct file upload** -- drag & drop or file picker
2. **Fandom wiki scraping** -- scrape all articles from a Fandom wiki (e.g. `harrypotter.fandom.com`)
   with optional regex filtering, output as single file or per-article files
3. **MediaWiki scraping** -- scrape articles from any MediaWiki instance
4. **Web scraping** -- scrape arbitrary web URLs (one per line)
5. **YouTube transcripts** -- download video transcripts by URL or video ID, with optional language code
6. **Notepad** -- manual text entry

Files are uploaded to the server via `uploadFileAttachmentToServer()`, stored in the user's `files/`
directory, and referenced by URL in the settings metadata.

### 5.4 Enable/Disable Mechanism

Individual attachments can be disabled without deletion. Disabled URLs are stored in
`extension_settings.disabled_attachments`. Disabled files are excluded from vectorization
and retrieval by default.

### 5.5 Slash Commands for Data Bank

The attachments extension registers these slash commands:

| Command | Aliases | Function |
|---------|---------|----------|
| `/db` | `/databank`, `/data-bank` | Open the Data Bank manager UI |
| `/db-list` | `/databank-list` | List attachments (JSON array) |
| `/db-get` | `/databank-get` | Get text content of an attachment |
| `/db-add` | `/databank-add` | Add a new attachment (returns URL) |
| `/db-update` | `/databank-update` | Update attachment content (preserves name) |
| `/db-delete` | `/databank-delete` | Delete an attachment |
| `/db-disable` | `/databank-disable` | Disable an attachment |
| `/db-enable` | `/databank-enable` | Enable an attachment |

The vectors extension adds search-specific commands:

| Command | Function |
|---------|----------|
| `/db-ingest` | Force ingestion of all Data Bank attachments |
| `/db-purge` | Purge vector indexes for all Data Bank attachments |
| `/db-search <query>` | Search Data Bank with optional threshold, count, source, return format |


## 6. Chat Vectorization ("Smart Context")

### 6.1 How It Works

When "Enabled for chat messages" is checked, the extension vectorizes chat messages and uses
them for "memory recall" -- retrieving semantically relevant past messages that may have
scrolled out of the context window.

### 6.2 Message Vectorization: `synchronizeChat()`

Chat vectorization happens incrementally via `synchronizeChat()` (`index.js`, lines 328-403):

1. Get all non-system messages from the chat
2. Hash each message text (after parameter substitution): `getStringHash(substituteParams(x.mes))`
3. Fetch already-stored hashes from the Vectra collection (collection ID = chat ID)
4. Identify new messages (hash not in collection) and deleted messages (hash in collection but not in chat)
5. Optionally **summarize** new messages before embedding (via Main API, Extras, or WebLLM)
6. Optionally **chunk** messages using `splitByChunks()` with `message_chunk_size` (default 400 chars)
7. Insert new chunks via the embedding pipeline
8. Delete orphaned hashes

This runs on a debounced trigger whenever messages are sent, received, edited, deleted, or swiped.
It processes messages in batches (default 5, or 1 for transformers/ollama).

### 6.3 Full Vectorization

The "Vectorize All" button triggers `onVectorizeAllClick()`, which loops `synchronizeChat()` in
batches with a progress indicator showing percentage and ETA. It clears the summary cache first
to ensure all summaries are regenerated.

### 6.4 Optional Summarization

When `settings.summarize` is enabled, messages are summarized before embedding. Three endpoints
are supported (`index.js`, lines 296-326):

| Endpoint | Method |
|----------|--------|
| `main` | Calls `generateRaw()` with the summary prompt as system message |
| `extras` | Calls ST-Extras `/api/summarize` endpoint |
| `webllm` | Calls WebLLM extension with system prompt + user content |

Default summary prompt:
```
Ignore previous instructions. Summarize the most important parts of the message.
Limit yourself to 250 words or less. Your response should include nothing but the summary.
```

Summaries are cached in-memory (`cachedSummaries` Map) keyed by message hash to avoid
re-summarizing unchanged messages.


## 7. Query Pipeline

### 7.1 Trigger Point

The RAG pipeline is triggered before **every** LLM generation (except `quiet` prompts) via the
`generate_interceptor` mechanism. The extension framework calls
`runGenerationInterceptors(chat, contextSize, type)` (`public/scripts/extensions.js`, lines 1734-1754),
which iterates all extensions with a `generate_interceptor` and calls them in manifest loading order.

For the vectors extension, this calls `rearrangeChat()` (`index.js`, lines 636-719).

### 7.2 Full Flow: Message to Injected Context

```
User sends message
    |
    v
runGenerationInterceptors() called by prompt builder
    |
    v
rearrangeChat(chat, contextSize, abort, type)
    |
    +-- if type === 'quiet': skip entirely
    |
    +-- Clear extension prompts (both chat and Data Bank tags)
    |
    +-- [1] processFiles(chat)           -- File/Data Bank RAG
    |       |
    |       +-- ingestDataBankAttachments()
    |       |       For each DB file not yet in Vectra:
    |       |       download -> chunk -> embed -> insert
    |       |
    |       +-- injectDataBankChunks(queryText, collectionIds)
    |       |       queryMultipleCollections() -> filter by threshold
    |       |       -> sort by index -> join -> template -> setExtensionPrompt(TAG_DB)
    |       |
    |       +-- For each message attachment:
    |               vectorizeFile() if not yet indexed
    |               retrieveFileChunks() -> prepend to message text
    |
    +-- [2] activateWorldInfo(chat)      -- World Info vector activation
    |       Sync WI entries into per-world collections
    |       Query with chat text -> emit WORLDINFO_FORCE_ACTIVATE for matches
    |
    +-- [3] Chat memory retrieval
            |
            +-- Build query from last N messages (settings.query, default 2)
            |   Optionally summarize the query text
            |
            +-- queryCollection(chatId, queryText, settings.insert)
            |   settings.insert = 3 (default: retrieve top 3 results)
            |
            +-- Filter: exclude last N protected messages (settings.protect = 5)
            |
            +-- Match retrieved hashes to actual chat messages
            |
            +-- Sort matches by relevance (reversed -- more relevant = lower index)
            |
            +-- Remove matched messages from chat array (they'll be re-injected)
            |
            +-- Format as "Name: message" pairs, join with \n\n
            |
            +-- Apply template: "Past events:\n{{text}}"
            |
            +-- setExtensionPrompt(TAG, insertedText, position, depth)
```

### 7.3 Query Text Construction

The query is built from the **last N messages** (`settings.query`, default 2), with file
attachment text stripped out. If summarization is enabled for sent messages (`summarize_sent`),
the query messages are summarized first. Messages are reversed (most recent first), joined with
newlines, and collapsed (`collapseNewlines`).

```js
// index.js, lines 761-780
let hashedMessages = chat
    .map(x => ({ text: substituteParams(getTextWithoutAttachments(x)), ... }))
    .filter(x => x.text)
    .reverse()
    .slice(0, settings.query);
```

### 7.4 Similarity Scoring and Filtering

Vectra returns results sorted by cosine similarity score. The backend applies a threshold filter:

```js
const metadata = result.filter(x => x.score >= threshold).map(x => x.item.metadata);
```

Default threshold: **0.25** (configurable 0.0 to 1.0 in steps of 0.05).

For multi-collection queries (Data Bank), results from all collections are merged, sorted by
descending score, filtered by threshold, then truncated to top K.


## 8. Prompt Injection

### 8.1 Extension Prompt System

SillyTavern's prompt builder supports named "extension prompts" that are injected at configurable
positions. The `setExtensionPrompt()` function (`public/script.js`, lines 8817-8826) stores:

```js
extension_prompts[key] = {
    value: String(value),
    position: Number(position),  // 0=IN_PROMPT, 1=IN_CHAT, 2=BEFORE_PROMPT
    depth: Number(depth),        // For IN_CHAT: how many messages from the end
    scan: Boolean,               // Include in World Info scanning
    role: Number(role),          // 0=SYSTEM, 1=USER, 2=ASSISTANT
};
```

### 8.2 Two Injection Tags

The vectors extension uses two separate injection tags:

| Tag | Constant | Purpose |
|-----|----------|---------|
| `3_vectors` | `EXTENSION_PROMPT_TAG` | Chat memory retrieval results |
| `4_vectors_data_bank` | `EXTENSION_PROMPT_TAG_DB` | Data Bank file chunk results |

### 8.3 Chat Memory Injection

- **Default template**: `"Past events:\n{{text}}"`
- **Default position**: `IN_PROMPT` (0) -- after the main prompt / story string
- **Default depth**: 2
- **Configurable positions**: Before Main Prompt, After Main Prompt, or In-chat @ specific depth

The retrieved messages are formatted as `"Name: message_text"` pairs.

### 8.4 Data Bank Injection

- **Default template**: `"Related information:\n{{text}}"`
- **Default position**: `IN_PROMPT` (0)
- **Default depth**: 4
- **Default role**: System (0)
- **Configurable positions**: Same three options as chat memory, plus role (System/User/Assistant)

Retrieved chunks are sorted by their original index order (preserving document structure),
deduplicated, and joined with newlines.

### 8.5 Message Attachment Injection

For files attached directly to chat messages (not Data Bank), retrieved chunks are **prepended
to the message text itself** rather than using the extension prompt system:

```js
message.mes = `${allFileChunks.join('\n\n')}\n\n${message.mes}`;
```


## 9. World Info Vector Integration

When "Enable for World Info" is checked, the extension vectorizes World Info entries and uses
semantic search to activate relevant entries regardless of keyword matching.

### 9.1 How It Works (`activateWorldInfo`, index.js lines 1602-1705)

1. Fetch all sorted WI entries via `getSortedEntries()`
2. Filter: skip disabled entries, entries without content, and (optionally) non-vectorized entries
3. Group entries by their `world` field (lorebook name)
4. For each world, create a collection `world_<hash(world_name)>`
5. Sync: insert new entries, delete removed ones
6. Multi-query all world collections with the chat query text
7. Activated entries are emitted via `WORLDINFO_FORCE_ACTIVATE` event

### 9.2 Configuration

- **Enabled for all entries**: When checked, all non-disabled entries can be activated. When unchecked,
  only entries with the "vectorized" (chain link) status marker are eligible.
- **Max entries**: Maximum number of WI entries to activate (default 5).


## 10. Settings & Configuration

### 10.1 Complete Settings Object

All configurable parameters with their defaults (`index.js`, lines 57-116):

```js
const settings = {
    // Shared settings
    source: 'transformers',
    alt_endpoint_url: '',
    use_alt_endpoint: false,
    include_wi: false,                    // Include vector results in WI scanning
    force_chunk_delimiter: '',            // Custom chunk boundary
    summarize: false,
    summarize_sent: false,
    summary_source: 'main',
    summary_prompt: 'Ignore previous instructions. Summarize the most important parts...',

    // Per-source model settings
    togetherai_model: 'togethercomputer/m2-bert-80M-32k-retrieval',
    openai_model: 'text-embedding-ada-002',
    electronhub_model: 'text-embedding-3-small',
    openrouter_model: 'openai/text-embedding-3-large',
    cohere_model: 'embed-english-v3.0',
    ollama_model: 'mxbai-embed-large',
    ollama_keep: false,
    vllm_model: '',
    webllm_model: '',
    google_model: 'text-embedding-005',
    chutes_model: 'chutes-qwen-qwen3-embedding-8b',
    nanogpt_model: 'text-embedding-3-small',
    siliconflow_model: 'Qwen/Qwen3-Embedding-0.6B',

    // Chat vectorization
    enabled_chats: false,
    template: 'Past events:\n{{text}}',
    depth: 2,
    position: extension_prompt_types.IN_PROMPT,  // 0
    protect: 5,                           // Last N messages never rearranged
    insert: 3,                            // How many past messages to retrieve
    query: 2,                             // How many recent messages form the query
    message_chunk_size: 400,              // Chunk size for messages (chars)
    score_threshold: 0.25,

    // File vectorization (message attachments)
    enabled_files: false,
    translate_files: false,
    size_threshold: 10,                   // KB -- files smaller than this are not vectorized
    chunk_size: 5000,                     // Characters per chunk
    chunk_count: 2,                       // Number of chunks to retrieve
    overlap_percent: 0,
    only_custom_boundary: false,

    // Data Bank files
    size_threshold_db: 5,                 // KB
    chunk_size_db: 2500,                  // Characters per chunk
    chunk_count_db: 5,                    // Number of chunks to retrieve
    overlap_percent_db: 0,
    file_template_db: 'Related information:\n{{text}}',
    file_position_db: extension_prompt_types.IN_PROMPT,
    file_depth_db: 4,
    file_depth_role_db: extension_prompt_roles.SYSTEM,

    // World Info vectorization
    enabled_world_info: false,
    enabled_for_all: false,
    max_entries: 5,
};
```

### 10.2 Slash Commands for Runtime Configuration

| Command | Purpose |
|---------|---------|
| `/vector-threshold [n]` | Get/set score threshold (0-1) |
| `/vector-query [n]` | Get/set number of query messages |
| `/vector-max-entries [n]` | Get/set WI max entries |
| `/vector-chats-state [bool]` | Get/set chat vectorization enabled |
| `/vector-files-state [bool]` | Get/set file vectorization enabled |
| `/vector-worldinfo-state [bool]` | Get/set WI vectorization enabled |


## 11. Backend API Surface

All endpoints are mounted at `/api/vector/` via the Express router in `src/endpoints/vectors.js`.

| Method | Endpoint | Purpose | Key params |
|--------|----------|---------|------------|
| POST | `/api/vector/query` | Query single collection | `collectionId`, `searchText`, `topK`, `threshold`, `source` |
| POST | `/api/vector/query-multi` | Query multiple collections | `collectionIds[]`, `searchText`, `topK`, `threshold`, `source` |
| POST | `/api/vector/insert` | Insert items into collection | `collectionId`, `items[]`, `source` |
| POST | `/api/vector/list` | List hashes in collection | `collectionId`, `source` |
| POST | `/api/vector/delete` | Delete items by hash | `collectionId`, `hashes[]`, `source` |
| POST | `/api/vector/purge` | Delete entire collection | `collectionId` |
| POST | `/api/vector/purge-all` | Delete all vector data | (none) |

All endpoints accept the embedding `source` and source-specific settings in the request body
(model name, API URL, etc.) via `getSourceSettings()`.


## 12. Key Design Observations

### Strengths

1. **Wide provider support**: 19 embedding sources covering local, cloud, and hybrid setups.
2. **Zero-config default**: Local Transformers embedding works out of the box with no API keys.
3. **Three independent RAG channels**: Chat memory, file/Data Bank retrieval, and World Info
   activation can each be enabled/disabled independently.
4. **Incremental vectorization**: Chat messages are vectorized incrementally on each message event,
   not requiring a full re-index.
5. **Dedup by hash**: Unchanged messages are not re-embedded, saving compute.

### Limitations

1. **Single vector DB**: Only Vectra (file-system JSON). No support for external vector databases
   or scaling beyond single-user local storage.
2. **No hybrid search**: Pure vector similarity only. No BM25, keyword matching, or re-ranking.
3. **No cross-source migration**: Switching embedding providers creates entirely separate indexes.
   Existing indexes from the old provider are orphaned.
4. **Sequential multi-query**: Multiple collections are queried one-at-a-time in a loop, not in
   parallel (`multiQueryCollection` iterates `collectionIds` with `for...of`).
5. **Client-driven pipeline**: The chunking, query construction, and prompt injection logic all live
   in the browser extension JavaScript, making it difficult to reuse from server-side integrations.
6. **No relevance feedback or adaptive retrieval**: The pipeline uses fixed top-K and threshold
   without any mechanism for query expansion or retrieval quality monitoring.
