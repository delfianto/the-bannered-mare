# SillyTavern v1.17.0 -- Character Card System Analysis

> Analysis date: 2026-04-07
> Source: `/st/` (SillyTavern v1.17.0)


## 1. Card Specification Versions

SillyTavern supports three character card specification versions: **V1**, **V2**, and **V3**. Validation is handled by `src/validator/TavernCardValidator.js`.

### 1.1 V1 (TavernAI Legacy)

The original TavernAI format. A flat JSON object with six required string fields:

| Field         | Type   | Required |
|---------------|--------|----------|
| `name`        | string | Yes      |
| `description` | string | Yes      |
| `personality` | string | Yes      |
| `scenario`    | string | Yes      |
| `first_mes`   | string | Yes      |
| `mes_example` | string | Yes      |

Validation is a simple presence check -- every field must exist on the object via `Object.hasOwn`. No type checking is performed.

```js
// src/validator/TavernCardValidator.js:56
const requiredFields = ['name', 'description', 'personality', 'scenario', 'first_mes', 'mes_example'];
return requiredFields.every(field => {
    if (!Object.hasOwn(this.card, field)) {
        this.#lastValidationError = field;
        return false;
    }
    return true;
});
```

### 1.2 V2 (Character Card Spec V2)

The dominant format in the ecosystem. Built as an envelope around V1 data with additional metadata fields.

**Envelope-level validation:**
- `spec` must equal `'chara_card_v2'` (exact string match)
- `spec_version` must equal `'2.0'` (exact string match)
- `data` object must exist

**Required fields on `data`:**

| Field                       | Type     | Required | Notes                          |
|-----------------------------|----------|----------|--------------------------------|
| `name`                      | string   | Yes      | Inherited from V1              |
| `description`               | string   | Yes      | Inherited from V1              |
| `personality`               | string   | Yes      | Inherited from V1              |
| `scenario`                  | string   | Yes      | Inherited from V1              |
| `first_mes`                 | string   | Yes      | Inherited from V1              |
| `mes_example`               | string   | Yes      | Inherited from V1              |
| `creator_notes`             | string   | Yes      | New in V2                      |
| `system_prompt`             | string   | Yes      | New in V2                      |
| `post_history_instructions` | string   | Yes      | New in V2                      |
| `alternate_greetings`       | string[] | Yes      | Must be an Array               |
| `tags`                      | string[] | Yes      | Must be an Array               |
| `creator`                   | string   | Yes      | New in V2                      |
| `character_version`         | string   | Yes      | New in V2                      |
| `extensions`                | object   | Yes      | Must be typeof object          |

**Optional `character_book` validation** (if present):
- `extensions` (object) -- required
- `entries` (array) -- required

```js
// src/validator/TavernCardValidator.js:124-141
#validateCharacterBookV2() {
    const characterBook = this.card.data.character_book;
    if (!characterBook) {
        return true;  // character_book is optional
    }
    const requiredFields = ['extensions', 'entries'];
    // ...validates presence + type checks: entries is Array, extensions is object
}
```

### 1.3 V3 (Character Card Spec V3)

V3 validation is notably relaxed compared to V2.

**Envelope-level validation:**
- `spec` must equal `'chara_card_v3'`
- `spec_version` must be a number `>= 3.0` and `< 4.0`
- `data` must exist and be an object

There is **no field-level validation** on V3's `data` object. The validator only checks that `data` is a non-null object:

```js
// src/validator/TavernCardValidator.js:159-168
#validateDataV3() {
    const data = this.card.data;
    if (!data || typeof data !== 'object') {
        this.#lastValidationError = 'No tavern card data found';
        return false;
    }
    return true;
}
```

### 1.4 Validation Order

The `validate()` method tries V1 first, then V2, then V3. It returns the matched spec number (`1`, `2`, or `3`) or `false`:

```js
validate() {
    if (this.validateV1()) return 1;
    if (this.validateV2()) return 2;
    if (this.validateV3()) return 3;
    return false;
}
```

This means a V2 card would also pass V1 validation (since V2's top-level mirrors V1 fields via `readFromV2`). The validator returns the first match.


## 2. PNG Metadata Encoding

**File:** `src/character-card-parser.js`
**Dependencies:** `png-chunks-extract`, `png-chunk-text`, custom `src/png/encode.js`

Character data is stored in PNG tEXt chunks using base64-encoded JSON.

### 2.1 Chunk Names

| Chunk Keyword | Spec    | Purpose                                  |
|---------------|---------|------------------------------------------|
| `chara`       | V2      | Primary storage; always written           |
| `ccv3`        | V3      | Secondary storage; written as a copy of V2 data with mutated spec fields |

### 2.2 Write Process

When writing character data to a PNG:

1. **Extract** all existing chunks from the PNG buffer using `png-chunks-extract`
2. **Remove** all existing `chara` and `ccv3` tEXt chunks (case-insensitive keyword match)
3. **Encode** the character JSON as UTF-8, then base64
4. **Insert** a `chara` tEXt chunk before the IEND chunk
5. **Attempt** to also insert a `ccv3` chunk by cloning the data, setting `spec = 'chara_card_v3'` and `spec_version = '3.0'`, then base64-encoding. Errors are silently ignored.
6. **Re-encode** all chunks into a valid PNG buffer using the custom `src/png/encode.js`

```js
// src/character-card-parser.js:15-46
export const write = (image, data) => {
    const chunks = extract(new Uint8Array(image));
    const tEXtChunks = chunks.filter(chunk => chunk.name === 'tEXt');

    // Remove existing tEXt chunks
    for (const tEXtChunk of tEXtChunks) {
        const data = PNGtext.decode(tEXtChunk.data);
        if (data.keyword.toLowerCase() === 'chara' || data.keyword.toLowerCase() === 'ccv3') {
            chunks.splice(chunks.indexOf(tEXtChunk), 1);
        }
    }

    // Add V2 chunk
    const base64EncodedData = Buffer.from(data, 'utf8').toString('base64');
    chunks.splice(-1, 0, PNGtext.encode('chara', base64EncodedData));

    // Try adding V3 chunk (fire-and-forget)
    try {
        const v3Data = JSON.parse(data);
        v3Data.spec = 'chara_card_v3';
        v3Data.spec_version = '3.0';
        const base64EncodedData = Buffer.from(JSON.stringify(v3Data), 'utf8').toString('base64');
        chunks.splice(-1, 0, PNGtext.encode('ccv3', base64EncodedData));
    } catch (error) { /* silently ignored */ }

    return Buffer.from(encode(chunks));
};
```

Key detail: ST **always writes V2 as the canonical format** in the `chara` chunk. The `ccv3` chunk is a derived copy for compatibility with tools that read V3 only. Internally, ST stores everything as V2.

### 2.3 Read Process

1. Extract all tEXt chunks from the PNG
2. Search for `ccv3` keyword (case-insensitive) -- **V3 takes precedence**
3. If not found, fall back to `chara` keyword
4. Decode from base64 to UTF-8 string
5. If neither chunk exists, throw `Error('No PNG metadata.')`

```js
// src/character-card-parser.js:54-78
export const read = (image) => {
    const chunks = extract(new Uint8Array(image));
    const textChunks = chunks.filter((chunk) => chunk.name === 'tEXt')
        .map((chunk) => PNGtext.decode(chunk.data));

    const ccv3Index = textChunks.findIndex((chunk) => chunk.keyword.toLowerCase() === 'ccv3');
    if (ccv3Index > -1) {
        return Buffer.from(textChunks[ccv3Index].text, 'base64').toString('utf8');
    }

    const charaIndex = textChunks.findIndex((chunk) => chunk.keyword.toLowerCase() === 'chara');
    if (charaIndex > -1) {
        return Buffer.from(textChunks[charaIndex].text, 'base64').toString('utf8');
    }

    throw new Error('No PNG metadata.');
};
```

### 2.4 Custom PNG Encoder

`src/png/encode.js` is a minimal reimplementation of `png-chunks-encode` (MIT-licensed). It writes the PNG magic bytes (`89 50 4E 47 0D 0A 1A 0A`) followed by each chunk in standard PNG format: 4-byte length, 4-byte name, data, 4-byte CRC32 (using the `crc` npm package).


## 3. Character CRUD Operations

**File:** `src/endpoints/characters.js`

All character endpoints are mounted on an Express router. Characters are identified by their PNG filename (e.g., `MyCharacter.png`), which acts as both avatar and data container.

### 3.1 Create -- `POST /create`

1. Sanitize `ch_name` using `sanitize-filename`
2. Format data into V2 spec via `charaFormatData()`
3. Generate a unique PNG filename via `getPngName()` (appends incrementing suffix if name collides)
4. Create a chats directory for the character
5. If an avatar image was uploaded, use it; otherwise fall back to `DEFAULT_AVATAR_PATH` (`./public/img/ai4.png`)
6. Write character JSON into the PNG via `writeCharacterData()`
7. Return the avatar filename (e.g., `MyCharacter.png`)

```js
// src/endpoints/characters.js:1014-1041
router.post('/create', getFileNameValidationFunction('file_name'), async function (request, response) {
    request.body.ch_name = sanitize(request.body.ch_name);
    const char = JSON.stringify(charaFormatData(request.body, request.user.directories));
    const internalName = request.body.file_name || getPngName(request.body.ch_name, request.user.directories);
    const avatarName = `${internalName}.png`;
    const chatsPath = path.join(request.user.directories.chats, internalName);
    if (!fs.existsSync(chatsPath)) fs.mkdirSync(chatsPath);
    // ... write and respond
});
```

### 3.2 Read

**List All -- `POST /all`:**
- Reads all `.png` files from `directories.characters`
- Processes each file concurrently via `Promise.all`
- For each file: reads PNG metadata, parses JSON, enriches with stats (chat size, dates, data size)
- Supports **shallow mode** (controlled by `performance.lazyLoadCharacters` config) which returns only display-relevant fields

**Get Single -- `POST /get`:**
- Takes `avatar_url` in body (e.g., `MyCharacter.png`)
- Returns full character data (never shallow)

### 3.3 Update -- `POST /edit`

1. Re-format the incoming data via `charaFormatData()`
2. Preserve the existing `chat` and `create_date` fields
3. If a new avatar image was uploaded, use it; otherwise reuse the existing PNG
4. Write the updated JSON into the (possibly new) PNG
5. On avatar change: invalidate the thumbnail cache and bust the HTTP cache

### 3.4 Edit Avatar Only -- `POST /edit-avatar`

Replaces only the avatar image while preserving the existing character data:
1. Read the existing character data from the PNG
2. Write it back into the new uploaded image
3. Invalidate thumbnail and HTTP caches

### 3.5 Edit Attribute -- `POST /edit-attribute`

Surgically updates a single field on both the V1 top-level and `data.*` sub-object:
```js
char[request.body.field] = request.body.value;
char.data[request.body.field] = request.body.value;
```
Rejects edits to the `json_data` field.

### 3.6 Merge Attributes -- `POST /merge-attributes`

Deep-merges the request body with the existing character data. After merging, validates against `TavernCardValidator` (accepts V1, V2, or V3). This is the only CRUD endpoint that performs post-write validation.

### 3.7 Delete -- `POST /delete`

1. Validate and sanitize the avatar URL
2. Delete the PNG file with `fs.unlinkSync`
3. Invalidate the thumbnail
4. If `delete_chats == true`, recursively remove the chats directory

### 3.8 Rename -- `POST /rename`

1. Read existing character data
2. Update the `data.name` and `name` fields
3. Write data to a new PNG file
4. Copy chats directory to new name, then remove old
5. Delete the old PNG file
6. Return the new avatar filename

### 3.9 Duplicate -- `POST /duplicate`

File-level copy using `fs.copyFileSync`. Generates a unique name by appending `_N` suffixes. No data parsing involved.


## 4. Import System

**File:** `src/endpoints/characters.js` (lines 1416-1455)

The import endpoint dispatches to format-specific handlers based on `file_type`:

```js
const formatImportFunctions = {
    'yaml': importFromYaml,
    'yml':  importFromYaml,
    'json': importFromJson,
    'png':  importFromPng,
    'charx': importFromCharX,
    'byaf': importFromByaf,
};
```

All import functions follow the same signature: `(uploadPath, {request, response}, preservedFileName?) => Promise<string>`. They return the internal filename on success or empty string on failure.

### 4.1 PNG Import (`importFromPng`)

1. Read character data from PNG tEXt chunks via `readCharacterData()`
2. Parse JSON; sanitize name
3. If `spec` field exists (V2+): import RisuAI sprites, unset private fields, call `readFromV2()`, set fresh `create_date`
4. If only `name` exists (V1): construct a V1 object, convert to V2 via `convertToV2()`
5. Write to new PNG using the uploaded image as the avatar
6. Delete the temp upload file

### 4.2 JSON Import (`importFromJson`)

Handles three distinct JSON sub-formats:

| Detection Key     | Format              | Handler                                 |
|-------------------|---------------------|-----------------------------------------|
| `spec` exists     | V2/V3 JSON          | `readFromV2()` + RisuAI sprite import   |
| `name` exists     | V1 JSON             | Construct V1 object, `convertToV2()`    |
| `char_name` exists| Pygmalion/Gradio JSON| Map field names, `convertToV2()`        |

Field mapping for Pygmalion/Gradio format:
- `char_name` -> `name`
- `char_persona` -> `description`
- `char_greeting` -> `first_mes`
- `example_dialogue` -> `mes_example`
- `world_scenario` -> `scenario`

All JSON imports use `DEFAULT_AVATAR_PATH` since there is no image in a JSON file.

### 4.3 YAML Import (`importFromYaml`)

Minimal format with only `name`, `context` (mapped to `description`), and `greeting` (mapped to `first_mes`). All other fields default to empty strings. Uses `DEFAULT_AVATAR_PATH`.

### 4.4 CharX Import (`importFromCharX`)

**File:** `src/charx.js`

CharX is a ZIP-based archive format containing a `card.json` plus embedded assets.

1. Read the uploaded file into a buffer
2. Parse with `CharXParser` (handles SFX/self-extracting archives by scanning for the ZIP magic bytes `PK\x03\x04`)
3. Extract `card.json` from the ZIP
4. Collect embedded assets from `data.assets` array
5. Pick the icon asset (type `'icon'`, prefers `name === 'main'`)
6. Map auxiliary assets to storage categories: `sprite`, `background`, `misc`
7. Extract all needed buffers from the ZIP
8. Apply standard character transformations: `readFromV2()`, `unsetPrivateFields()`
9. Persist auxiliary assets to disk (sprites, backgrounds, misc images)
10. Write the card to PNG using the icon buffer as avatar

**Asset URI resolution:**
```js
// src/charx.js:10-11
const CHARX_EMBEDDED_URI_PREFIXES = ['embeded://', 'embedded://', '__asset:'];
```
Note the intentional inclusion of `'embeded://'` (misspelled) for RisuAI compatibility.

**Asset storage mapping:**

| `asset.type`       | Storage Category | Destination Directory                      |
|--------------------|------------------|--------------------------------------------|
| `emotion`          | sprite           | `characters/{charName}/`                   |
| `expression`       | sprite           | `characters/{charName}/`                   |
| `background`       | background       | `characters/{charName}/backgrounds/`       |
| (other)            | misc             | `userImages/{charName}/`                   |
| `icon`             | (avatar)         | Used as the PNG avatar image               |
| `user_icon`        | (skipped)        | Not imported                               |

Supported image extensions: `png, jpg, jpeg, webp, gif, apng, avif, bmp, jfif`

### 4.5 BYAF Import (`importFromByaf`)

**File:** `src/byaf.js`

BYAF (Backyard Archive Format) is a ZIP archive from Backyard AI.

**Archive structure:**
- `manifest.json` -- top-level manifest with `characters[]` and `scenarios[]` paths
- Character JSON files referenced from the manifest
- Scenario JSON files with messages, first messages, formatting instructions
- Image files for character icons and chat backgrounds

**Import process:**
1. Parse `manifest.json` from the ZIP
2. Extract the first character (only one character is imported even if multiple exist)
3. Extract all scenarios
4. Extract character images (primary + alternate icons)
5. Convert to V2 card format:
   - `character.persona` -> `description`
   - `scenarios[0].narrative` -> `scenario`
   - `scenarios[0].firstMessages[0].text` -> `first_mes`
   - `scenarios[0].exampleMessages` -> `mes_example` (formatted with `<START>` delimiters)
   - `scenarios[0].formattingInstructions` -> `system_prompt`
   - `manifest.author.name` -> `creator`
   - `manifest.author.backyardURL` -> `creator_notes`
   - Additional scenarios -> `alternate_greetings`
   - `character.loreItems` -> `character_book`
6. Import chat histories from scenarios as `.jsonl` files
7. Import chat backgrounds to `userImages/{fileName}/`
8. Import alternate character icons to `characters/{charName}/`

Macro replacement during BYAF import:
```js
// src/byaf.js:31-35
static replaceMacros(str) {
    return String(str || '')
        .replace(/#{user}:/gi, '{{user}}:')
        .replace(/#{character}:/gi, '{{char}}:')
        .replace(/{character}(?!})/gi, '{{char}}')
        .replace(/{user}(?!})/gi, '{{user}}');
}
```


## 5. Export System

**Endpoint:** `POST /export`

Two export formats are supported:

### 5.1 PNG Export

1. Read the raw PNG file buffer
2. Read the character JSON from the buffer
3. **Mutate** the JSON to remove private fields (`fav`, `chat`) via `mutateJsonString(rawData, unsetPrivateFields)`
4. Re-write the mutated JSON back into the PNG buffer
5. Send as `image/png` attachment with `Content-Disposition` header

This approach preserves the original avatar image while sanitizing the embedded data.

### 5.2 JSON Export

1. Read the character data from the PNG
2. Parse and ensure V2 format via `getCharaCardV2()`
3. Remove private fields
4. Send as pretty-printed JSON (`JSON.stringify(jsonObject, null, 4)`)

Private fields stripped on export:
```js
// src/endpoints/characters.js:498-502
function unsetPrivateFields(char) {
    _.set(char, 'fav', false);
    _.set(char, 'data.extensions.fav', false);
    _.unset(char, 'chat');
}
```


## 6. Character Data Model

**File:** `public/scripts/char-data.js`

### 6.1 V1 Character Data (`v1CharData`)

The top-level object. Includes both V1 native fields and injected server-side metadata.

| Field           | Type              | Source     | Notes                                          |
|-----------------|-------------------|------------|-------------------------------------------------|
| `name`          | string            | V1 spec    |                                                 |
| `description`   | string            | V1 spec    |                                                 |
| `personality`   | string            | V1 spec    |                                                 |
| `scenario`      | string            | V1 spec    |                                                 |
| `first_mes`     | string            | V1 spec    |                                                 |
| `mes_example`   | string            | V1 spec    |                                                 |
| `creatorcomment`| string            | V1 (ST)    | Maps to V2's `creator_notes`                   |
| `tags`          | string[]          | V1 (ST)    |                                                 |
| `talkativeness` | number            | V1 (ST)    | Default: 0.5                                   |
| `fav`           | boolean \| string | V1 (ST)    | Can be boolean or string `"true"`              |
| `create_date`   | string            | Server     | ISO 8601 timestamp                             |
| `data`          | v2CharData        | V2 ext     | The V2 data extension object                   |
| `chat`          | string            | Server     | Current chat file name (non-standard)          |
| `avatar`        | string            | Server     | PNG filename, acts as unique identifier        |
| `json_data`     | string            | Server     | Raw JSON string of the full card               |
| `shallow`       | boolean?          | Server     | True if lazy-loaded                            |

### 6.2 V2 Character Data (`v2CharData`)

The `data` sub-object within the V2 envelope.

| Field                       | Type                      | Default    |
|-----------------------------|---------------------------|------------|
| `name`                      | string                    | --         |
| `description`               | string                    | `''`       |
| `personality`               | string                    | `''`       |
| `scenario`                  | string                    | `''`       |
| `first_mes`                 | string                    | `''`       |
| `mes_example`               | string                    | `''`       |
| `creator_notes`             | string                    | `''`       |
| `system_prompt`             | string                    | `''`       |
| `post_history_instructions` | string                    | `''`       |
| `alternate_greetings`       | string[]                  | `[]`       |
| `tags`                      | string[]                  | `[]`       |
| `creator`                   | string                    | `''`       |
| `character_version`         | string                    | `''`       |
| `character_book`            | v2WorldInfoBook \| undef  | optional   |
| `extensions`                | v2CharDataExtensionInfos  | `{}`       |

### 6.3 Data Formatting (`charaFormatData`)

The `charaFormatData()` function is the central serializer, called on create and edit. It performs dual-write: setting fields at both the V1 top level and inside `data.*` for backward compatibility.

```js
// src/endpoints/characters.js:579-596 (abbreviated)
// V1 fields
_.set(char, 'name', data.ch_name);
_.set(char, 'description', data.description || '');
// ...
_.set(char, 'creatorcomment', data.creator_notes || '');
_.set(char, 'avatar', 'none');
_.set(char, 'chat', data.ch_name + ' - ' + humanizedDateTime());
_.set(char, 'talkativeness', data.talkativeness || 0.5);
_.set(char, 'fav', data.fav == 'true');

// V2 fields
_.set(char, 'spec', 'chara_card_v2');
_.set(char, 'spec_version', '2.0');
_.set(char, 'data.name', data.ch_name);
_.set(char, 'data.description', data.description || '');
// ... mirrors V1 fields into data.*
```

### 6.4 V2-to-V1 Field Hoisting (`readFromV2`)

When reading a V2 card, ST hoists V2 data fields to V1 top-level fields for backward compatibility:

```js
// src/endpoints/characters.js:513-523
const fieldMappings = {
    name: 'name',
    description: 'description',
    personality: 'personality',
    scenario: 'scenario',
    first_mes: 'first_mes',
    mes_example: 'mes_example',
    talkativeness: 'extensions.talkativeness',
    fav: 'extensions.fav',
    tags: 'tags',
};
```

If a V2 extension field is missing, ST backfills defaults:
- `talkativeness` -> `0.5`
- `fav` -> `false`


## 7. V2 Extensions System

**Type:** `v2CharDataExtensionInfos` in `public/scripts/char-data.js`

The `data.extensions` object is an open namespace. ST defines these standard extension fields:

### 7.1 Standard ST Extensions

| Field              | Type    | Default  | Description                                    |
|--------------------|---------|----------|------------------------------------------------|
| `talkativeness`    | number  | `0.5`    | Propensity to talk (0.0 to 1.0)               |
| `fav`              | boolean | `false`  | Favorite flag (stripped on export)             |
| `world`            | string  | `''`     | Associated World Info filename                 |
| `depth_prompt`     | object  | --       | Character-specific depth prompt injection      |
| `regex_scripts`    | array   | `[]`     | Custom regex find/replace scripts              |

### 7.2 Depth Prompt Object

```js
// src/endpoints/characters.js:620-626
_.set(char, 'data.extensions.depth_prompt.prompt', data.depth_prompt_prompt ?? '');
_.set(char, 'data.extensions.depth_prompt.depth', depth_value);  // default: 4
_.set(char, 'data.extensions.depth_prompt.role', role_value);    // default: 'system'
```

| Field    | Type                              | Default    |
|----------|-----------------------------------|------------|
| `prompt` | string                            | `''`       |
| `depth`  | number                            | `4`        |
| `role`   | `"system" \| "user" \| "assistant"` | `"system"` |

### 7.3 Regex Scripts

Each entry in `regex_scripts`:

| Field            | Type     | Description                                  |
|------------------|----------|----------------------------------------------|
| `id`             | string   | UUID                                         |
| `scriptName`     | string   | Display name                                 |
| `findRegex`      | string   | Regex pattern to match                       |
| `replaceString`  | string   | Replacement string                           |
| `trimStrings`    | string[] | Strings to trim                              |
| `placement`      | number[] | Where the script runs                        |
| `disabled`       | boolean  | Whether the script is disabled               |
| `markdownOnly`   | boolean  | Only applies to rendered markdown            |
| `promptOnly`     | boolean  | Only applies to prompt construction          |
| `runOnEdit`      | boolean  | Runs on message edits                        |
| `substituteRegex`| number   | Whether regex substitution is active         |
| `minDepth`       | number   | Minimum context depth                        |
| `maxDepth`       | number   | Maximum context depth                        |

### 7.4 Third-Party Extensions

ST preserves (but does not use) these extension fields set by external tools:

| Field                  | Source       | Type/Shape                                 |
|------------------------|--------------|--------------------------------------------|
| `pygmalion_id`         | Pygmalion    | string                                     |
| `github_repo`          | Community    | string                                     |
| `source_url`           | Community    | string                                     |
| `chub`                 | Chub.ai      | `{ full_path: string }`                   |
| `risuai`               | RisuAI       | `{ source: string[] }`                    |
| `sd_character_prompt`  | SD generation| `{ positive: string, negative: string }`  |

When importing, ST performs a deep merge of extensions, so third-party data survives round-trips:
```js
// src/endpoints/characters.js:646-654
if (data.extensions) {
    const extensions = JSON.parse(data.extensions);
    _.set(char, 'data.extensions', deepMerge(char.data.extensions, extensions));
}
```


## 8. Character Book (Embedded Lorebook)

The `character_book` is an optional field on `data` that embeds World Info (lorebook) entries directly in the character card.

### 8.1 Data Structure (`v2WorldInfoBook`)

```
{
  name: string,
  entries: v2DataWorldInfoEntry[],
  extensions: object    // required by V2 validator when character_book exists
}
```

### 8.2 Entry Structure (`v2DataWorldInfoEntry`)

Each entry contains:

| Field             | Type     | Description                              |
|-------------------|----------|------------------------------------------|
| `keys`            | string[] | Primary trigger keywords                 |
| `secondary_keys`  | string[] | Secondary/conditional keywords           |
| `comment`         | string   | Human-readable label                     |
| `content`         | string   | The lorebook content to inject           |
| `constant`        | boolean  | Always included regardless of triggers   |
| `selective`       | boolean  | Uses secondary key logic                 |
| `insertion_order` | number   | Processing priority                      |
| `enabled`         | boolean  | Active/inactive toggle                   |
| `position`        | string   | `'before_char'` or `'after_char'`        |
| `id`              | number   | Unique entry identifier                  |
| `extensions`      | object   | ST-specific extension fields (see below) |

### 8.3 Entry Extension Fields

The `extensions` object on each entry carries a rich set of ST-specific configuration:

| Field                          | Type    | Default | Description                               |
|--------------------------------|---------|---------|-------------------------------------------|
| `position`                     | number  | --      | Internal position enum                    |
| `exclude_recursion`            | boolean | false   | Skip during recursive scans               |
| `probability`                  | number  | null    | Chance of activation (0-1)                |
| `useProbability`               | boolean | false   | Whether probability is used               |
| `depth`                        | number  | 4       | Insertion depth in context                |
| `selectiveLogic`               | number  | 0       | Logic mode for selective activation       |
| `group`                        | string  | `''`    | Mutual exclusion group name               |
| `group_override`               | boolean | false   | Override group assignment                 |
| `group_weight`                 | number  | null    | Priority within group                     |
| `prevent_recursion`            | boolean | false   | Disallow recursive application            |
| `delay_until_recursion`        | boolean | false   | Only checked during recursion             |
| `scan_depth`                   | number  | null    | Max depth for trigger matching            |
| `match_whole_words`            | boolean | null    | Whole-word matching only                  |
| `use_group_scoring`            | boolean | false   | Use group weight for selection            |
| `case_sensitive`               | boolean | null    | Case-sensitive matching                   |
| `automation_id`                | string  | `''`    | Automation identifier                     |
| `role`                         | number  | 0       | Entry role/function                       |
| `vectorized`                   | boolean | false   | Optimized for vector search               |
| `display_index`                | number  | --      | UI display ordering                       |
| `sticky`                       | number  | null    | Persists for N messages after trigger     |
| `cooldown`                     | number  | null    | Cooldown between activations              |
| `delay`                        | number  | null    | Delay before activation                   |
| `match_persona_description`    | boolean | false   | Match against persona description         |
| `match_character_description`  | boolean | false   | Match against character description       |
| `match_character_personality`  | boolean | false   | Match against character personality       |
| `match_character_depth_prompt` | boolean | false   | Match against character depth prompt      |
| `match_scenario`               | boolean | false   | Match against scenario                    |
| `match_creator_notes`          | boolean | false   | Match against creator notes               |
| `triggers`                     | array   | `[]`    | Additional trigger conditions             |
| `ignore_budget`                | boolean | false   | Ignore token budget limits                |
| `outlet_name`                  | string  | `''`    | Named outlet for insertion                |

### 8.4 World Info to Character Book Conversion

When a character references a `world` file, ST converts the World Info format to the character book format on save:

```js
// src/endpoints/characters.js:628-644
if (data.world) {
    const file = readWorldInfoFile(directories, data.world, false);
    if (file && file.originalData) {
        _.set(char, 'data.character_book', file.originalData);
    }
    if (file && file.entries) {
        _.set(char, 'data.character_book', convertWorldInfoToCharacterBook(data.world, file.entries));
    }
}
```

The conversion maps ST's internal World Info field names to the V2 character book spec (e.g., `entry.key` -> `keys`, `entry.disable` -> `!enabled`, `entry.position == 0` -> `'before_char'`).


## 9. Avatar Management

### 9.1 Storage Model

Characters are stored as **PNG files with embedded metadata**. The avatar IS the character file.

- **Location:** `{user_data}/characters/{name}.png`
- **Standard dimensions:** 512 x 768 pixels (defined in `src/constants.js:356-357`)
- **Default avatar:** `./public/img/ai4.png`
- **Naming:** `sanitize-filename` with collision avoidance via numeric suffix

```js
// src/constants.js:356-358
export const AVATAR_WIDTH = 512;
export const AVATAR_HEIGHT = 768;
export const DEFAULT_AVATAR_PATH = './public/img/ai4.png';
```

### 9.2 Image Processing Pipeline

Avatar processing uses Jimp (JavaScript Image Manipulation Program):

1. **Read** the image from file path or buffer
2. **Crop** if crop parameters are provided (`x`, `y`, `width`, `height`)
3. **Resize** to standard dimensions if `want_resize` is true, otherwise use crop dimensions
4. **Cover** (scale + crop to fill the target dimensions without distortion)
5. **Encode** as PNG via `Jimp.getBuffer(JimpMime.png)`
6. If the image cannot be read (e.g., APNG), fall back to reading the raw file bytes

```js
// src/endpoints/characters.js:283-306
export async function applyAvatarCropResize(jimp, crop) {
    let finalWidth = image.bitmap.width, finalHeight = image.bitmap.height;
    if (typeof crop == 'object' && [crop.x, crop.y, crop.width, crop.height].every(x => typeof x === 'number')) {
        image.crop({ x: crop.x, y: crop.y, w: crop.width, h: crop.height });
        if (crop.want_resize) {
            finalWidth = AVATAR_WIDTH;   // 512
            finalHeight = AVATAR_HEIGHT; // 768
        } else {
            finalWidth = crop.width;
            finalHeight = crop.height;
        }
    }
    image.cover({ w: finalWidth, h: finalHeight });
    return await image.getBuffer(JimpMime.png);
}
```

### 9.3 Thumbnails

Avatar thumbnails are managed by `src/endpoints/thumbnails.js`:
- Stored in `{user_data}/thumbnails/avatar/`
- Generated on demand when requested
- Invalidated explicitly on avatar changes via `invalidateThumbnail(directories, 'avatar', filename)`
- Thumbnail resolution is configurable per type (avatar, background, persona)

### 9.4 Sprites (Expression Images)

Character sprites (expression/emotion images) are stored in `{user_data}/characters/{charName}/`:
- Used for visual novel-style expression display
- Imported from RisuAI format (`risuai.additionalAssets`, `risuai.emotions`)
- Imported from CharX format (assets with type `emotion` or `expression`)
- File naming uses hyphens for sprites (e.g., `happy.png`, `angry.png`) so ST's expression label extraction regex works


## 10. Caching Architecture

ST implements a **two-tier caching** strategy for character data.

### 10.1 Memory Cache (Tier 1)

```js
// src/endpoints/characters.js:30-31
const memoryCacheCapacity = getConfigValue('performance.memoryCacheCapacity', '100mb');
const memoryCache = new MemoryLimitedMap(memoryCacheCapacity);
```

`MemoryLimitedMap` (defined in `src/util.js:1113`) is a custom LRU-like Map:
- **Capacity:** Configurable, default `100mb` (estimated ~3000 characters)
- **Size estimation:** Each string character = 2 bytes (UTF-16)
- **Eviction:** FIFO -- oldest entries are evicted first when capacity is exceeded
- **Disabled on Android:** `isAndroid` flag prevents memory caching on mobile
- **Cache key:** `{filePath}-{mtimeMs}` -- invalidated when the file is modified

### 10.2 Disk Cache (Tier 2)

```js
// src/endpoints/characters.js:38-157
class DiskCache {
    static DIRECTORY = 'characters';
    static SYNC_INTERVAL = 5 * 60 * 1000;  // 5 minutes
}
```

Uses `node-persist` library for persistent key-value storage:
- **Location:** `{DATA_ROOT}/_cache/characters/`
- **TTL:** Disabled (no automatic expiration)
- **Sync interval:** Every 5 minutes, verifies cache entries against actual character files
- **Pruning:** Removes cache entries for characters that no longer exist on disk
- **Configurable:** Controlled by `performance.useDiskCache` (default: `true`)

### 10.3 Cache Read Path

```
Request -> Memory Cache hit? -> return
                          miss -> Disk Cache hit? -> return
                                              miss -> Parse PNG -> store in Memory + Disk -> return
```

### 10.4 Cache Invalidation

- **On write:** Memory cache entries matching the file path are deleted; disk cache sync is queued for the user handle
- **On delete:** Thumbnail cache is invalidated; character data cache is implicitly invalidated (file no longer exists)
- **On avatar edit:** Both thumbnail and HTTP caches are busted

### 10.5 Shallow Loading

When `performance.lazyLoadCharacters` is enabled, the character list endpoint returns only display-critical fields:

```js
// src/endpoints/characters.js:370-395
const toShallow = (character) => ({
    shallow: true,
    name: character.name,
    avatar: character.avatar,
    chat: character.chat,
    fav: character.fav,
    date_added: character.date_added,
    create_date: character.create_date,
    date_last_chat: character.date_last_chat,
    chat_size: character.chat_size,
    data_size: character.data_size,
    tags: character.tags,
    data: {
        name: _.get(character, 'data.name', ''),
        character_version: _.get(character, 'data.character_version', ''),
        creator: _.get(character, 'data.creator', ''),
        creator_notes: _.get(character, 'data.creator_notes', ''),
        tags: _.get(character, 'data.tags', []),
        extensions: {
            fav: _.get(character, 'data.extensions.fav', false),
            world: _.get(character, 'data.extensions.world', ''),
        },
    },
});
```

Full character data is then fetched on demand via the `/get` endpoint.


## 11. File-Based Storage Design

SillyTavern uses **no database** for character storage. Everything is on the filesystem.

### 11.1 Directory Layout

```
{user_data}/
  characters/                     # Character PNG files (avatar + embedded JSON)
    MyCharacter.png
    MyCharacter/                   # Sprites directory (expression images)
      happy.png
      sad.png
      backgrounds/                 # Character-specific backgrounds (from CharX)
        forest.png
  chats/
    MyCharacter/                   # Chat logs (named after PNG base name)
      MyCharacter - 2024-01-15.jsonl
  thumbnails/
    avatar/                        # Cached avatar thumbnails
      MyCharacter.png
  images/                          # User images / misc assets
    MyCharacter/                   # Misc CharX assets
  worlds/                          # World Info / lorebook JSON files
    MyWorld.json
```

### 11.2 Character Identity

The PNG filename is the character's unique identifier within a user's data. All references (chats directory, sprites directory, thumbnails) are derived from this filename:

```js
const chatsDirectory = path.join(directories.chats, item.replace('.png', ''));
```

### 11.3 Atomic Writes

All file writes use `write-file-atomic` (via `writeFileAtomicSync`) to prevent corruption from interrupted writes. This is important since the PNG file is both the avatar image and the data store.


## 12. CharX Format Deep Dive

**File:** `src/charx.js`

### 12.1 Archive Structure

CharX is a standard ZIP archive containing:
- `card.json` -- Character card data (V2 or V3 spec)
- Asset files referenced by `data.assets` URIs

### 12.2 Asset Model

Assets are declared in `card.data.assets` as an array of objects:

```json
{
  "type": "emotion",
  "name": "happy",
  "uri": "embedded://assets/happy.png",
  "ext": "png"
}
```

**URI prefixes recognized:**
- `embedded://` -- standard prefix
- `embeded://` -- RisuAI compatibility (intentional misspelling)
- `__asset:` -- alternative prefix

### 12.3 Asset Type Classification

| Asset Type     | Storage Category | Naming Strategy                          |
|----------------|-----------------|------------------------------------------|
| `icon`         | Avatar          | First `icon` with `name === 'main'`, or first `icon` |
| `user_icon`    | Skipped         | Not imported                             |
| `emotion`      | Sprite          | Hyphen-separated, lowercase              |
| `expression`   | Sprite          | Hyphen-separated, lowercase              |
| `background`   | Background      | Underscore-separated, lowercase          |
| (anything else)| Misc            | Underscore-separated, lowercase          |

### 12.4 SFX Archive Handling

CharX supports self-extracting (SFX) ZIP archives by scanning for the ZIP signature:

```js
// src/charx.js:16-30
const ZIP_SIGNATURE = Buffer.from([0x50, 0x4B, 0x03, 0x04]);

function findZipStart(buffer) {
    const index = buf.indexOf(ZIP_SIGNATURE);
    if (index > 0) {
        return buf.slice(index);
    }
    return buf;
}
```


## 13. Key Implementation Files

| File | Purpose |
|------|---------|
| `src/validator/TavernCardValidator.js` | V1/V2/V3 card validation |
| `src/character-card-parser.js` | PNG tEXt chunk read/write |
| `src/png/encode.js` | Custom PNG chunk encoder |
| `src/endpoints/characters.js` | Full CRUD, import/export, caching |
| `src/charx.js` | CharX ZIP format parser + asset persistence |
| `src/byaf.js` | BYAF (Backyard AI) format parser |
| `public/scripts/char-data.js` | JSDoc type definitions for character data |
| `src/endpoints/sprites.js` | Sprite/expression image management, RisuAI import |
| `src/endpoints/thumbnails.js` | Avatar thumbnail generation and caching |
| `src/constants.js` | Avatar dimensions, default paths |
| `src/util.js` | MemoryLimitedMap, deepMerge, sanitization utilities |
