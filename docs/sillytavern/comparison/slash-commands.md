# Command & Scripting Systems — SillyTavern v1.17.0 vs The Bannered Mare

This page assumes the [Slash Commands Analysis](/sillytavern/analysis/slash-commands) for how
SillyTavern's STscript works internally, and focuses on where The Bannered Mare diverges and why.
The comparison is honest about a fundamental architectural difference: SillyTavern is an interactive application with a chat input bar where users type commands directly; The Bannered Mare is a headless API backend that exposes functionality through HTTP endpoints. These are different paradigms solving different problems, and neither approach is wrong.


This is a paradigm difference, not a feature gap: the same operations are reached through a
chat-bar scripting language on one side and typed HTTP endpoints on the other:

<Figure tag="Figure 1" title="STscript REPL vs REST endpoints" id="fig-cmp-commands">
<svg viewBox="0 0 760 262" role="img" aria-label="SillyTavern STscript vs The Bannered Mare REST" style="font-family:var(--vp-font-family-base)">
  <rect x="24" y="16" width="344" height="230" rx="12" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <rect x="392" y="16" width="344" height="230" rx="12" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <rect x="24" y="16" width="344" height="44" rx="12" fill="var(--tbm-dgm-provider-soft)"/><rect x="24" y="36" width="344" height="24" fill="var(--tbm-dgm-provider-soft)"/>
  <rect x="392" y="16" width="344" height="44" rx="12" fill="var(--tbm-dgm-backend-soft)"/><rect x="392" y="36" width="344" height="24" fill="var(--tbm-dgm-backend-soft)"/>
  <text x="196" y="44" text-anchor="middle" font-size="13" font-weight="800" fill="var(--tbm-dgm-ink)">SillyTavern v1.17.0</text>
  <text x="564" y="44" text-anchor="middle" font-size="13" font-weight="800" fill="var(--tbm-dgm-ink)">The Bannered Mare</text>
  <g font-size="10.5" fill="var(--tbm-dgm-ink)">
    <text x="40" y="90">Interface — STscript in the chat bar (a REPL)</text>
    <text x="40" y="122">Power — Turing-complete, ~200+ commands</text>
    <text x="40" y="154">Blocks — closures · pipes · flow control</text>
    <text x="40" y="186">Switch model — /model gpt-4o</text>
    <text x="40" y="222" fill="var(--tbm-dgm-ink-2)">A shell embedded in the GUI</text>
    <text x="408" y="90">Interface — typed REST / SSE endpoints</text>
    <text x="408" y="122">Power — CRUD primitives, composed by the client</text>
    <text x="408" y="154">Blocks — HTTP verbs + JSON bodies</text>
    <text x="408" y="186">Switch model — PUT /api/chats/{id}</text>
    <text x="408" y="222" fill="var(--tbm-dgm-ink-2)">No command system (headless API)</text>
  </g>
</svg>
<template #caption>

**Same goal, different surface.** SillyTavern is an interactive app whose chat bar doubles as a
programmable REPL; The Bannered Mare is a headless backend, so the equivalent of `/model gpt-4o`
is a typed request against `/api/chats/{id}`.

</template>
</Figure>

## 1. Does The Bannered Mare Have a Command System?

No. The Bannered Mare has no slash commands, no scripting language, no macro system, no command registry, and no command parser. There is nothing in the codebase analogous to STscript.

This is not an oversight or a gap -- it is a direct consequence of the architectural split. The Bannered Mare is a backend API. It has no user-facing text input. It has no chat bar where a user could type `/send Hello`. Every operation is performed through typed REST endpoints consumed by a frontend client.

The ST equivalent of "switching a model" is `/model gpt-4o`. The The Bannered Mare equivalent is `PUT /api/chats/{id}` with `{"model_id": "..."}` in the request body. Both accomplish the same thing. The interface is different.


## 2. SillyTavern's STscript — What It Is

STscript is a Turing-complete scripting language embedded in SillyTavern's chat input — a
command-line shell wearing a GUI. In brief: ~200+ registered commands, a hand-written
recursive-descent parser producing an AST of first-class closures, pipe-based composition,
three variable scopes, full flow control (`/if`, `/while`, `/times`), a step debugger,
IDE-grade autocomplete, and Quick Replies as saved scripts with auto-execution hooks. Full
detail in [Analysis §1 Command Registry ›](/sillytavern/analysis/slash-commands#_1-command-registry),
[§3 Parser Architecture ›](/sillytavern/analysis/slash-commands#_3-parser-architecture),
[§4 Execution Engine ›](/sillytavern/analysis/slash-commands#_4-execution-engine),
[§5 Variable System ›](/sillytavern/analysis/slash-commands#_5-variable-system),
[§6 Flow Control ›](/sillytavern/analysis/slash-commands#_6-flow-control), and
[§7 Built-in Command Categories ›](/sillytavern/analysis/slash-commands#_7-built-in-command-categories).


## 3. What The Bannered Mare Has Instead

The Bannered Mare does not need a command language because it exposes the same operations through a different interface. Here is how each category of ST command maps to The Bannered Mare's API surface.

### 3.1 REST Endpoints as the "Command Interface"

| ST Command Category | The Bannered Mare Equivalent | Interface |
|--------------------|-----------------------|-----------|
| `/send`, `/sys`, `/sendas` | `POST /api/chats/{id}/messages` | JSON body with `role` and `content` |
| `/regenerate`, `/continue` | `POST /api/chats/{id}/messages?regenerate=true` | Query parameter |
| `/gen` (streaming) | `POST /api/chats/{id}/messages?stream=true` | SSE response |
| `/go name` (switch character) | `POST /api/chats` | New chat with a different `character_id` (a chat's character is fixed at creation) |
| `/model name` | `PUT /api/chats/{id}` | Update `model_id` |
| `/character-create` | `POST /api/characters` | Multipart form |
| `/character-update` | `PUT /api/characters/{id}` | Multipart form |
| `/character-delete` | `DELETE /api/characters/{id}` | -- |
| `/closechat`, `/delchat` | `DELETE /api/chats/{id}` | -- |
| `/api name` (switch provider) | `PUT /api/providers/{id}` | JSON body |
| Message alternatives (swipes) | `GET/PUT .../messages/{id}/alternatives` | Dedicated endpoints |
| Lorebook activation | Automatic via `ActivationEngine` | No manual command needed |
| Prompt injection | `PromptBuilder.build_api_messages()` | Template-driven, not ad-hoc |

The pattern is consistent: what ST exposes as imperative commands (`/verb object`), The Bannered Mare exposes as declarative resources (`METHOD /resource/{id}`).

### 3.2 Template System (Jinja2 vs ST Macros)

SillyTavern uses a custom macro substitution system with `{{getvar::name}}`, `{{char}}`, `{{user}}`, `{{pipe}}`, and dozens of other macro patterns. These are resolved by regex replacement during command execution and prompt assembly.

The Bannered Mare uses Jinja2 templates with a fixed set of context variables:

```
{{char}}          -- Character name
{{user}}          -- Persona name (or "User")
{{description}}   -- Character description
{{personality}}   -- Character personality
{{scenario}}      -- Scenario text
{{persona}}       -- Persona description
{{time}}          -- Current time (HH:MM)
{{date}}          -- Current date (YYYY-MM-DD)
{{chat_title}}    -- Chat title
```

The Bannered Mare's template system is intentionally narrower. There is no variable storage, no `{{pipe}}`, no `{{getvar::*}}`. Templates are rendered once during prompt assembly by `TemplateService.render()`, not iteratively during command execution. The trade-off is clear: ST's macros are more powerful and flexible; The Bannered Mare's templates are more predictable and easier to reason about.

### 3.3 Prompt Assembly (Declarative vs Imperative)

In ST, users can imperatively manipulate the prompt mid-session:

```text
/inject id=myLore position=4 depth=2 Here is some injected context.
/flushinject myLore
```

In The Bannered Mare, prompt assembly is fully declarative. The `PromptBuilder` reads the template's `component_order` and `components_enabled` configuration, assembles components in the specified order, applies the token budget, and injects activated lore entries at their configured positions. There is no way for a user to inject arbitrary text into the prompt at runtime via the API.

The equivalent of `/inject` in The Bannered Mare is creating a lore entry with the desired `InsertionPosition` and keywords that will activate when relevant. This is more constrained but also more auditable -- the prompt's content is always traceable to configured data, not runtime commands.

### 3.4 Parameter Control

ST's `/instruct name` and `/context name` commands switch presets at runtime during a scripted sequence. The Bannered Mare achieves this through its Preset system:

- Presets are stored as named parameter sets (temperature, top_p, etc.) in the database.
- A chat session references a preset via foreign key.
- The `ProviderGateway._get_effective_parameters()` method merges parameters in order: ModelFamily defaults, Model overrides, Preset overrides.
- Switching presets means updating the chat's preset reference via `PUT /api/chats/{id}`.


## 4. What The Bannered Mare Cannot Do (That ST Can)

These are capabilities that exist in STscript with no current The Bannered Mare equivalent:

| Capability | ST Implementation | The Bannered Mare Status |
|-----------|-------------------|-------------------|
| **User-defined scripting** | STscript closures, variables, flow control | Not applicable -- no UI layer |
| **Chained operations** | Pipe-based composition (`/cmd1 | /cmd2 | /cmd3`) | N/A for a REST API |
| **Runtime prompt injection** | `/inject` with arbitrary text, position, depth | No equivalent. Prompt content comes from configured data only |
| **Auto-execution hooks** | QR triggers on user message, AI response, chat change, etc. | No event hook system |
| **Text processing utilities** | `/upper`, `/lower`, `/replace`, `/match`, `/substr` | N/A -- text processing is a frontend/client concern |
| **Math operations** | `/add`, `/sub`, `/mul`, etc. in STscript | N/A |
| **UI interactions** | `/echo`, `/popup`, `/input`, `/buttons` | N/A -- headless backend |
| **Step debugger** | Breakpoints, step-into, variable inspection | N/A |
| **Quick Replies** | Saved scripts with auto-execution flags | No equivalent |
| **Dynamic autocomplete** | Parser-driven suggestions with enum providers | N/A -- no text input |
| **Variable persistence** | Chat-local and global variables | No runtime variable storage |

The "N/A" entries are not missing features. They are capabilities that belong in a frontend application, not a backend API. A future The Bannered Mare frontend could implement its own scripting layer that calls the REST API, but that scripting layer would live in the client, not the server.


## 5. What The Bannered Mare Has (That ST Doesn't)

The headless API architecture provides capabilities that ST's monolithic approach does not:

| Capability | The Bannered Mare Implementation | ST Equivalent |
|-----------|---------------------------|---------------|
| **Multi-client support** | Any HTTP client can consume the API | Single browser tab |
| **Typed request/response contracts** | Pydantic schemas with validation | None -- commands accept arbitrary strings |
| **Structured error responses** | HTTP status codes, typed error bodies | Toast notifications, CSS classes |
| **Pagination** | Cursor-based and offset-based pagination on all list endpoints | N/A for commands |
| **Concurrent access** | Async request handling, database transactions | Single-user JS event loop |
| **Database-backed persistence** | PostgreSQL with Alembic migrations | JSON files on disk |
| **Provider adapter abstraction** | `ProviderGateway` with typed `CompletionResponse` / `StreamChunk` | Per-provider code paths in `sendGenerationRequest` |
| **Audit logging** | PostgreSQL-backed HTTP and LLM call logging | Browser console |
| **Lore activation engine** | Keyword/regex matching with primary + secondary logic, token budgeting | Similar (World Info), but triggered manually via commands too |


## 6. The Architectural Trade-off

This comparison boils down to one fundamental design decision:

**SillyTavern is a complete application.** It owns the UI, the business logic, and the data layer. Users interact directly with the system through the chat input. The slash command system exists because users need a way to perform complex operations within that single interface. STscript grew organically to meet that need -- from simple shortcuts to a full programming language.

**The Bannered Mare is a backend service.** It owns the business logic and the data layer, but not the UI. Users interact through a client application that makes API calls. There is no need for a command language because the API itself is the command interface. Each endpoint is a "command" with typed parameters and typed responses.

The trade-offs are symmetric:

| | SillyTavern | The Bannered Mare |
|-|-------------|-----------------|
| **User power** | High -- users can script arbitrary sequences | Low -- limited to what the API exposes |
| **Predictability** | Lower -- runtime scripts can modify state in unexpected ways | Higher -- all state changes go through validated API endpoints |
| **Complexity budget** | STscript parser + execution engine + debugger + autocomplete = significant codebase surface | Zero command infrastructure to maintain |
| **Extension model** | Extensions register commands into the global registry | Future extensions would be new API modules (routers + services) |
| **Frontend flexibility** | Tightly coupled to ST's UI | Any client can connect -- web app, mobile app, CLI tool, another service |

Neither approach is superior. ST's command system is a genuine engineering achievement that enables sophisticated user workflows within a single application. The Bannered Mare's API-first design trades user-facing scriptability for client flexibility and operational simplicity. The "missing" command system in The Bannered Mare is an intentional absence, not a gap to be filled.


## 7. If The Bannered Mare Ever Needed Automation

If future requirements demanded server-side automation (batch operations, scheduled tasks, webhook-triggered sequences), the The Bannered Mare approach would not be a command language. It would likely be:

1. **Webhook / event endpoints** -- external systems POST to trigger actions.
2. **Background task queues** -- Celery or similar for deferred multi-step operations.
3. **Composable service methods** -- internal orchestration in the service layer, not user-facing scripts.

The key difference would remain: automation logic would be in typed Python code with database-backed state, not in a user-authored scripting language executed at runtime.
