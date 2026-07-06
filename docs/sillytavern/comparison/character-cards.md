# Character Card System Comparison: SillyTavern v1.17.0 vs The Bannered Mare

> Comparison date: 2026-04-07
> ST analysis source: `docs/st_analysis/CHARACTER_CARD.md`
> The Bannered Mare source: `src/character/` module


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

### SillyTavern

Supports three specification versions via `TavernCardValidator.js`:

| Spec | Validation Depth | Notes |
|------|-----------------|-------|
| V1 (TavernAI Legacy) | Field presence check on 6 required string fields | No type checking |
| V2 (chara_card_v2) | Envelope + 14 required fields + type checks on arrays/objects | Includes optional `character_book` validation |
| V3 (chara_card_v3) | Envelope only (`spec`, `spec_version`, `data` existence) | No field-level validation on `data` |

Validation order is V1 -> V2 -> V3, returning the first match. A V2 card passes V1 validation since V2's top level mirrors V1 fields.

### The Bannered Mare

Supports two specification versions in `card_parser.py`:

| Spec | Detection Logic | Notes |
|------|----------------|-------|
| V1 | Fallback: no `spec` or `data` key present | Also handles Pygmalion/Gradio field names (`char_name`, `char_persona`, etc.) |
| V2 | `spec` and/or `data` dict present | Permissive: reads fields with `.get()` defaults, no strict validation |

Detection is V2-first: if `spec` and `data` exist, or if `data` is a dict, parse as V2. Otherwise fall back to V1.

### Comparison

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

### SillyTavern

File-based, no database. The PNG file is both the avatar image and the data store.

```
{user_data}/characters/MyCharacter.png     # Avatar + embedded JSON
{user_data}/characters/MyCharacter/        # Sprites
{user_data}/chats/MyCharacter/             # Chat logs (.jsonl)
{user_data}/thumbnails/avatar/             # Cached thumbnails
```

- Character identity is the PNG filename (e.g., `MyCharacter.png`).
- All references (chats, sprites, thumbnails) derive from this filename.
- Atomic writes via `write-file-atomic` to prevent corruption.
- V1 and V2 fields are dual-written at both the top level and inside `data.*` for backward compatibility.

### The Bannered Mare

PostgreSQL database with filesystem for binary assets only.

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

### Comparison

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

### SillyTavern

**Import formats (6):**

| Format | Extension | Handler | Avatar Source |
|--------|-----------|---------|---------------|
| PNG | `.png` | `importFromPng` | Uploaded image |
| JSON | `.json` | `importFromJson` | Default avatar (`ai4.png`) |
| YAML | `.yml`/`.yaml` | `importFromYaml` | Default avatar |
| CharX | `.charx` | `importFromCharX` | Icon asset from ZIP |
| BYAF | `.byaf` | `importFromByaf` | Character image from ZIP |

JSON import handles three sub-formats: V2/V3 (has `spec`), V1 (has `name`), and Pygmalion/Gradio (has `char_name`).

**Export formats (2):** PNG (avatar + embedded JSON), JSON (V2 format, pretty-printed with 4-space indent).

Private fields (`fav`, `chat`) are stripped on export.

### The Bannered Mare

**Import formats (2):**

| Format | Extension | Handler | Avatar Source |
|--------|-----------|---------|---------------|
| PNG | `.png` | `parse_card_png` | The PNG file itself |
| JSON | `.json` | `parse_card_json` | None (no avatar) |

JSON detection: if `spec`+`data` present, parse as V2; if `data` is a dict, parse as V2; otherwise V1 (including Pygmalion field aliases).

**Export formats (2):** PNG (V2 JSON in tEXt chunk), JSON (V2 format, 2-space indent).

No field stripping on export -- all persisted fields are included.

### Comparison

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

### SillyTavern

Uses `png-chunks-extract` + `png-chunk-text` + custom `src/png/encode.js` for chunk manipulation.

**Write process:**
1. Extract all chunks from PNG buffer.
2. Remove existing `chara` and `ccv3` tEXt chunks (case-insensitive).
3. Base64-encode V2 JSON and insert as `chara` tEXt chunk before IEND.
4. Clone data, mutate to V3 spec fields, insert as `ccv3` tEXt chunk (errors silently ignored).
5. Re-encode all chunks into valid PNG.

**Read process:** Prefer `ccv3` chunk if present; fall back to `chara` chunk. Case-insensitive keyword matching.

### The Bannered Mare

Manual PNG chunk parsing in `card_parser.py` using `struct` and `zlib` (no third-party PNG libraries for chunk handling; `Pillow` used only for image operations).

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

### Comparison

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
| `extensions` | `data.extensions` (open namespace) | Not persisted directly | The Bannered Mare has `ParsedCard.extensions` but does not store it in DB |
| `character_book` | `data.character_book` | Separate `lorebooks` table | See section 7 |

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
- `card.extensions` is silently discarded (not persisted).
- Version is hardcoded to `2` for all imports.

ST's `readFromV2` hoists V2 data fields to V1 top-level fields and backfills defaults for missing extension fields (`talkativeness` -> 0.5, `fav` -> false).


## 6. Avatar Management

### SillyTavern

The avatar IS the character file. Changing the avatar means rewriting the PNG with the same embedded JSON.

| Aspect | Detail |
|--------|--------|
| Standard dimensions | 512 x 768 px |
| Processing library | Jimp |
| Operations | Crop (optional), resize, cover (fill without distortion) |
| Output format | Always PNG |
| Default avatar | `./public/img/ai4.png` |
| Thumbnail storage | `{user_data}/thumbnails/avatar/` |
| Thumbnail generation | On demand, cached |
| Thumbnail invalidation | Explicit call on avatar change |
| Sprites support | Yes (expression images in character subdirectory) |
| Avatar-only edit | Dedicated endpoint (`POST /edit-avatar`) |

### The Bannered Mare

Avatar is decoupled from character data. Stored as a separate file with a DB reference.

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

### Comparison

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

### SillyTavern

The `character_book` is an optional embedded field on `data` following the V2 spec.

**Structure:**
```
data.character_book = {
  name: string,
  entries: [...],
  extensions: object
}
```

Each entry has 8 spec fields (`keys`, `secondary_keys`, `comment`, `content`, `constant`, `selective`, `insertion_order`, `enabled`, `position`, `id`, `extensions`) plus 25+ ST-specific extension fields (probability, depth, group, sticky, cooldown, delay, match targets, etc.).

**Integration points:**
- `data.extensions.world` links a character to an external World Info file.
- On save, ST converts the referenced World Info file to `character_book` format and embeds it.
- On import, the embedded `character_book` is extracted and available for use.
- World Info and character book share the same data model but use different field names (mapped via `convertWorldInfoToCharacterBook`).

### The Bannered Mare

Lorebooks are a separate database entity with a foreign key relationship to characters.

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
- No automatic embedding into character export (the card parser's `ParsedCard` does not include a `character_book` field).
- Import does not extract `character_book` from incoming cards.

### Comparison

| Aspect | SillyTavern | The Bannered Mare |
|--------|-------------|-----------------|
| Storage location | Embedded in character JSON (`data.character_book`) | Separate `lorebooks` + `lore_entries` tables |
| Portability | Travels with the character card | Must be exported/imported separately |
| Global lorebooks | Via World Info files | Via `is_global` flag on `lorebooks` |
| Entry fields | 8 spec + 25+ extension fields | 16 columns (maps to core V2 spec + selected ST extensions) |
| Import from card | Extracted and usable | `character_book` in `extensions` is discarded |
| Export to card | Embedded via `convertWorldInfoToCharacterBook` | Not embedded in export |
| Group/exclusion logic | Groups, weights, mutual exclusion | Not implemented |
| Probability activation | Yes (per-entry probability) | Not implemented |
| Sticky/cooldown/delay | Yes | Not implemented |
| Match targets | 6 configurable targets (persona, character desc, personality, etc.) | Not implemented |
| Regex matching | Via ST extensions | `use_regex` column on `lore_entries` |

The Bannered Mare's lorebook schema covers the core activation model (keys, secondary keys, position, depth, priority) but omits ST's advanced features (probability, stickiness, cooldown, group scoring, multi-target matching). The critical gap for interoperability is that character book data is not round-tripped through import/export.


## 8. Caching

### SillyTavern

Two-tier caching strategy driven by the cost of parsing PNG metadata on every request.

**Tier 1 -- Memory cache:**
- `MemoryLimitedMap` with configurable capacity (default 100 MB, ~3000 characters).
- FIFO eviction. Key: `{filePath}-{mtimeMs}`.
- Disabled on Android.

**Tier 2 -- Disk cache:**
- `node-persist` key-value store in `{DATA_ROOT}/_cache/characters/`.
- No TTL. Synced every 5 minutes against actual character files.
- Configurable via `performance.useDiskCache`.

**Read path:** Memory -> Disk -> Parse PNG -> store in both tiers.

**Shallow loading:** When `performance.lazyLoadCharacters` is enabled, the list endpoint returns only display fields. Full data loaded on demand.

### The Bannered Mare

No application-level caching layer. PostgreSQL handles query caching internally.

- Character list uses database pagination (`LIMIT`/`OFFSET` with `ORDER BY created_at DESC`).
- No in-memory character cache.
- No lazy loading mode; the list endpoint returns full `CharacterResponse` objects.
- Thumbnail is pre-generated (not cached on demand).

### Comparison

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

### SillyTavern

Express router with POST-based RPC-style endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/all` | POST | List all characters |
| `/get` | POST | Get single character by avatar URL |
| `/create` | POST | Create character |
| `/edit` | POST | Update character |
| `/edit-avatar` | POST | Replace avatar only |
| `/edit-attribute` | POST | Update single field |
| `/merge-attributes` | POST | Deep-merge fields |
| `/delete` | POST | Delete character |
| `/rename` | POST | Rename + re-key |
| `/duplicate` | POST | File-level copy |
| `/export` | POST | Export as PNG or JSON |
| `/import` | POST | Import from any format |

All endpoints use POST regardless of semantics. Character identification is by avatar filename in the request body.

### The Bannered Mare

FastAPI router with RESTful resource-oriented endpoints:

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

### Comparison

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
| Lorebook portability | Embedded in card (round-trips) | Separate entity (does not round-trip) |
| Caching | Two-tier (memory + disk) | Database-native |
| Extensions system | Open `extensions` namespace preserved across round-trips | Extensions parsed but not persisted |
| Sprite/expression system | Full support | Not implemented |
| API style | RPC (POST-only) | REST (proper HTTP methods) |
| Type safety | JSDoc typedefs (runtime: none) | Pydantic + SQLAlchemy mapped types + basedpyright |
| Query capability | File scan + client-side filter | SQL indexes, pagination, server-side filtering |
