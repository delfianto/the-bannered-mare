# Character Card System Comparison: SillyTavern v1.17.0 vs The Bannered Mare

This page assumes the [Character Cards Analysis](/sillytavern/analysis/character-cards) for how
SillyTavern works internally, and focuses on where The Bannered Mare diverges and why.

Both read the same card ecosystem, but differ on how many specs they cover and how strictly they
validate:

<Figure tag="Figure 1" title="Strict 3-spec validation vs permissive 2-spec parsing" id="fig-cmp-cards">
<svg viewBox="0 0 760 262" role="img" aria-label="SillyTavern vs The Bannered Mare character cards" style="font-family:var(--vp-font-family-base)">
  <rect x="24" y="16" width="344" height="230" rx="12" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <rect x="392" y="16" width="344" height="230" rx="12" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <rect x="24" y="16" width="344" height="44" rx="12" fill="var(--tbm-dgm-provider-soft)"/><rect x="24" y="36" width="344" height="24" fill="var(--tbm-dgm-provider-soft)"/>
  <rect x="392" y="16" width="344" height="44" rx="12" fill="var(--tbm-dgm-backend-soft)"/><rect x="392" y="36" width="344" height="24" fill="var(--tbm-dgm-backend-soft)"/>
  <text x="196" y="44" text-anchor="middle" font-size="13" font-weight="800" fill="var(--tbm-dgm-ink)">SillyTavern v1.17.0</text>
  <text x="564" y="44" text-anchor="middle" font-size="13" font-weight="800" fill="var(--tbm-dgm-ink)">The Bannered Mare</text>
  <g font-size="10.5" fill="var(--tbm-dgm-ink)">
    <text x="40" y="90">Specs — V1 · V2 · V3</text>
    <text x="40" y="122">Validation — strict (presence + type checks)</text>
    <text x="40" y="154">Order — try V1 → V2 → V3, first match wins</text>
    <text x="40" y="186">Storage — PNG tEXt chunk (chara / ccv3)</text>
    <text x="40" y="222" fill="var(--tbm-dgm-ink-2)">Broader specs, reports errors</text>
    <text x="408" y="90">Specs — V1 · V2 (+ Pygmalion field names)</text>
    <text x="408" y="122">Validation — permissive (.get with defaults)</text>
    <text x="408" y="154">Detection — V2-first, else fall back to V1</text>
    <text x="408" y="186">Storage — DB model + local asset files</text>
    <text x="408" y="222" fill="var(--tbm-dgm-ink-2)">Fewer specs, lenient import</text>
  </g>
</svg>
<template #caption>

**Strict-and-broad vs lenient-and-focused.** SillyTavern validates V1/V2/V3 with type checks and
error reporting; The Bannered Mare parses V1/V2 permissively (filling missing fields with
defaults) and also accepts legacy Pygmalion field names.

</template>
</Figure>

## 1. Card Specification Support

SillyTavern supports three spec versions (V1, V2, V3) with a strict V1 → V2 → V3 validation cascade and type checks ([Analysis §1 ›](/sillytavern/analysis/character-cards#_1-card-specification-versions)).

**The Bannered Mare** supports two specification versions in `card_parser.py`:

| Spec | Detection Logic | Notes |
|------|----------------|-------|
| V1 | Fallback: no `spec` or `data` key present | Also handles Pygmalion/Gradio field names (`char_name`, `char_persona`, etc.) |
| V2 | `spec` and/or `data` dict present | Permissive: reads fields with `.get()` defaults, no strict validation |

Detection is V2-first: if `spec` and `data` exist, or if `data` is a dict, parse as V2. Otherwise fall back to V1.

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| V1 support | Yes | Yes (including Pygmalion field names) |
| V2 support | Yes, strict validation | Yes, permissive parsing |
| V3 support | Yes (minimal validation) | No |
| Validation strictness | Presence + type checks with error reporting | No validation; missing fields get defaults |
| CharX support | Yes (ZIP-based archive) | No |
| BYAF support | Yes (Backyard AI) | No |
| YAML import | Yes | No |

The Bannered Mare's parser is deliberately lenient -- it accepts partial cards without error. ST's validator rejects cards missing required fields but still has fallback paths (V1 -> V2 -> V3 cascade).


## 2. Storage Model

SillyTavern is file-based with no database: the PNG file is simultaneously the avatar and the data store, and identity is the filename ([Analysis §11 ›](/sillytavern/analysis/character-cards#_11-file-based-storage-design)).

**The Bannered Mare** uses a PostgreSQL database with the filesystem for binary assets only.

```
characters table (PostgreSQL):
  id            VARCHAR(12) PK   -- NanoID, stable identifier
  name          VARCHAR(100)
  description   TEXT
  personality   TEXT
  first_message TEXT
  ...14 more columns...
  created_at    TIMESTAMP
  updated_at    TIMESTAMP

{storage_path}/characters/{id}/avatar_original.png
{storage_path}/characters/{id}/avatar_thumbnail.jpg
```

- Character identity is a NanoID (`BaseModel` generates 12-char IDs).
- All character fields are individual database columns with proper types.
- Array fields (`example_dialogues`, `alternate_greetings`, `tags`) use `ARRAY(String)` on PostgreSQL, falling back to `JSON` for SQLite in tests.
- Avatars stored as separate files referenced by relative path columns.
- Relationships (`chats`, `lorebooks`) enforced via foreign keys with cascade deletes.

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| Primary store | Filesystem (PNG files) | PostgreSQL |
| Identity scheme | Filename string | NanoID (12-char) |
| Data-image coupling | Tightly coupled (same file) | Decoupled (DB row + separate file) |
| Schema enforcement | None (JSON blob) | Column types, NOT NULL, FK constraints |
| Atomic writes | `write-file-atomic` | Database transactions |
| Query capability | Full file scan + in-memory filter | SQL with indexes, pagination, filtering |
| Migration path | Manual file manipulation | Alembic migrations |

The fundamental difference: ST treats the PNG as a self-contained document, while The Bannered Mare normalizes data into relational columns. ST's approach is simpler for single-user desktop use; The Bannered Mare's enables structured queries and referential integrity.


## 3. Import/Export Formats

SillyTavern imports six formats (PNG, JSON, YAML, CharX, BYAF, with JSON auto-detecting V2/V3/V1/Pygmalion sub-forms) and exports two (PNG, JSON), stripping private fields on export ([Analysis §4 ›](/sillytavern/analysis/character-cards#_4-import-system), [§5 ›](/sillytavern/analysis/character-cards#_5-export-system)).

**The Bannered Mare** supports two import formats:

| Format | Extension | Handler | Avatar Source |
|--------|-----------|---------|---------------|
| PNG | `.png` | `parse_card_png` | The PNG file itself |
| JSON | `.json` | `parse_card_json` | None (no avatar) |

JSON detection: if `spec`+`data` present, parse as V2; if `data` is a dict, parse as V2; otherwise V1 (including Pygmalion field aliases).

Export formats (2): PNG (V2 JSON in tEXt chunk), JSON (V2 format, 2-space indent). No field stripping on export -- all persisted fields are included.

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| Import formats | 6 (PNG, JSON, YAML, CharX, BYAF) | 2 (PNG, JSON) |
| Export formats | 2 (PNG, JSON) | 2 (PNG, JSON) |
| Archive formats | CharX (ZIP), BYAF (ZIP) | None |
| YAML support | Yes | No |
| Pygmalion/Gradio fields | JSON import only | Both V1 paths (card_parser handles `char_name`, `char_persona`, etc.) |
| Export sanitization | Strips `fav`, `chat` | No stripping (no private metadata stored) |
| Export spec version | V2 (also writes V3 copy in PNG) | V2 only |

ST's broader import support reflects its role as a community hub tool that must interoperate with many character sources. The Bannered Mare covers the two dominant exchange formats (PNG cards from Chub/community, raw JSON).


## 4. PNG Metadata Handling

SillyTavern uses `png-chunks-extract` + a custom encoder to write both a `chara` (V2) and a `ccv3` (V3) tEXt chunk, reading `ccv3` first with case-insensitive keyword matching ([Analysis §2 ›](/sillytavern/analysis/character-cards#_2-png-metadata-encoding)).

**The Bannered Mare** parses PNG chunks manually in `card_parser.py` using `struct` and `zlib` (no third-party PNG libraries for chunk handling; `Pillow` used only for image operations).

**Write process (`export_card_png`):**
1. Open avatar with Pillow (or generate 1x1 transparent placeholder).
2. Save as PNG to buffer.
3. Build a tEXt chunk (`_build_text_chunk`): keyword + null byte + value, with CRC32.
4. Locate IEND position, splice tEXt chunk before it.

**Read process (`_read_png_text_chunks`):**
1. Validate PNG magic bytes.
2. Walk chunks sequentially: read length (4 bytes big-endian), type (4 bytes), data, CRC.
3. For `tEXt` type: split on null byte to get keyword and value.
4. Stop at IEND.
5. Look for `chara` keyword, base64-decode, parse JSON.

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| PNG library | `png-chunks-extract` + custom encoder | Manual `struct`/`zlib` parsing |
| tEXt chunks written | `chara` (V2) + `ccv3` (V3) | `chara` (V2) only |
| tEXt chunks read | `ccv3` preferred, `chara` fallback | `chara` only |
| Keyword matching | Case-insensitive | Exact match (case-sensitive) |
| Existing chunk removal | Strips old `chara`/`ccv3` before write | No removal (appends before IEND on fresh PNG from Pillow) |
| Error on missing chunk | Throws `Error('No PNG metadata.')` | Raises `ValueError` |
| Placeholder image | Default avatar file (`ai4.png`) | 1x1 transparent RGBA |

The Bannered Mare's manual parser is lightweight but does not handle `ccv3` (V3) chunks and does not do case-insensitive matching. ST's approach is more defensive with its case-insensitive lookups and dual-chunk strategy.


## 5. Field Mapping

### V2 Spec to Internal Representation

| V2 `data.*` Field | SillyTavern Internal | The Bannered Mare DB Column | Notes |
|--------------------|---------------------|---------------------|-------|
| `name` | `name` + `data.name` (dual-write) | `name` VARCHAR(100) | ST dual-writes to V1 top-level and V2 `data.*` |
| `description` | `description` + `data.description` | `description` TEXT | |
| `personality` | `personality` + `data.personality` | `personality` TEXT | |
| `scenario` | `scenario` + `data.scenario` | `scenario` TEXT | |
| `first_mes` | `first_mes` + `data.first_mes` | `first_message` TEXT | The Bannered Mare renames to `first_message` |
| `mes_example` | `mes_example` + `data.mes_example` | `example_dialogues` ARRAY | The Bannered Mare converts single string to `list[str]` |
| `creator_notes` | `creatorcomment` (V1) + `data.creator_notes` | `creator_notes` TEXT | ST uses different V1 field name |
| `system_prompt` | `data.system_prompt` | `system_prompt` TEXT | |
| `post_history_instructions` | `data.post_history_instructions` | `post_history_instructions` TEXT | |
| `alternate_greetings` | `data.alternate_greetings` (string[]) | `alternate_greetings` ARRAY | Same type |
| `tags` | `tags` (V1) + `data.tags` | `tags` ARRAY | |
| `creator` | `data.creator` | `creator` VARCHAR(100) | |
| `character_version` | `data.character_version` | `character_version` VARCHAR(100) | |
| `extensions` | `data.extensions` (open namespace) | Not stored as a column, but species/gender/age/custom_gender are extracted from it into dedicated columns | The Bannered Mare reads `extensions.bannered_mare` (and legacy keys) for those fields; the rest of the `extensions` dict is not persisted |
| `character_book` | `data.character_book` | Separate `lorebooks` + `lore_entries` tables (round-tripped) | See section 7 |

### ST-Only Fields (No The Bannered Mare Equivalent)

| Field | Type | Purpose |
|-------|------|---------|
| `fav` / `data.extensions.fav` | boolean | Favorite flag |
| `chat` | string | Current active chat filename |
| `avatar` | string | PNG filename (identity) |
| `talkativeness` / `data.extensions.talkativeness` | number | Talk propensity (0.0-1.0) |
| `create_date` | string | ISO timestamp (server-injected) |
| `json_data` | string | Raw JSON (server-injected) |
| `shallow` | boolean | Lazy-load indicator |
| `data.extensions.world` | string | Associated World Info file |
| `data.extensions.depth_prompt` | object | Character-specific depth prompt |
| `data.extensions.regex_scripts` | array | Per-character regex scripts |

### The Bannered Mare-Only Fields (No ST Equivalent)

| Column | Type | Purpose |
|--------|------|---------|
| `id` | VARCHAR(12) | Stable NanoID identifier |
| `gender` | ENUM | Character gender (male, female, non_binary, others) |
| `custom_gender` | VARCHAR(100) | Free-text gender when `gender = 'others'` |
| `avatar_thumbnail` | VARCHAR(255) | Separate thumbnail path |
| `version` | INTEGER | Internal card version counter |
| `created_at` | TIMESTAMP | Auto-managed by BaseModel |
| `updated_at` | TIMESTAMP | Auto-managed by BaseModel |

### Import Field Mapping

On import (`service.import_card`), The Bannered Mare maps `ParsedCard` to the `Character` model:

- `card.example_dialogues` (single string in V2) is wrapped in a single-element list: `[card.example_dialogues]`.
- Empty strings are converted to `None` for nullable columns.
- The raw `card.extensions` dict is not persisted, but its species/gender/age/custom_gender values (extracted by the parser) are written to their dedicated columns.
- `card.character_book`, if present, is expanded into a `Lorebook` plus mapped `LoreEntry` rows.
- Version is hardcoded to `2` for all imports.

ST's `readFromV2` hoists V2 data fields to V1 top-level fields and backfills defaults for missing extension fields (`talkativeness` -> 0.5, `fav` -> false).


## 6. Avatar Management

For SillyTavern the avatar *is* the character file: changing it rewrites the PNG (512x768, Jimp) with the same embedded JSON, plus lazily cached thumbnails and sprite support ([Analysis §9 ›](/sillytavern/analysis/character-cards#_9-avatar-management)).

**The Bannered Mare** decouples the avatar from character data, storing it as a separate file with a DB reference.

| Aspect | Detail |
|--------|--------|
| Max dimensions | 2048 x 2048 px (validation limit) |
| Max file size | 5 MB |
| Processing library | Pillow |
| Allowed formats | PNG, JPG, JPEG, GIF, WebP |
| Thumbnail dimensions | 128 x 128 px |
| Thumbnail format | JPEG (quality 85, optimized) |
| Thumbnail generation | Immediate on upload |
| Storage structure | `{storage}/characters/{id}/avatar_original.{ext}` |
| Thumbnail path | `{storage}/characters/{id}/avatar_thumbnail.jpg` |
| Sprites support | No |
| Validation | Extension check, file size, image integrity (Pillow verify), dimensions |
| API endpoints | `GET /{id}/avatar`, `GET /{id}/avatar_thumbnail` |

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| Avatar-data coupling | Same file | Separate files + DB columns |
| Sprites/expressions | Yes | No |
| Processing library | Jimp (JS) | Pillow (Python) |
| Forced dimensions | 512x768 (crop-to-fill) | No forced resize; max 2048x2048 validated |
| Thumbnail timing | Lazy (on demand) | Eager (on upload) |
| Accepted input formats | PNG (output always PNG) | PNG, JPG, JPEG, GIF, WebP |
| Upload validation | Minimal (Jimp handles errors) | Extension, size, integrity, dimension checks |
| On import from PNG | PNG file becomes the avatar | PNG file saved as avatar via `save_character_avatar` |


## 7. Character Book / Lorebook Integration

In SillyTavern the `character_book` is an optional embedded field on `data` (V2 spec) — 8 spec fields plus 25+ ST extension fields per entry — linked to external World Info files and round-tripped with the card ([Analysis §8 ›](/sillytavern/analysis/character-cards#_8-character-book-embedded-lorebook)).

**The Bannered Mare** makes lorebooks a separate database entity with a foreign key relationship to characters.

**Structure:**
```
lorebooks table:
  id, name, description, is_global, character_id (FK -> characters)

lore_entries table:
  id, lorebook_id (FK -> lorebooks), name, content,
  keys (ARRAY), secondary_keys (ARRAY),
  secondary_logic (ENUM: and_any, and_all, not_any, not_all),
  case_sensitive, match_whole_words, use_regex,
  enabled, constant,
  position (ENUM: before_character, after_character, at_depth, ...),
  depth, role (ENUM: system, user, assistant),
  priority, scan_depth, ignore_budget, order
```

**Integration points:**
- `Character.lorebooks` relationship with cascade delete.
- Lorebooks can be character-scoped (`character_id` set) or global (`is_global = True`).
- `ParsedCard` carries a `character_book` field, so lorebooks round-trip through import/export.
- On import (`service.import_card`), an embedded `character_book` is extracted into a new `Lorebook` plus mapped `LoreEntry` rows (keys, secondary keys/logic, position, depth, role, priority, flags).
- On export (`_character_to_card` + `card_to_v2_dict`), the character's first lorebook is serialized back into `data.character_book`.

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| Storage location | Embedded in character JSON (`data.character_book`) | Separate `lorebooks` + `lore_entries` tables |
| Portability | Travels with the character card | Must be exported/imported separately |
| Global lorebooks | Via World Info files | Via `is_global` flag on `lorebooks` |
| Entry fields | 8 spec + 25+ extension fields | 16 columns (maps to core V2 spec + selected ST extensions) |
| Import from card | Extracted and usable | Extracted into `Lorebook` + `LoreEntry` rows |
| Export to card | Embedded via `convertWorldInfoToCharacterBook` | Embedded in `data.character_book` (first lorebook) |
| Group/exclusion logic | Groups, weights, mutual exclusion | Not implemented |
| Probability activation | Yes (per-entry probability) | Not implemented |
| Sticky/cooldown/delay | Yes | Not implemented |
| Match targets | 6 configurable targets (persona, character desc, personality, etc.) | Not implemented |
| Regex matching | Via ST extensions | `use_regex` column on `lore_entries` |

The Bannered Mare's lorebook schema covers the core activation model (keys, secondary keys, position, depth, priority) but omits ST's advanced features (probability, stickiness, cooldown, group scoring, multi-target matching). Character book data now round-trips through import/export -- an embedded `character_book` is expanded into `Lorebook`/`LoreEntry` rows on import and re-embedded on export -- though only the core V2 fields survive the round trip; ST's advanced extension fields are dropped.


## 8. Caching

SillyTavern runs a two-tier cache (memory `MemoryLimitedMap` + `node-persist` disk store) plus shallow lazy-loading, because parsing PNG metadata on every request is expensive ([Analysis §10 ›](/sillytavern/analysis/character-cards#_10-caching-architecture)).

**The Bannered Mare** has no application-level caching layer; PostgreSQL handles query caching internally.

- Character list uses database pagination (`LIMIT`/`OFFSET` with `ORDER BY created_at DESC`).
- No in-memory character cache.
- No lazy loading mode; the list endpoint returns full `CharacterResponse` objects.
- Thumbnail is pre-generated (not cached on demand).

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| Application cache | Two-tier (memory + disk) | None |
| Cache necessity | High (PNG parsing is expensive) | Low (database queries are indexed) |
| Lazy loading | Yes (shallow mode) | No (full objects returned) |
| Cache invalidation | File mtime + explicit invalidation | N/A (DB is source of truth) |
| Thumbnail caching | On-demand generation + cache | Pre-generated on upload |
| Scalability bottleneck | File I/O + PNG parsing | Standard DB query performance |

ST needs caching because reading character data requires PNG binary parsing on every access. The Bannered Mare's relational storage eliminates this need -- indexed SQL queries serve the same purpose without an application cache layer. If The Bannered Mare's character count grows large, standard database optimization (indexes, connection pooling) applies rather than custom caching.


## 9. API Design

SillyTavern exposes an Express router of POST-only, RPC-style endpoints (`/all`, `/get`, `/create`, `/edit`, `/edit-avatar`, `/edit-attribute`, etc.), identifying characters by avatar filename in the request body ([Analysis §3 ›](/sillytavern/analysis/character-cards#_3-character-crud-operations)).

**The Bannered Mare** uses a FastAPI router with RESTful resource-oriented endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/characters` | GET | List with pagination + filters |
| `/api/characters` | POST | Create character |
| `/api/characters/{id}` | GET | Get by ID |
| `/api/characters/{id}` | PUT | Update character |
| `/api/characters/{id}` | DELETE | Delete character |
| `/api/characters/{id}/avatar` | GET | Serve avatar |
| `/api/characters/{id}/avatar_thumbnail` | GET | Serve thumbnail |
| `/api/characters/{id}/export/json` | GET | Export as JSON |
| `/api/characters/{id}/export/png` | GET | Export as PNG |
| `/api/characters/import` | POST | Import PNG or JSON |

Uses proper HTTP methods, path-based resource identification, Pydantic response models, and multipart form data for avatar uploads.

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| Style | RPC (all POST) | RESTful |
| Resource identification | Avatar filename in body | NanoID in URL path |
| Pagination | None (returns all) | Page-based with total count |
| Filtering | None (client-side) | Server-side (name, gender, tags, date) |
| Response format | Raw JSON objects | Pydantic-validated response models |
| Input validation | Minimal (`sanitize-filename`) | Pydantic schemas with field constraints |
| Avatar edit | Dedicated endpoint | Part of update (multipart form) |
| Single-field edit | Dedicated endpoint (`edit-attribute`) | Not supported (full PUT) |
| Duplicate | Dedicated endpoint | Not supported |
| Rename | Dedicated endpoint | Part of update (change `name` field) |


## 10. Summary of Architectural Differences

| Dimension | SillyTavern | The Bannered Mare |
|-----------|-------------|-----------------|
| Architecture | File-based monolith (Express + filesystem) | Modular monolith (FastAPI + PostgreSQL + filesystem) |
| Data model | JSON blob embedded in PNG | Relational columns with typed constraints |
| Character identity | Mutable filename | Immutable NanoID |
| Spec coverage | V1 + V2 + V3 + CharX + BYAF + YAML | V1 + V2 |
| Import breadth | 6 formats | 2 formats |
| Lorebook portability | Embedded in card (round-trips) | Separate entity, round-tripped via `character_book` on import/export |
| Caching | Two-tier (memory + disk) | Database-native |
| Extensions system | Open `extensions` namespace preserved across round-trips | Extensions read for species/gender/age/custom_gender; the rest not persisted |
| Sprite/expression system | Full support | Not implemented |
| API style | RPC (POST-only) | REST (proper HTTP methods) |
| Type safety | JSDoc typedefs (runtime: none) | Pydantic + SQLAlchemy mapped types + basedpyright |
| Query capability | File scan + client-side filter | SQL indexes, pagination, server-side filtering |
