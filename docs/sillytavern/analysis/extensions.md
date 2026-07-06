# SillyTavern v1.17.0 — Extension & Plugin System Analysis

## Table of Contents

1. [Extension Architecture Overview](#1-extension-architecture-overview)
2. [Server Plugins](#2-server-plugins)
3. [Frontend Extensions](#3-frontend-extensions)
4. [Built-in Extensions Catalog](#4-built-in-extensions-catalog)
5. [Extension Settings Persistence](#5-extension-settings-persistence)
6. [Deep Dive: Regex Scripts](#6-deep-dive-regex-scripts)
7. [Deep Dive: Memory / Summarization](#7-deep-dive-memory--summarization)
8. [Deep Dive: Connection Manager](#8-deep-dive-connection-manager)
9. [Git-Based Extension Management](#9-git-based-extension-management)
10. [Event System Integration](#10-event-system-integration)
11. [Third-Party Extension Ecosystem](#11-third-party-extension-ecosystem)


## 1. Extension Architecture Overview

SillyTavern has two fundamentally different extension systems that serve different layers of the application:

| Aspect | Server Plugins | Frontend Extensions |
|---|---|---|
| **Location** | `./plugins/` directory (server root) | `public/scripts/extensions/` |
| **Runtime** | Node.js (Express backend) | Browser (client-side JS) |
| **Entry file** | `src/plugin-loader.js` (293 lines) | `public/scripts/extensions.js` (1877 lines) |
| **Backend API** | `src/endpoints/extensions.js` (457 lines) | N/A (this IS the backend for frontend exts) |
| **Loading** | At server startup | At page load, after settings are loaded |
| **Scope** | Express router, server-side processing | UI rendering, prompt manipulation, chat events |
| **Config toggle** | `enableServerPlugins` in config.yaml | `extension_settings.disabledExtensions` array |
| **Distribution** | Git repos cloned into `./plugins/` | Built-in (ships with ST) or git repos into `third-party/` |

The server plugin system is opt-in and security-gated. Frontend extensions are the primary mechanism and are always active unless individually disabled.


## 2. Server Plugins

**Source:** `src/plugin-loader.js`

### 2.1 Plugin Loading Flow

The plugin system is loaded at server startup in `src/server-main.js`:

```js
// src/server-main.js:302-303
const pluginsDirectory = path.join(serverDirectory, 'plugins');
const cleanupPlugins = await loadPlugins(app, pluginsDirectory);
```

The `loadPlugins` function follows this sequence:

1. **Gate check** -- `enableServerPlugins` must be `true` in config.yaml (default: `false`)
2. **Auto-update** -- All git-based plugin directories are pulled from remote (if `enableServerPluginsAutoUpdate` is `true`, default)
3. **Iterate `./plugins/`** -- For each entry:
   - If it is a **directory**: check for `package.json` (npm package), then fall back to `index.js`/`index.cjs`/`index.mjs`
   - If it is a **file**: load directly if `.js`, `.cjs`, or `.mjs`
4. **Dynamic import** -- The file is imported via `import()` using a file URL
5. **Plugin initialization** -- `initPlugin()` validates and registers the plugin

### 2.2 Plugin Module Contract

Every plugin must export an `info` object and an `init` function:

```js
// Required exports (plugin-loader.js:179-199)
const info = plugin.info || plugin.default?.info;
// info must have: { id: string, name: string, description: string }

const init = plugin.init || plugin.default?.init;
// init(router: express.Router) => Promise<void>
```

Plugin ID validation is strict -- only lowercase alphanumeric, hyphens, and underscores:

```js
// plugin-loader.js:167-169
function isValidPluginID(id) {
    return /^[a-z0-9_-]+$/.test(id);
}
```

### 2.3 Lifecycle Hooks

Server plugins have exactly two lifecycle hooks:

| Hook | When | Signature |
|---|---|---|
| `init(router)` | Server startup, after auto-update | Receives an Express Router scoped to `/api/plugins/{id}` |
| `exit()` | Server shutdown | Called during `exitProcess`, all exit hooks run in parallel via `Promise.all` |

```js
// plugin-loader.js:214-228
const router = express.Router();
await init(router);
loadedPlugins.set(id, plugin);

if (router.stack.length > 0) {
    app.use(`/api/plugins/${id}`, router);
}

const exit = plugin.exit || plugin.default?.exit;
if (typeof exit === 'function') {
    exitHooks.push(exit);
}
```

### 2.4 Auto-Update Mechanism

Plugin auto-update runs before any plugin is loaded (`plugin-loader.js:237-293`):

1. Iterates all directories in `./plugins/` (skipping dotfiles)
2. For each directory, checks if it is a git repo via `checkIsRepo()`
3. Fetches from remote, compares HEAD to tracking branch
4. If behind, runs `git pull`
5. Requires system `git` binary (checked via `command-exists`)

```js
// plugin-loader.js:262-284
const pluginRepo = git(pluginPath);
const isRepo = await pluginRepo.checkIsRepo(CheckRepoActions.IS_REPO_ROOT);
if (!isRepo) continue;
await pluginRepo.fetch();
// ... compare commits ...
if (log.total === 0) continue;
await pluginRepo.pull();
```

### 2.5 Plugin Deduplication

Plugin IDs must be globally unique. Attempting to load a plugin with an already-registered ID fails:

```js
// plugin-loader.js:208-210
if (loadedPlugins.has(id)) {
    console.error(`Failed to load plugin module; plugin ID '${id}' is already in use`);
    return false;
}
```


## 3. Frontend Extensions

**Source:** `public/scripts/extensions.js` (1877 lines)

### 3.1 Extension Discovery

Extensions are discovered via `GET /api/extensions/discover` (`src/endpoints/extensions.js:422-457`). The server scans three locations and returns a typed list:

| Type | Location | Priority |
|---|---|---|
| `system` | `public/scripts/extensions/` (excluding `third-party/`) | Built-in, ships with ST |
| `local` | `{user_data}/extensions/` | Per-user third-party installs |
| `global` | `public/scripts/extensions/third-party/` | Shared across all users (admin only) |

If a local and global extension share the same name, the local version wins:

```js
// src/endpoints/extensions.js:449-451
const globalExtensions = fs.readdirSync(PUBLIC_DIRECTORIES.globalExtensions)
    .filter(f => !userExtensions.some(e => e.name === f.name));
```

### 3.2 Manifest Format

Every extension has a `manifest.json`. The schema based on all 14 built-in extensions:

```json
{
    "display_name": "string (required) -- Human-readable name",
    "loading_order": "number (required) -- Lower loads first",
    "requires": "string[] -- Extras API modules needed (hard dependency)",
    "optional": "string[] -- Extras API modules that enhance functionality",
    "js": "string -- Entry point JS file (e.g., 'index.js')",
    "css": "string -- Stylesheet file (e.g., 'style.css')",
    "author": "string -- Author name/handle",
    "version": "string -- Semver version",
    "homePage": "string -- URL to repository/homepage",
    "generate_interceptor": "string -- Global function name for generation interception",
    "auto_update": "boolean -- Enable auto-update for third-party extensions",
    "minimum_client_version": "string -- Minimum ST client version required",
    "dependencies": "string[] -- Other extension names required",
    "hooks": "object -- Lifecycle hook function mappings",
    "i18n": "object -- Locale file mappings { 'en': 'locales/en.json' }"
}
```

### 3.3 Extension Activation Flow

The activation flow in `activateExtensions()` (line 512-609):

1. Extensions are sorted by `loading_order` (ascending), then alphabetically by `display_name`
2. For each extension, the loader checks:
   - **Client version** -- `minimum_client_version` must be satisfied
   - **Extras modules** -- All items in `requires[]` must be connected
   - **Extension dependencies** -- All items in `dependencies[]` must exist and be enabled
   - **Disabled state** -- Not in `extension_settings.disabledExtensions`
3. If all checks pass:
   - Load i18n locale data (`addExtensionLocale`)
   - Load JS as an ES module (`addExtensionScript`)
   - Load CSS stylesheet (`addExtensionStyle`)
   - Call the `activate` lifecycle hook
4. Track in `activeExtensions` Set

```js
// extensions.js:573-587
if (meetsModuleRequirements && meetsExtensionDeps && meetsClientMinimumVersion && !isDisabled) {
    const promise = addExtensionLocale(name, manifest).finally(() =>
        Promise.all([addExtensionScript(name, manifest), addExtensionStyle(name, manifest)]),
    );
    await promise
        .then(() => {
            activeExtensions.add(name);
            return callExtensionHook(name, 'activate');
        })
        // ...
}
```

### 3.4 Extension Lifecycle Hooks (Frontend)

Frontend extensions support six lifecycle hooks defined in `manifest.hooks`:

| Hook | Trigger |
|---|---|
| `install` | After `git clone` completes |
| `update` | After `git pull` completes |
| `delete` | Before extension directory is deleted |
| `enable` | When user enables the extension |
| `disable` | When user disables the extension |
| `activate` | After JS/CSS are loaded during activation |

Hook values in the manifest are function names that must be exported from the extension's JS entry point:

```js
// extensions.js:365-425
async function callExtensionHook(name, hookName) {
    const hookFunctionName = manifest.hooks[hookName];
    const url = `/scripts/extensions/${name}/${manifest.js}`;
    const module = await import(url);
    // Call with 5-second timeout
    const result = await Promise.race([
        module[hookFunctionName](),
        delay(HOOK_TIMEOUT).then(() => HOOK_RESULT.TIMEOUT),
    ]);
}
```

### 3.5 Generate Interceptors

Extensions can declare a `generate_interceptor` in their manifest. This is a **global function name** (on `globalThis`) that is called before every LLM generation:

```js
// extensions.js:1734-1759
export async function runGenerationInterceptors(chat, contextSize, type) {
    let aborted = false;
    const abort = (immediately) => { aborted = true; exitImmediately = immediately; };

    for (const manifest of Object.values(manifests)
        .filter(x => x.generate_interceptor)
        .sort((a, b) => sortManifestsByOrder(a, b))) {
        const interceptorKey = manifest.generate_interceptor;
        if (typeof globalThis[interceptorKey] === 'function') {
            await globalThis[interceptorKey](chat, contextSize, abort, type);
        }
    }
    return aborted;
}
```

Two built-in extensions use this:
- **Image Generation** (`stable-diffusion`): `SD_ProcessTriggers`
- **Vector Storage** (`vectors`): `vectors_rearrangeChat`

### 3.6 APIs Available to Extensions

Extensions receive a rich context object via `getContext()` (defined in `public/scripts/st-context.js`). Key APIs include:

| Category | APIs |
|---|---|
| **Chat** | `chat`, `addOneMessage`, `deleteLastMessage`, `deleteMessage`, `saveChat`, `reloadCurrentChat` |
| **Characters** | `characters`, `characterId`, `groupId`, `selectCharacterById` |
| **Generation** | `generate`, `generateQuietPrompt`, `generateRaw`, `sendStreamingRequest`, `stopGeneration` |
| **Events** | `eventSource`, `eventTypes` |
| **Slash Commands** | `SlashCommandParser`, `SlashCommand`, `SlashCommandArgument`, `executeSlashCommandsWithOptions` |
| **Tokenization** | `getTokenCountAsync`, `getTextTokens`, `tokenizers` |
| **Prompts** | `setExtensionPrompt`, `extensionPrompts`, `substituteParams`, `substituteParamsExtended` |
| **UI** | `renderExtensionTemplateAsync`, `callGenericPopup`, `Popup` |
| **Settings** | `extensionSettings`, `saveSettingsDebounced`, `chatMetadata`, `updateChatMetadata` |
| **Tools** | `registerFunctionTool`, `unregisterFunctionTool`, `ToolManager` |
| **Data Bank** | `registerDataBankScraper` |
| **Macros** | `registerMacro` (deprecated), `macros` system |
| **Storage** | `accountStorage` |
| **i18n** | `t`, `translate`, `getCurrentLocale`, `addLocaleData` |

Extensions also have access to:
- `renderExtensionTemplateAsync(extensionName, templateId)` -- Renders HTML templates from the extension's own directory
- `writeExtensionField(characterId, key, value)` -- Writes to a character's `data.extensions` object
- `extension_settings` -- Direct access to the per-extension settings namespace


## 4. Built-in Extensions Catalog

SillyTavern v1.17.0 ships with **14 built-in extensions**, all of type `system`. They live in `public/scripts/extensions/`:

| Extension | Display Name | Loading Order | Files | Key Features |
|---|---|---|---|---|
| **connection-manager** | Connection Profiles | 1 | 7 (index.js, style.css, 5 templates) | Multi-profile API switching (model, preset, proxy, etc.) |
| **regex** | Regex | 1 | 12 (engine.js, index.js, 8 templates, style.css) | Find/replace regex scripts on messages and prompts |
| **translate** | Chat Translation | 1 | 6 (index.js, style.css, templates) | Real-time message translation via multiple providers |
| **attachments** | Data Bank (Chat Attachments) | 3 | 13 (index.js, style.css, 11 templates) | File attachments, web scraping, fandom/wiki import |
| **caption** | Image Captioning | 4 | 6 (index.js, style.css, templates) | Multimodal image description via LLMs |
| **expressions** | Character Expressions | 6 | 10 (index.js, style.css, templates) | Sprite-based character expressions/emotions |
| **gallery** | Gallery | 6 | 8 (index.js, style.css, templates) | Character image gallery management |
| **memory** | Summarize | 9 | 6 (index.js, style.css, settings.html) | Auto-summarization of chat history |
| **stable-diffusion** | Image Generation | 10 | 7 (index.js, style.css, 3 templates) | SD/DALL-E/ComfyUI image generation with trigger detection |
| **tts** | TTS | 10 | 36 files (index.js + 22 provider adapters) | Text-to-speech with 22+ provider backends |
| **quick-reply** | Quick Replies | 12 | 4 (index.js, style.css/less) | Macro buttons, auto-execution on events |
| **assets** | Assets | 15 | 9 (index.js, style.css, templates) | Character asset library browser |
| **token-counter** | Token Counter | -- | 4 (index.js, style.css, templates) | Token counting display in UI |
| **vectors** | Vector Storage | 100 | 6 (index.js, style.css, templates) | RAG via vector embeddings (loaded last) |

Additionally, `public/scripts/extensions/shared.js` (~31KB) provides cross-extension utilities, primarily the multimodal caption API and WebLLM integration functions.

### Notable Architecture Points

- **TTS is the largest extension** with 36 files and 22 provider adapters (ElevenLabs, OpenAI, Edge, Azure, Coqui, Kokoro, etc.)
- **Regex** has two files: `engine.js` (the processing core) and `index.js` (the UI/management layer)
- **Vectors** loads last (`loading_order: 100`) to ensure all other extensions have registered their data
- Both **stable-diffusion** and **vectors** use `generate_interceptor` to hook into the generation pipeline


## 5. Extension Settings Persistence

### 5.1 The `extension_settings` Object

All extension settings are stored in a single global object defined in `public/scripts/extensions.js` (lines 128-213). Each extension gets its own namespace key:

```js
export const extension_settings = {
    apiUrl: defaultUrl,           // Extras API URL
    apiKey: '',                   // Extras API key
    autoConnect: false,           // Auto-connect to Extras
    disabledExtensions: [],       // List of disabled extension names
    memory: {},                   // Summarize extension settings
    caption: { refine_mode: false },
    expressions: { api: undefined, custom: [], ... },
    connectionManager: { selectedProfile: '', profiles: [] },
    regex: [],                    // Global regex scripts array
    regex_presets: [],            // Regex preset configurations
    tts: {},
    sd: { prompts: {}, ... },
    translate: {},
    quickReply: {},
    vectors: {},
    attachments: [],
    // ... more per-extension namespaces
};
```

### 5.2 Loading Settings

Settings are loaded from the server-side settings file and merged into `extension_settings`:

```js
// extensions.js:1521-1546
export async function loadExtensionSettings(settings, versionChanged, enableAutoUpdate) {
    if (settings.extension_settings) {
        Object.assign(extension_settings, settings.extension_settings);
    }
    // Discover available extensions
    const extensions = await discoverExtensions();
    extensionNames = extensions.map(x => x.name);
    manifests = await getManifests(extensionNames);
    // Auto-update on version change
    if (versionChanged && enableAutoUpdate) {
        await autoUpdateExtensions(false);
    }
    await activateExtensions();
}
```

### 5.3 Per-Extension Settings Pattern

Each extension follows the same pattern for managing its settings:

1. **Define defaults** in the extension's own code
2. **Merge with `extension_settings.{name}`** on load
3. **Call `saveSettingsDebounced()`** on every change

Example from the memory extension:

```js
// memory/index.js:108-139
const defaultSettings = {
    memoryFrozen: false,
    source: summary_sources.extras,
    prompt: defaultPrompt,
    template: defaultTemplate,
    position: extension_prompt_types.IN_PROMPT,
    promptWords: 200,
    promptInterval: 10,
    // ... 15+ more settings
};

function loadSettings() {
    if (Object.keys(extension_settings.memory).length === 0) {
        Object.assign(extension_settings.memory, defaultSettings);
    }
    for (const key of Object.keys(defaultSettings)) {
        if (extension_settings.memory[key] === undefined) {
            extension_settings.memory[key] = defaultSettings[key];
        }
    }
}
```

### 5.4 Chat-Level Metadata

Extensions can also store per-chat data via `chatMetadata` and `saveMetadataDebounced()`. The memory extension stores summaries directly in message objects:

```js
// memory/index.js:974-984
if (saveToMessage && context.chat.length) {
    const idx = index ?? context.chat.length - 2;
    const mes = context.chat[idx < 0 ? 0 : idx];
    if (!mes.extra) { mes.extra = {}; }
    mes.extra.memory = value;
    saveChatDebounced();
}
```

### 5.5 Character-Level Extension Data

Extensions can write to character data via `writeExtensionField()` (extensions.js:1768-1808), which persists to `character.data.extensions.{key}` and syncs to the server via `/api/characters/merge-attributes`.


## 6. Deep Dive: Regex Scripts

**Source:** `public/scripts/extensions/regex/engine.js` (466 lines) + `public/scripts/extensions/regex/index.js`

### 6.1 Architecture

The regex system is split into two layers:

- **`engine.js`** -- Pure logic: regex compilation, caching, script execution, script type management
- **`index.js`** -- UI, slash commands, import/export, preset management

### 6.2 Script Types (Priority Order)

Regex scripts come from three sources, processed in this priority order:

```js
// engine.js:11-16
export const SCRIPT_TYPES = {
    GLOBAL: 0,   // extension_settings.regex[]
    PRESET: 2,   // Current API preset's extension field
    SCOPED: 1,   // Current character's data.extensions.regex_scripts
};
```

When `getRegexScripts()` is called (engine.js:98-99), it concatenates scripts from all three types via `flatMap`:

```js
export function getRegexScripts(options) {
    return [...Object.values(SCRIPT_TYPES).flatMap(type => getScriptsByType(type, options))];
}
```

**Scoped scripts** (character-level) require explicit permission via `extension_settings.character_allowed_regex` -- the user must approve per-character regex scripts as a security measure. Similarly, **preset scripts** require per-preset approval.

### 6.3 Regex Placement Targets

Each script defines where it applies via `placement[]`:

```js
// engine.js:281-292
export const regex_placement = {
    MD_DISPLAY: 0,    // Deprecated
    USER_INPUT: 1,    // Applied to user messages before sending
    AI_OUTPUT: 2,     // Applied to AI responses
    SLASH_COMMAND: 3,  // Applied to slash command output
    WORLD_INFO: 5,    // Applied to World Info entries
    REASONING: 6,     // Applied to reasoning/thinking blocks
};
```

### 6.4 The RegexProvider Cache

The engine includes an LRU cache for compiled regex objects (`engine.js:40-90`):

```js
export class RegexProvider {
    #cache = new Map();  // LRU map
    #maxSize = 1000;     // Max cached regexes
    static instance = new RegexProvider();

    get(regexString) {
        // LRU: re-insert on hit, evict oldest on capacity
        if (isCached) {
            this.#cache.delete(regexString);
            this.#cache.set(regexString, regex);
        } else {
            if (this.#cache.size >= this.#maxSize) {
                const firstKey = this.#cache.keys().next().value;
                this.#cache.delete(firstKey);
            }
            this.#cache.set(regexString, regex);
        }
        // Reset lastIndex for global/sticky regexes
        if (regex.global || regex.sticky) { regex.lastIndex = 0; }
        return regex;
    }
}
```

### 6.5 Script Execution Flow

`getRegexedString()` is the main entry point, called from multiple places across ST (5 files: `slash-commands.js`, `world-info.js`, `reasoning.js`, `welcome-screen.js`, and the engine itself):

```
getRegexedString(rawString, placement, params)
  -> getRegexScripts({ allowedOnly: true })      // Gather all scripts from 3 sources
  -> for each script:
       -> Check markdownOnly / promptOnly flags
       -> Check runOnEdit flag
       -> Check minDepth / maxDepth bounds
       -> Check if placement matches script.placement[]
       -> runRegexScript(script, rawString, params)
```

`runRegexScript()` handles the actual replacement (engine.js:391-448):

1. **Macro substitution in find pattern** -- Based on `substituteRegex` mode (NONE, RAW, ESCAPED)
2. **Compile regex** via `RegexProvider.instance.get()`
3. **Run `String.replace()`** with a custom replacer function:
   - Supports `{{match}}` as alias for `$0`
   - Supports numbered groups (`$1`, `$2`) and named groups (`$<name>`)
   - Applies `trimStrings` filtering to each captured group
   - Runs `substituteParams()` on the final replacement string

### 6.6 Script Data Model

Each regex script contains:

- `scriptName`, `findRegex`, `replaceString` -- Core find/replace
- `trimStrings[]` -- Strings to strip from captured groups
- `placement[]` -- Which targets to apply to
- `disabled` -- Toggle state
- `markdownOnly` / `promptOnly` -- Context-specific execution
- `runOnEdit` -- Whether to run when messages are edited
- `minDepth` / `maxDepth` -- Chat depth range filter
- `substituteRegex` -- Macro substitution mode (NONE=0, RAW=1, ESCAPED=2)

### 6.7 Regex Presets

The `RegexPresetManager` class allows saving and loading configurations of which scripts are enabled/disabled across all three script types (global, scoped, preset). Presets capture the enabled script IDs and can be applied or reverted with change detection.

### 6.8 Event Subscriptions

```js
// regex/index.js:2117-2122
eventSource.on(event_types.MAIN_API_CHANGED, onMainApiChanged);
eventSource.on(event_types.CHAT_CHANGED, checkCharEmbeddedRegexScripts);
eventSource.on(event_types.CHARACTER_DELETED, purgeEmbeddedRegexScripts);
eventSource.on(event_types.PRESET_RENAMED_BEFORE, onPresetRenamed);
eventSource.on(event_types.PRESET_CHANGED, checkPresetEmbeddedRegexScripts);
eventSource.on(event_types.PRESET_DELETED, purgePresetEmbeddedRegexScripts);
```


## 7. Deep Dive: Memory / Summarization

**Source:** `public/scripts/extensions/memory/index.js` (~1100 lines)

### 7.1 Summary Sources

The extension supports three summarization backends:

```js
// memory/index.js:93-97
const summary_sources = {
    'extras': 'extras',    // SillyTavern Extras API (external Python server)
    'main': 'main',        // Current main LLM API (OpenAI, Anthropic, etc.)
    'webllm': 'webllm',    // In-browser WebLLM inference
};
```

### 7.2 Prompt Builders

For the `main` source, there are three prompt construction strategies:

```js
const prompt_builders = {
    DEFAULT: 0,          // Uses generateQuietPrompt (piggybacks on current chat)
    RAW_BLOCKING: 1,     // Uses generateRaw, blocks send button during summarization
    RAW_NON_BLOCKING: 2, // Uses generateRaw, allows concurrent sends
};
```

### 7.3 Trigger Conditions

Summarization is triggered by chat events and gated by multiple conditions (`getSummaryPromptForNow()`, line 565-626):

1. **Interval check**: `promptInterval` -- number of messages since last summary (configurable, 0-250)
2. **Word count check**: `promptForceWords` -- total words since last summary exceeds threshold
3. **Frozen check**: `memoryFrozen` flag prevents any summarization
4. **Streaming check**: Skips if streaming is in progress
5. **Concurrency guard**: `inApiCall` flag prevents parallel summarization

```js
// memory/index.js:604-613
if (messagesSinceLastSummary >= extension_settings.memory.promptInterval) {
    conditionSatisfied = true;
}
if (extension_settings.memory.promptForceWords &&
    wordsSinceLastSummary >= extension_settings.memory.promptForceWords) {
    conditionSatisfied = true;
}
```

### 7.4 Raw Summary Prompt Construction

For RAW prompt builders, `getRawSummaryPrompt()` (line 761-825) constructs the input:

1. Starts from the message after the latest summary
2. Iterates forward through chat messages
3. Builds a buffer of `"Name:\nMessage"` entries
4. Stops when the token count (including system prompt and existing summary) exceeds the context window
5. Respects `maxMessagesPerRequest` limit
6. Returns the raw prompt and the index of the last message included

```js
// memory/index.js:794-820
for (let index = latestSummaryIndex + 1; index < chat.length; index++) {
    const entry = `${message.name}:\n${message.mes}`;
    chatBuffer.push(entry);
    const tokens = await countSourceTokens(getMemoryString(true), PADDING);
    if (tokens > PROMPT_SIZE) {
        chatBuffer.pop();
        break;
    }
}
```

### 7.5 Summary Injection

The summary is injected into the prompt via `setExtensionPrompt()`:

```js
// memory/index.js:964-965
function setMemoryContext(value, saveToMessage, index = null) {
    setExtensionPrompt(
        MODULE_NAME,                              // '1_memory'
        formatMemoryValue(value),                  // Template: '[Summary: {{summary}}]'
        extension_settings.memory.position,        // IN_PROMPT, etc.
        extension_settings.memory.depth,           // Chat depth for insertion
        extension_settings.memory.scan,            // Whether to include in WI scan
        extension_settings.memory.role             // SYSTEM, USER, ASSISTANT
    );
}
```

The template system uses `{{summary}}` macro substitution:

```js
// memory/index.js:77-89
const formatMemoryValue = function (value) {
    if (extension_settings.memory.template) {
        return substituteParamsExtended(extension_settings.memory.template, { summary: value });
    } else {
        return `Summary: ${value}`;
    }
};
```

### 7.6 Summary Storage

Summaries are persisted in the chat message's `extra.memory` field. The system finds the latest summary by walking the chat in reverse:

```js
// memory/index.js:357-371
function getLatestMemoryFromChat(chat) {
    const reversedChat = chat.slice().reverse();
    reversedChat.shift(); // Skip last message
    for (let mes of reversedChat) {
        if (mes.extra && mes.extra.memory) {
            return mes.extra.memory;
        }
    }
    return '';
}
```

### 7.7 Default Settings

Key defaults from `memory/index.js:108-139`:

| Setting | Default | Range |
|---|---|---|
| `promptWords` | 200 | 25 - 1000 (step 25) |
| `promptInterval` | 10 messages | 0 - 250 (step 1) |
| `promptForceWords` | 0 (disabled) | 0 - 10000 (step 100) |
| `overrideResponseLength` | 0 (auto) | 0 - 4096 (step 16) |
| `maxMessagesPerRequest` | 0 (unlimited) | 0 - 250 (step 1) |
| `depth` | 2 | Insertion depth in chat |
| `position` | IN_PROMPT | Prompt placement |
| `template` | `[Summary: {{summary}}]` | -- |

### 7.8 Event Subscriptions

```js
// memory/index.js:1079-1083
eventSource.on(event_types.CHAT_CHANGED, onChatChanged);
eventSource.makeLast(event_types.CHARACTER_MESSAGE_RENDERED, onChatEvent);
for (const event of [event_types.MESSAGE_DELETED, event_types.MESSAGE_UPDATED, event_types.MESSAGE_SWIPED]) {
    eventSource.on(event, onChatEvent);
}
```

The `makeLast` call ensures the memory extension processes `CHARACTER_MESSAGE_RENDERED` after all other handlers -- important so the message is fully rendered before summarization considers it.


## 8. Deep Dive: Connection Manager

**Source:** `public/scripts/extensions/connection-manager/index.js`

### 8.1 Profile Structure

A connection profile captures the complete API configuration state:

```js
// connection-manager/index.js:155-177
/**
 * @typedef {Object} ConnectionProfile
 * @property {string} id           Unique identifier (UUID)
 * @property {string} mode         'cc' (Chat Completion) or 'tc' (Text Completion)
 * @property {string} [name]       Profile name
 * @property {string} [api]        API provider
 * @property {string} [preset]     Settings preset
 * @property {string} [model]      Model name
 * @property {string} [proxy]      Proxy preset
 * @property {string} [instruct]   Instruct template
 * @property {string} [context]    Context template
 * @property {string} [tokenizer]  Tokenizer
 * @property {string} [stop-strings]  Custom stopping strings
 * @property {string} [start-reply-with]  Start reply with
 * @property {string} [reasoning-template]  Reasoning template
 * @property {string} [secret-id]  Secret identifier
 * @property {string} [regex-preset]  Regex preset ID
 * @property {string[]} [exclude]  Commands to exclude from profile
 */
```

### 8.2 Two Command Sets

The connection manager operates in two modes with different command sets:

**Chat Completion (CC) mode** -- 12 commands:
```js
const CC_COMMANDS = [
    'api', 'preset', 'api', 'api-url', 'model', 'proxy',
    'stop-strings', 'start-reply-with', 'reasoning-template',
    'prompt-post-processing', 'secret-id', 'regex-preset',
];
```

**Text Completion (TC) mode** -- 12 commands:
```js
const TC_COMMANDS = [
    'api', 'preset', 'api-url', 'model', 'sysprompt', 'sysprompt-state',
    'instruct', 'context', 'instruct-state', 'tokenizer',
    'stop-strings', 'start-reply-with', 'reasoning-template',
    'secret-id', 'regex-preset',
];
```

Note: CC mode intentionally calls `api` twice -- once before preset, once after -- because the preset selection can override the API setting.

### 8.3 Profile Application via Slash Commands

Profiles are applied by programmatically executing slash commands with quiet mode:

```js
// connection-manager/index.js:387-418
async function applyConnectionProfile(profile) {
    ConnectionManagerSpinner.abort();  // Cancel any in-progress application
    const commands = mode === 'cc' ? CC_COMMANDS : TC_COMMANDS;
    const spinner = new ConnectionManagerSpinner();
    spinner.start();

    for (const command of commands) {
        if (spinner.isAborted()) { throw new Error('Profile application aborted'); }
        const argument = profile[command];
        if (!argument) continue;
        const args = getNamedArguments();  // includes { quiet: 'true' }
        await SlashCommandParser.commands[command].callback(args, argument);
    }
    spinner.stop();
}
```

### 8.4 Profile Reading (Capture Current State)

Creating a profile captures the current state by invoking each command with no arguments (which returns the current value):

```js
// connection-manager/index.js:210-246
async function readProfileFromCommands(mode, profile, cleanUp = false) {
    const commands = mode === 'cc' ? CC_COMMANDS : TC_COMMANDS;
    for (const command of commands) {
        const result = await SlashCommandParser.commands[command].callback(args, '');
        if (result) { profile[command] = result; }
    }
}
```

### 8.5 Profile Storage

Profiles are stored in `extension_settings.connectionManager.profiles[]` and persisted with the global settings. The selected profile ID is tracked via `extension_settings.connectionManager.selectedProfile`.

### 8.6 Abort Mechanism

The `ConnectionManagerSpinner` class manages an abort controller array, allowing profile switches to cancel in-progress applications:

```js
static abort() {
    for (const controller of ConnectionManagerSpinner.abortControllers) {
        controller.abort();
    }
    ConnectionManagerSpinner.abortControllers = [];
}
```


## 9. Git-Based Extension Management

**Source:** `src/endpoints/extensions.js` + `src/git/client.js`

### 9.1 Git Backend Abstraction

SillyTavern supports two git backends, selected via `config.yaml` (`git.backend`):

```js
// src/git/client.js:9-13
export const GIT_BACKENDS = {
    AUTO: 'auto',      // Prefer system git, fall back to built-in
    SYSTEM: 'system',  // Require system git binary
    BUILTIN: 'builtin' // Use isomorphic-git (pure JS implementation)
};
```

This means extensions can be installed even without `git` on the system, using `isomorphic-git` as a fallback.

### 9.2 Extension API Endpoints

The backend exposes six endpoints under `/api/extensions/`:

| Endpoint | Method | Function |
|---|---|---|
| `/install` | POST | `git clone` from URL to extensions directory |
| `/update` | POST | `git pull` for a named extension |
| `/delete` | POST | Remove extension directory recursively |
| `/version` | POST | Get current branch, commit hash, update status |
| `/branches` | POST | List local and remote branches |
| `/switch` | POST | Switch to a different branch |
| `/move` | POST | Move between local and global directories |
| `/discover` | GET | List all available extensions with types |

### 9.3 Installation Flow

```
User provides Git URL
  -> POST /api/extensions/install
  -> Validate URL, create target directory
  -> git clone --depth 1 [--branch <branch>] <url> <path>
  -> Read manifest.json from cloned repo
  -> Return { version, author, display_name, extensionPath, folderName }
  -> Client calls loadExtensionSettings() to discover new extension
  -> Client calls callExtensionHook(name, 'install')
```

Clone options:
- **Shallow clone** (`depth: 1`) by default for fast installation
- Optional **branch/tag selection** via the `branch` parameter

### 9.4 Update Flow

```
POST /api/extensions/update { extensionName, global }
  -> Resolve path (global vs user-local)
  -> Verify directory is a git repo
  -> git fetch origin
  -> Compare HEAD to origin/<current_branch>
  -> If not up to date: git pull origin <branch>
  -> Return { shortCommitHash, extensionPath, isUpToDate, remoteUrl }
```

### 9.5 Branch Switching

The `/branches` endpoint unshallows the repo if necessary (since shallow clones don't have all branches):

```js
// src/endpoints/extensions.js:201-210
const isShallow = await git.revparse(['--is-shallow-repository']) === 'true';
if (isShallow) {
    await git.fetch('origin', ['--unshallow']);
}
await git.remote(['set-branches', 'origin', '*']);
await git.fetch('origin');
```

### 9.6 Global vs Local Extensions

- **Local extensions**: Per-user, stored in `{user_data}/extensions/`
- **Global extensions**: Shared, stored in `public/scripts/extensions/third-party/`
- Only **admin users** can install/update/delete/move global extensions
- The `/move` endpoint handles bidirectional moves between local and global

### 9.7 Git Timeout

All git operations use a 5-minute block timeout:

```js
// src/endpoints/extensions.js:17
const OPTIONS = Object.freeze({ timeout: { block: 5 * 60 * 1000 } });
```


## 10. Event System Integration

**Source:** `public/scripts/events.js`

### 10.1 Event Infrastructure

SillyTavern uses a custom `EventEmitter` with 100+ named event types. Extensions subscribe via `eventSource.on()` and emit via `eventSource.emit()`:

```js
// events.js:105
export const eventSource = new EventEmitter([event_types.APP_READY, event_types.APP_INITIALIZED]);
```

The two events passed to the constructor are "sticky" events -- late subscribers still receive them.

### 10.2 Complete Event Catalog

Organized by category, the 103 event types defined in `public/scripts/events.js`:

**Application lifecycle:**
- `APP_INITIALIZED`, `APP_READY`, `EXTRAS_CONNECTED`

**Message events:**
- `MESSAGE_SENT`, `MESSAGE_RECEIVED`, `MESSAGE_EDITED`, `MESSAGE_DELETED`
- `MESSAGE_UPDATED`, `MESSAGE_SWIPED`, `MESSAGE_SWIPE_DELETED`
- `MESSAGE_FILE_EMBEDDED`, `MESSAGE_REASONING_EDITED`, `MESSAGE_REASONING_DELETED`
- `USER_MESSAGE_RENDERED`, `CHARACTER_MESSAGE_RENDERED`
- `MORE_MESSAGES_LOADED`, `IMPERSONATE_READY`

**Generation events:**
- `GENERATION_AFTER_COMMANDS`, `GENERATION_STARTED`, `GENERATION_STOPPED`, `GENERATION_ENDED`
- `GENERATE_BEFORE_COMBINE_PROMPTS`, `GENERATE_AFTER_COMBINE_PROMPTS`, `GENERATE_AFTER_DATA`
- `STREAM_TOKEN_RECEIVED`, `STREAM_REASONING_DONE`

**Chat events:**
- `CHAT_CHANGED`, `CHAT_LOADED`, `CHAT_DELETED`, `CHAT_CREATED`
- `GROUP_CHAT_DELETED`, `GROUP_CHAT_CREATED`

**Character events:**
- `CHARACTER_EDITOR_OPENED`, `CHARACTER_EDITED`, `CHARACTER_PAGE_LOADED`
- `CHARACTER_FIRST_MESSAGE_SELECTED`, `CHARACTER_DELETED`, `CHARACTER_DUPLICATED`
- `CHARACTER_RENAMED`, `CHARACTER_RENAMED_IN_PAST_CHAT`
- `CHARACTER_GROUP_OVERLAY_STATE_CHANGE_BEFORE/AFTER`
- `CHARACTER_MANAGEMENT_DROPDOWN`

**Settings events:**
- `SETTINGS_LOADED`, `SETTINGS_UPDATED`, `SETTINGS_LOADED_BEFORE/AFTER`
- `EXTENSION_SETTINGS_LOADED`, `EXTENSIONS_FIRST_LOAD`
- `CHATCOMPLETION_SOURCE_CHANGED`, `CHATCOMPLETION_MODEL_CHANGED`
- `OAI_PRESET_CHANGED_BEFORE/AFTER`, `OAI_PRESET_EXPORT/IMPORT_READY`
- `TEXT_COMPLETION_SETTINGS_READY`, `CHAT_COMPLETION_SETTINGS_READY`
- `CHAT_COMPLETION_PROMPT_READY`

**World Info events:**
- `WORLDINFO_SETTINGS_UPDATED`, `WORLDINFO_UPDATED`
- `WORLD_INFO_ACTIVATED`, `WORLDINFO_FORCE_ACTIVATE`
- `WORLDINFO_ENTRIES_LOADED`, `WORLDINFO_SCAN_DONE`

**Connection events:**
- `CONNECTION_PROFILE_LOADED/CREATED/DELETED/UPDATED`
- `ONLINE_STATUS_CHANGED`, `MAIN_API_CHANGED`

**Preset events:**
- `PRESET_CHANGED`, `PRESET_DELETED`, `PRESET_RENAMED`, `PRESET_RENAMED_BEFORE`

**Secret events:**
- `SECRET_WRITTEN`, `SECRET_DELETED`, `SECRET_ROTATED`, `SECRET_EDITED`

**UI/Media events:**
- `FORCE_SET_BACKGROUND`, `MOVABLE_PANELS_RESET`, `IMAGE_SWIPED`
- `SD_PROMPT_PROCESSING`, `OPEN_CHARACTER_LIBRARY`

**Group events:**
- `GROUP_UPDATED`, `GROUP_MEMBER_DRAFTED`
- `GROUP_WRAPPER_STARTED/FINISHED`

**Tool events:**
- `TOOL_CALLS_PERFORMED`, `TOOL_CALLS_RENDERED`

**File events:**
- `FILE_ATTACHMENT_DELETED`, `MEDIA_ATTACHMENT_DELETED`

**Persona events:**
- `PERSONA_CHANGED`

**TTS events:**
- `TTS_JOB_STARTED`, `TTS_AUDIO_READY`, `TTS_JOB_COMPLETE`

### 10.3 How Extensions Use Events

Built-in extensions collectively subscribe to 42 event handlers across 25 distinct event types. Representative patterns:

**React to chat changes** (most common):
```js
eventSource.on(event_types.CHAT_CHANGED, onChatChanged);
```

**React to messages** (for processing):
```js
eventSource.on(event_types.MESSAGE_SENT, onChatEvent);
eventSource.on(event_types.MESSAGE_RECEIVED, onChatEvent);
eventSource.on(event_types.MESSAGE_SWIPED, onChatEvent);
```

**Control execution order:**
```js
// Ensure this handler runs LAST for CHARACTER_MESSAGE_RENDERED
eventSource.makeLast(event_types.CHARACTER_MESSAGE_RENDERED, onChatEvent);
```

**Queue execution until ready:**
```js
// quick-reply pattern: queue events until initialization is complete
eventSource.on(event_types.CHAT_CHANGED, (...args) =>
    executeIfReadyElseQueue(onChatChanged, args));
```


## 11. Third-Party Extension Ecosystem

### 11.1 Installation Methods

Third-party extensions are installed via two methods:

1. **UI dialog** -- `openThirdPartyExtensionMenu()` prompts for a Git URL, with options for:
   - Install just for the current user (local)
   - Install for all users (global, admin only)
   - Optional branch/tag specification

2. **Programmatic** -- `installExtension(url, global, branch)` can be called directly

### 11.2 Extension Classification

Once installed, third-party extensions appear with the prefix `third-party/` in their name:

```js
// extensions.js:927
const isExternal = name.startsWith('third-party');
```

The UI displays different icons per type:
- `fa-cog` -- System (built-in)
- `fa-user` -- Local (per-user)
- `fa-server` -- Global (shared)

### 11.3 Update Checking

ST checks for updates in two ways:

1. **Daily notification** -- If `notifyUpdates` is enabled, checks once per day (tracked via `extension_update_nag` in localStorage)
2. **Manual check** -- In the extensions panel, with concurrency-limited version checks (max 5 parallel)

```js
// extensions.js:1556-1577
const concurrencyLimit = 5;
let activeRequestsCount = 0;
const versionCheckQueue = [];
// Queue-based concurrent version checking
```

### 11.4 Auto-Update Behavior

Third-party extensions with `auto_update: true` in their manifest are auto-updated:
- On client version change
- With a 60-second per-extension timeout
- Only for enabled extensions (unless `forceAll` is set)

### 11.5 Third-Party Extension Capabilities

Third-party extensions have the same capabilities as built-in extensions:
- Full access to `getContext()` APIs
- Event system subscription
- Slash command registration
- Generate interceptors
- Template rendering
- Settings persistence
- Lifecycle hooks

The only differences are:
- They can be installed/deleted by users
- They are git-managed (branching, updating)
- They can be moved between local and global scopes
- They show update indicators and repo links in the UI

### 11.6 Security Considerations

SillyTavern has minimal security barriers for third-party extensions:
- Extensions run with full access to the browser context
- No sandboxing or capability restrictions
- Character-scoped regex scripts require explicit user approval
- Server plugins require `enableServerPlugins: true` in config
- Global extension management requires admin privileges
- The UI warns: "Make sure you know exactly what they do, and only install plugins from trusted sources!"


## Summary Statistics

| Metric | Value |
|---|---|
| Frontend extension loader | 1,877 lines |
| Backend extension endpoints | 457 lines |
| Server plugin loader | 293 lines |
| Built-in extensions | 14 |
| Total event types | 103 |
| Extension lifecycle hooks (frontend) | 6 (install, update, delete, enable, disable, activate) |
| Plugin lifecycle hooks (server) | 2 (init, exit) |
| Generate interceptors in use | 2 (stable-diffusion, vectors) |
| TTS provider adapters | 22+ |
| Git backends supported | 2 (system git, isomorphic-git) |
| Extension API endpoints | 8 |
| Regex placement targets | 6 |
| Summary sources | 3 (extras, main LLM, webllm) |
| Connection profile command fields | ~14 per mode |
