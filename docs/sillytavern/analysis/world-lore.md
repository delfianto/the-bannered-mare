# SillyTavern v1.17.0 -- World Lore (World Info / Lorebook) System Analysis

> Source: `public/scripts/world-info.js` (6,273 lines, client-side engine)
> Backend: `src/endpoints/worldinfo.js` (158 lines, file CRUD)

The World Lore system is SillyTavern's most complex subsystem. It functions as a dynamic
context injection engine: entries containing lore content are conditionally activated by
keyword scanning against the chat history, then inserted into specific positions within
the LLM prompt. The entire activation engine runs client-side in the browser; the server
is a thin JSON file store.


## 1. Entry Data Model

Defined at `public/scripts/world-info.js:3984` in `newWorldInfoEntryDefinition`. Every WI
entry carries 35+ fields, organized here by function.

### 1.1 Trigger / Matching Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `key` | `string[]` | `[]` | Primary keywords (comma-separated). At least one must match for activation. Supports plain text and `/regex/flags` syntax. |
| `keysecondary` | `string[]` | `[]` | Secondary keywords (Optional Filter). Used with `selectiveLogic` to apply AND/NOT conditions after a primary match. |
| `selective` | `boolean` | `true` | Enables secondary keyword evaluation. All entries are selective by default in current versions. |
| `selectiveLogic` | `enum(0-3)` | `0` (AND_ANY) | Logic for combining secondary keys. See Section 2 for details. |
| `constant` | `boolean` | `false` | Always-on entry -- bypasses all keyword scanning. Activated unconditionally every generation. |
| `vectorized` | `boolean` | `false` | Entry activated via vector/embedding similarity search (handled by the `vectors` extension, not the core engine). |
| `probability` | `number` | `100` | Percentage chance (0-100) of activation after keyword match. Rolled per generation. |
| `useProbability` | `boolean` | `true` | Whether to apply the probability roll at all. |
| `triggers` | `string[]` | `[]` | Generation type filter. If non-empty, entry only activates for listed trigger types: `normal`, `continue`, `impersonate`, `swipe`, `regenerate`, `quiet`. Empty means "all triggers". |

### 1.2 Content Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `content` | `string` | `''` | The lore text injected into the prompt. Supports SillyTavern macros (substituted at activation time via `substituteParams`). May begin with decorator lines (see `@@activate`, `@@dont_activate`). |
| `comment` | `string` | `''` | Title/memo for the entry. Used for display in the editor. Not sent to the LLM. |
| `addMemo` | `boolean` | `false` | Whether to display the comment/memo field in the editor header. |

### 1.3 Activation Control Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `disable` | `boolean` | `false` | Completely disables the entry. Skipped during scanning. |
| `automationId` | `string` | `''` | ID for triggering Quick Replies or other automation when this entry activates. |

### 1.4 Insertion / Positioning Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `position` | `enum(0-7)` | `0` (before) | Where in the prompt the content is injected. See Section 4 for all 8 positions. |
| `depth` | `number` | `4` | When `position=4` (atDepth), specifies how many messages from the end to inject at. |
| `role` | `enum(0-2)` | `0` (SYSTEM) | When `position=4`, the message role: `0`=System, `1`=User, `2`=Assistant. |
| `order` | `number` | `100` | Insertion priority. Higher-order entries are placed first. Entries are sorted descending by order, then assembled via `unshift` (so order=999 ends up at the top of its position group). |
| `outletName` | `string` | `''` | When `position=7` (outlet), the named outlet to route content to. Referenced via `{{outlet::Name}}` macro in prompts. |

### 1.5 Token Budget Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `ignoreBudget` | `boolean` | `false` | If true, this entry is injected even after the WI token budget is exhausted. All other activation checks still apply. |

### 1.6 Recursion Control Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `excludeRecursion` | `boolean` | `false` | "Non-recursable" -- this entry cannot be activated by recursive scanning (i.e., by content from other activated entries). |
| `preventRecursion` | `boolean` | `false` | "Prevent further recursion" -- this entry's content is not added to the recursion buffer, so it cannot trigger other entries. |
| `delayUntilRecursion` | `number` | `0` | Entry only activates during recursion passes. Supports tiered levels: entries with `delayUntilRecursion=1` activate on the first recursion delay tier, `=2` on the second, etc. |

### 1.7 Group / Mutual Exclusion Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `group` | `string` | `''` | Inclusion group label. Supports multiple comma-separated groups. Only one entry per group is activated per generation. |
| `groupOverride` | `boolean` | `false` | "Prioritize" -- if true, this entry wins the group selection unconditionally (highest `order` among prioritized entries wins). |
| `groupWeight` | `number` | `100` | Relative weight for weighted random selection within the group. Higher = more likely to win. |
| `useGroupScoring` | `boolean?` | `null` | Per-entry override for group scoring (key match count comparison). `null` = use global setting. |

### 1.8 Timed Effect Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `sticky` | `number?` | `null` | If set, entry stays active for N messages after first activation, regardless of keyword matching. |
| `cooldown` | `number?` | `null` | If set, entry cannot activate for N messages after its sticky period ends (or after activation if not sticky). |
| `delay` | `number?` | `null` | Entry cannot activate until the chat has at least N messages. |

### 1.9 Scan Target Fields (Additional Matching Sources)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `matchPersonaDescription` | `boolean` | `false` | Also scan user persona description for keyword matches. |
| `matchCharacterDescription` | `boolean` | `false` | Also scan character description. |
| `matchCharacterPersonality` | `boolean` | `false` | Also scan character personality. |
| `matchCharacterDepthPrompt` | `boolean` | `false` | Also scan character's note / depth prompt. |
| `matchScenario` | `boolean` | `false` | Also scan character scenario. |
| `matchCreatorNotes` | `boolean` | `false` | Also scan character creator notes. |

### 1.10 Per-Entry Scan Override Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `scanDepth` | `number?` | `null` | Per-entry override for scan depth (how many messages to scan). `null` = use global setting. |
| `caseSensitive` | `boolean?` | `null` | Per-entry override for case sensitivity. `null` = use global setting. |
| `matchWholeWords` | `boolean?` | `null` | Per-entry override for whole-word matching. `null` = use global setting. |

### 1.11 Character Filter Fields

These are stored as a nested `characterFilter` object on the entry (not as top-level
fields), but exposed as virtual fields in the slash command API:

| Field | Storage Path | Type | Default | Purpose |
|---|---|---|---|---|
| `characterFilterNames` | `characterFilter.names` | `string[]` | `[]` | List of character filenames this entry applies to. |
| `characterFilterTags` | `characterFilter.tags` | `string[]` | `[]` | List of tag IDs this entry applies to. |
| `characterFilterExclude` | `characterFilter.isExclude` | `boolean` | `false` | If false, entry only activates FOR listed characters. If true, entry activates for everyone EXCEPT listed characters. |

### 1.12 Internal / Computed Fields

These are not part of `newWorldInfoEntryDefinition` but are added at runtime:

| Field | Type | Purpose |
|---|---|---|
| `uid` | `number` | Unique identifier within a lorebook. Assigned at creation, never changes. |
| `world` | `string` | Name of the lorebook file this entry belongs to. Attached during `getSortedEntries`. |
| `hash` | `number` | String hash of the entry JSON. Computed during sorting. Used to identify entries across timed effects. |
| `decorators` | `string[]` | Parsed from content prefix lines (`@@activate`, `@@dont_activate`). Stripped from content before injection. |
| `displayIndex` | `number` | Visual ordering in the editor UI. |


## 2. Activation Engine (`checkWorldInfo`)

**Location:** `public/scripts/world-info.js:4579`

This is the core algorithm. It is an `async` function that accepts the chat messages
(reversed order), the maximum context size, a dry-run flag, and global scan data. It
returns categorized WI content for each insertion position.

### 2.1 High-Level Flow

```
1. Construct WorldInfoBuffer from chat messages + global scan data
2. Add extension prompt injections to the scan buffer
3. Calculate token budget: floor(world_info_budget% * maxContext), capped by world_info_budget_cap
4. Load and sort all entries via getSortedEntries()
5. Initialize WorldInfoTimedEffects (check sticky/cooldown/delay state)
6. Calculate delayUntilRecursion level tiers
7. MAIN LOOP (while scanState != NONE):
   a. For each entry in sortedEntries:
      - Skip: already activated, disabled, failed probability, wrong trigger type
      - Skip: character filter mismatch, tag filter mismatch
      - Skip: delay active, cooldown active (unless sticky), delayUntilRecursion not satisfied
      - Skip: excludeRecursion during RECURSION state
      - Activate: @@activate decorator, external activation, constant, sticky
      - Test: primary keyword match against scan buffer
      - Test: secondary keywords with selectiveLogic
      - If all pass -> add to activatedNow set
   b. Sort newly activated entries (sticky first, then by original sort order)
   c. Filter by inclusion groups (mutual exclusion)
   d. Probability roll for each surviving entry
   e. Token budget check (cumulative), skip if overflowed (unless ignoreBudget)
   f. Add to allActivatedEntries map
   g. Determine next scan state:
      - RECURSION if recursive enabled and new entries found
      - MIN_ACTIVATIONS if min activation count not met
      - NONE if nothing new
   h. Add activated content to recursion buffer
   i. Fire WORLDINFO_SCAN_DONE event
8. Build prompt output: categorize entries by position
9. Set timed effects for activated entries
10. Return structured result
```

### 2.2 Primary vs. Secondary Keywords

**Primary keys** (`entry.key`): An array of strings or regex patterns. A primary match
requires **at least one** key to be found in the scan buffer. Each key is passed through
`substituteParams()` for macro expansion before matching.

**Secondary keys** (`entry.keysecondary`): Only evaluated if a primary match succeeds and
the entry has non-empty secondary keys. The `selectiveLogic` enum controls how they
combine:

```javascript
// public/scripts/world-info.js:33-38
export const world_info_logic = {
    AND_ANY: 0,   // Primary match + ANY secondary key matches
    NOT_ALL: 1,   // Primary match + NOT ALL secondary keys match (at least one missing)
    NOT_ANY: 2,   // Primary match + NO secondary keys match
    AND_ALL: 3,   // Primary match + ALL secondary keys match
};
```

The logic is implemented at line 4813 in `matchSecondaryKeys()`:
- `AND_ANY`: Short-circuits true on first secondary match found.
- `NOT_ALL`: Short-circuits true on first secondary key NOT found.
- `NOT_ANY`: True only if zero secondary keys match.
- `AND_ALL`: True only if every secondary key matches.

### 2.3 Keyword Matching Mechanics

Implemented in `WorldInfoBuffer.matchKeys()` at line 337:

1. **Regex detection**: If the key is a `/pattern/flags` string, it is parsed into a
   `RegExp` and tested against the haystack. This bypasses all other matching options.
2. **Case sensitivity**: Controlled per-entry (`entry.caseSensitive`) or globally
   (`world_info_case_sensitive`). When insensitive, both haystack and needle are
   lowercased.
3. **Whole-word matching**: When enabled, single-word keys use a regex boundary check
   (`(?:^|\W)(keyword)(?:$|\W)`). Multi-word phrases use simple `includes()`.
4. **Default**: Plain substring match via `String.includes()`.

### 2.4 Decorators

Parsed from content prefix lines at `parseDecorators()` (line 4522):
- `@@activate` -- forces the entry to activate unconditionally (like `constant`, but
  defined in content).
- `@@dont_activate` -- suppresses the entry unconditionally.
- `@@@decorator` -- escaped decorator (the leading `@` is stripped, treated as content).


## 3. Scan Buffer Construction

**Class:** `WorldInfoBuffer` at line 199.

### 3.1 Buffer Components

The buffer has four internal layers:

| Layer | Description |
|---|---|
| `#depthBuffer[]` | Chat messages, indexed by depth (0 = most recent). Populated from the reversed chat array at construction. Max size: `MAX_SCAN_DEPTH` (1000). |
| `#globalScanData` | Chat-independent context: persona description, character description, character personality, depth prompt, scenario, creator notes, trigger type. |
| `#recurseBuffer[]` | Strings added by recursive scanning (activated entry content from previous passes). |
| `#injectBuffer[]` | Extension prompt injections marked with `scan: true`. |

### 3.2 Buffer Assembly (`get` method, line 279)

When an entry requests its scan text:

```
1. Determine depth: entry.scanDepth ?? globalDepth + skew
2. Slice depthBuffer[startDepth..depth]
3. Join with \n + MATCHER character (\x01)
4. Conditionally append global scan sources based on entry flags:
   - matchPersonaDescription -> personaDescription
   - matchCharacterDescription -> characterDescription
   - matchCharacterPersonality -> characterPersonality
   - matchCharacterDepthPrompt -> characterDepthPrompt
   - matchScenario -> scenario
   - matchCreatorNotes -> creatorNotes
5. Append injectBuffer contents
6. If NOT in MIN_ACTIVATIONS state: append recurseBuffer contents
```

The `MATCHER` sentinel character (`\x01`) is prepended to handle boundary matching at
the start of the buffer text.

### 3.3 Depth and Skew

- **Global scan depth** (`world_info_depth`): Default 2. Controls how many recent messages
  are scanned.
- **Per-entry scan depth** (`entry.scanDepth`): Overrides the global depth for that
  specific entry.
- **Skew** (`#skew`): Incremented by `advanceScan()` during MIN_ACTIVATIONS mode. Each
  increment extends the scan range by one additional message deeper into history.
- **startDepth** (`#startDepth`): Normally 0. Could be offset if needed.


## 4. Insertion Positions

Defined at `public/scripts/world-info.js:855`:

```javascript
export const world_info_position = {
    before: 0,     // Before Character Definitions
    after: 1,      // After Character Definitions
    ANTop: 2,      // Before Author's Note
    ANBottom: 3,   // After Author's Note
    atDepth: 4,    // At specific depth in chat (with role)
    EMTop: 5,      // Before Example Messages
    EMBottom: 6,   // After Example Messages
    outlet: 7,     // Named outlet (macro-referenced)
};
```

### 4.1 Position Details

| Value | UI Label | Behavior |
|---|---|---|
| 0 | `Before Char` | Content prepended before character definitions in the system prompt. Entries joined with `\n` into `worldInfoBefore`. |
| 1 | `After Char` | Content appended after character definitions. Entries joined into `worldInfoAfter`. |
| 2 | `Before AN` | Content inserted before the Author's Note block. The AN prompt string is recomposed as `[ANTop entries]\n[original AN]\n[ANBottom entries]`. |
| 3 | `After AN` | Content inserted after the Author's Note block. |
| 4 + role=0 | `@D System` | Injected at a specific message depth as a System message. Entries at the same depth+role are grouped together. Depth is specified by `entry.depth` (default 4). |
| 4 + role=1 | `@D User` | Same as above but as a User message. |
| 4 + role=2 | `@D Assistant` | Same as above but as an Assistant message. |
| 5 | `Before EM` | Before Example Messages block. Wrapped with `{ position: wi_anchor_position.before }`. |
| 6 | `After EM` | After Example Messages block. Wrapped with `{ position: wi_anchor_position.after }`. |
| 7 | `Outlet` | Not placed into the prompt directly. Collected into `WIOutletEntries[outletName]` and accessed via `{{outlet::Name}}` macros elsewhere in the prompt template. |

### 4.2 Assembly Order

Entries are sorted descending by `order` (line 5066: `sort((a, b) => b.order - a.order)`),
then assembled via `unshift()`. This means within each position bucket, higher-order
entries appear earlier (closer to the top) in the output text.


## 5. Token Budget

### 5.1 Calculation (line 4606)

```javascript
let budget = Math.round(world_info_budget * maxContext / 100) || 1;

if (world_info_budget_cap > 0 && budget > world_info_budget_cap) {
    budget = world_info_budget_cap;
}
```

- `world_info_budget`: Percentage of max context (default 25%). Range: 1-100.
- `world_info_budget_cap`: Absolute token cap. 0 = disabled. If set and the percentage
  calculation exceeds it, the cap wins.
- The budget is always at least 1 token.

### 5.2 Budget Enforcement (line 4924)

For each activated entry (after probability checks pass):

```javascript
if (!entry.ignoreBudget && (textToScanTokens + (await getTokenCountAsync(newContent))) >= budget) {
    token_budget_overflowed = true;
    continue; // skip this entry
}
```

- `textToScanTokens` is the token count of all previously activated content.
- `newContent` accumulates the content of entries being processed in the current loop pass.
- Once budget overflows, all subsequent non-`ignoreBudget` entries are skipped.
- `ignoreBudget` entries bypass the budget check entirely and are always included (assuming
  they pass all other checks).
- Budget overflow does NOT terminate the scan loop -- it only prevents new entries from
  being added. This allows `ignoreBudget` entries later in the sort order to still activate.

### 5.3 Overflow Alert

When `world_info_overflow_alert` is enabled, a toast warning is shown to the user when the
budget is reached (line 4929).


## 6. Recursive Scanning

### 6.1 Scan States

Defined at line 43:

```javascript
export const scan_state = {
    NONE: 0,           // Stop scanning
    INITIAL: 1,        // First pass
    RECURSION: 2,      // Triggered by newly activated entries
    MIN_ACTIVATIONS: 3 // Triggered by min activation depth extension
};
```

### 6.2 Recursion Flow

1. **INITIAL** pass scans the chat buffer and activates matching entries.
2. If `world_info_recursive` is enabled and new entries were found (that don't have
   `preventRecursion`), the content of those entries is added to the recursion buffer
   (line 5002-5006) and `scanState` advances to **RECURSION**.
3. In **RECURSION**, the buffer now includes the previously activated content. This
   allows entries to chain-trigger: Entry A's content may contain keywords that activate
   Entry B.
4. Entries with `excludeRecursion=true` are skipped during RECURSION passes.
5. Entries with `preventRecursion=true` do not contribute their content to the recursion
   buffer, breaking the chain.
6. The loop continues as long as new entries are found and the budget is not exhausted.

### 6.3 Recursion Delay Levels

Entries with `delayUntilRecursion` set to a numeric value participate in tiered recursion:

```javascript
// line 4624-4632
const availableRecursionDelayLevels = [...new Set(sortedEntries
    .filter(entry => entry.delayUntilRecursion)
    .map(entry => entry.delayUntilRecursion === true ? 1 : entry.delayUntilRecursion),
)].sort((a, b) => a - b);
```

Initially, only entries at the first (lowest) delay level are eligible. When no more
entries match at the current level, the engine advances to the next level (line 4992-4996).
This enables controlled multi-phase activation.

### 6.4 Infinite Loop Prevention

1. **`world_info_max_recursion_steps`**: Hard cap on loop iterations (line 4638). When
   set, min activations is disabled (mutually exclusive -- line 6106-6109).
2. **Budget overflow**: Once the token budget is exhausted, no new entries can activate
   (except `ignoreBudget`), which naturally terminates recursion.
3. **No new entries**: If a pass produces zero new entries, the loop drops to
   `scan_state.NONE` and stops.
4. **`preventRecursion`**: Entries that set this flag do not feed the recursion buffer.

### 6.5 Min Activations Mode

When `world_info_min_activations > 0` and fewer entries have activated than the minimum:
- The buffer's scan depth is incremented by one (`buffer.advanceScan()`).
- The state becomes `MIN_ACTIVATIONS`, and another full scan pass runs with the extended
  depth.
- This continues until the minimum is met, the depth ceiling
  (`world_info_min_activations_depth_max`) is reached, or the chat length is exceeded.
- Crucially, the recursion buffer is NOT included in `MIN_ACTIVATIONS` scans (line 323),
  preventing activated entry content from influencing deeper scans.


## 7. Group / Mutual Exclusion

**Core function:** `filterByInclusionGroups()` at line 5251.

### 7.1 Group Assignment

An entry's `group` field is a comma-separated string. Each group label creates a separate
mutual exclusion constraint:

```javascript
// line 5254-5262
const grouped = newEntries.filter(x => x.group).reduce((acc, item) => {
    item.group.split(/,\s*/).filter(x => x).forEach(group => {
        if (!acc[group]) { acc[group] = []; }
        acc[group].push(item);
    });
    return acc;
}, {});
```

### 7.2 Selection Algorithm

For each group with multiple activated entries, the winner is determined in this priority
order:

1. **Timed Effects Filter** (`filterGroupsByTimedEffects`, line 5200):
   - If any entry in the group is currently sticky, all non-sticky entries are removed.
   - Entries on cooldown or delay are removed.

2. **Group Scoring** (`filterGroupsByScoring`, line 5155):
   - If `useGroupScoring` is enabled (globally or per-entry), entries are scored by
     how many of their keys match in the buffer (`buffer.getScore()`).
   - Only the entry(ies) with the highest score survive. Ties are preserved for the
     next selection step.
   - Scoring counts both primary and secondary key matches (for AND_ANY and AND_ALL
     logic types).

3. **Already activated check** (line 5294): If any entry from this group was already
   activated in a previous loop pass, all new candidates are removed.

4. **Priority Override** (`groupOverride`, line 5307): Entries with `groupOverride=true`
   win unconditionally. If multiple have priority, the one with the highest `order`
   value wins (they are pre-sorted by `sortFn`).

5. **Weighted Random** (line 5315-5328): If no priority entry exists, a weighted random
   roll selects the winner using `groupWeight` values:
   ```javascript
   const totalWeight = group.reduce((acc, item) => acc + (item.groupWeight ?? 100), 0);
   const rollValue = Math.random() * totalWeight;
   ```


## 8. Timed Effects

**Class:** `WorldInfoTimedEffects` at line 479.

### 8.1 Sticky

- When an entry with `sticky=N` activates, a timed effect is stored in
  `chat_metadata.timedWorldInfo.sticky`.
- The effect records `start` (current chat length) and `end` (start + N).
- While active, the entry activates unconditionally (bypasses keyword scanning) on every
  generation (line 4769).
- When the sticky period expires, if the entry also has a `cooldown`, the cooldown effect
  begins immediately (line 518-528 in `#onEnded.sticky`).

### 8.2 Cooldown

- When an entry with `cooldown=N` has its sticky period expire (or activates without
  sticky), a cooldown effect is stored in `chat_metadata.timedWorldInfo.cooldown`.
- While on cooldown, the entry is suppressed from activation (line 4724).
- Cooldown entries that are also sticky are NOT suppressed (sticky overrides cooldown).

### 8.3 Delay

- An entry with `delay=N` cannot activate until `chat.length >= N` (line 6672-676).
- Unlike sticky/cooldown, delay is not stored in chat metadata -- it is computed purely
  from the entry's field and the current chat length.
- Delay-suppressed entries are skipped during scanning (line 4719).

### 8.4 State Persistence

Sticky and cooldown states are persisted in `chat_metadata.timedWorldInfo`, which is saved
as part of the chat file. This means timed effects survive page reloads and persist across
sessions for the same chat.

The structure:
```javascript
chat_metadata.timedWorldInfo = {
    sticky: {
        "worldName.uid": { hash, start, end, protected }
    },
    cooldown: {
        "worldName.uid": { hash, start, end, protected }
    }
}
```

The `protected` flag prevents removal of an effect if the chat hasn't advanced (line 626).
Effects with non-matching hashes (entry was modified) or expired intervals are cleaned up
each evaluation pass.


## 9. Import / Export

### 9.1 Import (`importWorldInfo`, line 5713)

The import function handles multiple file formats:

| Format | Detection | Converter Function | Key Mapping |
|---|---|---|---|
| **SillyTavern native** | Has `entries` property | None (direct use) | N/A |
| **NovelAI Lorebook** | `jsonData.lorebookVersion !== undefined` | `convertNovelLorebook()` (line 5430) | `keys` -> `key`, `text` -> `content`, `displayName` -> `comment`, `contextConfig.budgetPriority` -> `order` |
| **Agnai Memory Book** | `jsonData.kind === 'memory'` | `convertAgnaiMemoryBook()` (line 5340) | `keywords` -> `key`, `entry` -> `content`, `name` -> `comment`, `weight` -> `order`, `enabled` -> `!disable` |
| **Risu Lorebook** | `jsonData.type === 'risu'` | `convertRisuLorebook()` (line 5385) | `key` (comma-split) -> `key[]`, `secondkey` -> `keysecondary[]`, `comment` -> `comment`, `content` -> `content`, `alwaysActive` -> `constant`, `insertorder` -> `order`, `activationPercent` -> `probability` |
| **Character Book** (V2 Spec) | Via `convertCharacterBook()` (line 5480) | Inline conversion | `keys` -> `key`, `secondary_keys` -> `keysecondary`, `insertion_order` -> `order`, `position` -> `position`, plus `extensions.*` for all ST-specific fields |
| **PNG with embedded data** | `.png` file extension | Extracts `naidata` from PNG metadata | Parsed then routed through above converters |

All converters produce output in ST's native format by spreading `newWorldInfoEntryTemplate`
as a base and overwriting the source-specific fields.

### 9.2 Character Book Conversion Details

`convertCharacterBook()` (line 5480) is the most complete converter. It maps the
Character Card V2 specification's `character_book.entries[]` to ST entries. All
ST-specific extensions are read from the `entry.extensions` namespace:

```javascript
// line 5500-5533 (abbreviated)
position: entry.extensions?.position ?? (entry.position === 'before_char' ? 0 : 1),
excludeRecursion: entry.extensions?.exclude_recursion ?? false,
preventRecursion: entry.extensions?.prevent_recursion ?? false,
delayUntilRecursion: entry.extensions?.delay_until_recursion ?? false,
probability: entry.extensions?.probability ?? 100,
depth: entry.extensions?.depth ?? DEFAULT_DEPTH,
selectiveLogic: entry.extensions?.selectiveLogic ?? world_info_logic.AND_ANY,
group: entry.extensions?.group ?? '',
groupOverride: entry.extensions?.group_override ?? false,
groupWeight: entry.extensions?.group_weight ?? DEFAULT_WEIGHT,
scanDepth: entry.extensions?.scan_depth ?? null,
caseSensitive: entry.extensions?.case_sensitive ?? null,
matchWholeWords: entry.extensions?.match_whole_words ?? null,
useGroupScoring: entry.extensions?.use_group_scoring ?? null,
role: entry.extensions?.role ?? extension_prompt_roles.SYSTEM,
sticky: entry.extensions?.sticky ?? null,
cooldown: entry.extensions?.cooldown ?? null,
delay: entry.extensions?.delay ?? null,
triggers: entry.extensions?.triggers || [],
ignoreBudget: entry.extensions?.ignore_budget ?? false,
```

### 9.3 Export

Export is straightforward -- the raw JSON data object is serialized and downloaded:

```javascript
// line 2542-2544
const jsonValue = JSON.stringify(data);
const fileName = `${name}.json`;
download(jsonValue, fileName, 'application/json');
```

### 9.4 Original Data Preservation

When importing a Character Book, the original `characterBook` object is preserved as
`data.originalData` (line 5481). Functions `setWIOriginalDataValue()` and
`deleteWIOriginalDataValue()` (lines 2676, 2694) keep this in sync when entries are
modified, allowing round-trip fidelity when re-exporting to Character Card format.


## 10. Backend CRUD (`src/endpoints/worldinfo.js`)

The server is 158 lines of Express.js, providing a minimal JSON file store.

### 10.1 Storage Format

- Each lorebook is a single JSON file: `{worlds_directory}/{name}.json`
- Filenames are sanitized via the `sanitize-filename` package.
- Files are written atomically using `write-file-atomic` to prevent corruption.
- The JSON structure is `{ entries: { [uid]: EntryObject }, originalData?: {...}, ... }`.

### 10.2 API Endpoints

All routes are mounted under `/api/worldinfo/`:

| Method | Path | Purpose | Request Body | Response |
|---|---|---|---|---|
| POST | `/list` | List all lorebooks | (none) | `[{ file_id, name, extensions }]` |
| POST | `/get` | Read a lorebook | `{ name }` | Full JSON file contents |
| POST | `/edit` | Save/update a lorebook | `{ name, data }` | `{ ok: true }` |
| POST | `/delete` | Delete a lorebook | `{ name }` | 200 status |
| POST | `/import` | Import a lorebook file | `multipart (file)` + optional `convertedData` | `{ name }` |

### 10.3 Key Implementation Details

- **`readWorldInfoFile()`** (line 17): Synchronous read helper. Returns a dummy
  `{ entries: {} }` object when `allowDummy=true` and the file doesn't exist.
- **`/list`** (line 39): Reads the worlds directory, parses each JSON file to extract
  `name` and `extensions` metadata. Sorts alphabetically by filename.
- **`/import`** (line 99): Accepts either raw uploaded file or pre-converted data in
  `request.body.convertedData` (client-side conversion). Validates that the JSON contains
  an `entries` key.
- **`/edit`** (line 134): Writes the entire data object to disk. The client sends the
  full lorebook, not incremental patches. Uses `JSON.stringify(data, null, 4)` for
  human-readable formatting.


## 11. Global Settings

All global WI settings are exported as module-level variables and persisted via
`saveSettings()` / `saveSettingsDebounced()`:

| Setting | Type | Default | Purpose |
|---|---|---|---|
| `world_info_depth` | `number` | `2` | Number of recent chat messages to scan for keywords. |
| `world_info_budget` | `number` | `25` | Percentage of max context allocated to WI content. |
| `world_info_budget_cap` | `number` | `0` | Absolute token cap for WI budget. 0 = disabled. |
| `world_info_recursive` | `boolean` | `false` | Enable recursive scanning (activated entries can trigger other entries). |
| `world_info_max_recursion_steps` | `number` | `0` | Maximum recursion loop iterations. 0 = unlimited. Mutually exclusive with `min_activations`. |
| `world_info_min_activations` | `number` | `0` | Minimum number of entries to activate. If not met, scan depth increases incrementally. |
| `world_info_min_activations_depth_max` | `number` | `0` | Maximum depth for min activation scanning. 0 = unlimited. |
| `world_info_include_names` | `boolean` | `true` | Include character names in chat messages when scanning. |
| `world_info_case_sensitive` | `boolean` | `false` | Global case sensitivity for keyword matching. |
| `world_info_match_whole_words` | `boolean` | `false` | Global whole-word matching for keywords. |
| `world_info_use_group_scoring` | `boolean` | `false` | Enable scoring-based selection within inclusion groups (highest key match count wins). |
| `world_info_character_strategy` | `enum(0-2)` | `1` (character_first) | How character vs. global lore entries are sorted: `0`=evenly (interleaved by order), `1`=character first, `2`=global first. |
| `world_info_overflow_alert` | `boolean` | `false` | Show a toast warning when the WI token budget is exceeded. |

### 11.1 Insertion Strategy

Controls the priority ordering between character-specific and globally-activated
lorebooks (line 4478-4495):

```javascript
export const world_info_insertion_strategy = {
    evenly: 0,          // All entries sorted by order, regardless of source
    character_first: 1,  // Character entries first, then global (each group sorted internally)
    global_first: 2,     // Global entries first, then character
};
```

Chat lore and persona lore always sort before both groups (line 4495):
```javascript
entries = [...chatLore.sort(sortFn), ...personaLore.sort(sortFn), ...entries];
```


## 12. Lore Sources

Four independent sources contribute entries to the scan. Loaded in parallel at
`getSortedEntries()` (line 4460):

| Source | Function | Origin | Priority |
|---|---|---|---|
| **Chat Lore** | `getChatLore()` (line 4414) | Lorebook bound to the current chat via `chat_metadata.world_info`. | Highest (sorted first) |
| **Persona Lore** | `getPersonaLore()` (line 4434) | Lorebook linked to the active user persona via `power_user.persona_description_lorebook`. | Second |
| **Character Lore** | `getCharacterLore()` (line 4345) | Primary lorebook from `character.data.extensions.world` plus auxiliary books from `world_info.charLore[].extraBooks`. | Third (or first, depending on strategy) |
| **Global Lore** | `getGlobalLore()` (line 4397) | All lorebooks selected in the global World Info dropdown (`selected_world_info[]`). | Fourth (or first, depending on strategy) |

Deduplication: If a lorebook is already activated via a higher-priority source, it is
skipped in lower-priority sources (e.g., if a character's world is also globally selected,
it won't be loaded twice).


## 13. Event System Integration

The WI engine emits events at key points:

| Event | Trigger Point | Payload |
|---|---|---|
| `WORLDINFO_ENTRIES_LOADED` | After loading all lore sources (line 4474) | `{ globalLore, characterLore, chatLore, personaLore }` |
| `WORLDINFO_SCAN_DONE` | After each scan loop iteration (line 5038) | State info, activated entries, budget status, timed effects |
| `WORLDINFO_UPDATED` | After saving a lorebook (line 4062) | `name, data` |
| `WORLDINFO_SETTINGS_UPDATED` | After any setting change | (none) |

The `WORLDINFO_SCAN_DONE` event is particularly powerful -- listeners can modify the
scan state, budget, and delay levels mid-scan, enabling extension-driven behavior.


## 14. Caching

`worldInfoCache` (line 882) is a `StructuredCloneMap` that caches loaded lorebook data:

```javascript
export const worldInfoCache = new StructuredCloneMap({ cloneOnGet: true, cloneOnSet: false });
```

- **Clone on get**: Every read returns a deep clone, preventing accidental mutation of
  cached data.
- **No clone on set**: The saved reference is used directly, so callers must not modify
  data after calling `saveWorldInfo()`.
- The cache is populated by `loadWorldInfo()` and updated by `saveWorldInfo()`.


## 15. Complexity Metrics

| Metric | Value |
|---|---|
| Total lines (`world-info.js`) | 6,273 |
| Fields per entry | 35+ (including runtime fields) |
| Insertion positions | 8 (10 if counting atDepth role variants) |
| Import format converters | 4 (NovelAI, Agnai, Risu, Character Book) |
| Scan states | 4 (NONE, INITIAL, RECURSION, MIN_ACTIVATIONS) |
| Selective logic modes | 4 (AND_ANY, NOT_ALL, NOT_ANY, AND_ALL) |
| Timed effect types | 3 (sticky, cooldown, delay) |
| Lore sources | 4 (chat, persona, character, global) |
| Backend endpoints | 5 (list, get, edit, delete, import) |
| Slash commands registered | 11 (`/world`, `/getchatbook`, `/wi-list-books`, etc.) |
| Global settings | 13 configurable parameters |
