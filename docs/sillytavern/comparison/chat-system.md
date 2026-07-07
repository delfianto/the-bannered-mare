# Chat System Comparison: SillyTavern v1.17.0 vs The Bannered Mare

This page assumes the [Chat System Analysis](/sillytavern/analysis/chat-system) for how
SillyTavern works internally, and focuses on where The Bannered Mare diverges and why.

The core divergence is the store itself — portable files versus a relational database:

<Figure tag="Figure 1" title="JSONL files vs a relational database" id="fig-cmp-chat">
<svg viewBox="0 0 760 262" role="img" aria-label="SillyTavern vs The Bannered Mare chat storage" style="font-family:var(--vp-font-family-base)">
  <rect x="24" y="16" width="344" height="230" rx="12" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <rect x="392" y="16" width="344" height="230" rx="12" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <rect x="24" y="16" width="344" height="44" rx="12" fill="var(--tbm-dgm-provider-soft)"/><rect x="24" y="36" width="344" height="24" fill="var(--tbm-dgm-provider-soft)"/>
  <rect x="392" y="16" width="344" height="44" rx="12" fill="var(--tbm-dgm-backend-soft)"/><rect x="392" y="36" width="344" height="24" fill="var(--tbm-dgm-backend-soft)"/>
  <text x="196" y="44" text-anchor="middle" font-size="13" font-weight="800" fill="var(--tbm-dgm-ink)">SillyTavern v1.17.0</text>
  <text x="564" y="44" text-anchor="middle" font-size="13" font-weight="800" fill="var(--tbm-dgm-ink)">The Bannered Mare</text>
  <g font-size="10.5" fill="var(--tbm-dgm-ink)">
    <text x="40" y="90">Storage — JSONL file per conversation</text>
    <text x="40" y="122">IDs — filename + array index (no stable ID)</text>
    <text x="40" y="154">Writes — full-state overwrite each save</text>
    <text x="40" y="186">Query — read &amp; parse whole files</text>
    <text x="40" y="222" fill="var(--tbm-dgm-ink-2)">Maximally portable, scales poorly</text>
    <text x="408" y="90">Storage — PostgreSQL (SQLAlchemy 2.0)</text>
    <text x="408" y="122">IDs — NanoID primary keys</text>
    <text x="408" y="154">Writes — incremental INSERT / UPDATE</text>
    <text x="408" y="186">Query — indexed SQL, row locking</text>
    <text x="408" y="222" fill="var(--tbm-dgm-ink-2)">Queryable + concurrent-write safe</text>
  </g>
</svg>
<template #caption>

**Portability vs queryability.** A SillyTavern chat is one self-contained file you can copy or
share, rewritten wholesale on every save; The Bannered Mare persists each message as a row,
trading portability for indexed queries and safe concurrent writes.

</template>
</Figure>

## 1. Chat Storage

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| **Format** | JSONL files on disk (one `.jsonl` per conversation) | PostgreSQL database (SQLAlchemy 2.0 ORM) |
| **Session identity** | Filename (humanized datetime, e.g. `2024-4-15@10h30m22s.jsonl`) | NanoID primary key (`chats.id`, 12 chars) |
| **Message identity** | Array index within the JSONL file (no stable ID) | NanoID primary key (`messages.id`) |
| **Write strategy** | Full-state overwrite -- the client sends the entire chat array on every save; the server replaces the file atomically | Incremental -- each message is `INSERT`ed individually; only the mutated row is `UPDATE`d on edit |
| **Concurrency guard** | UUID integrity slug in header; mismatches reject the save with HTTP 400 | Database-level row locking and transactions via SQLAlchemy session management |
| **Querying** | Must read and parse entire JSONL files; full-text search scans all files in a directory | Standard SQL queries with indexes on `chat_id`, `created_at`, and foreign keys |

**Observations.** SillyTavern's file-based approach maximizes portability -- a chat is a single self-contained file that can be copied, backed up, or shared trivially. The Bannered Mare trades that for queryability and concurrent-write safety inherent in a relational database. SillyTavern's full-state saves are simple but scale poorly with conversation length. The Bannered Mare's row-level persistence avoids this but requires a running database process.


## 2. Message Data Model

SillyTavern's `ChatMessage` is a positional object keyed by array index, with boolean role flags (`is_user`/`is_system`), three timestamp fields, inline swipe arrays, and a freeform `extra` metadata bag ([Analysis §3 ›](/sillytavern/analysis/chat-system#_3-message-data-model)).

**The Bannered Mare** (`Message` model):

```
id                 string(12)   NanoID primary key
chat_id            string(12)   FK -> chats.id (indexed)
role               enum         user | assistant | system
content            text         Message text
token_count        int?         Cached token count
reasoning_content  text?        Model reasoning/thinking content
active_index       int          Index of active alternative (0 = original)
created_at         datetime     Auto-set on creation
updated_at         datetime     Auto-updated
```

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| **Identity** | Positional (array index) | Stable NanoID primary key |
| **Role representation** | Boolean flags (`is_user`, `is_system`) -- implicit "assistant" when both are false | Enum (`user`, `assistant`, `system`) |
| **Speaker name** | Stored per-message in `name` field | Derived from `chat.character.name` or the user persona via relationships |
| **Timestamps** | Three fields: `send_date`, `gen_started`, `gen_finished` | Two fields: `created_at`, `updated_at` (no generation-timing metadata) |
| **Provider metadata** | Stored in `extra.api`, `extra.model` per message | Not stored per-message; the provider/model is a property of the Chat session |
| **Extensibility** | Freeform `extra` dict -- any extension can attach arbitrary data | Fixed column schema; new fields require Alembic migrations |
| **Reasoning** | `extra.reasoning`, `extra.reasoning_duration`, `extra.reasoning_signature` | Dedicated `reasoning_content` column on the Message model |
| **Token count** | `extra.token_count` (optional) | `token_count` column, actively maintained by the service on create/edit |

**Observations.** SillyTavern's `extra` bag provides unlimited extensibility at the cost of schema discipline -- any plugin or feature can attach arbitrary data without coordination. The Bannered Mare's strict column schema enforces data integrity and enables typed queries but requires explicit migrations for every new field. SillyTavern's per-message provider tracking is useful for chats where the user switches models mid-conversation; The Bannered Mare currently tracks the model at the session level only.


## 3. Swipes / Alternatives

SillyTavern stores alternatives ("swipes") inline on the message as parallel arrays (`swipes[]`, `swipe_info[]`, `swipe_id`), kept in sync with `mes` via sync functions, with configurable overswipe navigation ([Analysis §4 ›](/sillytavern/analysis/chat-system#_4-message-swipes-alternatives)).

**The Bannered Mare** stores alternatives in a dedicated `message_alternatives` table:

```
id           string(12)   NanoID primary key
message_id   string(12)   FK -> messages.id (indexed, CASCADE delete)
content      text         Alternative text
token_count  int?         Cached token count
ordinal      int          0-based position in the alternatives list
created_at   datetime
```

The parent `Message` tracks `active_index` (which ordinal is currently displayed). The service updates the message's `content` and `token_count` to match the selected alternative. On first regeneration, the original content is preserved as ordinal 0 before the new response is stored.

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| **Storage** | Inline parallel arrays on the message JSON | Separate `message_alternatives` table with FK relationship |
| **Initialization** | Lazy -- arrays created on first swipe | On-demand -- first regeneration creates ordinal 0 (original) + ordinal 1 (new) |
| **Per-alternative metadata** | Full metadata snapshot per swipe (`send_date`, `gen_started`, `gen_finished`, per-swipe `extra` with `api`, `model`, etc.) | Content and token count only -- no generation timestamps or provider metadata per alternative |
| **Navigation** | Left/right swipe with configurable overswipe behavior | API-driven: `GET /{message_id}/alternatives` lists all, `PUT /{message_id}/alternatives/{alt_id}/activate` switches |
| **Overswipe** | Five behaviors (Regenerate, Loop, None, Pristine Greeting, Edit+Generate) | Not implemented; regeneration is a separate explicit API call |
| **Individual deletion** | Supported -- can delete a single swipe from the array | Not implemented |

**Observations.** SillyTavern's inline approach is simpler for its JSONL-file model -- everything travels as one unit. The parallel-array structure with manual sync functions is fragile but avoids joins. The Bannered Mare's normalized table design is cleaner relationally but currently stores less metadata per alternative. The loss of per-alternative provider/model information means The Bannered Mare cannot show which model generated each alternative.


## 4. Message Editing

SillyTavern edits messages fully client-side (inline textarea, auto-save on keystroke, full-state save), syncing `swipes[swipe_id]`, setting a `tainted` flag, and supporting reorder/delete ([Analysis §5 ›](/sillytavern/analysis/chat-system#_5-message-editing)).

**The Bannered Mare** edits server-side via a REST endpoint:

```
PUT /api/chats/{chat_id}/messages/{message_id}
Body: { "content": "updated text" }
```

The service (`edit_message`) validates the message exists in the chat, updates the content, recalculates the token count, and persists.

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| **Execution** | Client-side DOM manipulation + full-state save | Server-side REST endpoint with row-level update |
| **Swipe sync on edit** | Automatically updates `swipes[swipe_id]` | Does not propagate edits to the alternatives table |
| **Undo** | Cancel restores original text before save | No undo -- the previous content is overwritten |
| **Token recount** | Not explicitly recounted on edit | Recounted using `TokenizerService` after every edit |
| **Message reordering** | Supported (swap in array + DOM) | Not supported |
| **Tainted flag** | Marks chat as edited, affecting overswipe behavior | No equivalent metadata |


## 5. Regeneration

SillyTavern implements regeneration through the swipe mechanism: overswiping past the last swipe triggers `Generate('swipe')` and stores the result as a new swipe, preserving the original ([Analysis §6 ›](/sillytavern/analysis/chat-system#_6-regeneration)).

**The Bannered Mare** has two dedicated API paths:

**Non-streaming:**
```
POST /api/chats/{chat_id}/messages?regenerate=true
```

**Streaming (SSE):**
```
POST /api/chats/{chat_id}/messages?regenerate=true&stream=true
```

The service (`regenerate` / `regenerate_stream`):

1. Validates the last message is from the assistant.
2. Builds the prompt excluding the last assistant message.
3. Calls the provider for a new completion.
4. Stores the old content as an alternative (via `_store_alternative`), then updates the message with the new response.

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| **Mechanism** | Extension of the swipe system (overswipe) | Dedicated regeneration logic in the service layer |
| **Original preservation** | Automatic -- old text remains as a swipe entry | Automatic -- old text is stored as a `MessageAlternative` with ordinal tracking |
| **Streaming** | Yes (standard generation pipeline) | Yes (SSE with typed events: `start`, `text`, `reasoning`, `usage`, `done`, `error`) |
| **Group regeneration** | Deletes all messages from the last `gen_id` batch, then re-generates | Not applicable (no group chat support) |
| **Prompt construction** | Sends the full chat context; the swipe position determines what is included | Explicitly filters out the last assistant message before building the prompt |


## 6. Branching and Bookmarks

SillyTavern implements checkpoints and branches by duplicating the JSONL file (copy message 0..N into a new chat), cross-linked via `chat_metadata.main_chat` and `extra.bookmark_link` / `extra.branches[]` ([Analysis §7 ›](/sillytavern/analysis/chat-system#_7-chat-branching-and-bookmarks)).

**The Bannered Mare — branching / checkpoints: not implemented.** There is no chat-copy, checkpoint, or branch-off-a-swipe feature.

**Bookmarks: partially implemented (session-level only).** A `Chat` row carries an `is_bookmarked` boolean, toggled through the chat-update endpoint (`is_bookmarked` field). A dedicated `GET /api/bookmarks/sessions` endpoint lists every bookmarked chat. Sibling endpoints for bookmarked characters (`GET /api/bookmarks/characters`) and pinned message fragments (`GET /api/bookmarks/messages`) exist as stubs that return empty lists. There is no per-message bookmark link or parent-chat reference -- bookmarking is a simple favorite flag on the whole session, not a checkpoint into a new chat.

**Observations.** Branching is straightforward to implement with SillyTavern's file-based model -- copy the file, truncate, done. In a relational model, branching would require either duplicating message rows (expensive, breaks referential identity) or implementing a tree/DAG structure on the messages table (e.g., a `parent_message_id` column or a separate `branches` table). This is a non-trivial design decision that The Bannered Mare has not yet addressed. Its current bookmark support is limited to flagging whole sessions as favorites, not the checkpoint/branch semantics SillyTavern offers.


## 7. Group Chats

SillyTavern has full multi-character group chat support: JSON group metadata with member lists, four activation strategies (NATURAL/LIST/MANUAL/POOLED), three generation modes (SWAP/APPEND/APPEND_DISABLED), and `gen_id`-batched messages ([Analysis §8 ›](/sillytavern/analysis/chat-system#_8-group-chats)).

**The Bannered Mare — not implemented.** The `Chat` model has a single `character_id` FK, structurally limiting it to 1:1 user-character conversations.

**Observations.** Group chats require substantial architectural additions: a many-to-many relationship between chats and characters, a turn-ordering system, multi-character prompt assembly, and per-turn speaker attribution on messages. SillyTavern's activation strategies (especially NATURAL with talkativeness rolls) represent significant game-design logic that goes beyond basic chat infrastructure.


## 8. Personas

SillyTavern stores personas in `power_user` settings as key-value maps, with a three-tier lock system (chat > character > default) and per-persona configurable prompt injection (position, depth, role) ([Analysis §11 ›](/sillytavern/analysis/chat-system#_11-persona-system)).

**The Bannered Mare** makes personas a first-class domain entity with their own table:

```
personas table:
  id               string(12)   NanoID PK
  name             string(100)  Unique, indexed
  description      text?        Persona description for RP context
  is_default       boolean      Auto-select for new chats
  avatar           string(255)? Path to avatar image
  avatar_thumbnail string(255)? Path to thumbnail
```

The `Chat` model has a `persona_id` FK, binding a persona to a specific chat session. Prompt injection is handled by the `PromptBuilder`, which inserts the persona description as a system message (`"User Persona: {description}"`) at a fixed position in the component order.

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| **Storage** | Key-value maps in user settings JSON | Dedicated database table with CRUD API |
| **Binding** | Three-tier lock system (chat > character > default) | Single FK on the Chat model; `is_default` flag for new chats |
| **Injection position** | Configurable per-persona (position, depth, role) | Fixed position in the prompt template component order |
| **Character connections** | Persona can be locked to specific characters/groups | Not supported |
| **Lorebook integration** | Each persona can reference an associated World Info book | Not implemented |

**Observations.** SillyTavern's persona system is more flexible in terms of binding and prompt injection control. The Bannered Mare's database-backed approach provides better CRUD ergonomics and queryability but currently lacks the multi-level lock resolution and per-persona injection configuration.


## 9. Presets (Generation Parameters)

SillyTavern stores presets as per-API-type configuration files (e.g., `OpenAI/`, `TextCompletion/`), each carrying the full parameter set for that API and deeply coupled to the API type. Presets are their own topic; see the [Presets Analysis](/sillytavern/analysis/presets#_2-chat-completion-preset-structure) for how ST structures per-API-type presets.

**The Bannered Mare** makes presets a first-class entity with a flexible JSON parameters column:

```
presets table:
  id          string(12)   NanoID PK
  name        string(100)  Unique, indexed
  description text?
  parameters  JSON         Sampling parameter overrides (temperature, top_p, etc.)
  is_default  boolean
```

The `Chat` model has a `preset_id` FK. The `ProviderGateway` receives `preset_parameters` and merges them into the API call.

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| **Storage** | JSON files organized by API type | Database table with JSON `parameters` column |
| **Schema** | Fixed per API type -- each type has its own parameter set | Schema-free JSON dict -- any key-value pairs |
| **API coupling** | Tightly coupled -- preset structure varies by API type | Decoupled -- the gateway maps generic parameters to provider-specific formats |
| **Binding** | Global (applies to all chats using that API) | Per-chat via FK, with `is_default` fallback |
| **Parameter validation** | UI-level validation based on known parameter ranges | Relies on `ModelFamily.parameters` schema and `unsupported_parameters` list for validation hints |

**Observations.** SillyTavern's per-API-type presets capture the reality that different providers accept different parameters. The Bannered Mare's generic JSON approach is more flexible but shifts the burden of parameter compatibility to the gateway layer and model family metadata.


## 10. File Attachments

SillyTavern stores two per-message attachment categories — media (`extra.media[]`) and documents (`extra.files[]`, text extracted client-side) — across three scopes (GLOBAL/CHARACTER/CHAT) ([Analysis §12 ›](/sillytavern/analysis/chat-system#_12-file-attachments-in-chat)).

**The Bannered Mare — not implemented.** There is no file attachment system. Messages contain text content only.

**Observations.** File attachments are a substantial feature involving storage management, text extraction, multimodal prompt construction (for vision models), and scope-based access control. For The Bannered Mare, implementing this would require a new `attachments` table, a file storage service, and integration with the prompt builder to inject attachment content or references into the API call.


## 11. Import / Export

SillyTavern imports six formats with auto-detection (Oobabooga, Agnai, CAI Tools, Kobold Lite, RisuAI, native JSONL/Chub), normalizing all to `ChatMessage`, and exports JSONL or plaintext ([Analysis §9 ›](/sillytavern/analysis/chat-system#_9-chat-importexport)).

**The Bannered Mare — not implemented.** There is no import or export functionality.

**Observations.** Import/export is important for interoperability with the broader RP tool ecosystem. The Bannered Mare's relational model means export would require serializing joined data (chat + messages + alternatives + character metadata) into a portable format. Import would need format detection and mapping logic similar to SillyTavern's. Supporting at least JSONL and the Character Card V2 chat format would provide baseline interoperability.


## 12. Prompt Construction

While not strictly part of the "chat system," prompt construction is tightly coupled to how messages are assembled for LLM calls. SillyTavern assembles the prompt client-side from a configurable component order (character card, persona, world info, examples, history), using generation modes for group chats.

**The Bannered Mare** constructs prompts server-side in the `PromptBuilder` service using the `PromptTemplate` entity:

- Configurable component order (`DEFAULT_COMPONENT_ORDER`): `system_prompt`, `world_lore_before_character`, `character_context`, `world_lore_after_character`, `scenario`, `persona`, `world_lore_before_examples`, `example_dialogues`, `rag_context`, `chat_history`, `post_history_instructions`.
- Per-component enable/disable toggles (`components_enabled`).
- A single Jinja2 `system_template` for the base system prompt; NSFW/jailbreak/instruction text now lives in reusable `PromptFragment`s attached via `TemplateFragment` at positions (`after_system`, `pre_history`, `post_history`, `at_depth`), rather than as fixed prompt components.
- Token-budgeted chat history with configurable `max_history_tokens` (default 4096).
- AT_DEPTH lore entries and `at_depth` fragments injected into chat history at a depth from the end.
- Template resolution chain: `Chat.template` -> `Model.template` -> default template. Models carry a `template_id` FK, so selecting a model can automatically determine the prompt template.
- A per-character `system_prompt` can override the template's `system_template`; otherwise there is no model-level system prompt field.

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| **Execution** | Client-side JavaScript | Server-side Python (`PromptBuilder`) |
| **Template engine** | Macro substitution (`{{char}}`, `{{user}}`, etc.) | Jinja2 templates with typed `TemplateContext` |
| **Component ordering** | Configurable | Configurable per-template with enable/disable toggles |
| **Token budgeting** | Yes, with configurable budget | Yes, `max_history_tokens` per template (default 4096) |
| **Lore injection** | World Info with position/depth controls | Lore activation engine with `InsertionPosition` enum and depth-based injection |
| **Template resolution** | Single active preset per API type | Chain: Chat -> Model -> default template; model selection can auto-resolve the template |


## 13. Summary Matrix

| Feature | SillyTavern v1.17.0 | The Bannered Mare |
|---------|---------------------|-----------------|
| Chat storage | JSONL files | PostgreSQL |
| Message identity | Array index (positional) | NanoID (stable) |
| Swipes / alternatives | Inline arrays with per-swipe metadata | Normalized table, content + token count only |
| Message editing | Client-side, auto-save, swipe-synced | Server-side REST, token recount |
| Message reordering | Supported | Not implemented |
| Regeneration | Via swipe overswipe mechanism | Dedicated API endpoint (blocking + SSE) |
| Branching / bookmarks | File duplication with parent references | Branching not implemented; session-level bookmark flag (`is_bookmarked`) with a bookmarks-list endpoint |
| Group chats | Full support (4 activation strategies, 3 generation modes) | Not implemented |
| Personas | Three-tier lock system, configurable injection | Database entity, per-chat FK binding |
| Presets | Per-API-type file-based | Database entity with generic JSON parameters |
| File attachments | Media + documents with text extraction | Not implemented |
| Import / export | 6 import formats, 2 export formats | Not implemented |
| Prompt construction | Client-side, macro substitution | Server-side, Jinja2 templates, component ordering, Chat->Model->default template resolution |
| Streaming | Yes | Yes (SSE with typed events) |
| Backup system | Throttled automatic backups with browser UI | Not implemented |
| Reasoning content | In `extra` metadata | Dedicated column + auto-parse from think tags |

### Architectural Trade-offs

**SillyTavern** optimizes for portability, extensibility, and self-contained data. Every chat is a standalone file. The freeform `extra` bag and client-side architecture allow rapid feature addition without schema migrations. The cost is fragile data synchronization (parallel arrays, manual sync functions), limited queryability, and the full-state-save bottleneck for long conversations.

**The Bannered Mare** optimizes for data integrity, type safety, and server-side control. The relational model with strict schemas enables efficient queries, concurrent access, and typed validation. The cost is reduced portability (requires a database), migration overhead for schema changes, and a smaller current feature set. Several features that SillyTavern has mature implementations of (branching, group chats, file attachments, import/export) remain unimplemented.
