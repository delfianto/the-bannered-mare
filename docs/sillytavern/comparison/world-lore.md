# World Lore System Comparison: SillyTavern v1.17.0 vs The Bannered Mare

> SillyTavern source: `public/scripts/world-info.js` (6,273 lines, client-side) +
> `src/endpoints/worldinfo.js` (158 lines, file CRUD)
>
> The Bannered Mare source: `src/lore/activation_engine.py`, `src/lore/service.py`,
> `src/lore/repository.py`, `src/lore/router.py`, `src/lore/schemas.py`,
> `src/core/persistence/models.py`, `src/core/persistence/enums.py`


The Bannered Mare keeps the core activation mechanics and trims the long tail of ST-specific
fields accumulated over the years:

<Figure tag="Figure 1" title="35+ fields / 8 positions vs 18 fields / 4 positions" id="fig-cmp-lore">
<svg viewBox="0 0 760 262" role="img" aria-label="SillyTavern vs The Bannered Mare world lore" style="font-family:var(--vp-font-family-base)">
  <rect x="24" y="16" width="344" height="230" rx="12" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <rect x="392" y="16" width="344" height="230" rx="12" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <rect x="24" y="16" width="344" height="44" rx="12" fill="var(--tbm-dgm-provider-soft)"/><rect x="24" y="36" width="344" height="24" fill="var(--tbm-dgm-provider-soft)"/>
  <rect x="392" y="16" width="344" height="44" rx="12" fill="var(--tbm-dgm-backend-soft)"/><rect x="392" y="36" width="344" height="24" fill="var(--tbm-dgm-backend-soft)"/>
  <text x="196" y="44" text-anchor="middle" font-size="13" font-weight="800" fill="var(--tbm-dgm-ink)">SillyTavern v1.17.0</text>
  <text x="564" y="44" text-anchor="middle" font-size="13" font-weight="800" fill="var(--tbm-dgm-ink)">The Bannered Mare</text>
  <g font-size="10.5" fill="var(--tbm-dgm-ink)">
    <text x="40" y="90">Fields — 35+ per entry</text>
    <text x="40" y="122">Positions — 8 insertion positions</text>
    <text x="40" y="154">Engine — client-side (6,273 lines)</text>
    <text x="40" y="186">Extras — probability · triggers · vectorized · outlets</text>
    <text x="40" y="222" fill="var(--tbm-dgm-ink-2)">Years of accreted options</text>
    <text x="408" y="90">Fields — 18 persisted</text>
    <text x="408" y="122">Positions — 4 insertion positions</text>
    <text x="408" y="154">Engine — server-side activation_engine</text>
    <text x="408" y="186">Extras — split priority + order fields</text>
    <text x="408" y="222" fill="var(--tbm-dgm-ink-2)">Core mechanics, trimmed surface</text>
  </g>
</svg>
<template #caption>

**Same idea, fewer knobs.** Keys, secondary logic, constant entries, depth, and budget are
equivalent on both sides; The Bannered Mare omits ST extras like per-entry probability, trigger
filters, vectorized activation, and outlets, and splits ST's single `order` into `priority` +
`order`.

</template>
</Figure>

## 1. Entry Data Model

### 1.1 Structural Overview

SillyTavern entries carry 35+ fields, accumulated over years of feature additions.
The Bannered Mare entries carry 18 persisted fields, covering the core activation and insertion
mechanics while omitting several ST-specific extensions.

| Category | SillyTavern | The Bannered Mare | Notes |
|---|---|---|---|
| Primary keys | `key: string[]` | `keys: list[str]` | Equivalent. Both support comma-separated or array-based keywords. |
| Secondary keys | `keysecondary: string[]` | `secondary_keys: list[str]` | Equivalent. |
| Secondary logic | `selectiveLogic: enum(0-3)` | `secondary_logic: SecondaryLogic` | Same four modes: AND_ANY, AND_ALL, NOT_ANY, NOT_ALL. |
| Content | `content: string` | `content: str` | ST supports macro substitution (`{{char}}`, etc.) and decorator lines (`@@activate`). The Bannered Mare stores raw text. |
| Display name | `comment: string` | `name: str` | ST calls it "comment/memo"; The Bannered Mare uses a required `name` field with max 200 chars. |
| Enabled/disabled | `disable: boolean` | `enabled: boolean` | Inverted polarity. ST defaults `disable=false`; The Bannered Mare defaults `enabled=True`. |
| Constant | `constant: boolean` | `constant: bool` | Equivalent. Both bypass keyword scanning when true. |
| Regex matching | Inline `/pattern/flags` in key strings | `use_regex: bool` column | ST detects regex syntax per-key. The Bannered Mare applies a model-level toggle that makes all keys on the entry behave as regex patterns. |
| Case sensitivity | `caseSensitive: boolean?` (nullable, falls back to global) | `case_sensitive: bool` (default False) | ST supports per-entry nullable with global fallback. The Bannered Mare stores a concrete boolean per entry with no global override. |
| Whole-word matching | `matchWholeWords: boolean?` (nullable, falls back to global) | `match_whole_words: bool` (default False) | Same nullable-vs-concrete distinction as case sensitivity. |
| Position | `position: enum(0-7)` | `position: InsertionPosition` | ST has 8 positions. The Bannered Mare has 4. See Section 4. |
| Depth | `depth: number` | `depth: int` | Both default to 4. Used with at-depth insertion. |
| Role | `role: enum(0-2)` | `role: MessageRole` | ST uses integer enum (0=System,1=User,2=Assistant). The Bannered Mare uses string enum (`system`, `user`, `assistant`). |
| Priority/order | `order: number` | `priority: int` + `order: int` | ST uses a single `order` field for both insertion priority and display ordering. The Bannered Mare separates these: `priority` (higher = inserted first, default 100) and `order` (display ordering, default 0). |
| Scan depth | `scanDepth: number?` | `scan_depth: int?` | Both support per-entry override. |
| Ignore budget | `ignoreBudget: boolean` | `ignore_budget: bool` | Equivalent. |
| Probability | `probability: number`, `useProbability: boolean` | -- | Not implemented. |
| Trigger filter | `triggers: string[]` | -- | Not implemented. |
| Vectorized | `vectorized: boolean` | -- | Not implemented. ST delegates to the `vectors` extension. |
| Automation | `automationId: string` | -- | Not implemented. |
| Outlet name | `outletName: string` | -- | Not implemented (no outlet position). |

### 1.2 Fields Present in The Bannered Mare but Absent in SillyTavern

| Field | Purpose |
|---|---|
| `lorebook_id: str` | Foreign key to parent lorebook (normalized relational storage). ST stores entries nested inside the lorebook JSON object. |
| `id: str` (NanoID) | Globally unique identifier. ST uses a per-lorebook `uid` integer. |
| `created_at`, `updated_at` | Audit timestamps from `BaseModel`. ST has no equivalent. |

### 1.3 Data Storage

| Aspect | SillyTavern | The Bannered Mare |
|---|---|---|
| Persistence | Flat JSON files in a `worlds/` directory. One file per lorebook. | PostgreSQL via SQLAlchemy ORM. Lorebooks and entries are separate tables with FK relationships. |
| Write semantics | Full-file overwrite on every save (`JSON.stringify` + `write-file-atomic`). | Row-level updates through repository pattern. |
| Entry identity | Integer `uid` scoped to the lorebook file. | NanoID string, globally unique. |
| Caching | `StructuredCloneMap` with clone-on-get. | SQLAlchemy session identity map. |


## 2. Activation Engine

### 2.1 Architecture

| Aspect | SillyTavern | The Bannered Mare |
|---|---|---|
| Runtime | Client-side browser (async JavaScript). | Server-side Python (synchronous). |
| Entry point | `checkWorldInfo()` -- async function, ~500 lines. | `activate_entries()` -- pure function, ~50 lines. |
| Algorithm | Multi-pass iterative loop with four scan states (INITIAL, RECURSION, MIN_ACTIVATIONS, NONE). | Single-pass linear scan. No recursion, no min-activation expansion. |
| Statefulness | Stateful: tracks scan state, recursion buffers, timed effects across passes within a single generation call. | Stateless: processes the full entry list once and returns results. |

### 2.2 Matching Pipeline

Both systems follow the same two-stage pattern:

```
1. Primary match: at least one key found in scan text
2. Secondary filter: apply logic (AND_ANY / AND_ALL / NOT_ANY / NOT_ALL)
```

**SillyTavern implementation** (`matchKeys()` at line 337):
- Regex detection via `/pattern/flags` syntax per key string.
- Case handling: per-entry nullable with global fallback.
- Whole-word: regex boundary check for single words, `includes()` for multi-word.
- Default: `String.includes()` substring match.
- Supports macro expansion on keys via `substituteParams()` before matching.

**The Bannered Mare implementation** (`_match_keyword()` and `_match_regex()`):
- Regex mode controlled by `entry.use_regex` boolean (applies to all keys on the entry).
- Whole-word matching uses `\b` word boundaries via `re.escape()` + `re.search()`.
- Default: `re.escape()` + `re.search()` for substring matching.
- No macro substitution system.

### 2.3 Constant Entry Handling

Both systems handle constants identically: constant entries skip keyword scanning and are
unconditionally included. In SillyTavern, `@@activate` decorators in content provide an
alternative way to achieve the same effect. The Bannered Mare has no decorator system.

### 2.4 Priority and Budget Enforcement Order

Both systems sort activated entries by priority (descending) before applying the token
budget. Higher-priority entries are guaranteed budget allocation first.

In The Bannered Mare, entries with `priority < 0` are excluded entirely during budget enforcement
(treated as disabled for budget purposes). SillyTavern has no equivalent negative-priority
cutoff.


## 3. Scan Buffer

### 3.1 SillyTavern: Multi-Layer Buffer

ST's `WorldInfoBuffer` class maintains four internal layers:

| Layer | Description |
|---|---|
| `depthBuffer[]` | Chat messages indexed by depth (0 = most recent), up to MAX_SCAN_DEPTH (1000). |
| `globalScanData` | Character description, personality, persona, scenario, creator notes, depth prompt. |
| `recurseBuffer[]` | Content from previously activated entries (fed back during recursion passes). |
| `injectBuffer[]` | Extension prompt injections marked with `scan: true`. |

Per-entry flags (`matchPersonaDescription`, `matchCharacterDescription`, etc.) control
which global scan sources are included for that specific entry.

### 3.2 The Bannered Mare: Flat String

The Bannered Mare passes a single `scan_text: str` parameter to `activate_entries()`. The caller
(`LoreService.get_activated_entries()`) is responsible for constructing this string from
chat messages and character context before calling the engine.

### 3.3 Comparison

| Aspect | SillyTavern | The Bannered Mare |
|---|---|---|
| Buffer structure | Multi-layer with depth indexing | Flat pre-built string |
| Per-entry scan sources | 6 boolean flags to include character/persona fields | No per-entry source control; all sources pre-merged by caller |
| Depth control | Global `world_info_depth` + per-entry `scanDepth` + skew | Per-entry `scan_depth` field exists on the model but is not consumed by `activate_entries()` (the caller must implement depth slicing) |
| Recursion buffer | Dedicated layer, populated across passes | Not applicable (single-pass) |
| Extension injections | Separate `injectBuffer` for extension content | Not applicable |


## 4. Insertion Positions

### 4.1 Position Map

| ST Position | ST Value | The Bannered Mare Equivalent | CK Enum Value |
|---|---|---|---|
| Before Character Definitions | `0` (before) | `BEFORE_CHARACTER` | `before_character` |
| After Character Definitions | `1` (after) | `AFTER_CHARACTER` | `after_character` |
| Before Author's Note | `2` (ANTop) | -- | -- |
| After Author's Note | `3` (ANBottom) | -- | -- |
| At Depth (System/User/Assistant) | `4` (atDepth) + role | `AT_DEPTH` | `at_depth` |
| Before Example Messages | `5` (EMTop) | `BEFORE_EXAMPLES` | `before_examples` |
| After Example Messages | `6` (EMBottom) | -- | -- |
| Named Outlet | `7` (outlet) | -- | -- |

### 4.2 Analysis

The Bannered Mare implements 4 of ST's 8 positions. The omissions:

- **Author's Note positions (ANTop/ANBottom)**: ST's Author's Note is a separate system
  prompt component. The Bannered Mare's prompt template system (`PromptTemplate.component_order`)
  handles prompt section ordering differently and does not have a dedicated Author's Note
  component.
- **After Example Messages (EMBottom)**: Only "before examples" is supported. Adding a
  symmetric "after" position would be straightforward.
- **Named Outlet**: ST's outlet system allows lore content to be referenced via
  `{{outlet::Name}}` macros anywhere in the prompt template. This requires a macro/template
  engine that The Bannered Mare does not currently implement.

### 4.3 Prompt Integration

The Bannered Mare's `PromptTemplate` model defines a `component_order` list that includes three
world lore slots: `world_lore_before_character`, `world_lore_after_character`, and
`world_lore_before_examples`. The service method `get_entries_by_position()` groups
activated entries by `InsertionPosition`, returning a dict keyed by position enum for the
prompt builder to consume.

SillyTavern assembles lore into position-specific strings (`worldInfoBefore`,
`worldInfoAfter`, etc.) that are injected during prompt construction. AT_DEPTH entries
are inserted as discrete messages at the specified chat history depth.


## 5. Token Budget

### 5.1 Budget Calculation

| Aspect | SillyTavern | The Bannered Mare |
|---|---|---|
| Input | Percentage of max context (`world_info_budget`, default 25%) capped by `world_info_budget_cap`. | Absolute token count passed as `token_budget` parameter. |
| Minimum | Always at least 1 token. | `0` means unlimited (no budget enforcement). |
| Calculation | `floor(budget% * maxContext / 100)`, then apply cap. | Caller provides the computed value directly. |

### 5.2 Budget Enforcement

| Aspect | SillyTavern | The Bannered Mare |
|---|---|---|
| Enforcement point | After probability roll, before adding to activated set. | After sorting by priority, during budget accumulation loop. |
| `ignoreBudget` handling | Entry bypasses budget check entirely; scan continues past overflow. | Field exists on the data model but is NOT consumed by `activate_entries()` -- the engine treats all entries equally during budget enforcement. This is a known gap (noted in a code comment). |
| Overflow behavior | Budget overflow does not terminate the scan. Non-budget entries later in sort order can still activate. | Budget enforcement stops adding entries once the limit is reached. No post-overflow scanning. |
| Overflow alert | Toast notification via `world_info_overflow_alert`. | No user-facing notification. |

### 5.3 Token Counting

Both systems delegate token counting to a tokenizer service. SillyTavern uses
`getTokenCountAsync()` (async, likely tiktoken-based). The Bannered Mare uses a synchronous
`TokenizerService.count_tokens()` method.


## 6. Recursive Scanning

### 6.1 SillyTavern: Full Implementation

ST's recursive scanning is a multi-pass system with four scan states:

| State | Behavior |
|---|---|
| `INITIAL` | First pass: scan chat buffer against all entries. |
| `RECURSION` | Subsequent passes: activated entry content is added to the scan buffer, potentially triggering new entries. |
| `MIN_ACTIVATIONS` | If fewer entries activated than `world_info_min_activations`, scan depth increases incrementally. Recursion buffer excluded. |
| `NONE` | Terminal state. |

Control fields per entry:
- `excludeRecursion`: Entry cannot be activated during recursion passes.
- `preventRecursion`: Entry's content is not added to the recursion buffer.
- `delayUntilRecursion`: Entry only activates during recursion, with tiered delay levels.

Infinite loop prevention: max recursion steps, budget exhaustion, no-new-entries termination,
`preventRecursion` flag.

### 6.2 The Bannered Mare: Not Implemented

`activate_entries()` performs a single pass. There is no recursion buffer, no multi-pass
loop, and no scan state machine. The entry model has no fields for recursion control
(`excludeRecursion`, `preventRecursion`, `delayUntilRecursion`).

### 6.3 Assessment

Recursive scanning is one of ST's most powerful features for complex world-building (e.g.,
mentioning a faction name triggers a faction entry, whose content mentions a leader name,
triggering the leader's entry). It is also one of the most complex to implement correctly
and a common source of performance issues in large lorebooks. The Bannered Mare's single-pass
design is simpler and more predictable but cannot express entry chaining.


## 7. Group / Mutual Exclusion

### 7.1 SillyTavern: Full Implementation

ST's `filterByInclusionGroups()` provides mutual exclusion within named groups:

- Entries declare group membership via comma-separated `group` labels.
- Only one entry per group activates per generation.
- Selection algorithm (in priority order):
  1. Timed effects filter (sticky entries win over non-sticky).
  2. Group scoring (highest key match count wins, if enabled).
  3. Already-activated check (previous-pass winners block new candidates).
  4. Priority override (`groupOverride=true` wins unconditionally).
  5. Weighted random selection using `groupWeight`.

### 7.2 The Bannered Mare: Not Implemented

The entry model has no `group`, `groupOverride`, `groupWeight`, or `useGroupScoring`
fields. All matching entries activate independently with no mutual exclusion constraints.

### 7.3 Assessment

Group exclusion is valuable for scenarios like "activate one of several weather entries"
or "only one faction reputation level at a time." Without it, users must manually
ensure conflicting entries have non-overlapping keywords or use secondary keys for
exclusion logic.


## 8. Timed Effects

### 8.1 SillyTavern: Full Implementation

Three timed effect types, tracked in `chat_metadata.timedWorldInfo`:

| Effect | Behavior |
|---|---|
| `sticky` | Entry stays active for N messages after first activation, bypassing keyword checks. Triggers cooldown on expiry if configured. |
| `cooldown` | Entry is suppressed for N messages after activation (or after sticky expires). |
| `delay` | Entry cannot activate until the chat has at least N messages. Computed from entry field and chat length. |

State is persisted per-chat and survives page reloads.

### 8.2 The Bannered Mare: Not Implemented

No `sticky`, `cooldown`, or `delay` fields on the entry model. No timed effect state
tracking. All entries are evaluated purely against the current scan text on every request.

### 8.3 Assessment

Timed effects enable dynamic storytelling mechanics (e.g., a curse that persists for 5
messages, a cooldown on weather changes, lore that only appears after the story progresses).
These require per-chat state tracking, which adds persistence complexity. The Bannered Mare's
stateless activation model is simpler to reason about but cannot express temporal entry
behavior.


## 9. Import Formats

### 9.1 SillyTavern: Multi-Format Support

| Format | Detection | Key Mapping Highlights |
|---|---|---|
| SillyTavern native | Has `entries` property | Direct use |
| NovelAI Lorebook | `lorebookVersion` present | `keys` -> `key`, `text` -> `content`, `budgetPriority` -> `order` |
| Agnai Memory Book | `kind === 'memory'` | `keywords` -> `key`, `entry` -> `content`, `weight` -> `order` |
| Risu Lorebook | `type === 'risu'` | `key` (comma-split), `secondkey`, `alwaysActive` -> `constant` |
| Character Book (V2 Spec) | Via `convertCharacterBook()` | Full mapping including `extensions.*` namespace for ST-specific fields |
| PNG with embedded data | `.png` file extension | Extracts `naidata` from metadata, routes through above converters |

Original Character Book data is preserved as `originalData` for round-trip fidelity.

### 9.2 The Bannered Mare: API-Only

The Bannered Mare provides a RESTful CRUD API (`POST /api/lorebooks`, `POST /api/lorebooks/{id}/entries`)
with Pydantic schema validation. There is no file import endpoint and no format converters.

Import of external lorebook formats would need to be handled by a client application or a
future import service that maps external formats to `LoreEntryCreate` / `LorebookCreate`
schemas.

### 9.3 Assessment

ST's multi-format import is critical for its role as a community platform where users share
character cards with embedded lorebooks across different tools. As a backend API, The Bannered Mare
delegates import concerns to its consumers but would benefit from a Character Card V2
import endpoint to enable direct card ingestion.


## 10. Additional Features in SillyTavern Not Present in The Bannered Mare

| Feature | Description | Complexity to Add |
|---|---|---|
| Probability roll | Per-entry activation chance (0-100%). | Low -- add `probability` and `use_probability` fields, random check in engine. |
| Trigger type filter | Entry only activates for specific generation types (normal, continue, impersonate, swipe, regenerate). | Low -- add `triggers` list field, check against current generation type. |
| Content decorators | `@@activate` / `@@dont_activate` parsed from content prefix lines. | Low -- string parsing before activation check. |
| Character filter | Per-entry include/exclude list for specific characters or tags. | Medium -- add `character_filter` JSON field, evaluate during activation. |
| Scan target flags | 6 boolean flags to include character description, personality, persona, scenario, etc. in per-entry scan. | Medium -- requires refactoring scan buffer from flat string to structured source. |
| Macro substitution | `{{char}}`, `{{user}}`, etc. expanded in keys and content at activation time. | Medium -- requires a template engine for lore content. |
| Lore sources | Four distinct sources (chat, persona, character, global) with configurable priority ordering. | Medium -- The Bannered Mare has character + global. Chat-bound and persona-bound lorebooks would need schema additions. |
| Insertion strategy | Global setting for character-first vs global-first vs interleaved entry ordering. | Low -- add configuration and sort logic. |
| Event system | Hooks at scan-done, entries-loaded, settings-changed. | Medium -- depends on broader event architecture. |
| Group scoring | Score entries by key match count for group winner selection. | Medium -- requires groups feature first. |
| Named outlets | Lore injected via `{{outlet::Name}}` macros in prompt templates. | High -- requires macro/template engine integration. |
| Min activations | Auto-extend scan depth until N entries activate. | Medium -- requires multi-pass scan buffer with depth control. |


## 11. Architectural Differences Summary

| Dimension | SillyTavern | The Bannered Mare |
|---|---|---|
| Engine location | Client-side (browser JavaScript) | Server-side (Python) |
| Persistence | JSON files (filesystem) | PostgreSQL (relational) |
| Statefulness | Stateful multi-pass with scan state machine | Stateless single-pass pure function |
| Entry field count | 35+ | 18 |
| Insertion positions | 8 | 4 |
| Activation features | Keywords, regex, probability, decorators, vectorized, timed effects, recursion, groups | Keywords, regex, constants |
| Budget model | Percentage-of-context with absolute cap | Absolute token count (caller-computed) |
| API style | Internal function calls + slash commands + 5 REST endpoints | RESTful CRUD (7 endpoints) + activation service method |
| Import formats | 5 (native, NovelAI, Agnai, Risu, Character Book V2) + PNG extraction | None (API-only) |
| Type safety | Runtime JavaScript (no type checking) | SQLAlchemy models + Pydantic schemas + BasedPyright strict mode |


## 12. The Bannered Mare Design Strengths

Despite the smaller feature surface, The Bannered Mare's implementation has several engineering
advantages:

1. **Separation of concerns**: Activation logic (`activation_engine.py`) is a pure function
   with no side effects, making it trivially testable. ST's `checkWorldInfo()` mixes
   activation, budget enforcement, timed effect tracking, recursion state management, and
   event emission in a single 500-line async function.

2. **Relational data model**: Lorebooks and entries live in normalized tables with FK
   constraints, cascade deletes, and proper indexing. ST's flat JSON files require
   full-file rewrites and manual UID management.

3. **Clean layering**: Router (HTTP) -> Service (business logic) -> Repository (data
   access) -> Activation Engine (pure computation). Each layer has a single responsibility.

4. **Type safety**: The full stack is statically typed -- SQLAlchemy mapped columns, Pydantic
   schemas for API validation, string enums for positions and logic modes, and strict
   BasedPyright checking.

5. **Priority vs order separation**: Using distinct `priority` (insertion ordering) and
   `order` (display ordering) fields avoids the ambiguity of ST's single `order` field
   that serves both purposes.

6. **Server-side activation**: Running the engine server-side means consistent behavior
   regardless of client, no client-side performance concerns with large lorebooks, and the
   ability to cache or optimize activation at the infrastructure level.
