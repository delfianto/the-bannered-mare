# SillyTavern v1.17.0 — Code Structure Analysis

An in-depth analysis of SillyTavern's codebase organization, architecture patterns,
and code metrics. All paths are relative to the SillyTavern project root unless
stated otherwise.


## 1. Top-Level Organization

```
SillyTavern/
├── server.js                # Entry point (18 lines)
├── package.json             # 172 lines, 96 runtime deps, 24 dev deps
├── webpack.config.js        # Webpack config for bundling public/lib.js
├── plugins.js               # Plugin CLI management script
├── post-install.js          # npm postinstall hook
├── index.d.ts               # Global TypeScript declarations (server-side)
├── jsconfig.json            # Server-side JS/TS checker config
├── .eslintrc.cjs            # ESLint config with server/browser overrides
│
├── src/                     # Backend (Express server) -- 31,741 LoC
├── public/                  # Frontend (SPA served as static files) -- 141,463 LoC
├── tests/                   # Test suite (Jest + Playwright)
├── default/                 # Default config, scaffold data, bundled content
├── plugins/                 # Server plugin directory (empty scaffold)
├── docker/                  # Docker-specific configs
├── colab/                   # Google Colab launcher
├── backups/                 # Empty backup directory
├── data/                    # Runtime user data root (gitignored)
└── .github/                 # CI workflows, issue templates
```

**Total JavaScript**: ~185,000 lines across 340 `.js` files (excluding node_modules).

The project is an **ESM-native Node.js application** (`"type": "module"` in
package.json). It targets Node >= 20 and also advertises experimental Deno and Bun
support through dedicated npm scripts.


## 2. Backend Architecture (`src/`)

### 2.1 Startup Chain

The boot sequence is a linear promise chain initiated from `server.js`:

```
server.js (18 lines)
  -> CommandLineParser.parse()           # Parse CLI args + config.yaml
  -> import('./src/server-main.js')      # The real entrypoint
```

`src/server-main.js` (466 lines) is the orchestrator. It:
1. Creates the Express app and attaches all middleware.
2. Chains initialization through a `.then()` waterfall at the bottom of the file:

```js
// server-main.js, lines 457-466
initUserStorage(globalThis.DATA_ROOT)
    .then(setDnsResolutionOrder)
    .then(ensurePublicDirectoriesExist)
    .then(migrateUserData)
    .then(migrateSystemPrompts)
    .then(verifySecuritySettings)
    .then(preSetupTasks)
    .then(apply404Middleware)
    .then(() => new ServerStartup(app, cliArgs).start())
    .then(postSetupTasks);
```

`src/server-startup.js` (450 lines) contains the `ServerStartup` class that
handles HTTP/HTTPS server creation, IPv4/IPv6 dual-stack binding, and SSL
certificate validation.

### 2.2 Top-Level Source Files

| File | Lines | Role |
|------|------:|------|
| `src/util.js` | 1,565 | Swiss-army utility: config parsing, color output, git version, UUID generation, zip extraction, streaming response forwarding, YAML merge, JSON schema flattening |
| `src/prompt-converters.js` | 1,445 | Converts unified chat format to provider-specific prompt formats (Claude, Google, Cohere, Mistral, AI21, xAI) |
| `src/users.js` | 1,100 | Multi-user system: storage init, auth middleware, user CRUD, directory management, data migration |
| `src/constants.js` | 558 | Shared constants: directory templates, API provider enums, API key allowlists, safety settings |
| `src/server-main.js` | 466 | Express app setup, middleware registration, startup/shutdown lifecycle |
| `src/server-startup.js` | 450 | HTTP(S) server creation and listen logic |
| `src/byaf.js` | 449 | Backyard AI Format parser (character card import) |
| `src/command-line.js` | 375 | CLI argument parser using yargs, config.yaml overlay |
| `src/charx.js` | ~400 | CharX format parser (zip-based character cards) |
| `src/config-init.js` | ~220 | Config file initialization, key migration between config versions |

### 2.3 Endpoint Organization (`src/endpoints/`)

All backend API routes are Express routers. Each file exports a `router` that is
mounted by `setupPrivateEndpoints()` in `server-startup.js`. There are **46
endpoint files** totaling ~21,861 lines.

The endpoints follow a flat, one-file-per-domain pattern -- no internal layering
(no separate service/repository). Each file typically:
1. Creates `express.Router()`
2. Defines route handlers inline with request validation, business logic, and
   file I/O all in the same function.

**Largest endpoint files:**

| File | Lines | Mount Path |
|------|------:|------------|
| `endpoints/backends/chat-completions.js` | 2,683 | `/api/backends/chat-completions` |
| `endpoints/stable-diffusion.js` | 2,031 | `/api/sd` |
| `endpoints/characters.js` | 1,543 | `/api/characters` |
| `endpoints/tokenizers.js` | 1,137 | `/api/tokenizers` |
| `endpoints/chats.js` | 1,077 | `/api/chats` |
| `endpoints/content-manager.js` | 1,054 | `/api/content` |
| `endpoints/openai.js` | 883 | `/api/openai` |
| `endpoints/data-maid.js` | 816 | `/api/data-maid` |
| `endpoints/image-metadata.js` | 741 | `/api/image-metadata` |

**Smallest endpoint files** (under 100 lines): `moving-ui.js` (17), `caption.js`
(29), `quick-replies.js` (32), `themes.js` (38), `classify.js` (55).

**Backend sub-directory: `endpoints/backends/`**

This contains the LLM completion proxies, split by completion paradigm:
- `chat-completions.js` (2,683 lines) -- Handles 20+ API providers including
  OpenAI, Claude, Google, Cohere, Mistral, Groq, Perplexity, xAI, DeepSeek, and
  others. This is the single largest endpoint file.
- `text-completions.js` (646 lines) -- Text completion APIs (Ollama, vLLM,
  KoboldCpp, etc.)
- `kobold.js` (281 lines) -- KoboldAI-specific completion endpoint.

### 2.4 Route Mounting Map

All 44 private routes are mounted in `setupPrivateEndpoints()` (server-startup.js,
lines 139-186). The URL structure follows a clear pattern:

```
/api/characters      -> charactersRouter
/api/chats           -> chatsRouter
/api/groups          -> groupsRouter
/api/worldinfo       -> worldInfoRouter
/api/settings        -> settingsRouter
/api/secrets         -> secretsRouter
/api/openai          -> openAiRouter         (provider-specific)
/api/google          -> googleRouter
/api/anthropic       -> anthropicRouter
/api/novelai         -> novelAiRouter
/api/backends/chat-completions -> chatCompletionsRouter
/api/backends/text-completions -> textCompletionsRouter
/api/backends/kobold           -> koboldRouter
/api/sd              -> stableDiffusionRouter
/api/vector          -> vectorsRouter
/api/translate       -> translateRouter
/api/speech          -> speechRouter
/api/search          -> searchRouter
/api/users           -> usersPrivateRouter, usersAdminRouter
...
```

There is also a deprecated endpoint redirect system (lines 68-133 of
server-startup.js) that maps 30+ legacy URLs like `/createcharacter` to their
modern `/api/characters/create` equivalents using HTTP 308 redirects.

### 2.5 Other Backend Modules

| Directory/File | Purpose |
|----------------|---------|
| `src/middleware/` | 9 middleware files (see Section 5) |
| `src/vectors/` | 9 vector embedding provider implementations (OpenAI, Ollama, Cohere, Google, etc.) |
| `src/tokenizers/` | Tokenizer model files (sentencepiece `.model`, tiktoken `.json`) |
| `src/types/` | TypeScript declaration files (`byaf.d.ts`, `spec-v2.d.ts`) |
| `src/electron/` | Electron desktop app wrapper |
| `src/git/` | `client.js` -- Git operations for extensions auto-update |
| `src/png/` | `encode.js` -- PNG chunk encoding for character card metadata |
| `src/validator/` | `TavernCardValidator.js` -- Character card format validation |
| `src/additional-headers.js` | Provider-specific header injection |
| `src/character-card-parser.js` | PNG/JSON character card reading/writing |
| `src/request-proxy.js` | Outgoing HTTP request proxy configuration |
| `src/server-events.js` | Node EventEmitter-based server event bus |
| `src/plugin-loader.js` | Server plugin discovery, loading, and auto-update |


## 3. Frontend Architecture (`public/`)

### 3.1 Overview

The frontend is a **jQuery-based single-page application** with modern ES module
imports. It is NOT built with a framework like React or Vue. The HTML is a single
monolithic `index.html` (8,176 lines) with inline template fragments.

| File | Lines | Role |
|------|------:|------|
| `public/index.html` | 8,176 | Monolithic HTML with all UI panels |
| `public/script.js` | 12,481 | Main application entry point and global state |
| `public/style.css` | 6,376 | Primary stylesheet |
| `public/lib.js` | 136 | Webpack entry: bundles NPM libs for browser use |
| `public/global.d.ts` | 241 | Frontend TypeScript declarations |
| `public/login.html` | ~140 | Separate login page |

### 3.2 Library Bundling

`public/lib.js` declares all NPM dependencies that need to be available in the
browser. Webpack bundles these into a single `lib.js` output file at startup:

```js
// public/lib.js -- bundled libraries
import lodash from 'lodash';
import Fuse from 'fuse.js';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';
import localforage from 'localforage';
import Handlebars from 'handlebars';
import showdown from 'showdown';
import moment from 'moment';
import morphdom from 'morphdom';
import chalk from 'chalk';
import yaml from 'yaml';
import * as chevrotain from 'chevrotain';
// ... 26 libraries total
```

These are also shimmed onto `window.*` for backward compatibility with older
extensions via `initLibraryShims()`.

### 3.3 The God Object: `script.js`

`public/script.js` (12,481 lines) is the application's central nervous system. It:

- Imports from **74 local module files** and the library bundle.
- Exports **217 symbols** (variables, functions, constants) consumed by other modules.
- Contains all global mutable state: `characters`, `chat`, `chat_metadata`,
  `name1`, `name2`, `this_chid`, `streamingProcessor`, etc.
- Houses the core `Generate()` function, chat rendering, character loading, save
  logic, and the main jQuery event wiring.
- Ends with a massive jQuery document-ready block that wires up hundreds of UI
  event handlers.

This file acts as the application's **implicit dependency hub** -- almost every
other frontend module imports something from it.

### 3.4 Frontend Module Breakdown (`public/scripts/`)

There are **201 JavaScript files** under `public/scripts/`, totaling ~141,000 lines.
They are organized into flat files and a few subdirectories:

**Top-level modules (largest files):**

| File | Lines | Domain |
|------|------:|--------|
| `slash-commands.js` | 7,181 | Slash command registration and execution |
| `openai.js` | 6,996 | OpenAI/Chat Completion settings UI and request building |
| `world-info.js` | 6,273 | World Info (lorebook) management UI |
| `power-user.js` | 4,469 | Advanced user settings panel |
| `utils.js` | 2,995 | Frontend utility functions |
| `tags.js` | 2,850 | Tag system for characters and chats |
| `group-chats.js` | 2,490 | Group chat management |
| `chats.js` | 2,419 | Chat message rendering and manipulation |
| `variables.js` | 2,348 | Scripting variables system |
| `PromptManager.js` | 2,144 | Prompt template management UI |
| `personas.js` | 2,044 | User persona management |
| `extensions.js` | 1,877 | Extension loader and settings UI |
| `textgen-settings.js` | 1,847 | Text generation API settings |
| `reasoning.js` | 1,593 | Chain-of-thought / reasoning display |

**Subdirectories:**

| Directory | Files | Total Lines | Purpose |
|-----------|------:|------------:|---------|
| `scripts/slash-commands/` | 27 | 4,061 | Slash command parser, AST classes, closures |
| `scripts/autocomplete/` | 11 | 4,646 | Autocomplete engine for slash commands |
| `scripts/extensions/` | 16 dirs | 37,203 | Built-in extension modules |
| `scripts/macros/` | 17 | 6,171 | Macro engine: lexer, parser, CST walker, registry |
| `scripts/templates/` | 58 | N/A | Handlebars HTML template fragments |
| `scripts/util/` | 7 | ~600 | Small utility classes (mutex, storage, theming) |

### 3.5 Built-in Extensions

Each extension lives in `public/scripts/extensions/<name>/` and contains an
`index.js` entry point, optional HTML templates, and CSS:

| Extension | Lines | Purpose |
|-----------|------:|---------|
| `stable-diffusion/` | 5,951 | Image generation via SD, DALL-E, etc. |
| `expressions/` | 2,514 | Character expression/sprite system |
| `vectors/` | 2,313 | RAG / vector search integration |
| `regex/` | 2,126 | Regex-based text replacement rules |
| `quick-reply/` | ~4,000 | Quick reply buttons and macros |
| `tts/` | ~4,000 | Text-to-speech (AllTalk, MiniMax, ElevenLabs, etc.) |
| `memory/` | 1,131 | Chat memory / summarization |
| `gallery/` | 853 | Image gallery viewer |
| `caption/` | 807 | Image captioning |
| `translate/` | 804 | Message translation |
| `connection-manager/` | 827 | API connection profiles |
| `token-counter/` | ~300 | Token counting display |
| `attachments/` | ~1,500 | File attachment handling |
| `assets/` | ~500 | Character asset management |

A `shared.js` (876 lines) in the extensions root provides shared utilities.

### 3.6 Event System

The frontend uses a custom `EventEmitter` (from `public/lib/eventemitter.js`) with
**103 named event types** defined in `public/scripts/events.js`. These events
coordinate between modules without direct imports:

```js
// Sample from events.js
export const event_types = {
    APP_READY: 'app_ready',
    MESSAGE_SENT: 'message_sent',
    MESSAGE_RECEIVED: 'message_received',
    CHAT_CHANGED: 'chat_id_changed',
    GENERATION_STARTED: 'generation_started',
    GENERATION_ENDED: 'generation_ended',
    CHARACTER_EDITED: 'character_edited',
    SETTINGS_LOADED: 'settings_loaded',
    // ... 95 more
};

export const eventSource = new EventEmitter([
    event_types.APP_READY,
    event_types.APP_INITIALIZED,
]);
```

### 3.7 Context API

`public/scripts/st-context.js` provides a `getContext()` function that exposes the
application's global state as a stable API surface for extensions. It imports from
`script.js` and re-exports a curated set of functions and variables. This is the
recommended way for extensions to interact with the core.


## 4. Middleware Stack (`src/middleware/`)

Nine middleware files, all small and focused:

| File | Lines | Purpose |
|------|------:|---------|
| `whitelist.js` | 148 | IP whitelist enforcement with CIDR matching and Docker host resolution |
| `cacheBuster.js` | 110 | Sets `Clear-Site-Data: "cache"` header per user-agent to bust browser cache |
| `basicAuth.js` | 56 | HTTP Basic Auth with optional per-user authentication |
| `webpack-serve.js` | 55 | Serves Webpack-compiled `lib.js` and runs the compiler on startup |
| `accessLogWriter.js` | ~60 | Writes access logs for remote connections |
| `hostWhitelist.js` | ~60 | Validates the `Host` header against allowed values |
| `corsProxy.js` | 42 | Proxies requests to external domains, stripping security headers |
| `multerMonkeyPatch.js` | 30 | Fixes multer's Latin1 filename encoding to UTF-8 |
| `validateFileName.js` | ~45 | Validates uploaded file names against path traversal |

The middleware is applied in `server-main.js` in this order:
1. `helmet` (security headers, CSP disabled)
2. `compression` (gzip)
3. `responseTime` (X-Response-Time header)
4. `bodyParser.json` + `bodyParser.urlencoded` (500MB limit)
5. `cors` (configurable)
6. `basicAuth` (conditional: only when `listen` + `basicAuthMode`)
7. `whitelist` (conditional: only when `whitelistMode`)
8. `hostWhitelist` (always)
9. `accessLogger` (conditional: only when `listen`)
10. `cookieSession`
11. `setUserDataMiddleware` (attaches `req.user` with profile and directories)
12. CSRF protection via `csrf-sync`
13. `cacheBuster` (on index route)
14. Static file serving (`express.static`)
15. `requireLoginMiddleware` (authentication gate for all `/api/*` routes)
16. `multer` (file uploads) + `multerMonkeyPatch`


## 5. Configuration System

### 5.1 Config Sources (Priority Order)

1. **Environment variables**: `SILLYTAVERN_<KEY>` format. Dot-separated keys become
   underscored (e.g., `extensions.models.speechToText` becomes
   `SILLYTAVERN_EXTENSIONS_MODELS_SPEECHTOTEXT`).
2. **CLI arguments**: Parsed by yargs in `src/command-line.js`.
3. **config.yaml**: Read once and cached by `getConfig()` in `src/util.js`.
4. **Hardcoded defaults**: Defined in `CommandLineParser.getDefaultConfig()`.

The config file is 349 lines in `default/config.yaml` with sections for server,
SSL, security, CORS, extensions, performance, backups, and more.

### 5.2 Config Migration

`src/config-init.js` contains a `keyMigrationMap` array that automatically
migrates old config keys to new nested keys when the server starts. For example,
`disableThumbnails` becomes `thumbnails.enabled` (with value inversion).

### 5.3 Data Storage

SillyTavern uses **no database**. All data is stored as flat files on disk:
- Characters: PNG files with embedded JSON metadata (TavernCard v2 spec) in
  `data/<user>/characters/`
- Chats: JSONL files (one JSON object per line) in `data/<user>/chats/<char>/`
- Groups: JSON files in `data/<user>/groups/`
- Settings: `settings.json` in user data root
- Secrets (API keys): Encrypted JSON file
- World Info: JSON files in `data/<user>/worlds/`

The `node-persist` library provides a key-value store (backed by JSON files) for
user account data and server-level metadata.

Performance-sensitive data uses `MemoryLimitedMap` (an LRU cache with configurable
byte-size limit, defaulting to 100MB) and a `DiskCache` class backed by
`node-persist` for character data.


## 6. Type System

SillyTavern is a **pure JavaScript project** that uses JSDoc annotations and
TypeScript declaration files for type checking. It does NOT use TypeScript
compilation.

### 6.1 JSDoc Annotations

All backend code uses JSDoc `@typedef`, `@param`, `@returns`, and `@type` annotations
extensively. Example from `src/users.js`:

```js
/**
 * @typedef {Object} User
 * @property {string} handle
 * @property {string} name
 * @property {number} created
 * @property {string} password
 * @property {string} salt
 * @property {boolean} enabled
 * @property {boolean} admin
 */
```

### 6.2 TypeScript Declaration Files

- `index.d.ts` (74 lines): Augments global `NodeJS.Process`, `Express.Request`,
  `CookieSessionInterfaces`, and declares global variables (`DATA_ROOT`,
  `COMMAND_LINE_ARGS`).
- `public/global.d.ts` (241 lines): Declares frontend global types including
  `ChatMessage`, `ChatMetadata`, `Group`, `MediaAttachment`, jQuery plugin
  extensions, and the `window.SillyTavern` API.
- `src/types/byaf.d.ts`: Types for Backyard AI Format parsing.
- `src/types/spec-v2.d.ts`: Types for TavernCard v2 specification.

### 6.3 jsconfig.json

Two separate configs:
- Root `jsconfig.json`: Server-side, `strictNullChecks: true`,
  `strictFunctionTypes: true`, `checkJs: true`. Excludes `public/`.
- `public/jsconfig.json`: Client-side, `checkJs: true`, maps `/` paths for
  absolute imports. Excludes `lib/` and minified files.

Both enable type checking on plain `.js` files through the TypeScript language
service.


## 7. Build System

### 7.1 Webpack

Webpack is used solely to bundle frontend NPM dependencies into a single
`lib.js` file. The config (`webpack.config.js`, 124 lines):
- Entry: `public/lib.js`
- Output: ESM module (`libraryTarget: 'module'`)
- Mode: production
- Cache: Filesystem-based with version-keyed directories and automatic pruning

The compilation runs at server startup via `webpackMiddleware.runWebpackCompiler()`
in `preSetupTasks()`. Docker builds pre-compile into a `/dist` directory.

### 7.2 No Frontend Build Pipeline

The frontend JavaScript files are served directly as ES modules via
`express.static`. There is no transpilation, bundling, or minification of the
application code itself. The `<script type="module">` in `index.html` loads
`script.js` which imports all other modules natively.

### 7.3 npm Scripts

```json
"start": "node server.js",
"debug": "node --inspect server.js",
"start:electron": "cd ./src/electron && npm run start",
"start:deno": "deno run ... server.js",
"start:bun": "bun server.js",
"lint": "eslint \"src/**/*.js\" \"public/**/*.js\" ./*.js",
"postinstall": "node post-install.js"
```


## 8. Code Metrics Summary

### 8.1 Codebase Size

| Area | Files | Lines of Code |
|------|------:|-------------:|
| Backend (`src/`) | ~80 | 31,741 |
| Frontend (`public/scripts/` + `script.js`) | ~202 | ~141,463 |
| Tests | ~14 | ~5,000 |
| Config/Build/Other | ~15 | ~5,800 |
| **Total** | **~340** | **~185,000** |

### 8.2 Largest Files (Top 15)

| File | Lines |
|------|------:|
| `public/script.js` | 12,481 |
| `public/index.html` | 8,176 |
| `public/scripts/slash-commands.js` | 7,181 |
| `public/scripts/openai.js` | 6,996 |
| `public/style.css` | 6,376 |
| `public/scripts/world-info.js` | 6,273 |
| `public/scripts/extensions/stable-diffusion/index.js` | 5,951 |
| `public/scripts/power-user.js` | 4,469 |
| `public/scripts/utils.js` | 2,995 |
| `public/scripts/tags.js` | 2,850 |
| `src/endpoints/backends/chat-completions.js` | 2,683 |
| `public/scripts/group-chats.js` | 2,490 |
| `public/scripts/chats.js` | 2,419 |
| `public/scripts/variables.js` | 2,348 |
| `public/scripts/PromptManager.js` | 2,144 |

### 8.3 Dependency Count

- **Runtime dependencies**: 96 packages
- **Dev dependencies**: 24 packages (mostly @types/* for JSDoc type checking)
- Notable runtime deps: express, multer, cors, helmet, cookie-session, csrf-sync,
  node-fetch, webpack, tiktoken, sentencepiece, jimp, isomorphic-git, simple-git,
  ws (WebSocket), archiver, yaml, lodash, chalk, handlebars, showdown (markdown),
  highlight.js, fuse.js, morphdom, chevrotain (parser), dompurify


## 9. Dependency Graph and Coupling Patterns

### 9.1 Backend Dependency Flow

```
server.js
  └── src/server-main.js
        ├── src/util.js              (imported by almost everything)
        ├── src/constants.js         (imported by almost everything)
        ├── src/users.js             (auth, user dirs -- imported by endpoints)
        ├── src/middleware/*          (each imports from util.js)
        ├── src/server-startup.js    (imports all 44 endpoint routers)
        │     └── src/endpoints/*    (each is self-contained, imports util/constants)
        └── src/prompt-converters.js (imported by chat-completions.js)
```

**Key coupling observations:**

- `src/util.js` is the universal dependency. It exports 40+ functions and is
  imported by every endpoint, middleware, and infrastructure file.
- `src/constants.js` is the second most imported module, providing all shared
  enums and configuration constants.
- `src/users.js` is imported by any endpoint that needs user-scoped file paths
  (via `req.user.directories`).
- Endpoint files are largely **independent of each other**, with a few exceptions:
  - `characters.js` imports from `worldinfo.js`, `thumbnails.js`, `sprites.js`,
    `chats.js` (for cross-cutting concerns like importing character cards with
    embedded world info).
  - `backends/chat-completions.js` imports from `secrets.js`, `tokenizers.js`,
    `google.js`, and `prompt-converters.js`.

### 9.2 Frontend Dependency Flow

The frontend has no dependency hierarchy so much as a gravitational centre. `script.js` is a
12,481-line god object that both exports to and imports from most feature modules — the
double-headed edges below are the coupling that makes any one module hard to change in
isolation:

<Figure tag="Figure 1" title="script.js — the bidirectional hub" id="fig-scriptjs-hub">
<svg viewBox="0 0 720 460" role="img" aria-label="script.js as a bidirectionally coupled hub" style="font-family:var(--vp-font-family-base)">
  <defs>
    <marker id="tbm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-arrow)"/>
    </marker>
  </defs>
  <g stroke="var(--tbm-dgm-danger)" stroke-width="1.6" fill="none" marker-start="url(#tbm-ah)" marker-end="url(#tbm-ah)">
    <path d="M300 200 L188 80"/>
    <path d="M420 200 L532 80"/>
    <path d="M290 222 L164 228"/>
    <path d="M430 222 L556 228"/>
    <path d="M300 262 L188 382"/>
    <path d="M420 262 L532 382"/>
  </g>
  <g font-size="11.5" text-anchor="middle">
    <rect x="52" y="40" width="136" height="40" rx="9" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="120" y="65" fill="var(--tbm-dgm-ink)">openai.js</text>
    <rect x="532" y="40" width="136" height="40" rx="9" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="600" y="65" fill="var(--tbm-dgm-ink)">world-info.js</text>
    <rect x="24" y="208" width="140" height="40" rx="9" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="94" y="233" fill="var(--tbm-dgm-ink)">group-chats.js</text>
    <rect x="556" y="208" width="140" height="40" rx="9" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="626" y="233" fill="var(--tbm-dgm-ink)">power-user.js</text>
    <rect x="44" y="380" width="150" height="40" rx="9" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="119" y="405" fill="var(--tbm-dgm-ink)">slash-commands.js</text>
    <rect x="530" y="380" width="140" height="40" rx="9" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="600" y="405" fill="var(--tbm-dgm-ink)">textgen-settings.js</text>
  </g>
  <rect x="286" y="196" width="148" height="72" rx="12" fill="var(--tbm-dgm-danger-soft)" stroke="var(--tbm-dgm-danger)"/>
  <text x="360" y="222" text-anchor="middle" font-size="13" font-weight="800" fill="var(--tbm-dgm-ink)">script.js</text>
  <text x="360" y="240" text-anchor="middle" font-size="10" fill="var(--tbm-dgm-ink-2)">THE HUB · 12,481 lines</text>
  <text x="360" y="255" text-anchor="middle" font-size="10" fill="var(--tbm-dgm-ink-2)">217 exports · 74 imports</text>
  <text x="360" y="446" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-faint)">…and 65+ more modules. Double-headed = bidirectional import (tight coupling).</text>
</svg>
<template #caption>

**A hub, not a layer.** `openai.js` imports `Generate` from `script.js` while `script.js`
imports `oai_settings` from `openai.js`; the same mutual dependency repeats across most modules.
`events.js` (an EventEmitter with 103 event types) decouples *some* interactions, but shared
mutable globals like `characters`, `chat`, and `chat_metadata` keep the coupling tight.

</template>
</Figure>

```
public/script.js  (THE HUB: 217 exports, 74 local imports)
  ├── public/scripts/openai.js         (bidirectional: imports from script.js)
  ├── public/scripts/world-info.js     (bidirectional)
  ├── public/scripts/group-chats.js    (bidirectional)
  ├── public/scripts/power-user.js     (bidirectional)
  ├── public/scripts/textgen-settings.js (bidirectional)
  ├── public/scripts/slash-commands.js  (bidirectional)
  ├── public/scripts/events.js         (event bus, imported everywhere)
  ├── public/scripts/extensions.js     (extension loader)
  └── ... 65+ other modules
```

**Critical coupling issue**: `script.js` has **bidirectional dependencies** with
many modules. For example, `openai.js` imports `Generate` from `script.js`, and
`script.js` imports `oai_settings` from `openai.js`. This creates tight coupling
that makes it difficult to modify one without affecting the other.

The `events.js` module (EventEmitter with 103 event types) partially decouples
modules by allowing event-driven communication, but many modules still rely on
direct imports from `script.js` for mutable global state like `characters`,
`chat`, and `chat_metadata`.

### 9.3 Cross-Boundary Dependencies

The frontend communicates with the backend exclusively through HTTP `fetch()` calls
to the Express API endpoints. There is no shared code between frontend and backend
except for conceptual duplication:

```js
// src/constants.js, line 219
// TODO: this is copied from the client code; there should be a way to
// de-duplicate it eventually
export const TEXTGEN_TYPES = { ... };
```


## 10. Testing Infrastructure

### 10.1 Test Setup

Tests live in a separate `tests/` directory with its own `package.json` and
dependencies. Two test frameworks are used:

- **Jest** (unit tests): Configured via `jest.config.json` with
  `--experimental-vm-modules` for ESM support.
- **Playwright** (E2E tests): Configured via `playwright.config.js`, targeting
  `http://127.0.0.1:8000`.

### 10.2 Test Files

| File | Lines | Type |
|------|------:|------|
| `util-pure.test.js` | ~380 | Jest unit tests for pure utility functions |
| `util.test.js` | ~100 | Jest unit tests for server utilities (flattenSchema) |
| `mock-server.test.js` | ~40 | Jest test for mock server setup |
| `sample.e2e.js` | 12 | Playwright smoke test (page title check) |
| `frontend/MacroEngine.e2e.js` | 3,411 | Playwright E2E tests for macro engine |
| `frontend/MacroLexer.e2e.js` | ~200 | Playwright E2E tests for macro lexer |
| `frontend/MacroParser.e2e.js` | ~200 | Playwright E2E tests for macro parser |
| `frontend/MacroRegistry.e2e.js` | ~200 | Playwright E2E tests for macro registry |
| ... | | (8 macro-related E2E test files total) |

### 10.3 Test Coverage Assessment

Testing coverage is **minimal**. The ~5,000 lines of test code cover a tiny
fraction of the 185,000-line codebase. Most tests focus on the macro engine
(a relatively new subsystem). There are no tests for:
- API endpoint handlers
- Authentication/authorization
- Character card parsing
- Chat operations
- Provider-specific prompt conversion
- Any frontend UI logic beyond macros


## 11. Internationalization

The frontend supports 18 languages via `public/locales/` JSON files and the
`public/scripts/i18n.js` module (331 lines). Translation keys are embedded in
HTML elements using `data-i18n` attributes and processed at render time.

Supported locales: ar-sa, de-de, en, es-es, fr-fr, is-is, it-it, ja-jp, ko-kr,
nl-nl, pt-pt, ru-ru, th-th, uk-ua, vi-vn, zh-cn, zh-tw.


## 12. Key Architectural Patterns

### 12.1 File-Based Data Storage
No database. All persistence is through the filesystem using JSON, JSONL, and
PNG files with embedded metadata. This makes the system simple to deploy but
limits query capability and concurrent access.

### 12.2 Express Router-Per-Domain
Each API domain (characters, chats, settings, etc.) gets one Express router file.
No service layer or repository abstraction. Business logic and I/O are co-located
in route handlers.

### 12.3 Global Mutable State (Frontend)
`script.js` exports mutable variables (`let characters = []`, `let chat = []`)
that any module can import and mutate. This is a source of coupling and makes
data flow hard to trace.

### 12.4 Provider Adapter Pattern
The `chat-completions.js` endpoint and `prompt-converters.js` implement a
manual adapter pattern. A unified chat format is converted to provider-specific
payloads through dedicated converter functions (`convertClaudeMessages`,
`convertGooglePrompt`, `convertCohereMessages`, etc.).

### 12.5 Plugin System
Server plugins are loaded from the `plugins/` directory by `src/plugin-loader.js`.
Plugins can register Express routes and get access to the Express app instance.
They are auto-updated via git. This is opt-in via `enableServerPlugins` config.

### 12.6 Extension System (Frontend)
Built-in extensions in `public/scripts/extensions/` follow a convention-based
loading pattern. Third-party extensions can be installed into
`public/scripts/extensions/third-party/`. Extensions communicate with the core
through the `eventSource` EventEmitter and the `getContext()` API.
