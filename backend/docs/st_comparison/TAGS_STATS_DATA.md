# Tags, Stats, and Data Integrity -- Engineering Comparison

This document compares how SillyTavern v1.17.0 and The Bannered Mare approach tag management, statistics tracking, search/filtering, and data integrity. The analysis covers current implementations as of April 2026.

**Reference material:** [docs/st_analysis/TAGS_STATS_DATA.md](../st_analysis/TAGS_STATS_DATA.md)

---

## 1. Tag System

### 1.1 Data Model

**SillyTavern** stores tags as a flat array of JavaScript objects in the user's `settings.json`. Each tag carries an ID, name, folder type, filter state, sort order, two color values, a creation timestamp, and a visibility flag. A separate `tag_map` object maps entity keys (avatar filenames for characters, group IDs for groups) to arrays of tag IDs. Tags and their assignments are two independent structures that must be kept in sync manually.

```
tags: Tag[]                         -- all tag definitions
tag_map: { [entityKey]: tagId[] }   -- entity-to-tag assignments
```

**The Bannered Mare** stores tags as a PostgreSQL array column directly on the `characters` table:

```python
tags: Mapped[list[str] | None] = mapped_column(
    StringList, nullable=True,
    comment="Tags for categorizing and filtering characters"
)
```

The `StringList` type resolves to `postgresql.ARRAY(String)` in production and `JSON` for SQLite test environments. Tags are plain strings -- there is no separate tag registry, no tag IDs, no color metadata, and no folder semantics. A character's tags are simply a list of strings stored alongside the character record.

### 1.2 Comparison Table

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| Storage location | `settings.json` (client-side) | `characters.tags` column (PostgreSQL) |
| Tag identity | UUID-keyed objects with metadata | Plain strings, no registry |
| Tag-entity binding | `tag_map` (separate index) | Column on the entity itself |
| Supported entities | Characters + Groups | Characters only (currently) |
| Color coding | Two colors per tag (bg + fg) | Not implemented |
| Folder semantics | Tags can act as virtual folders (OPEN/CLOSED/NONE) | Not implemented |
| Sort ordering | Manual, alphabetical, or by usage count | Not implemented |
| Visibility toggle | Per-tag hiding on character cards | Not implemented |
| Max tags per entity | 50 on import (anti-troll), no hard limit otherwise | No limit (constrained only by array column size) |
| Default tags | 6 format-related defaults (Plain Text, OpenAI, W++, etc.) | None |
| Bulk operations | Assign/remove across multiple characters, prune unused, merge on delete | Not implemented |
| Tag import from cards | Four modes (ASK/NONE/ALL/ONLY_EXISTING) with conflict handling | Tags from imported cards are stored directly, no import mode selection |
| Backup/restore | Dedicated export/import of tag data as JSON | Handled by standard database backup |
| Slash commands | 5 tag commands for scripting | N/A (no scripting layer) |

### 1.3 Design Trade-offs

SillyTavern's tag system is a full-featured organizational tool with ~2,850 lines of dedicated code. Tags have their own identity, visual configuration, and can serve as navigational containers (folders). The trade-off is complexity: tags and their assignments live in two separate structures that must be synchronized, and the server has no awareness of tags at all -- everything is client-side.

The Bannered Mare's tags are deliberately minimal. Plain strings on a database column give transactional safety (tags cannot drift out of sync with the character they belong to, since they are part of the same row) but offer no cross-entity tag management. There is no way to rename a tag globally, view all characters sharing a tag, or assign colors. The current design treats tags as metadata annotations rather than a first-class organizational system.

A future evolution path for The Bannered Mare would be a normalized tag table (`id`, `name`, `color`, etc.) with a many-to-many join table to characters and any other taggable entities. This would preserve relational integrity while enabling the richer feature set ST provides.

---

## 2. Search and Filtering

### 2.1 SillyTavern Approach

ST performs all search and filtering client-side using Fuse.js for fuzzy matching. The `FilterHelper` class chains seven filter types in sequence: `SEARCH -> FAV -> GROUP -> FOLDER -> TAG -> WORLD_INFO_SEARCH -> PERSONA_SEARCH`. Each filter narrows the dataset further.

Key characteristics:
- **Fuzzy search** with Fuse.js (threshold 0.2, location-independent matching)
- **Weighted fields** -- character name (weight 20), tags (10), description (3), personality (2), etc.
- **Three-state tag filter** -- each tag cycles through SELECTED (include), EXCLUDED (exclude), and UNDEFINED (ignore)
- **AND logic** for inclusion (all selected tags must match), **OR logic** for exclusion (any excluded tag disqualifies)
- **Score caching** per search term per category
- **Fallback** to plain case-insensitive substring matching when fuzzy search is disabled
- **Filter state persistence** across page reloads via browser storage

### 2.2 The Bannered Mare Approach

The Bannered Mare handles filtering server-side through the `BaseRepository._apply_filters()` method, which translates query parameters into SQLAlchemy `WHERE` clauses. The character list endpoint (`GET /api/characters`) accepts filter parameters via `CharacterFilterParams`:

```python
class CharacterFilterParams(BaseModel):
    name__ilike: str | None     # Case-insensitive name search
    gender: Gender | None       # Exact gender match
    tags__ilike: str | None     # Case-insensitive tag content search
    created_at__ge: datetime | None  # Created after date
```

The `_apply_filters` method supports nine operators: `eq`, `ne`, `gt`, `lt`, `ge`, `le`, `in`, `like`, `ilike`. The `tags__ilike` filter performs a case-insensitive `LIKE` match against the serialized tag array column.

### 2.3 Comparison Table

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| Execution location | Client-side (browser) | Server-side (PostgreSQL) |
| Search engine | Fuse.js (fuzzy matching) | SQL `ILIKE` (substring matching) |
| Fuzzy/typo tolerance | Yes (threshold 0.2) | No |
| Indexed fields | 11 character fields, 4 group fields, tags, personas, world info | Name, gender, tags, created_at |
| Field weighting | Per-field weights (name=20, tags=10, description=3, etc.) | Equal weight (binary match) |
| Tag filter logic | Three-state (include/exclude/ignore) with AND/OR | Single inclusion filter (`ILIKE`) |
| Filter chaining | Seven filter types in pipeline | AND combination of all provided filters |
| Favorites filter | Dedicated toggle | Not implemented |
| Pagination | Client-side filtering of full dataset | Server-side `LIMIT`/`OFFSET` with total count |
| Performance scaling | Degrades with dataset size (all data in browser memory) | Scales with database indexing |
| State persistence | Browser localStorage | Stateless (query parameters per request) |

### 2.4 Design Trade-offs

ST's client-side search is powerful for small-to-medium collections: fuzzy matching, weighted relevance, and instant UI updates without network round-trips. The cost is that the entire dataset must be loaded into browser memory, and search performance is bounded by JavaScript execution speed.

The Bannered Mare's server-side filtering is more scalable -- PostgreSQL handles large datasets efficiently -- but currently offers much less search sophistication. There is no fuzzy matching, no relevance scoring, and no multi-field weighted search. The `ILIKE` operator on an array column is functional but limited: it matches against the serialized representation rather than individual array elements.

PostgreSQL offers paths to close this gap without reimplementing a client-side search engine: `pg_trgm` for trigram-based fuzzy matching, `GIN` indexes on array columns for efficient tag containment queries (`@>` operator), and full-text search with `tsvector`/`tsquery` for weighted multi-field search.

---

## 3. Statistics Tracking

### 3.1 SillyTavern Approach

ST tracks per-character statistics in a `stats.json` file. Each character entry (keyed by avatar filename) records:

| Field | Type | Description |
|-------|------|-------------|
| `total_gen_time` | number | Total LLM generation time (ms) |
| `user_word_count` | number | Words written by the user |
| `non_user_word_count` | number | Words generated by the AI |
| `user_msg_count` | number | Total user messages |
| `non_user_msg_count` | number | Total AI messages |
| `total_swipe_count` | number | Total regeneration count |
| `chat_size` | number | Total chat file size (bytes) |
| `date_last_chat` | number | Most recent activity timestamp |
| `date_first_chat` | number | First activity timestamp |

Stats are updated via two paths:
- **Real-time:** The frontend increments counters on each message event and pushes updates to the server via `POST /api/stats/update`
- **Batch rebuild:** `POST /api/stats/recreate` scans all chat `.jsonl` files from disk, parsing every message line and recalculating everything from scratch

Persistence uses a 5-minute auto-save interval with dirty tracking and atomic file writes (`write-file-atomic`).

### 3.2 The Bannered Mare Approach

The Bannered Mare does not implement character-level RP statistics (word counts, message counts, generation times). Instead, it tracks **LLM usage statistics** through the admin logging system.

The `MongoLogger` records every LLM API call to a `llm_audit` collection in MongoDB with fields including: provider, model, prompt/completion/total tokens, latency, status (success/error), and estimated cost. The admin endpoint `GET /admin/logs/llm/stats` runs a MongoDB aggregation pipeline that groups by provider+model and computes:

- Total API calls
- Total prompt/completion/total tokens
- Total estimated cost (USD)
- Average latency
- Success/error counts and success rate

HTTP request logs (`http_logs`) and application errors (`error_logs`) are also stored in MongoDB with TTL indexes for automatic expiration.

### 3.3 Comparison Table

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| Stat scope | Per-character RP metrics | Per-provider/model operational metrics |
| What is tracked | Word counts, message counts, swipes, gen time, chat size | Tokens, latency, cost, success rate, errors |
| Storage | `stats.json` (flat file per user) | MongoDB `llm_audit` collection |
| Update mechanism | Dual: real-time frontend push + batch rebuild from chat files | Automatic on every LLM call (middleware) |
| Data retention | Indefinite (file persists) | TTL-based expiration via MongoDB indexes |
| UI | User stats popup + per-character stats popup | Admin API endpoints (no UI) |
| Rebuild capability | Full rebuild by re-parsing all `.jsonl` chat files | Not needed (each call logged independently) |
| Per-character breakdown | Yes (primary key is character avatar filename) | No (grouped by provider+model, not character) |
| Chat-level stats | Aggregated into per-character totals | Queryable by `chat_id` in raw logs |

### 3.4 Design Trade-offs

These are fundamentally different metrics for different audiences. ST's stats answer user-facing questions: "How much have I chatted with this character? How many words has the AI generated?" The Bannered Mare's stats answer operational questions: "How many tokens am I consuming? What is the error rate? How much is this costing?"

ST's dual-path approach (real-time + batch rebuild) is pragmatic for file-based storage. The real-time path can drift if the browser crashes, but the batch rebuild provides an authoritative recalculation. The downside is that the rebuild must parse every message in every chat file, which becomes slow for large histories.

The Bannered Mare's approach of logging each LLM call independently to MongoDB avoids the drift problem entirely -- each event is recorded at the time it happens, and aggregation is a read-only query over the recorded data. However, it does not capture RP-specific metrics like word counts or swipe counts. Those would need to be derived from the message data already stored in PostgreSQL, which is straightforward (the `messages` and `message_alternatives` tables contain all the raw data) but not yet implemented.

A per-character stats view for The Bannered Mare could be built entirely from existing data using SQL aggregation over the `messages` table joined to `chats` and `characters`, without any additional storage.

---

## 4. Data Integrity

### 4.1 SillyTavern: Data Maid

ST's "Data Maid" is a dedicated integrity checker (~816 lines backend, ~404 lines frontend) that identifies **orphaned files** -- data on disk no longer referenced by any active entity. It scans nine categories:

| Category | What it checks |
|----------|---------------|
| Images | User-uploaded images not referenced in any chat message |
| Files | Uploaded files not referenced in chats or settings |
| Chats | Chat directories for deleted characters |
| Group Chats | Group chat files not referenced by any group |
| Avatar Thumbnails | Thumbnails for missing character avatars |
| Background Thumbnails | Thumbnails for deleted backgrounds |
| Persona Thumbnails | Thumbnails for deleted personas |
| Chat Backups | Automatic chat backup files |
| Settings Backups | Automatic settings backup files |

The Data Maid uses a security model where file paths are SHA-256 hashed before being sent to the frontend, and a cryptographic token (32 random bytes) is issued per scan session. All view/delete operations must include the valid token, and the token is invalidated when the session ends.

Detection works by cross-referencing the filesystem against parsed chat files: the Data Maid reads every `.jsonl` message looking for media references (`extra.image`, `extra.file`, etc.) and every chat metadata block, then flags files that appear on disk but not in any reference set.

Separately, the tag system has its own "Prune" feature that removes tags with zero assignments and `tag_map` entries pointing to deleted entities. And the stats system can be rebuilt from chat files via `recreateStats` to purge entries for deleted characters.

### 4.2 The Bannered Mare: Relational Integrity

The Bannered Mare delegates data integrity to PostgreSQL's relational constraint system. The schema uses foreign keys with explicit `ON DELETE` behaviors:

| Relationship | Constraint | Effect |
|-------------|-----------|--------|
| `Character -> Chats` | `CASCADE` | Deleting a character deletes all its chats |
| `Character -> Lorebooks` | `CASCADE` | Deleting a character deletes all its lorebooks |
| `Lorebook -> LoreEntries` | `CASCADE` | Deleting a lorebook deletes all its entries |
| `Chat -> Messages` | `CASCADE` | Deleting a chat deletes all its messages |
| `Message -> MessageAlternatives` | `CASCADE` | Deleting a message deletes all its swipes |
| `Chat -> Model` | `SET NULL` | Deleting a model nullifies the reference (chat preserved) |
| `Chat -> PromptTemplate` | `SET NULL` | Deleting a template nullifies the reference |
| `Chat -> Persona` | `SET NULL` | Deleting a persona nullifies the reference |
| `Chat -> Preset` | `SET NULL` | Deleting a preset nullifies the reference |
| `Model -> Provider` | `RESTRICT` | Cannot delete a provider that still has models |
| `Model -> ModelFamily` | `RESTRICT` | Cannot delete a model family that still has models |

Additionally, the `CharacterService.delete()` method explicitly calls `delete_character_files()` which uses `shutil.rmtree` to remove the entire character asset directory from the filesystem.

SQLAlchemy ORM relationships use `cascade="all, delete-orphan"` on the Python side, which mirrors the database-level cascades and also handles in-session orphan cleanup.

### 4.3 Comparison Table

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| Primary integrity mechanism | Post-hoc scanning (Data Maid) | Preventive constraints (foreign keys) |
| When integrity is enforced | On-demand (user triggers scan) | At write time (every INSERT/UPDATE/DELETE) |
| Orphan handling | Detect and offer to delete | Prevented by CASCADE or SET NULL |
| Cascade deletion | Manual (delete character files, then chats, then tags) | Automatic (database cascades) |
| Cross-entity references | Must parse all chat files to find references | Tracked by foreign key relationships |
| File-database sync | Not applicable (all data is files) | `delete_character_files()` removes filesystem assets on character deletion |
| Tag cleanup | Prune feature (removes unused tags, dangling tag_map entries) | Not needed (tags are column data on the entity) |
| Stats cleanup | `recreateStats` rebuilds from surviving chat files | MongoDB TTL handles expiration; operational stats have no entity-level orphan risk |
| Security model for cleanup | Token-based, path-hashing, single-use tokens | N/A (integrity is structural, not a user-facing operation) |
| Risk of orphaned data | Present (files can accumulate without references) | Minimal for relational data; possible for filesystem assets if application crashes mid-delete |

### 4.4 Design Trade-offs

ST's file-based architecture means data integrity is fundamentally an application-level concern. When a character is deleted, the chat files, thumbnails, tag references, and stat entries must each be cleaned up by separate code paths. If any step fails or is skipped, orphans accumulate. The Data Maid exists precisely because this is a known, expected condition -- it provides a controlled way to detect and resolve the inevitable drift between filesystem state and application state.

The Bannered Mare's relational model pushes most integrity concerns down to the database engine. Foreign keys with `CASCADE` and `SET NULL` behaviors guarantee that deleting a character atomically removes all associated chats, messages, alternatives, and lorebooks in a single transaction. There is no possibility of orphaned chat records pointing to a deleted character, because the database will not allow the inconsistency to exist.

The one gap in The Bannered Mare's approach is the filesystem. Avatar images and thumbnails live on disk, outside the database transaction. If the application crashes after the database deletion completes but before `delete_character_files()` finishes, orphaned image files could remain. This is a much smaller surface area than ST's full-filesystem integrity problem, but it is not zero. A periodic cleanup job that cross-references the `characters/` storage directory against the `characters` table would close this gap.

---

## 5. Cross-System Integration

### 5.1 SillyTavern

- **Tags + Search:** Fuzzy search indexes tag names as a weighted field (weight 10), so typing a tag name in the search bar surfaces matching characters.
- **Tags + Stats:** Independent systems. Cannot filter stats by tag or use stats to inform tag behavior.
- **Data Maid + Tags:** Independent. Tag cleanup is handled by the tag system's Prune feature, not the Data Maid.
- **Data Maid + Stats:** Independent. Stats for deleted characters persist in `stats.json` until a manual `recreateStats` rebuild is triggered.

### 5.2 The Bannered Mare

- **Tags + Search:** The `tags__ilike` filter parameter enables searching by tag content, but tags are not integrated into a broader multi-field search.
- **Tags + Stats:** LLM stats are grouped by provider/model, not by character or tag. No cross-referencing exists.
- **Data Integrity + Tags:** Tags are part of the character row. Deleting a character deletes its tags atomically.
- **Data Integrity + Stats:** LLM audit logs in MongoDB are independent of relational data. Character deletion does not affect audit logs, which expire via TTL.

---

## 6. Summary of Key Differences

| Dimension | SillyTavern | The Bannered Mare |
|-----------|-------------|-----------------|
| **Tag architecture** | First-class entities with UUID identity, colors, folders, bulk ops | Plain string annotations on the character column |
| **Search model** | Client-side fuzzy search with weighted multi-field indexing | Server-side SQL filtering with `ILIKE` operators |
| **Stats focus** | User-facing RP metrics (words, messages, swipes per character) | Operational metrics (tokens, cost, latency per provider/model) |
| **Integrity strategy** | Post-hoc detection and cleanup (Data Maid) | Preventive relational constraints (foreign keys, cascades) |
| **Orphan risk** | Inherent to file-based architecture; mitigated by scanning tools | Minimal for relational data; small gap for filesystem assets |
| **Complexity** | ~4,500 lines across tags, stats, and data maid | ~50 lines (tag column + filter params); stats via existing logging infrastructure |

The fundamental architectural difference shapes every aspect: SillyTavern's file-based storage requires sophisticated application-level tooling to maintain consistency, while The Bannered Mare's relational database handles most consistency guarantees structurally. Conversely, SillyTavern's tag and stats systems are far more feature-complete for end-user workflows, while The Bannered Mare's current implementations are minimal and focused on operational concerns.
