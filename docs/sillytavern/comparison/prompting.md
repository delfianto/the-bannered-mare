# Prompting System Comparison: SillyTavern v1.17.0 vs The Bannered Mare

Both assemble a prompt within a token budget, but one is a large client-server pipeline and the
other a small server-side pass:

<Figure tag="Figure 1" title="~12,000 lines client+server vs ~800 lines server-side" id="fig-cmp-prompting">
<svg viewBox="0 0 760 262" role="img" aria-label="SillyTavern vs The Bannered Mare prompting pipeline" style="font-family:var(--vp-font-family-base)">
  <rect x="24" y="16" width="344" height="230" rx="12" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <rect x="392" y="16" width="344" height="230" rx="12" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <rect x="24" y="16" width="344" height="44" rx="12" fill="var(--tbm-dgm-provider-soft)"/><rect x="24" y="36" width="344" height="24" fill="var(--tbm-dgm-provider-soft)"/>
  <rect x="392" y="16" width="344" height="44" rx="12" fill="var(--tbm-dgm-backend-soft)"/><rect x="392" y="36" width="344" height="24" fill="var(--tbm-dgm-backend-soft)"/>
  <text x="196" y="44" text-anchor="middle" font-size="13" font-weight="800" fill="var(--tbm-dgm-ink)">SillyTavern v1.17.0</text>
  <text x="564" y="44" text-anchor="middle" font-size="13" font-weight="800" fill="var(--tbm-dgm-ink)">The Bannered Mare</text>
  <g font-size="10.5" fill="var(--tbm-dgm-ink)">
    <text x="40" y="90">Runs — client (browser) + server format-convert</text>
    <text x="40" y="122">Size — ~12,000 lines of JavaScript</text>
    <text x="40" y="154">Assembly — 5+ phases, reserve/free budgeting</text>
    <text x="40" y="186">Extend — CHAT_COMPLETION_PROMPT_READY hook</text>
    <text x="40" y="222" fill="var(--tbm-dgm-ink-2)">Powerful, many handoff points</text>
    <text x="408" y="90">Runs — server-side (Python)</text>
    <text x="408" y="122">Size — ~800 lines</text>
    <text x="408" y="154">Assembly — single-pass iterate-and-append</text>
    <text x="408" y="186">Extend — none; DB-configured order + fragments</text>
    <text x="408" y="222" fill="var(--tbm-dgm-ink-2)">Compact, one orchestration method</text>
  </g>
</svg>
<template #caption>

**Fifteen-to-one on line count.** SillyTavern's assembly spans the browser and server with a
multi-phase reserve/free budget and an extension hook; The Bannered Mare does it in one
server-side `PromptBuilder` pass driven by a database-stored `component_order`.

</template>
</Figure>

## 1. Architecture Overview

### SillyTavern

The prompting system is a **client-server split pipeline**. Prompt assembly happens entirely in the browser via JavaScript classes (`ChatCompletion`, `Message`, `MessageCollection`, `PromptManager`). The assembled prompt -- always in OpenAI ChatML format -- is sent to a Node.js backend that performs provider-specific format conversion via `prompt-converters.js` before forwarding to the API.

Key files: `openai.js` (6996 lines), `PromptManager.js` (2144 lines), `macros.js`, `instruct-mode.js`, `prompt-converters.js` (1445 lines).

Total complexity: ~12,000 lines of JavaScript across the prompt assembly path.

### The Bannered Mare

The prompting system is a **server-side monolithic pipeline**. A single `PromptBuilder` class (`prompt_builder.py`, ~220 lines) constructs the message array from database-persisted `PromptTemplate` configuration. Provider-specific formatting is handled by a separate `ProviderAdapter` hierarchy that transforms the canonical OpenAI-format messages into each provider's native format.

Key files: `prompt_builder.py`, `core/utils/template.py` (~115 lines), `core/persistence/models.py` (PromptTemplate + PromptFragment + TemplateFragment + DEFAULT_COMPONENT_ORDER), `prompt_fragment/service.py` (~178 lines), `lore/activation_engine.py` (~153 lines), `provider/adapters/*.py`.

Total complexity: ~800 lines of Python across the prompt assembly path.


## 2. Prompt Assembly Pipeline

### SillyTavern

The pipeline is a multi-phase orchestration with several handoff points:

1. `Generate()` in `script.js` collects character data, runs macro substitution, and calls `prepareOpenAIMessages()`.
2. `preparePromptsForChatCompletion()` merges system prompts (world info, character fields, extensions) with the user-configured prompt ordering from `PromptManager`.
3. `populateChatCompletion()` fills a `ChatCompletion` object within a token budget using a reserve/free pattern:
   - Adds mandatory prompts (character definition, world info) first.
   - Reserves budget for control prompts (impersonation, quiet prompts).
   - Fills chat history newest-first until budget is exhausted.
   - Fills example dialogues if budget remains.
   - Inserts absolute-position (depth) injections into the chat history.
4. `squashSystemMessages()` optionally merges consecutive system messages.
5. The flat message array is sent to the server for provider-specific conversion.

The pipeline supports a `CHAT_COMPLETION_PROMPT_READY` event hook, allowing extensions to modify the assembled prompt before it is sent.

### The Bannered Mare

The pipeline is a single-method orchestration in `PromptBuilder.build_api_messages()`:

1. Resolve the `PromptTemplate` (from the chat or the system default).
2. Build a `TemplateContext` from the character, persona, and chat data.
3. Group activated lore entries by `InsertionPosition`.
4. Resolve the system prompt (character override takes precedence over template).
5. Build a components dictionary keyed by slot name (11 named slots).
6. Iterate the template's `component_order` list, appending enabled components to the output. After specific components, inject any attached **prompt fragments** at the mapped position (`system_prompt` -> `after_system`, `example_dialogues` -> `pre_history`, `chat_history` -> `post_history`).
7. Return the flat `[{role, content}]` array.

There is no event system or extension hook mechanism.

### Comparison

| Aspect | SillyTavern | The Bannered Mare |
|---|---|---|
| Execution context | Client-side (browser JS) | Server-side (Python) |
| Assembly steps | 5+ phases with reserve/free budgeting | Single-pass iterate-and-append |
| Extension hooks | Event-driven (`CHAT_COMPLETION_PROMPT_READY`) | None |
| Continue/impersonate modes | Dedicated handling with budget reservations | Not implemented |
| Group chat support | Group nudge, multi-character handling | Not implemented |


## 3. Component Ordering

### SillyTavern

The default component order has 12 slots, managed as an array of `{identifier, enabled}` entries per character:

```
1. main (system prompt)
2. worldInfoBefore
3. personaDescription
4. charDescription
5. charPersonality
6. scenario
7. enhanceDefinitions (disabled by default)
8. nsfw
9. worldInfoAfter
10. dialogueExamples (marker)
11. chatHistory (marker)
12. jailbreak
```

Users can fully reorder via drag-and-drop UI. Per-character overrides are stored alongside a global fallback (dummy character ID `100001`). The order is a UI-editable array stored in `serviceSettings.prompt_order`.

### The Bannered Mare

The default component order has 11 slots, stored as a JSON column on the `PromptTemplate` model:

```python
DEFAULT_COMPONENT_ORDER = [
    "system_prompt",
    "world_lore_before_character",
    "character_context",
    "world_lore_after_character",
    "scenario",
    "persona",
    "world_lore_before_examples",
    "example_dialogues",
    "rag_context",
    "chat_history",
    "post_history_instructions",
]
```

The `rag_context` slot injects retrieved context from a RAG pipeline (if available) between example dialogues and chat history, giving the model relevant reference material immediately before the conversation.

The earlier `nsfw_prompt` and `jailbreak_prompt` component slots were removed. Their function is now handled by the **Prompt Fragment** system (see Section 9). During component iteration, fragments are injected at 3 positions mapped to specific components:

| After component | Injection position | Typical use |
|---|---|---|
| `system_prompt` | `after_system` | NSFW rules, writing style instructions |
| `example_dialogues` | `pre_history` | Context-setting fragments before conversation |
| `chat_history` | `post_history` | Jailbreak instructions, final reminders |

Each component also has a boolean toggle in `DEFAULT_COMPONENTS_ENABLED`. Templates are reorderable via API (PUT with a new `component_order` list), but there is no drag-and-drop UI layer yet.

### Comparison

| Aspect | SillyTavern | The Bannered Mare |
|---|---|---|
| Number of default slots | 12 (incl. hardcoded nsfw + jailbreak) | 11 fixed slots (incl. RAG context) + fragments at 3 injection points |
| Instruction slot approach | Dedicated named slots (`nsfw`, `jailbreak`) | User-defined fragments attached to any template |
| Storage | Per-character JS array in settings | Per-template JSON column in PostgreSQL |
| Reordering mechanism | Drag-and-drop UI | API endpoint (PUT with new list) |
| Per-character overrides | Yes (per-character prompt_order) | No (template is per-chat, not per-character) |
| Enable/disable toggle | Per-entry `enabled` flag | Per-component `components_enabled` dict |
| Default NSFW state | Enabled (dedicated slot) | No default (user attaches a fragment as needed) |
| Default character_context | Enabled | Disabled |
| Lore insertion points | 2 (before/after character) | 3 (before character, after character, before examples) |
| Fragment reusability | N/A (presets are monolithic) | Same fragment attachable to multiple templates |


## 4. Template Engine

### SillyTavern

Two template engines coexist:

**Legacy engine (default):** Regex-based `evaluateMacros()` in `macros.js`. Processes macros in three phases (pre-environment, environment variables, post-environment). Uses `{{macro}}` double-brace syntax. No control flow -- purely substitution.

**Experimental engine:** Full lexer/parser behind `power_user.experimental_macro_engine` flag. Structured into categories (core, env, state, chat, time, variable, instruct). Still uses `{{macro}}` syntax but supports richer evaluation.

**Handlebars for story strings:** The text-completion context template uses Handlebars (`{{#if field}}...{{/if}}`) for conditional assembly. Compiled via `Handlebars.compile()` with `noEscape: true`.

### The Bannered Mare

Single engine: **Jinja2** via `TemplateService` (`core/utils/template.py`). The environment is configured with:
- `autoescape=False` (no HTML escaping)
- `trim_blocks=True`, `lstrip_blocks=True` (clean whitespace handling)

Templates are rendered from string (`env.from_string()`), not from filesystem. The service also provides `validate_template()` for syntax checking before persistence.

### Comparison

| Aspect | SillyTavern | The Bannered Mare |
|---|---|---|
| Engine count | 2 (legacy regex + experimental parser) + Handlebars | 1 (Jinja2) |
| Syntax | `{{macro}}` (custom), `{{#if}}` (Handlebars) | `{{ variable }}`, `{% if %}` (Jinja2 standard) |
| Control flow | Handlebars `{{#if}}` only (story strings) | Full Jinja2 (`if`, `for`, `macro`, filters) |
| Template source | Inline strings in settings | Database column (Jinja2 string) |
| Validation | None (fails silently or at render time) | `validate_template()` before save |
| Escaping | Disabled | Disabled |


## 5. Macro / Variable System

### SillyTavern

60+ built-in macros across multiple categories:

**Character/Names:** `{{user}}`, `{{char}}`, `{{group}}`, `{{charIfNotGroup}}`, `{{notChar}}`
**Character Data:** `{{description}}`, `{{personality}}`, `{{scenario}}`, `{{persona}}`, `{{mesExamples}}`
**Chat State:** `{{lastMessage}}`, `{{lastUserMessage}}`, `{{lastCharMessage}}`, `{{lastMessageId}}`, `{{firstIncludedMessageId}}`
**Date/Time:** `{{time}}`, `{{date}}`, `{{weekday}}`, `{{isotime}}`, `{{isodate}}`, `{{idle_duration}}`, `{{time_UTC+N}}`
**Utilities:** `{{random::a::b::c}}`, `{{pick::a::b}}`, `{{roll:NdM}}`, `{{reverse:text}}`, `{{banned "word"}}`
**Instruct:** `{{instructInput}}`, `{{instructOutput}}`, `{{systemPrompt}}`, `{{chatStart}}`
**STscript:** `{{getvar::name}}`, `{{setvar::name::value}}`, `{{getglobalvar::name}}`
**Metadata:** `{{model}}`, `{{maxPrompt}}`, `{{maxContext}}`, `{{maxResponse}}`
**Special:** `{{original}}` (resolves to original prompt content when overridden), `{{outlet::key}}` (World Info custom outlets)

Macros are evaluated at assembly time in `preparePrompt()` via `substituteParams()`. The evaluation order matters -- phase 1 macros (instruct sequences) run before phase 2 (environment variables) and phase 3 (chat state, date/time).

### The Bannered Mare

10 built-in variables exposed via `TemplateService._build_variables()`:

**Character:** `{{char}}`, `{{description}}`, `{{personality}}`, `{{scenario}}`
**Persona:** `{{user}}`, `{{persona}}`
**Temporal:** `{{time}}` (HH:MM), `{{date}}` (YYYY-MM-DD)
**Chat:** `{{chat_title}}`

All variables are evaluated in a single pass by Jinja2's native rendering. There are no phased evaluation or ordering dependencies.

### Comparison

| Aspect | SillyTavern | The Bannered Mare |
|---|---|---|
| Variable count | 60+ | 10 |
| Chat state access | Yes (`lastMessage`, IDs, swipe tracking) | No |
| Date/time formatting | Full (moment.js, custom format, UTC offsets) | Basic (HH:MM, YYYY-MM-DD) |
| Randomness | `{{random}}`, `{{pick}}`, `{{roll}}` | None (achievable via Jinja2 extensions) |
| Instruct macros | Yes (full set) | No (no instruct mode) |
| Script variables | Yes (`getvar`/`setvar`) | No |
| Override tracking | `{{original}}` macro | Not applicable |
| Extensibility | Register new macros via `MacroRegistry` | Extend `_build_variables()` or add Jinja2 globals |


## 6. Token Budgeting

### SillyTavern

A dedicated `TokenHandler` + `ChatCompletion` budget system:

1. **Budget calculation:** `max_context - max_response_tokens`
2. **Mandatory prompt allocation:** System prompts, character data, and world info are added first. If they exceed the budget, a `TokenBudgetExceededError` is thrown.
3. **Reserve/free pattern:** Budget is reserved for control prompts (impersonation, quiet prompts) and chat-history bookends (new chat marker, group nudge) before chat history insertion. After history is filled, the reservation is freed and the reserved prompts are inserted at their final positions.
4. **Greedy history fill:** Messages are inserted newest-first until the budget runs out.
5. **Example dialogue fill:** Entire example blocks are added only if the full block fits.
6. **Token counting:** Asynchronous, server-side tokenizer endpoint. Per-message token counts are computed on `Message` creation. Images add 85+ tokens; video uses 263 tokens/second.
7. **Category tracking:** Counts tracked per category (prompt, bias, nudge, jailbreak, examples, conversation).

### The Bannered Mare

A simpler budget system in `PromptBuilder._build_chat_history()`:

1. **Budget source:** `template.max_history_tokens` (default: 4096).
2. **History-only budgeting:** Only chat history messages are subject to the token budget. System prompts, character data, lore entries, and other components are added without budget checks.
3. **Greedy history fill:** Messages are iterated in reverse chronological order. Each message's `token_count` is read from the database (or computed via `TokenizerService`). A 3-token overhead per message is added.
4. **No reservation pattern:** There is no reserve/free mechanism. Components outside chat history are not budget-constrained.
5. **No example dialogue budgeting:** Example dialogues are included unconditionally (not budget-gated).

### Comparison

| Aspect | SillyTavern | The Bannered Mare |
|---|---|---|
| Budget scope | Entire prompt (all components) | Chat history only |
| Budget source | `max_context - max_response_tokens` | `template.max_history_tokens` (default 4096) |
| Mandatory prompt protection | Yes (throws if they exceed budget) | No (always included) |
| Reserve/free pattern | Yes (for control prompts, bookends) | No |
| History insertion order | Newest-first (greedy) | Newest-first (greedy) |
| Example dialogue budgeting | Yes (full-block-or-nothing) | No (always included) |
| Per-message overhead | Model-specific tokenizer | Fixed 3-token overhead |
| Category tracking | Yes (7 categories) | No |
| Image/video token estimation | Yes | No |


## 7. Lore / World Info Injection

### SillyTavern

World Info entries are processed by the World Info extension and injected at two primary positions:

- **`worldInfoBefore`**: Entries placed before the character definition block.
- **`worldInfoAfter`**: Entries placed after the character definition block.

Additionally, entries can use **absolute (depth) injection** to place content at a specific depth within the chat history. Depth injection uses `injection_position: ABSOLUTE`, `injection_depth` (number of messages from the end), and `injection_order` (priority). Multiple entries at the same depth are grouped by role and priority.

World Info activation is handled by a separate keyword-scanning system (not covered in the prompting analysis, but the injection points are wired through the `PromptManager` and `populationInjectionPrompts()`).

### The Bannered Mare

Lore activation is handled by a dedicated `activation_engine.py`:

1. **Keyword scanning:** `activate_entries()` iterates all enabled `LoreEntry` records. Entries marked `constant` bypass keyword matching. Otherwise, primary keys are matched via substring or regex, then secondary keys are filtered via configurable logic (`AND_ANY`, `AND_ALL`, `NOT_ANY`, `NOT_ALL`).
2. **Token budget enforcement:** Activated entries are sorted by priority (descending) and accumulated until the token budget is exhausted.
3. **Insertion positions:** Four positions defined in the `InsertionPosition` enum:
   - `BEFORE_CHARACTER` -- Before character description
   - `AFTER_CHARACTER` -- After character description
   - `AT_DEPTH` -- Injected into chat history at a specific message depth
   - `BEFORE_EXAMPLES` -- Before example dialogues

The `PromptBuilder` groups activated entries by position and routes them to the correct component slot. `AT_DEPTH` entries are injected during `_build_chat_history()`, sorted by depth in descending order and inserted at `len(history) - entry.depth`.

### Comparison

| Aspect | SillyTavern | The Bannered Mare |
|---|---|---|
| Activation engine | External (World Info extension) | Built-in (`activation_engine.py`) |
| Keyword matching | Separate system (not in prompt pipeline) | Primary + secondary keys with configurable logic |
| Secondary key logic | Not documented in prompt analysis | `AND_ANY`, `AND_ALL`, `NOT_ANY`, `NOT_ALL` |
| Constant entries | Yes | Yes (`constant` flag bypasses keywords) |
| Insertion positions | 2 relative + absolute depth | 3 relative + absolute depth |
| Depth injection | Priority-ordered, role-grouped | Priority-sorted, sequential insertion |
| Token budget for lore | Part of overall prompt budget | Separate lore-specific budget parameter |
| Per-entry role | Configurable (system/user/assistant) | Configurable (system/user/assistant) |
| Regex support | Via World Info system | Per-entry `use_regex` flag |
| Case sensitivity | Via World Info system | Per-entry `case_sensitive` flag |
| Whole-word matching | Via World Info system | Per-entry `match_whole_words` flag |


## 8. Instruct Mode

### SillyTavern

Instruct mode wraps messages with model-specific prefix/suffix sequences for text completion APIs. Each instruct preset defines 15+ properties including:

- Per-role sequences: `input_sequence`/`suffix`, `output_sequence`/`suffix`, `system_sequence`/`suffix`
- Position overrides: `first_output_sequence`, `last_output_sequence`, `first_input_sequence`, `last_input_sequence`
- Behavior flags: `wrap`, `macro`, `names_behavior`, `skip_examples`, `system_same_as_user`
- Auto-detection: `activation_regex`, `bind_to_context` for model-based auto-selection
- Chat template hash matching for known models (Llama 3, Mistral V2/V3, Gemma 2, etc.)

Instruct mode also exposes macros (`{{instructInput}}`, `{{instructOutput}}`, etc.) that can be used inside other templates.

### The Bannered Mare

There is no instruct mode implementation. All provider communication uses the Chat Completions API format (structured `{role, content}` messages). The `ProviderAdapter` hierarchy handles the structural transformation:

- `AnthropicAdapter`: Extracts system messages into the `system` parameter, sends chat messages in Anthropic's Messages API format.
- `GeminiAdapter`: Extracts system messages into `systemInstruction`, maps roles (`assistant` -> `model`), uses `parts` format.
- `OpenAIAdapter`: Passes messages through as-is (native format).
- `OllamaAdapter`: Extends `OpenAIAdapter` with local-server defaults.

Text completion API support (raw prompt string) is not implemented.

### Comparison

| Aspect | SillyTavern | The Bannered Mare |
|---|---|---|
| Instruct mode | Full implementation (15+ config properties) | Not implemented |
| Text completion API | Supported (via instruct wrapping + `convertTextCompletionPrompt`) | Not supported |
| Chat completion API | Supported | Supported (primary and only mode) |
| Template auto-detection | Yes (regex, hash matching) | Not applicable |
| Per-role sequence customization | Yes (input/output/system, with first/last overrides) | Not applicable |


## 9. Instruction Slots and Prompt Fragments

### SillyTavern

Three user-editable Jinja2/Handlebars template slots stored in presets:

1. **Main prompt** (`main`): The primary system instruction. Default: `"Write {{char}}'s next reply in a fictional chat between {{charIfNotGroup}} and {{user}}."`
2. **NSFW prompt** (`nsfw`): Auxiliary instruction for NSFW content. Default: empty.
3. **Jailbreak / Post-History Instructions** (`jailbreak`): Instruction placed after chat history. Default: empty.

Additionally, the **story string** is a Handlebars template that controls how character data is assembled for text completion contexts.

Character cards can override `main` and `jailbreak` via their `system_prompt` and `post_history_instructions` fields. The override is blocked if the preset prompt has `forbid_overrides` set. The `{{original}}` macro inside an override resolves to the preset's original content.

These slots are fixed -- adding a new instruction category (e.g., a writing-style directive) requires repurposing one of the existing three slots or using an extension's injection point.

### The Bannered Mare

One fixed template slot plus a composable **Prompt Fragment Library**:

1. **`system_template`** (required): The primary system prompt template. Rendered via Jinja2 with the full `TemplateContext`.

The earlier `nsfw_template` and `jailbreak_template` columns on `PromptTemplate` have been removed. Their function -- and any number of additional instruction categories -- is now served by **prompt fragments**.

**Prompt Fragment system** (`src/prompt_fragment/`):

A `PromptFragment` is a standalone, reusable instruction block stored in the database. Each fragment has:
- **`name`** -- display label (e.g., "NSFW Explicit", "Jailbreak v2", "Victorian Writing Style")
- **`fragment_type`** -- category tag: `system`, `nsfw`, `jailbreak`, `instruction`, or `context`
- **`content`** -- Jinja2 template text, rendered with the same `TemplateContext` as the system prompt
- **`is_global`** -- if true, the fragment is available to all templates

Fragments are attached to templates via the `TemplateFragment` join table, which stores:
- **`position`** -- injection point: `after_system`, `pre_history`, or `post_history`
- **`ordinal`** -- ordering within a position (0-based, ascending)

During prompt assembly, `PromptBuilder` injects fragments after specific components by mapping component names to positions:

```python
_FRAGMENT_POSITIONS = {
    "system_prompt": "after_system",
    "example_dialogues": "pre_history",
    "chat_history": "post_history",
}
```

For each component in the template's `component_order`, after appending the component's messages, the builder checks if that component has a mapped fragment position and injects all attached fragments at that position (ordered by `ordinal`). Each fragment is rendered through Jinja2 and emitted as a `{"role": "system", "content": ...}` message.

The same fragment can be attached to multiple templates, and multiple fragments can occupy the same position on a single template. The `FragmentService` provides CRUD operations, attach/detach, and bulk reordering of a template's fragments.

Character-level override: If `character.system_prompt` is set, it replaces the template's `system_template` for that character (rendered through the same Jinja2 engine). There is no `forbid_overrides` mechanism and no `{{original}}` equivalent.

The `post_history_instructions` field on the Character model provides an additional injection point after chat history, independent of any attached fragments.

### Comparison

| Aspect | SillyTavern | The Bannered Mare |
|---|---|---|
| Instruction architecture | 3 hardcoded slots (main, nsfw, jailbreak) | 1 fixed slot (system) + N user-defined fragments |
| Adding new instruction categories | Requires repurposing an existing slot or extension | Create a new fragment and attach it |
| Fragment reuse across templates | N/A (each preset has its own slot text) | Same fragment attachable to multiple templates |
| Injection positions | Fixed: nsfw in prompt area, jailbreak after history | 3 positions (`after_system`, `pre_history`, `post_history`) per fragment |
| Ordering within position | N/A (one item per slot) | `ordinal` field on `TemplateFragment` join table |
| Template language | Custom macros + Handlebars | Jinja2 |
| Character override | `system_prompt` and `post_history_instructions` fields | `system_prompt` field + `post_history_instructions` as separate component |
| Override protection | `forbid_overrides` flag | Not implemented |
| Original content access | `{{original}}` macro | Not implemented |
| Story string (text completion) | Handlebars template | Not applicable (no text completion support) |
| Fragment types / categorization | N/A | 5 types: `system`, `nsfw`, `jailbreak`, `instruction`, `context` |


## 10. Provider-Specific Formatting

### SillyTavern

All prompts are assembled into OpenAI ChatML format client-side, then converted server-side by dedicated functions in `prompt-converters.js`:

- **Anthropic:** Extracts system messages into `systemPrompt`, enforces strict role alternation by merging consecutive same-role messages, moves images from assistant to user, applies prompt caching at depth.
- **Gemini:** Extracts system messages into `system_instruction.parts`, maps roles, converts to `parts` format, handles thought signatures.
- **Cohere:** Prepends character names to content, returns `{chatHistory}` format.
- **Mistral:** Sanitizes tool call IDs, fixes message ordering, supports prefill via `prefix` flag.
- **xAI:** Prepends character names, handles group name prefixing.
- **Generic merge modes:** `merge`, `semi`, `strict`, `single` for OpenAI-compatible and custom endpoints with varying levels of role enforcement and message merging.

Post-processing also includes `squashSystemMessages()` which merges consecutive system messages into one.

### The Bannered Mare

The `ProviderAdapter` hierarchy handles format transformation within `build_payload()`:

- **`AnthropicAdapter`:** Extracts all system messages and joins them with `\n\n` into a single `system` parameter with prompt caching. Non-system messages are passed as `{role, content}` dicts. Does not enforce role alternation (relies on the prompt builder producing valid sequences).
- **`GeminiAdapter`:** Extracts system messages into `systemInstruction.parts`. Maps `assistant` -> `model`. Converts messages to `{role, parts: [{text}]}` format.
- **`OpenAIAdapter`:** Passes messages through with no transformation. Serves as the base for xAI, OpenRouter, and custom providers.
- **`OllamaAdapter`:** Extends `OpenAIAdapter` with a different URL path and longer timeout.

There is no message merging, role alternation enforcement, name prefixing, or post-processing mode system.

### Comparison

| Aspect | SillyTavern | The Bannered Mare |
|---|---|---|
| Conversion architecture | Centralized converter functions | Per-provider adapter classes |
| Dedicated provider converters | 6 (Anthropic, Gemini, Cohere, Mistral, xAI, Generic) | 4 (Anthropic, Gemini, OpenAI, Ollama) |
| Role alternation enforcement | Yes (Anthropic, Gemini) | No |
| Message merging | Yes (consecutive same-role) | No |
| System message squashing | Optional (`squashSystemMessages`) | No (Anthropic adapter joins system parts) |
| Name prefixing | Yes (Cohere, xAI, generic merge) | No |
| Post-processing modes | 5 modes (none, merge, semi, strict, single) | None |
| Tool call handling | Yes (Anthropic, Mistral) | Not implemented |
| Image handling | Yes (format conversion per provider) | Not implemented |
| Prompt caching | Yes (Anthropic depth-based) | Yes (Anthropic ephemeral cache_control) |


## 11. Summary of Maturity Gaps

The following table summarizes features present in SillyTavern that are not yet implemented in The Bannered Mare, and vice versa.

### Features in SillyTavern not in The Bannered Mare

| Feature | Impact |
|---|---|
| Full-prompt token budgeting | Risk of exceeding context window if system prompts + lore + history are large |
| Reserve/free budget pattern | No guaranteed placement of control prompts |
| Instruct mode / text completion | Cannot use text completion APIs or local models that require prompt templates |
| Group chat support | Single-character sessions only |
| Continue/impersonate modes | No mid-generation continuation or user-voice generation |
| Message squashing | More API messages than necessary for some providers |
| Role alternation enforcement | May produce invalid message sequences for Anthropic/Gemini |
| Extension event hooks | No third-party extension point for prompt modification |
| 60+ macros | Limited template expressiveness (10 variables) |
| `forbid_overrides` / `{{original}}` | No fine-grained override control |
| Image/video token estimation | No multimodal token awareness |
| Chat template auto-detection | No automatic instruct preset selection |

### Features in The Bannered Mare not in SillyTavern

| Feature | Impact |
|---|---|
| Server-side prompt assembly | Prompt logic not exposed to client tampering |
| Jinja2 with full control flow | Templates can use conditionals, loops, filters, macros natively |
| Template syntax validation | Malformed templates are rejected before persistence |
| Composable prompt fragment library | Users define reusable instruction blocks (NSFW, jailbreak, style, etc.) and attach them to any template at 3 injection points, replacing hardcoded instruction slots |
| Fragment reuse across templates | A single fragment can be shared by multiple templates; updates propagate everywhere |
| `BEFORE_EXAMPLES` lore position | Additional insertion point for lore entries |
| Secondary keyword logic (4 modes) | More flexible lore activation than ST's World Info (as seen from the prompting pipeline) |
| Separate lore token budget | Lore budget is independent from overall prompt budget |
| Database-persisted templates | Templates survive across sessions without import/export |
| Typed adapter hierarchy | Provider adapters are statically typed and unit-testable |
