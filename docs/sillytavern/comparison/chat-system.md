# Chat System Comparison: SillyTavern v1.17.0 vs The Bannered Mare

> Engineering comparison of the two systems' chat architectures.
> SillyTavern analysis based on commit `1695f8e`; The Bannered Mare based on current `develop` branch.

---

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

---

## 2. Message Data Model

### SillyTavern (`ChatMessage` interface)

```
name          string    Speaker name (character or user display name)
mes           string    Message text (Markdown)
is_user       boolean   true for user messages
is_system     boolean   true for system/hidden messages
send_date     string    ISO 8601 or formatted datetime
gen_started   string    When generation began
gen_finished  string    When generation completed
force_avatar  string    Avatar URL override (group chats)
extra         object    Extensible metadata bag (api, model, token_count,
                        reasoning, files, media, bookmark_link, branches, ...)
swipes        string[]  Alternative message texts
swipe_info    object[]  Per-swipe metadata (timestamps, extra)
swipe_id      number    Index of the active swipe
```

### The Bannered Mare (`Message` model)

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

### Key Differences

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

---

## 3. Swipes / Alternatives

### SillyTavern

Alternatives ("swipes") are stored inline on the message object:

- `swipes: string[]` -- parallel array of alternative texts.
- `swipe_info: SwipeInfo[]` -- parallel array of per-swipe metadata (timestamps, `extra` snapshot).
- `swipe_id: number` -- index of the currently displayed swipe.

Arrays are lazily initialized on first swipe. Two sync functions (`syncMesToSwipe`, `syncSwipeToMes`) keep the top-level `mes` field in sync with the active `swipes[swipe_id]` entry.

Navigation supports left/right swiping with configurable overswipe behavior per message (`REGENERATE`, `LOOP`, `PRISTINE_GREETING`, `NONE`, `EDIT_GENERATE`).

### The Bannered Mare

Alternatives are stored in a dedicated `message_alternatives` table:

```
id           string(12)   NanoID primary key
message_id   string(12)   FK -> messages.id (indexed, CASCADE delete)
content      text         Alternative text
token_count  int?         Cached token count
ordinal      int          0-based position in the alternatives list
created_at   datetime
```

The parent `Message` tracks `active_index` (which ordinal is currently displayed). The service updates the message's `content` and `token_count` to match the selected alternative.

On first regeneration, the original content is preserved as ordinal 0 before the new response is stored.

### Comparison

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| **Storage** | Inline parallel arrays on the message JSON | Separate `message_alternatives` table with FK relationship |
| **Initialization** | Lazy -- arrays created on first swipe | On-demand -- first regeneration creates ordinal 0 (original) + ordinal 1 (new) |
| **Per-alternative metadata** | Full metadata snapshot per swipe (`send_date`, `gen_started`, `gen_finished`, per-swipe `extra` with `api`, `model`, etc.) | Content and token count only -- no generation timestamps or provider metadata per alternative |
| **Navigation** | Left/right swipe with configurable overswipe behavior | API-driven: `GET /{message_id}/alternatives` lists all, `PUT /{message_id}/alternatives/{alt_id}/activate` switches |
| **Overswipe** | Five behaviors (Regenerate, Loop, None, Pristine Greeting, Edit+Generate) | Not implemented; regeneration is a separate explicit API call |
| **Individual deletion** | Supported -- can delete a single swipe from the array | Not implemented |

**Observations.** SillyTavern's inline approach is simpler for its JSONL-file model -- everything travels as one unit. The parallel-array structure with manual sync functions is fragile but avoids joins. The Bannered Mare's normalized table design is cleaner relationally but currently stores less metadata per alternative. The loss of per-alternative provider/model information means The Bannered Mare cannot show which model generated each alternative.

---

## 4. Message Editing

### SillyTavern

Editing is fully client-side:

1. Enter edit mode (`messageEdit`): replaces rendered HTML with a `<textarea>`.
2. Auto-save on keystroke (`messageEditAuto`): updates in-memory `chat[mesId].mes` and debounces a save.
3. Save (`messageEditDone`): re-renders the message; full-state save to server.
4. Cancel (`messageEditCancel`): restores original text.

Key behaviors:
- Editing updates both `mes.mes` and `mes.swipes[mes.swipe_id]` to keep them synchronized.
- Sets `chat_metadata.tainted = true`, which disables the "pristine greeting" overswipe behavior.
- Supports message reordering (swap adjacent messages) and full message deletion.

### The Bannered Mare

Editing is server-side via a REST endpoint:

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

---

## 5. Regeneration

### SillyTavern

Regeneration is implemented through the swipe mechanism. Right-swiping past the last swipe on an AI message triggers `OVERSWIPE_BEHAVIOR.REGENERATE`:

1. Clear the current message text (show "..." placeholder).
2. Call `Generate('swipe')` to send context to the LLM.
3. The response is stored as a new swipe via `saveReply({ type: 'swipe' })`.

The original message is not lost -- it remains as a prior swipe entry. Group chat regeneration differs: it deletes all messages from the last AI batch (matching `gen_id`) and re-runs generation.

### The Bannered Mare

Regeneration has two dedicated API paths:

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

---

## 6. Branching and Bookmarks

### SillyTavern

Two related features implemented in `bookmarks.js`:

**Checkpoints (Bookmarks):**
- Copy chat from message 0 to the selected message into a new JSONL file.
- The new chat's `chat_metadata.main_chat` references the parent.
- The source message gets `extra.bookmark_link` pointing to the checkpoint.
- Navigation: click the flag icon to open the checkpoint; "Back to Main" to return.

**Branches:**
- Similar to checkpoints, but the user is automatically navigated to the new chat.
- Can branch from a specific swipe (not just the currently displayed one).
- Tracked via `extra.branches[]` on the source message.

Storage is via file duplication -- each branch/checkpoint is a fully independent JSONL file. No shared history.

### The Bannered Mare

**Not implemented.** There is no branching, checkpoint, or bookmark system.

**Observations.** Branching is straightforward to implement with SillyTavern's file-based model -- copy the file, truncate, done. In a relational model, branching would require either duplicating message rows (expensive, breaks referential identity) or implementing a tree/DAG structure on the messages table (e.g., a `parent_message_id` column or a separate `branches` table). This is a non-trivial design decision that The Bannered Mare has not yet addressed.

---

## 7. Group Chats

### SillyTavern

Full multi-character group chat support:

**Group metadata** stored as JSON (not JSONL) in `groups/`:
- `members[]` -- character avatar filenames.
- `disabled_members[]` -- muted characters.
- `activation_strategy` -- NATURAL (mention/talkativeness roll), LIST (all in order), MANUAL (explicit trigger), POOLED (round-robin).
- `generation_mode` -- SWAP (one card at a time), APPEND (all cards combined), APPEND_DISABLED (includes muted).

**Group messages** are standard `ChatMessage` objects with additional fields:
- `force_avatar` -- character's avatar URL for display.
- `original_avatar` -- character's avatar filename for identity resolution.
- `extra.gen_id` -- batch ID linking messages from the same generation turn.

**Regeneration** in groups deletes all messages sharing the last `gen_id`, then re-runs the group generation pipeline.

### The Bannered Mare

**Not implemented.** The `Chat` model has a single `character_id` FK, structurally limiting it to 1:1 user-character conversations.

**Observations.** Group chats require substantial architectural additions: a many-to-many relationship between chats and characters, a turn-ordering system, multi-character prompt assembly, and per-turn speaker attribution on messages. SillyTavern's activation strategies (especially NATURAL with talkativeness rolls) represent significant game-design logic that goes beyond basic chat infrastructure.

---

## 8. Personas

### SillyTavern

Personas are stored in `power_user` settings (not individual files):

```
power_user.personas[avatarId] = personaName
power_user.persona_descriptions[avatarId] = {
    description, position, depth, role, lorebook, connections, title
}
```

Features:
- **Chat lock:** Persona bound to a specific chat file (`chat_metadata.persona`).
- **Character lock:** Persona bound to a character/group via `connections[]`.
- **Default lock:** Global fallback (`power_user.default_persona`).
- **Resolution order:** Chat lock > Character lock > Default lock > Current persona.
- **Auto-lock:** Optionally locks the selected persona to the current chat on selection.
- **Prompt injection:** Configurable position (`IN_PROMPT` or `IN_PROMPT_AT_DEPTH`) with adjustable depth and role.

### The Bannered Mare

Personas are a first-class domain entity with their own table:

```
personas table:
  id               string(12)   NanoID PK
  name             string(100)  Unique, indexed
  description      text?        Persona description for RP context
  is_default       boolean      Auto-select for new chats
  avatar           string(255)? Path to avatar image
  avatar_thumbnail string(255)? Path to thumbnail
```

The `Chat` model has a `persona_id` FK, binding a persona to a specific chat session.

Prompt injection is handled by the `PromptBuilder`, which inserts the persona description as a system message (`"User Persona: {description}"`) at a fixed position in the component order.

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| **Storage** | Key-value maps in user settings JSON | Dedicated database table with CRUD API |
| **Binding** | Three-tier lock system (chat > character > default) | Single FK on the Chat model; `is_default` flag for new chats |
| **Injection position** | Configurable per-persona (position, depth, role) | Fixed position in the prompt template component order |
| **Character connections** | Persona can be locked to specific characters/groups | Not supported |
| **Lorebook integration** | Each persona can reference an associated World Info book | Not implemented |

**Observations.** SillyTavern's persona system is more flexible in terms of binding and prompt injection control. The Bannered Mare's database-backed approach provides better CRUD ergonomics and queryability but currently lacks the multi-level lock resolution and per-persona injection configuration.

---

## 9. Presets (Generation Parameters)

### SillyTavern

Presets are per-API-type configuration files stored on disk (e.g., `OpenAI/`, `TextCompletion/`, `NovelAI/` directories under `openai_settings/` or `textgen_settings/`). Each preset file contains the full parameter set for that API type (temperature, top_p, top_k, penalties, samplers, etc.).

The preset system is deeply coupled to the API type -- different APIs expose different parameter schemas, and the UI dynamically renders controls based on the selected API.

### The Bannered Mare

Presets are a first-class entity with a flexible JSON parameters column:

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

---

## 10. File Attachments

### SillyTavern

Two attachment categories stored per-message:

**Media** (`extra.media[]`): Images, video, audio.
- Stored as files under `user/files/`.
- Supports inline display and API-generated images.
- Per-message `media_index` tracks the currently displayed media item.

**Documents** (`extra.files[]`): PDF, DOCX, TXT, EPUB, XLSX, etc.
- Text is extracted client-side using format-specific converters.
- The extracted text is uploaded as a `.txt` file.
- 350 MB size limit.

Three attachment scopes: GLOBAL, CHARACTER, CHAT.

### The Bannered Mare

**Not implemented.** There is no file attachment system. Messages contain text content only.

**Observations.** File attachments are a substantial feature involving storage management, text extraction, multimodal prompt construction (for vision models), and scope-based access control. For The Bannered Mare, implementing this would require a new `attachments` table, a file storage service, and integration with the prompt builder to inject attachment content or references into the API call.

---

## 11. Import / Export

### SillyTavern

**Import** supports six formats with auto-detection:
- Oobabooga (`data_visible` array)
- Agnai (`messages` array)
- CAI Tools (`histories` object)
- Kobold Lite (`savedsettings` object)
- RisuAI (`type === 'risuChat'`)
- Native JSONL / Chub

All formats are normalized to the standard `ChatMessage` structure on import.

**Export** supports two modes:
- JSONL (native format, raw download)
- Plaintext (formatted as `Name: Message` pairs)

### The Bannered Mare

**Not implemented.** There is no import or export functionality.

**Observations.** Import/export is important for interoperability with the broader RP tool ecosystem. The Bannered Mare's relational model means export would require serializing joined data (chat + messages + alternatives + character metadata) into a portable format. Import would need format detection and mapping logic similar to SillyTavern's. Supporting at least JSONL and the Character Card V2 chat format would provide baseline interoperability.

---

## 12. Prompt Construction

While not strictly part of the "chat system," prompt construction is tightly coupled to how messages are assembled for LLM calls.

### SillyTavern

Prompt assembly is client-side, driven by a configurable component order. The system combines character cards, personas, world info, example dialogues, and chat history into a single prompt. Group chats use generation modes (SWAP, APPEND) to control how multiple character cards are included.

### The Bannered Mare

The `PromptBuilder` service constructs prompts server-side using the `PromptTemplate` entity:

- Configurable component order: `system_prompt`, `nsfw_prompt`, `world_lore_before_character`, `character_context`, `world_lore_after_character`, `scenario`, `persona`, `world_lore_before_examples`, `example_dialogues`, `chat_history`, `jailbreak_prompt`, `post_history_instructions`.
- Per-component enable/disable toggles.
- Jinja2 templates for system, NSFW, and jailbreak prompts.
- Token-budgeted chat history with configurable `max_history_tokens`.
- AT_DEPTH lore entry injection into chat history at specified positions.
- Template resolution chain: `Chat.template` -> `Model.template` -> default template. Models carry a `template_id` FK, so selecting a model can automatically determine the prompt template.
- Prompt configuration is template + fragments only -- there is no model-level system prompt field.

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| **Execution** | Client-side JavaScript | Server-side Python (`PromptBuilder`) |
| **Template engine** | Macro substitution (`{{char}}`, `{{user}}`, etc.) | Jinja2 templates with typed `TemplateContext` |
| **Component ordering** | Configurable | Configurable per-template with enable/disable toggles |
| **Token budgeting** | Yes, with configurable budget | Yes, `max_history_tokens` per template (default 4096) |
| **Lore injection** | World Info with position/depth controls | Lore activation engine with `InsertionPosition` enum and depth-based injection |
| **Template resolution** | Single active preset per API type | Chain: Chat -> Model -> default template; model selection can auto-resolve the template |

---

## 13. Summary Matrix

| Feature | SillyTavern v1.17.0 | The Bannered Mare |
|---------|---------------------|-----------------|
| Chat storage | JSONL files | PostgreSQL |
| Message identity | Array index (positional) | NanoID (stable) |
| Swipes / alternatives | Inline arrays with per-swipe metadata | Normalized table, content + token count only |
| Message editing | Client-side, auto-save, swipe-synced | Server-side REST, token recount |
| Message reordering | Supported | Not implemented |
| Regeneration | Via swipe overswipe mechanism | Dedicated API endpoint (blocking + SSE) |
| Branching / bookmarks | File duplication with parent references | Not implemented |
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
