# Extension & Plugin Systems — SillyTavern v1.17.0 vs The Bannered Mare

## Table of Contents

1. [Fundamental Architectural Difference](#1-fundamental-architectural-difference)
2. [SillyTavern's Extension Ecosystem](#2-sillytaverns-extension-ecosystem)
3. [The Bannered Mare's Extensibility Model](#3-the-bannered-mares-extensibility-model)
4. [Feature-by-Feature Comparison](#4-feature-by-feature-comparison)
5. [How ST Extension Capabilities Map to The Bannered Mare](#5-how-st-extension-capabilities-map-to-the-bannered-mare)
6. [Provider Extensibility](#6-provider-extensibility)
7. [Prompt Pipeline Extensibility](#7-prompt-pipeline-extensibility)
8. [Message Processing Extensibility](#8-message-processing-extensibility)
9. [Event Systems](#9-event-systems)
10. [Third-Party Integration Surface](#10-third-party-integration-surface)
11. [Trade-off Analysis](#11-trade-off-analysis)


## 1. Fundamental Architectural Difference

This is the most structurally different area between the two systems. SillyTavern is a self-contained application with a full plugin runtime. The Bannered Mare is a headless API server with no plugin system at all.

| Aspect | SillyTavern v1.17.0 | The Bannered Mare |
|---|---|---|
| **Application type** | Monolithic app (Node.js server + browser client) | Headless REST/SSE API (FastAPI) |
| **Extension mechanism** | Two plugin runtimes (server + frontend) | None. Extensibility through the API surface. |
| **Plugin count** | 14 built-in + unlimited third-party | 0 |
| **Extension loader code** | ~2,627 lines (1,877 frontend + 293 server + 457 backend endpoints) | N/A |
| **Event system** | 103 named event types, custom EventEmitter | N/A |
| **Extension settings** | Dedicated persistence layer per extension | N/A |
| **Extension distribution** | Git-based install/update/branch management | N/A |

The difference is not a gap in capability -- it reflects two different answers to the question "where does customization logic live?"

- **SillyTavern:** Customization lives inside the application. Extensions modify behavior at runtime through hooks, interceptors, and event handlers.
- **The Bannered Mare:** Customization lives in the client. The API exposes every primitive (characters, presets, templates, lore, providers, models) as CRUD endpoints. A frontend or automation script composes these primitives however it wants.


## 2. SillyTavern's Extension Ecosystem

### 2.1 Two-Layer Plugin Architecture

ST runs two independent extension systems:

**Server Plugins** (`./plugins/`):
- Node.js modules loaded at startup
- Each receives a scoped Express Router (`/api/plugins/{id}`)
- Lifecycle: `init(router)` and `exit()`
- Opt-in via `enableServerPlugins` config flag
- Auto-updated from git remotes on startup

**Frontend Extensions** (`public/scripts/extensions/`):
- Browser-side ES modules loaded at page init
- Full access to chat state, generation pipeline, UI rendering, slash commands, events
- Six lifecycle hooks: install, update, delete, enable, disable, activate
- Manifest-driven (`manifest.json`) with loading order, dependency declarations, version requirements

### 2.2 Built-in Extensions

ST ships 14 extensions covering capabilities that range from core RP features to multimedia integrations:

| Extension | What It Does |
|---|---|
| Connection Manager | Multi-profile API switching (model, preset, proxy, tokenizer) |
| Regex | Find/replace scripts on messages and prompts (3 scopes, 6 placement targets) |
| Translate | Real-time message translation via external providers |
| Data Bank | File attachments, web scraping, fandom/wiki import |
| Image Captioning | Multimodal image description via LLMs |
| Character Expressions | Sprite-based character emotion rendering |
| Gallery | Character image gallery management |
| Summarize (Memory) | Auto-summarization of chat history (3 backends) |
| Image Generation | SD/DALL-E/ComfyUI generation with trigger detection |
| TTS | Text-to-speech with 22+ provider adapters |
| Quick Replies | Macro buttons with auto-execution on events |
| Assets | Character asset library browser |
| Token Counter | Token count display in UI |
| Vector Storage | RAG via vector embeddings |

### 2.3 Extension APIs

Extensions access application state through `getContext()`, which exposes APIs for chat manipulation, character data, generation control, event subscription, slash commands, tokenization, prompt injection, UI rendering, tool registration, data bank scraping, macro registration, and i18n.

### 2.4 Third-Party Ecosystem

Third-party extensions install via git clone and have identical capabilities to built-in extensions. ST manages their lifecycle through 8 dedicated API endpoints (`/api/extensions/install`, `/update`, `/delete`, `/version`, `/branches`, `/switch`, `/move`, `/discover`). Auto-update is supported with concurrent version checking (max 5 parallel).

Security is minimal: extensions run with full browser context access, no sandboxing, no capability restrictions. The primary guard is user trust.


## 3. The Bannered Mare's Extensibility Model

The Bannered Mare has no plugin loader, no extension directory, no event bus, and no hook system. This is a deliberate architectural choice, not an omission.

### 3.1 API-First Extensibility

The system exposes 12 resource routers, each providing full CRUD:

| Router | Prefix | Capabilities |
|---|---|---|
| Providers | `/api/providers` | Register/configure AI providers (API keys, base URLs, provider types) |
| Model Families | `/api/model-families` | Define model families with parameter schemas and defaults |
| Models | `/api/models` | Register models with parameter overrides, OpenRouter routing |
| Characters | `/api/characters` | Character CRUD, TavernCard V1/V2 import/export (PNG + JSON) |
| Chat Sessions | `/api/chats` | Chat lifecycle, model/preset/persona assignment |
| Chat Messages | `/api/chats/{id}/messages` | Send, stream (SSE), edit, regenerate, manage alternatives |
| Personas | `/api/personas` | User persona CRUD |
| Presets | `/api/presets` | Parameter preset CRUD with default selection |
| Prompt Templates | `/api/prompt-templates` | Jinja2 templates with preview rendering and default selection |
| Lorebooks | `/api/lorebooks` | Lorebook and lore entry CRUD with keyword activation config |
| Health | `/health` | Readiness checks |
| Admin Logs | `/admin/logs` | HTTP, LLM audit, and error log querying with aggregation |

Any behavior that ST achieves through an extension, a Bannered Mare client can achieve by calling these endpoints in the right sequence. The "extension logic" lives in the client, not the server.

### 3.2 Composable Primitives

Several of ST's built-in extensions map directly to first-class The Bannered Mare API resources:

- **Connection Manager** (ST extension) maps to the Providers, Models, and Presets APIs. A client can switch a chat's model, preset, or persona with a single PUT to `/api/chats/{id}`.
- **Summarize / Memory** (ST extension) has no built-in equivalent, but a client can implement summarization by reading chat history via the messages API, calling an LLM through any provider, and storing the result (e.g., as a lore entry or system prompt update).
- **Regex** (ST extension) has no server-side equivalent. Regex-based message transformation would be a client responsibility.

### 3.3 Where Extensibility Points Do Exist

While The Bannered Mare has no plugin system, it does have internal extensibility patterns:

**Provider Adapter Registry** (`src/provider/adapters/__init__.py`):
A typed registry mapping `ProviderType` enums to adapter classes. Adding a new provider requires adding an adapter class implementing `ProviderAdapter` (5 abstract methods) and registering it in `_REGISTRY`. This is compile-time extensibility, not runtime.

**Jinja2 Template Engine** (`src/core/utils/template.py`):
Prompt templates are user-editable Jinja2 strings stored in the database. Users control prompt structure (system messages, variable injection, conditional blocks) through template authoring, not code.

**Lore Activation Engine** (`src/lore/activation_engine.py`):
A stateless keyword/regex matching engine that activates lore entries based on recent message content. Supports primary keys, secondary keys with AND/NOT logic, regex patterns, case sensitivity, whole-word matching, priority ordering, and token budgets. This is data-driven extensibility -- behavior changes by editing lore entries, not code.

**Preset Parameter System** (`src/provider/gateway.py`):
Three-layer parameter merging: ModelFamily defaults, Model overrides, Preset overrides. Users control generation parameters through API-managed presets without touching server code.

**FastAPI Middleware** (`src/main.py`):
CORS and request logging middleware are registered at startup. Adding new middleware requires a code change.


## 4. Feature-by-Feature Comparison

| Capability | SillyTavern | The Bannered Mare |
|---|---|---|
| **Plugin runtime** | Two (server + frontend) | None |
| **Plugin lifecycle hooks** | 8 (2 server + 6 frontend) | N/A |
| **Event bus** | 103 event types, custom EventEmitter | N/A |
| **Generate interceptors** | Yes (pre-generation hooks) | N/A |
| **Extension settings storage** | Per-extension namespaced persistence | N/A |
| **Third-party distribution** | Git clone/update/branch management | N/A |
| **Regex message processing** | Built-in extension (3 scopes, 6 targets) | Client responsibility |
| **Auto-summarization** | Built-in extension (3 backends) | Client responsibility |
| **Connection profiles** | Built-in extension (14 fields per profile) | API-composed (Provider + Model + Preset) |
| **Image generation** | Built-in extension (SD/DALL-E/ComfyUI) | Out of scope |
| **TTS** | Built-in extension (22+ providers) | Out of scope |
| **RAG/Vector storage** | Built-in extension | Out of scope |
| **Translation** | Built-in extension | Client responsibility |
| **Slash commands** | Extensible command parser | N/A (API endpoints serve this role) |
| **Macro system** | `{{variable}}` substitution in prompts | Jinja2 template variables (`{{char}}`, `{{user}}`, etc.) |
| **Prompt injection** | `setExtensionPrompt()` API per extension | Lore entries with insertion positions + template editing |
| **Provider addition** | Server-side adapter code | Adapter class + registry entry (code change) |
| **Custom parameters** | Per-preset extension fields | Preset parameters (JSON) + model family parameter schemas |


## 5. How ST Extension Capabilities Map to The Bannered Mare

### 5.1 Capabilities That Map to API Primitives

These ST extension features have direct The Bannered Mare API equivalents:

**Connection Manager** --> Provider/Model/Preset/Chat APIs

ST's Connection Manager extension saves and restores "profiles" of 14 settings (API, model, preset, proxy, tokenizer, etc.) via slash command execution. In The Bannered Mare, this same workflow is:

```
PUT /api/chats/{id}  { "model_id": "...", "preset_id": "...", "persona_id": "..." }
```

One API call replaces the entire profile-switching mechanism. The client decides when and how to compose these switches.

**Memory/Summarize** --> Client-side orchestration

ST's Memory extension monitors message count/word count thresholds, calls an LLM to generate a summary, and injects it into the prompt via `setExtensionPrompt()`. A The Bannered Mare client can replicate this:

1. `GET /api/chats/{id}/messages` -- read history
2. Call any LLM (through The Bannered Mare or directly) with a summarization prompt
3. Store the summary as a lore entry (`POST /api/lorebooks/{id}/entries`) with `constant: true` and appropriate insertion position

The trigger logic (message count thresholds, word count gates) lives in the client.

**Quick Replies** --> Client UI

ST's Quick Replies are macro buttons that execute slash commands on events. In a headless API, this is purely a frontend concern -- the client renders buttons and maps them to API calls.

### 5.2 Capabilities That Require Client-Side Implementation

These ST extension features have no server-side equivalent and must be implemented by the client:

| ST Extension | Client Implementation Needed |
|---|---|
| Regex scripts | Client applies regex transforms before display or before sending user input |
| Translation | Client calls a translation API and substitutes message content |
| Token Counter | Client uses tokenization estimates from message responses or a local tokenizer |
| Character Expressions | Client-side sprite rendering based on message sentiment |

### 5.3 Capabilities Outside The Bannered Mare's Scope

These ST extensions cover domains that a headless chat API does not address:

- **Image Generation** (Stable Diffusion, DALL-E, ComfyUI)
- **TTS** (22+ voice synthesis providers)
- **Image Captioning** (multimodal description)
- **Gallery** (character image management beyond avatars)
- **Assets** (character asset library)
- **Data Bank** (file attachments, web scraping)
- **Vector Storage** (RAG embeddings)

These are not "missing features" -- they represent different scope decisions. A headless API handles text-based LLM interactions. Multimedia, voice synthesis, and vector search are adjacent systems that a client or sidecar service would integrate independently.


## 6. Provider Extensibility

### SillyTavern

ST supports 40+ providers through a combination of server-side endpoint modules and client-side format conversion. Adding a provider involves modifying multiple files across both server and client code. The provider list is hardcoded in `src/constants.js` and switching requires frontend UI interaction.

### The Bannered Mare

Providers are database-managed entities with a typed adapter system:

```
_REGISTRY: dict[ProviderType, type[ProviderAdapter]] = {
    ProviderType.OPENAI: OpenAIAdapter,
    ProviderType.ANTHROPIC: AnthropicAdapter,
    ProviderType.GOOGLE: GeminiAdapter,
    ProviderType.XAI: OpenAIAdapter,       # Reuses OpenAI-compatible adapter
    ProviderType.OPENROUTER: OpenAIAdapter, # Reuses OpenAI-compatible adapter
    ProviderType.OLLAMA: OllamaAdapter,
    ProviderType.CUSTOM: OpenAIAdapter,     # Fallback for OpenAI-compatible APIs
}
```

The adapter abstraction (`ProviderAdapter`) defines 5 methods: `build_url`, `build_headers`, `build_payload`, `parse_response`, `parse_stream_line`. Adding a new provider means writing one Python class and adding one registry entry.

The `ProviderType.CUSTOM` entry with `OpenAIAdapter` as the fallback means any OpenAI-compatible API (LM Studio, text-generation-webui, etc.) can be configured through the API without any code changes -- just register a new provider with the custom type and its base URL.

**Trade-off:** ST supports more providers out of the box. The Bannered Mare's adapter pattern is more uniform but requires a code change for genuinely new API formats.


## 7. Prompt Pipeline Extensibility

### SillyTavern

Extensions inject into the prompt pipeline via `setExtensionPrompt(name, content, position, depth, scan, role)`. Multiple extensions can inject at the same position, ordered by their loading order. The `generate_interceptor` mechanism allows extensions to abort or modify generation before it starts. The regex engine applies find/replace transformations at 6 different pipeline stages.

This creates a powerful but complex prompt assembly pipeline where the final prompt is the result of many layered transformations from independent extensions.

### The Bannered Mare

The prompt pipeline is assembled by `PromptBuilder` using four inputs:
1. **System template** -- Jinja2 template from the active prompt template
2. **Lore entries** -- Activated by the keyword engine, inserted at configured positions (`before_character`, `after_character`, `at_depth`, `before_examples`)
3. **Chat history** -- Messages from the database
4. **Preset parameters** -- Merged from family defaults, model overrides, and preset overrides

There are no runtime interceptors or hooks. The pipeline is deterministic: given the same inputs (template, lore, messages, preset), the same prompt is always produced.

A client that needs regex-style transformations or pre-generation interception must implement that logic before calling the send/stream endpoints.

**Trade-off:** ST's pipeline is more flexible at runtime -- extensions can modify prompts in ways the core developers did not anticipate. The Bannered Mare's pipeline is more predictable -- the prompt is a pure function of its configured inputs, making it easier to debug and reproduce.


## 8. Message Processing Extensibility

### SillyTavern

Messages pass through multiple processing stages:
- Regex scripts (6 placement targets: user input, AI output, slash commands, world info, reasoning, display)
- Event handlers (`MESSAGE_SENT`, `MESSAGE_RECEIVED`, `MESSAGE_EDITED`, `MESSAGE_SWIPED`, etc.)
- Generate interceptors (pre-generation)
- Macro substitution (`{{char}}`, `{{user}}`, custom macros)

Extensions can transform messages at any stage, and the order of transformations is controlled by loading order and event subscription priority.

### The Bannered Mare

Messages are stored and retrieved without transformation. The API returns message content exactly as received from the LLM (after optional `<think>` tag parsing for reasoning content). The template engine applies Jinja2 variable substitution at prompt assembly time, but message content itself is not modified.

If a client needs to display transformed messages (e.g., with regex replacements, markdown rendering, or custom formatting), it applies those transforms after fetching from the API.

**Trade-off:** ST's message processing pipeline is richer and enables features like automatic regex replacement and expression detection without client code. The Bannered Mare's approach keeps the server as a clean data store -- the message in the database is the message the LLM produced, with no server-side mutations, making it simpler to audit and replay conversations.


## 9. Event Systems

### SillyTavern

A custom `EventEmitter` with 103 named event types covering application lifecycle, messages, generation, chats, characters, settings, world info, connections, presets, secrets, UI, groups, tools, files, personas, and TTS. Extensions subscribe via `eventSource.on()` and can control execution order via `eventSource.makeLast()`. Two "sticky" events (`APP_READY`, `APP_INITIALIZED`) fire for late subscribers.

Built-in extensions collectively register 42 event handlers across 25 event types.

### The Bannered Mare

No event system. The application is request-response with SSE streaming for chat completions. Server-Sent Events during streaming emit 6 typed event types: `start`, `text`, `reasoning`, `usage`, `done`, `error`. These are stream protocol events, not an application event bus.

There is no mechanism for one part of the server to react to events from another part. Each request is handled by a single router -> service -> repository call chain.

**Trade-off:** ST's event system enables reactive, loosely-coupled extension behavior (e.g., the Memory extension reacting to `CHARACTER_MESSAGE_RENDERED` to trigger summarization). The Bannered Mare's lack of an event system means less implicit behavior and no ordering-dependent side effects, but also means features like auto-summarization cannot be triggered server-side.


## 10. Third-Party Integration Surface

### SillyTavern

Third-party developers can:
- Write frontend extensions with full access to chat state, generation, events, UI, and slash commands
- Write server plugins that mount Express routes under `/api/plugins/{id}`
- Distribute via git repositories with manifest-based metadata
- Declare dependencies on other extensions and ST Extras API modules
- Use lifecycle hooks for install/update/delete operations

### The Bannered Mare

Third-party developers can:
- Build any frontend against the REST/SSE API (OpenAPI spec available)
- Build automation scripts that compose API calls for custom workflows
- Build sidecar services that consume The Bannered Mare's API for features like TTS, image gen, or RAG
- Register custom OpenAI-compatible providers through the API without code changes

The integration boundary is HTTP. There is no way to inject code into the server at runtime.

**Trade-off:** ST offers deeper integration -- extensions can modify internal behavior in ways the API surface alone cannot express. The Bannered Mare offers cleaner boundaries -- the server's behavior is fully defined by its own code and database state, never by third-party code running inside it. This makes the server more predictable and easier to secure, but means the client must implement any "smart" behavior that ST would handle via extensions.


## 11. Trade-off Analysis

### What SillyTavern Gains from Extensions

1. **Feature density without core bloat** -- TTS, image generation, translation, and vector storage are extensions, not core code. The core can stay focused on chat while extensions handle adjacent domains.
2. **Community contribution model** -- Third-party developers can add features without forking or contributing to the core codebase.
3. **Runtime customization** -- Users can enable/disable features, change behavior, and install new capabilities without restarting or redeploying.
4. **Integrated UX** -- Extensions render UI directly in the application, providing a seamless experience rather than requiring external tools.

### What SillyTavern Pays for Extensions

1. **Complexity** -- 2,600+ lines just for extension loading/management. The 103-event system creates implicit coupling between independently developed extensions.
2. **Ordering dependencies** -- `loading_order`, `makeLast()`, and multiple extension injection points create a priority system that can produce surprising results when extensions interact.
3. **Security surface** -- Extensions run with full access to browser context and application state. No sandboxing, no capability model, no code review gate.
4. **Debugging difficulty** -- When something goes wrong in the prompt or message pipeline, the cause could be any of N active extensions, processed in priority order with regex transforms at 6 stages.

### What The Bannered Mare Gains from No Extensions

1. **Predictability** -- Given a set of inputs (template, lore, messages, preset, model), the system always produces the same prompt. No hidden side effects from extensions.
2. **Security** -- No third-party code runs inside the server. The attack surface is the API boundary, which is validated by Pydantic schemas.
3. **Debuggability** -- Every prompt is a deterministic function of database state. If a prompt is wrong, the cause is in the template, lore entries, or message history -- all of which are inspectable via the API.
4. **Client freedom** -- Any frontend technology (web, mobile, CLI, automation) can build on the API. The server does not assume a browser environment.

### What The Bannered Mare Pays for No Extensions

1. **Client burden** -- Features that ST handles with built-in extensions (regex, summarization, translation, connection profiles) must be implemented by every client independently.
2. **No shared ecosystem** -- There is no mechanism for community-contributed server-side features. Contributions must be PRs to the core codebase.
3. **No runtime customization** -- Changing server behavior requires code changes and redeployment. Users cannot install/enable/disable features through a UI.
4. **Feature parity gap** -- ST's 14 built-in extensions represent years of community-driven feature development. A headless API starts from zero on those capabilities.

### The Core Trade-off

SillyTavern optimizes for **feature completeness in a single application**. Everything a user needs for AI roleplay -- chat, TTS, image generation, regex processing, summarization, vector search -- is available as extensions within one running instance.

The Bannered Mare optimizes for **a clean API contract with client autonomy**. The server handles what a server should handle (persistence, LLM routing, prompt assembly, streaming) and leaves everything else to the client layer. This is a bet that the right abstraction boundary is HTTP, not an in-process plugin API.

Neither approach is inherently superior. The right choice depends on whether the deployment is a "batteries-included local app" (ST's model) or a "backend service powering diverse frontends" (The Bannered Mare's model).


## Summary Statistics

| Metric | SillyTavern | The Bannered Mare |
|---|---|---|
| Extension loader code | ~2,627 lines | 0 lines |
| Plugin runtimes | 2 (server + frontend) | 0 |
| Built-in extensions | 14 | 0 |
| Event types | 103 | 6 (SSE stream events only) |
| Extension lifecycle hooks | 8 | 0 |
| Third-party extension management endpoints | 8 | 0 |
| API resource routers | N/A (endpoints are endpoint-grouped) | 12 |
| Provider adapter pattern | Per-provider endpoint modules | Abstract base class + typed registry |
| Prompt injection points (extension-controlled) | Unlimited (via `setExtensionPrompt`) | 4 (lore insertion positions) |
| Message transform stages | 6+ (regex placements + events) | 0 (messages stored as-received) |
| Extensibility model | Runtime plugin loading | Compile-time code changes + API composition |
