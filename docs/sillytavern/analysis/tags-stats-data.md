# SillyTavern v1.17.0 — Tags, Stats, and Data Integrity Systems

This document analyzes SillyTavern's tag management, statistics tracking, data integrity checking ("Data Maid"), and local search/filtering systems. All file paths are relative to the SillyTavern repository root.


## 1. Tags System

**Primary file:** `public/scripts/tags.js` (~2,850 lines)
**Filter engine:** `public/scripts/filters.js` (~450 lines)

### 1.1 Data Model

A tag is a plain JavaScript object persisted as part of the user's settings JSON. The `Tag` typedef (tags.js:323-338):

```js
/**
 * @typedef {object} Tag
 * @property {string} id            - UUID v4 identifier
 * @property {string} name          - Display name
 * @property {string} [folder_type] - One of 'OPEN', 'CLOSED', 'NONE' (TAG_FOLDER_TYPES)
 * @property {string} [filter_state]- One of 'SELECTED', 'EXCLUDED', 'UNDEFINED'
 * @property {number} [sort_order]  - Integer for manual sorting
 * @property {string} [color]       - Background color (RGBA string)
 * @property {string} [color2]      - Foreground/text color (RGBA string)
 * @property {number} [create_date] - Timestamp (Date.now())
 * @property {boolean} [is_hidden_on_character_card] - Hide from inline card display
 */
```

Tags are created via `newTag()` (tags.js:1146-1158):
```js
function newTag(tagName) {
    return {
        id: uuidv4(),
        name: tagName,
        folder_type: TAG_FOLDER_DEFAULT_TYPE,  // 'NONE'
        filter_state: DEFAULT_FILTER_STATE,     // 'UNDEFINED'
        sort_order: Math.max(0, ...tags.map(t => t.sort_order)) + 1,
        is_hidden_on_character_card: false,
        color: '',
        color2: '',
        create_date: Date.now(),
    };
}
```

### 1.2 Storage Architecture

Two global structures hold all tag data:

| Structure | Type | Description |
|---|---|---|
| `tags` | `Tag[]` | Flat array of all tag definitions |
| `tag_map` | `{[entityKey: string]: string[]}` | Map from entity key to array of tag IDs |

Both are stored inside the user's main `settings.json` file and loaded on startup via `loadTagsSettings()` (tags.js:614-617):

```js
function loadTagsSettings(settings) {
    tags = settings.tags !== undefined ? settings.tags : DEFAULT_TAGS;
    tag_map = settings.tag_map !== undefined ? settings.tag_map : Object.create(null);
}
```

There is no dedicated server endpoint for tags. All tag operations occur client-side and persist via the general settings save mechanism (`saveSettingsDebounced()`).

**Entity key resolution:** The `tag_map` keys are:
- For characters: the character's `avatar` filename (e.g., `"Alice.png"`)
- For groups: the group's `id` string

The function `getTagKeyForEntity()` (tags.js:691-722) robustly resolves any entity reference (object, numeric ID, or string key) to its tag map key.

### 1.3 What Can Be Tagged

Tags apply to **characters** and **groups** only. Tags themselves can be promoted to "folders" (see Section 1.5), but folders do not receive their own tags. The entity-to-tag assignment is always via the `tag_map` keyed by avatar filename or group ID.

### 1.4 Default Tags

SillyTavern ships with six default tags representing common character card formats (tags.js:293-300):

```js
const DEFAULT_TAGS = [
    { id: uuidv4(), name: 'Plain Text', create_date: Date.now() },
    { id: uuidv4(), name: 'OpenAI',     create_date: Date.now() },
    { id: uuidv4(), name: 'W++',        create_date: Date.now() },
    { id: uuidv4(), name: 'Boostyle',   create_date: Date.now() },
    { id: uuidv4(), name: 'PList',       create_date: Date.now() },
    { id: uuidv4(), name: 'AliChat',     create_date: Date.now() },
];
```

### 1.5 Folder System ("Bogus Folders")

Tags can serve double duty as virtual folders. Each tag has a `folder_type` property that cycles through three states (tags.js:316-321):

| Folder Type | Icon | Behavior |
|---|---|---|
| `NONE` | X (red) | Normal tag, not a folder |
| `OPEN` | Check (green) | Folder -- shows all contained characters even if not directly selected |
| `CLOSED` | Eye-slash (yellow) | Folder -- hides contained characters unless the folder is explicitly opened |

Users cycle through these states by clicking the folder indicator in the tag management UI (`onTagAsFolderClick`, tags.js:2081-2096). Folders are enabled globally via a `power_user.bogus_folders` boolean.

When folders are active, the entity list rendering treats tags-as-folders as navigable containers. The `chooseBogusFolder()` function (tags.js:478-494) handles drill-down navigation by toggling the tag's filter state to `SELECTED`, which causes the filter system to show only entities tagged with that folder.

Key filtering for folders happens in `filterByTagState()` (tags.js:369-408):
- Tags already selected as filters are removed from the entity list to avoid recursive display
- Entities inside `CLOSED` folders are hidden unless the folder is explicitly opened
- Empty folders are hidden unless a text search is active

### 1.6 Color Coding

Each tag supports two colors:
- `color` -- Background color (default: semi-transparent black)
- `color2` -- Foreground/text color (default: theme main text color)

Colors are edited via `<toolcool-color-picker>` web components in the tag management popup. Changes propagate in real-time via `onTagColorize()` (tags.js:2184-2199) with debounced recoloring of all matching tag elements and folder avatars.

### 1.7 Tag Visibility on Character Cards

Individual tags can be hidden from character card inline display via `is_hidden_on_character_card`. When `printTagList()` is called with `tagOptions.isCharacterList = true`, hidden tags are filtered out (tags.js:1196-1198):

```js
if (tagOptions.isCharacterList) {
    printableTags = printableTags.filter(tag => !tag.is_hidden_on_character_card);
}
```

### 1.8 Bulk Operations

Tags support bulk operations via multiple mechanisms:

1. **Bulk tag assignment** -- The `selectTag()` handler checks for `#bulk_tags_div[data-characters]` (tags.js:931-932), which contains a JSON-encoded array of character IDs. When present, the tag is added to all characters simultaneously.

2. **Bulk tag removal** -- Similarly, `onTagRemoveClick()` (tags.js:1614-1641) checks for bulk character data and removes the tag from multiple entities.

3. **Tag pruning** -- `onTagsPruneClick()` (tags.js:1944-1980) removes unused tags (zero assignments in `tag_map`) and dangling `tag_map` entries pointing to deleted characters/groups.

4. **Tag merging on delete** -- When deleting a tag via `onTagDeleteClick()` (tags.js:2116-2163), the user can optionally merge it into another tag. All entities with the deleted tag receive the replacement.

### 1.9 Tag Sorting

Three sort modes exist (tags.js:254-258):

```js
export const tag_sort_mode = {
    MANUAL: 'manual',        // Drag-and-drop order (sort_order field)
    ALPHABETICAL: 'alphabetical', // Case-insensitive locale compare
    BY_ENTRIES: 'by_entries',     // Most-used tags first
};
```

The `compareTagsForSort()` function (tags.js:1782-1808) implements the comparison. Manual sorting uses jQuery UI Sortable with drag handles.

### 1.10 Tag Import from Character Cards

Character cards (PNG files with embedded metadata) can contain tag arrays. SillyTavern provides four import modes (tags.js:246-251):

```js
export const tag_import_setting = {
    ASK: 1,            // Show a popup for user to choose
    NONE: 2,           // Never import
    ALL: 3,            // Import all, create new if needed
    ONLY_EXISTING: 4,  // Import only tags already defined in ST
};
```

The import pipeline (`handleTagImport`, tags.js:998-1032):
1. Reads `character.tags` from the card data
2. Filters out reserved names (`ROOT`, `TAVERN`)
3. Caps at 50 tags per character (anti-troll measure: `ANTI_TROLL_MAX_TAGS`)
4. Separates existing vs. new tags
5. Optionally adds tags from the currently open folder
6. Presents the import dialog or auto-imports based on saved preference

### 1.11 Tag Backup and Restore

`onTagsBackupClick()` (tags.js:1933-1942) exports `{ tags, tag_map }` as a timestamped JSON file. The restore process (`onTagRestoreFileSelect`, tags.js:1810-1924):
1. Validates the JSON structure
2. Asks whether to overwrite existing tags
3. Handles ID conflicts via an `idToActualTagIdMap` that remaps imported IDs to existing ones
4. Validates that `tag_map` keys reference real characters/groups
5. Merges and deduplicates tag assignments

### 1.12 Slash Commands

Five slash commands are registered for scripting/automation (tags.js:2322-2594):

| Command | Description |
|---|---|
| `/tag-add [name=char] tagName` | Add tag to character (creates if new) |
| `/tag-remove [name=char] tagName` | Remove tag from character |
| `/tag-exists [name=char] tagName` | Check if tag is assigned (returns true/false) |
| `/tag-list [name=char]` | Get comma-separated list of assigned tags |
| `/tag-import [name=char] [mode=all\|existing\|none\|ask]` | Import card-embedded tags |

### 1.13 Tags on Message Divs

`applyCharacterTagsToMessageDivs()` (tags.js:2605-2674) iterates chat message DOM elements and decorates them with `data-char-tags` and `data-char-tag-{normalized-name}` attributes. This enables CSS-based styling of messages by character tag. Tag names are normalized by stripping diacritics, special characters, and converting to lowercase kebab-case.


## 2. Tag Filtering System

**Primary file:** `public/scripts/filters.js` (~450 lines)

### 2.1 Filter Architecture

The `FilterHelper` class manages all filtering for a given list context. Three independent instances exist:

| Instance | Selector | Purpose |
|---|---|---|
| `entitiesFilter` | `#rm_characters_block .rm_tag_filter` | Main character/group list |
| `groupCandidatesFilter` | Group add-members section | Characters available to add to a group |
| `groupMembersFilter` | Group members section | Current group members |

### 2.2 Filter Types

Seven filter types are defined (filters.js:15-23):

```js
export const FILTER_TYPES = {
    SEARCH: 'search',              // Text search (plain or fuzzy)
    TAG: 'tag',                    // Tag-based inclusion/exclusion
    FOLDER: 'folder',             // Folder display toggle
    FAV: 'fav',                   // Favorites filter
    GROUP: 'group',               // Groups-only filter
    WORLD_INFO_SEARCH: 'world_info_search',  // World Info entry search
    PERSONA_SEARCH: 'persona_search',        // Persona search
};
```

### 2.3 Three-State Filter Logic

Tags use a three-state toggle (filters.js:35-39):

| State | CSS Class | Effect |
|---|---|---|
| `SELECTED` | `.selected` | Entity must have this tag (inclusion) |
| `EXCLUDED` | `.excluded` | Entity must NOT have this tag (exclusion) |
| `UNDEFINED` | `.undefined` | No filtering on this tag |

The toggle cycles `UNDEFINED -> SELECTED -> EXCLUDED -> UNDEFINED` on each click, implemented by `toggleTagThreeState()` (tags.js:1449-1492).

### 2.4 AND/OR Logic for Tag Filtering

The tag filter uses **AND logic** by default -- all selected tags must be present. This is hardcoded in `tagFilter()` (filters.js:224-253):

```js
tagFilter(data) {
    const TAG_LOGIC_AND = true;
    const { selected, excluded } = this.filterData[FILTER_TYPES.TAG];
    // ...
    const tagFlags = selected.map(tagId => this.isElementTagged(entity, tagId));
    const trueFlags = tagFlags.filter(x => x);
    const isTagged = TAG_LOGIC_AND ? tagFlags.length === trueFlags.length : trueFlags.length > 0;
    const isExcluded = excludedTagFlags.includes(true);
    // ...
}
```

The logic for combined filtering:
1. If any excluded tag matches, entity is hidden (OR logic for exclusion)
2. If selected tags exist, all must match (AND logic for inclusion)
3. Tag entities (folders) always pass through

### 2.5 Filter Pipeline

`FilterHelper.applyFilters()` (filters.js:373-401) chains all filter functions sequentially:

```js
applyFilters(data, { clearScoreCache = true, tempOverrides = {}, clearFuzzySearchCaches = true } = {}) {
    // ...
    const result = Object.values(this.filterFunctions)
        .reduce((data, fn) => fn(data), data);
    return result;
}
```

The pipeline is: `SEARCH -> FAV -> GROUP -> FOLDER -> TAG -> WORLD_INFO_SEARCH -> PERSONA_SEARCH`. Each filter narrows the dataset further.

### 2.6 Actionable Tags (Special Filters)

Three special "actionable tags" provide quick-filter buttons in the UI (tags.js:269-276):

| Actionable | ID | Behavior |
|---|---|---|
| `FAV` | `'1'` | Toggle favorite-only view |
| `GROUP` | `'0'` | Toggle groups-only view |
| `FOLDER` | `'4'` | Toggle folder-only view |

Plus three utility buttons:

| Button | ID | Action |
|---|---|---|
| `VIEW` | `'2'` | Open tag management dialog |
| `HINT` | `'3'` | Show/hide the tag filter list |
| `UNFILTER` | `'5'` | Clear all active filters |

### 2.7 Filter State Persistence

Filter states persist across page reloads using `accountStorage` (a wrapper around localStorage/sessionStorage). Each filter context saves independently:

- Actionable tag states: `{context}_TagFilterState_{TYPE}` (e.g., `CharacterList_TagFilterState_FAV`)
- Regular tag states: `{context}_tag_{tagId}` (e.g., `CharacterList_tag_abc-123`)

Restoration happens in `restoreSavedTagFilters()` (tags.js:2763-2799) and `loadFilterStatesForContext()` (tags.js:1396-1438).


## 3. Search System (Local Character/Entity Search)

**Primary file:** `public/scripts/power-user.js` (fuzzy search functions)
**Filter integration:** `public/scripts/filters.js`

Note: `src/endpoints/search.js` handles **web search** (SerpApi, SearXNG, Tavily, etc.), not local entity search. Local search is entirely client-side.

### 3.1 Fuzzy Search Engine

SillyTavern uses [Fuse.js](https://www.fusejs.io/) for client-side fuzzy searching. The core function `performFuzzySearch()` (power-user.js:2110-2134):

```js
export function performFuzzySearch(type, data, keys, searchValue, fuzzySearchCaches = null) {
    if (fuzzySearchCaches) {
        const cache = fuzzySearchCaches[type];
        if (cache?.resultMap.has(searchValue)) {
            return cache.resultMap.get(searchValue);
        }
    }

    const fuse = new Fuse(data, {
        keys: keys,
        includeScore: true,
        ignoreLocation: true,
        useExtendedSearch: true,
        threshold: 0.2,
    });

    const results = fuse.search(searchValue);

    if (fuzzySearchCaches) {
        fuzzySearchCaches[type].resultMap.set(searchValue, results);
    }
    return results;
}
```

Key Fuse.js settings:
- `threshold: 0.2` -- Fairly strict matching (0 = exact, 1 = match anything)
- `ignoreLocation: true` -- Match anywhere in the string, not just the beginning
- `useExtendedSearch: true` -- Enables Fuse.js extended syntax (prefix exact, inverse, etc.)
- Results are cached per search term per category to avoid re-computation

### 3.2 Indexed Fields by Category

**Characters** (`fuzzySearchCharacters`, power-user.js:2142-2158):

| Field | Weight | Description |
|---|---|---|
| `data.name` | 20 | Character name (highest priority) |
| `#tags` | 10 | Assigned ST tag names (joined via `\|\|`) |
| `data.description` | 3 | Character description |
| `data.mes_example` | 3 | Example messages |
| `data.scenario` | 2 | Scenario text |
| `data.personality` | 2 | Personality summary |
| `data.first_mes` | 2 | First message / greeting |
| `data.creator_notes` | 2 | Creator notes |
| `data.creator` | 1 | Creator name |
| `data.tags` | 1 | Card-embedded tags |
| `data.alternate_greetings` | 1 | Alternate greetings |

**Groups** (`fuzzySearchGroups`, power-user.js:2223-2232):

| Field | Weight |
|---|---|
| `name` | 20 |
| `members` | 15 |
| `#tags` | 10 |
| `id` | 1 |

**Tags** (`fuzzySearchTags`, power-user.js:2209-2215):

| Field | Weight |
|---|---|
| `name` | 1 |

**World Info** (`fuzzySearchWorldInfo`, power-user.js:2167-2179):

| Field | Weight |
|---|---|
| `key` | 20 |
| `group` | 15 |
| `comment` | 10 |
| `keysecondary` | 10 |
| `content` | 3 |
| `uid` | 1 |
| `automationId` | 1 |

**Personas** (`fuzzySearchPersonas`, power-user.js:2188-2201):

| Field | Weight |
|---|---|
| `name` | 20 |
| `description` | 3 |

### 3.3 Non-Fuzzy Fallback

When `power_user.fuzzy_search` is disabled, the search falls back to simple case-insensitive, accent-insensitive substring matching via `includesIgnoreCaseAndAccents()` (filters.js:332-335):

```js
return includesIgnoreCaseAndAccents(entity.item?.name, searchValue);
```

### 3.4 Score Caching

The `FilterHelper` maintains a `scoreCache` (`Map<FilterType, Map<string|number, number>>`) that stores Fuse.js relevance scores. These scores are used for:
- Determining which items pass the search filter (score must exist)
- Potential sorting by relevance (scores are accessible via `getScore()`)

Caches are cleared on each call to `applyFilters()` by default.


## 4. Statistics Tracking

**Backend:** `src/endpoints/stats.js` (469 lines)
**Frontend:** `public/scripts/stats.js` (334 lines)

### 4.1 Data Model

Statistics are tracked **per character** (keyed by avatar filename, e.g., `"Alice.png"`). The stat object per character:

```js
{
    total_gen_time: 0,       // Total LLM generation time in milliseconds
    user_word_count: 0,      // Total words written by the user
    non_user_word_count: 0,  // Total words generated by the AI
    user_msg_count: 0,       // Total user messages
    non_user_msg_count: 0,   // Total AI messages
    total_swipe_count: 0,    // Total swipe (regeneration) count
    chat_size: 0,            // Total chat file size in bytes (backend only)
    date_last_chat: 0,       // Timestamp of most recent chat activity
    date_first_chat: <max>,  // Timestamp of first chat activity
}
```

The global stats object also carries a `timestamp` field for tracking when data was last modified.

### 4.2 Storage

Stats are stored in a `stats.json` file in each user's root data directory. The backend maintains an in-memory `Map<string, Object>` (`STATS`) keyed by user handle, and periodically flushes to disk.

Persistence strategy (stats.js:189-208):
- **Auto-save interval:** Every 5 minutes (`setInterval(saveStatsToFile, 5 * 60 * 1000)`)
- **Dirty tracking:** Only writes when `charStats.timestamp > lastSaveTimestamp`
- **Atomic writes:** Uses `write-file-atomic` to prevent file corruption
- **Graceful shutdown:** `onExit()` flushes stats to disk on process termination

### 4.3 Backend Stat Calculation

The `calculateStats()` function (stats.js:271-317) scans all chat files for a character:

1. Iterates all `.jsonl` files in the character's chat directory
2. For each message line, parses JSON and extracts:
   - **Generation time:** `gen_started` / `gen_finished` timestamps
   - **Word counts:** via regex `\b\w+\b` matching
   - **Swipes:** Counts `swipes.length - 1` (first entry is the original message)
   - **Swipe timing:** Reads `swipe_info[].gen_started/gen_finished` for accurate swipe generation times
3. Deduplicates messages using SHA-256 hashes of message content
4. Tracks file system `stat.size` and `stat.mtimeMs` for chat size and last-modified time

**Timestamp parsing** (stats.js:62-117) handles five formats:
- Unix timestamps (milliseconds)
- ST humanized format (`2024-07-12@01h31m37s123ms`)
- US date format (`June 19, 2023 2:20pm`)
- ISO 8601
- Date objects

### 4.4 Frontend Stat Processing

Real-time stat updates happen via `statMesProcess()` (stats.js:271-324 frontend), called whenever a message is sent, received, continued, or swiped:

```js
async function statMesProcess(line, type, characters, this_chid, oldMessage) {
    // type: 'append' | 'continue' | 'appendFinal' | 'swipe' | (normal)
    // ...
    stat.total_gen_time += calculateGenTime(line.gen_started, line.gen_finished);

    if (line.is_user) {
        if (type != 'append' && type != 'continue' && type != 'appendFinal') {
            stat.user_msg_count++;
            stat.user_word_count += countWords(line.mes);
        } else {
            // For appends/continues, only add the delta
            stat.user_word_count += countWords(line.mes) - oldMessage.split(' ').length;
        }
    }
    // ...similar for non-user messages...

    if (type === 'swipe') {
        stat.total_swipe_count++;
    }
}
```

### 4.5 Stats UI

Two views are available:

**User Stats** (`userStatsHandler`):
- Aggregates across all characters
- Shows: Chatting Since, Chat Time, User Messages, Character Messages, User Words, Character Words, Swipes

**Character Stats** (`characterStatsHandler`):
- Shows stats for the currently selected character
- Shows: First Interaction, Chat Time, User Messages, Character Messages, User Words, Character Words, Swipes
- Character messages display = `non_user_msg_count - total_swipe_count` (excludes swiped-away messages)

Both render as popup dialogs via `createHtml()` (stats.js:101-130). Generation time is humanized (e.g., "2 hours 15 minutes").

### 4.6 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `POST /api/stats/get` | POST | Returns the full stats object for the requesting user |
| `POST /api/stats/recreate` | POST | Rebuilds stats from chat files on disk |
| `POST /api/stats/update` | POST | Replaces the in-memory stats (used by frontend after real-time updates) |

A debug function `refreshStats` is registered to allow manual full-rebuild from the UI.


## 5. Data Maid (Data Integrity Checker)

**Backend:** `src/endpoints/data-maid.js` (816 lines)
**Frontend:** `public/scripts/data-maid.js` (404 lines)

### 5.1 Purpose

The Data Maid identifies **orphaned files** -- data that exists on disk but is no longer referenced by any active entity. It provides a secure review-and-delete workflow.

### 5.2 Architecture

The system follows a token-based security model:

1. **Report generation:** Backend scans directories, produces a raw report of orphaned files
2. **Sanitization:** File paths are SHA-256 hashed before being sent to the frontend (never exposes raw server paths)
3. **Token issuance:** A cryptographic token (32 random bytes, hex-encoded) is generated and tied to the report
4. **Operations:** View/download/delete requests must include the valid token
5. **Finalization:** Token is invalidated after the session ends

### 5.3 Orphan Detection Categories

The `DataMaidService.generateReport()` method (data-maid.js:110-125) checks nine categories:

| Category | Detection Method | Description |
|---|---|---|
| **Images** | Cross-reference `userImages/` against all chat message `extra.image`, `extra.video`, `extra.image_swipes`, `extra.media`, and `chat_metadata.chat_backgrounds` | User-uploaded images not referenced in any chat |
| **Files** | Cross-reference `files/` against chat `extra.file`, `extra.files`, `chat_metadata.attachments`, and settings `extension_settings.attachments` / `character_attachments` | Uploaded files not referenced anywhere |
| **Chats** | Compare `chats/` subdirectory names against `characters/*.png` filenames | Chat directories for deleted characters |
| **Group Chats** | Parse group JSON definitions for `chat_id` and `chats[]`, compare against `groupChats/*.jsonl` | Group chat files not referenced by any group |
| **Avatar Thumbnails** | Compare `thumbnailsAvatar/` against `characters/` filenames | Thumbnails for missing character avatars |
| **Background Thumbnails** | Compare `thumbnailsBg/` against `backgrounds/` filenames | Thumbnails for deleted backgrounds |
| **Persona Thumbnails** | Compare `thumbnailsPersona/` against `avatars/` filenames | Thumbnails for deleted personas |
| **Chat Backups** | Find files with `CHAT_BACKUPS_PREFIX` in `backups/` | Automatic chat backup files |
| **Settings Backups** | Find files with settings backup prefix in `backups/` | Automatic settings backup files |

### 5.4 Chat Parsing for Reference Checking

The Data Maid parses **every chat file** (both individual and group) to build reference sets. Two parsing methods:

**`#parseAllChats(filterFn)`** (data-maid.js:532-562): Reads all `.jsonl` files, parses each line as JSON, applies filter function to find messages with media/file references.

**`#parseAllMetadata(filterFn)`** (data-maid.js:570-627): Extracts `chat_metadata` from the first message of each chat file, plus checks group definition files for `chat_metadata` and `past_metadata` (legacy format).

For files specifically, the checker also reads `settings.json` to find references in `extension_settings.attachments` and `extension_settings.character_attachments` (data-maid.js:273-300).

### 5.5 Security Model

**Path safety:** All file operations validate that the target path is under the user's data directory via `isPathUnderParent()` (data-maid.js:748, 796).

**Token lifecycle:**
- One token per user at a time (old tokens are revoked on new report generation, data-maid.js:654-659)
- Token contains the user handle and a list of `{ path, hash }` entries
- View/delete operations look up files by hash within the token's path list
- The `/finalize` endpoint invalidates the token after the dialog closes

**Sanitized records** (data-maid.js:135-144) sent to the frontend contain:
```js
{
    name: "filename.png",     // Basename only
    hash: "sha256...",        // SHA-256 of full path
    parent: "subdirName",     // Parent directory name (optional)
    size: 12345,              // File size in bytes
    mtime: 1704067200000,     // Last modification timestamp
}
```

### 5.6 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `POST /api/data-maid/report` | POST | Generate orphan report and return sanitized version + token |
| `POST /api/data-maid/finalize` | POST | Invalidate the current session token |
| `GET /api/data-maid/view` | GET | Stream a file's contents by hash+token (for preview) |
| `POST /api/data-maid/delete` | POST | Delete files by array of hashes+token |

### 5.7 Frontend UI

The `DataMaidDialog` class (data-maid.js:17-394) renders a popup with:

1. **Scan button:** Triggers report generation with a loading spinner
2. **Category sections:** Each non-empty category displays:
   - Category name and description
   - Total file count and aggregate size
   - Individual file entries sorted by modification time (newest first)
3. **Per-item actions:**
   - **View:** Opens image preview or text content in a popup (data-maid.js:315-322)
   - **Download:** Triggers browser download via anchor tag
   - **Delete:** Removes single file with confirmation
4. **Bulk delete:** "Delete All" per category with confirmation

Category descriptions warn users about potentially destructive actions (data-maid.js:23-60):
- Files/Images: "WILL DELETE MANUAL UPLOADS!"
- Chats: "Chat files associated with deleted characters"
- Thumbnails: "Thumbnails for missing or deleted [entity type]"
- Backups: "Automatically generated [type] backups"


## 6. Relationships Between Systems

### 6.1 Tags and Search Integration

The fuzzy search system indexes tag names as a searchable field for both characters (weight 10) and groups (weight 10). This means typing a tag name in the search bar will surface all characters/groups with that tag, even without using the tag filter directly.

### 6.2 Tags and Stats

These systems are independent. Stats are keyed by character avatar filename, and tags are assigned to the same key, but there is no direct interaction -- you cannot filter stats by tag, nor does tagging affect stat tracking.

### 6.3 Data Maid and Tags

The Data Maid does not clean up orphaned tag references (tags pointing to deleted characters). That responsibility belongs to the tag system's "Prune" feature (`onTagsPruneClick`), which removes unused tags and stale `tag_map` entries.

### 6.4 Data Maid and Stats

The Data Maid does not scan or clean up the `stats.json` file. Stats for deleted characters remain in the file until a manual `recreateStats` is triggered, which rebuilds from existing chat files only.


## 7. Key Design Observations

### 7.1 Flat Tag Model (No Hierarchy)

Tags are a flat list. Despite the folder feature creating a visual hierarchy, there is no parent-child relationship between tags. A tag marked as a folder merely acts as a grouping container via the filter system. You cannot nest folders within folders at the data model level (though the UI allows "drilling down" by selecting multiple folder-tags in sequence).

### 7.2 Client-Side-Heavy Architecture

Tags and search operate entirely client-side. The server stores and retrieves `settings.json` as an opaque blob. This means:
- No server-side tag validation or querying
- Search performance depends on the browser's ability to run Fuse.js over the full character/group dataset
- Tag operations are effectively atomic (single JSON write)

### 7.3 Stats: Dual-Path Updates

Stats follow two paths:
- **Real-time:** Frontend increments counters on each message and pushes via `POST /api/stats/update`
- **Batch rebuild:** `POST /api/stats/recreate` re-scans all chat files from scratch

The real-time path is fast but can drift (e.g., if the browser crashes). The batch rebuild is authoritative but slow for large chat histories.

### 7.4 Data Maid: Conservative by Design

The Data Maid intentionally avoids false positives by:
- Parsing every chat file for references before flagging anything as orphaned
- Requiring explicit user confirmation for each deletion
- Never exposing raw file paths to the frontend
- Issuing one-time-use tokens tied to specific file sets
- Warning about potentially destructive operations (manual uploads)

### 7.5 Tag Display Limit

The `printTagList()` function (tags.js:1217-1220) caps visible tags at 50 per entity by default. Exceeding this shows a `"..."` expander. Folder-tags and active filter tags are always shown regardless of the limit (they are "mandatory print" items).

```js
const DEFAULT_TAGS_LIMIT = 50;
const tagsDisplayLimit = expanded ? Number.MAX_SAFE_INTEGER : DEFAULT_TAGS_LIMIT;
```
