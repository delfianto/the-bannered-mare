# SillyTavern v1.17.0 — Prompting System Analysis

## Executive Summary

SillyTavern's prompting system is a client-side prompt assembly pipeline that constructs chat completion API messages from character data, user prompts, and various injection points. The prompt is assembled in the browser via JavaScript classes (`ChatCompletion`, `Message`, `MessageCollection`, `PromptManager`), macro-expanded with a rich template engine, and then converted server-side to provider-specific formats before being sent to the API.

The assembly runs almost entirely in the browser; only the final format translation happens on
the server:

<Figure tag="Figure 1" title="The prompt assembly pipeline" id="fig-prompt-assembly">
<svg viewBox="0 0 640 522" role="img" aria-label="SillyTavern prompt assembly pipeline" style="font-family:var(--vp-font-family-base)">
  <defs>
    <marker id="tbm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-arrow)"/>
    </marker>
  </defs>
  <g font-size="12">
    <rect x="40" y="16" width="560" height="54" rx="10" fill="var(--tbm-dgm-frontend-soft)" stroke="var(--tbm-dgm-frontend)"/>
    <circle cx="68" cy="43" r="13" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-frontend)"/><text x="68" y="47" text-anchor="middle" font-size="11" font-weight="700" fill="var(--tbm-dgm-frontend)">1</text>
    <text x="92" y="40" font-weight="700" fill="var(--tbm-dgm-ink)">Generate()</text>
    <text x="92" y="58" font-size="10.5" fill="var(--tbm-dgm-ink-2)">assembly entry point · script.js</text>
    <rect x="40" y="86" width="560" height="54" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <circle cx="68" cy="113" r="13" fill="var(--tbm-dgm-frontend-soft)" stroke="var(--tbm-dgm-frontend)"/><text x="68" y="117" text-anchor="middle" font-size="11" font-weight="700" fill="var(--tbm-dgm-frontend)">2</text>
    <text x="92" y="110" font-weight="700" fill="var(--tbm-dgm-ink)">prepareOpenAIMessages()</text>
    <text x="92" y="128" font-size="10.5" fill="var(--tbm-dgm-ink-2)">new ChatCompletion · budget = context_max − response_max</text>
    <rect x="40" y="156" width="560" height="54" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <circle cx="68" cy="183" r="13" fill="var(--tbm-dgm-frontend-soft)" stroke="var(--tbm-dgm-frontend)"/><text x="68" y="187" text-anchor="middle" font-size="11" font-weight="700" fill="var(--tbm-dgm-frontend)">3</text>
    <text x="92" y="180" font-weight="700" fill="var(--tbm-dgm-ink)">preparePromptsForChatCompletion()</text>
    <text x="92" y="198" font-size="10.5" fill="var(--tbm-dgm-ink-2)">merge system prompts with the PromptManager order</text>
    <rect x="40" y="226" width="560" height="54" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <circle cx="68" cy="253" r="13" fill="var(--tbm-dgm-frontend-soft)" stroke="var(--tbm-dgm-frontend)"/><text x="68" y="257" text-anchor="middle" font-size="11" font-weight="700" fill="var(--tbm-dgm-frontend)">4</text>
    <text x="92" y="250" font-weight="700" fill="var(--tbm-dgm-ink)">populateChatCompletion()</text>
    <text x="92" y="268" font-size="10.5" fill="var(--tbm-dgm-ink-2)">fill messages until the token budget is spent</text>
    <rect x="40" y="296" width="560" height="54" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <circle cx="68" cy="323" r="13" fill="var(--tbm-dgm-frontend-soft)" stroke="var(--tbm-dgm-frontend)"/><text x="68" y="327" text-anchor="middle" font-size="11" font-weight="700" fill="var(--tbm-dgm-frontend)">5</text>
    <text x="92" y="320" font-weight="700" fill="var(--tbm-dgm-ink)">squash system messages</text>
    <text x="92" y="338" font-size="10.5" fill="var(--tbm-dgm-ink-2)">emit CHAT_COMPLETION_PROMPT_READY</text>
    <rect x="40" y="366" width="560" height="54" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <circle cx="68" cy="393" r="13" fill="var(--tbm-dgm-frontend-soft)" stroke="var(--tbm-dgm-frontend)"/><text x="68" y="397" text-anchor="middle" font-size="11" font-weight="700" fill="var(--tbm-dgm-frontend)">6</text>
    <text x="92" y="390" font-weight="700" fill="var(--tbm-dgm-ink)">getChat()</text>
    <text x="92" y="408" font-size="10.5" fill="var(--tbm-dgm-ink-2)">→ flat message array</text>
    <rect x="40" y="450" width="560" height="56" rx="10" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/>
    <circle cx="68" cy="478" r="13" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-backend)"/><text x="68" y="482" text-anchor="middle" font-size="11" font-weight="700" fill="var(--tbm-dgm-backend)">7</text>
    <text x="92" y="474" font-weight="700" fill="var(--tbm-dgm-ink)">server · prompt-converters.js</text>
    <text x="92" y="492" font-size="10.5" fill="var(--tbm-dgm-ink-2)">translate flat array → provider-specific format → API</text>
  </g>
  <g stroke="var(--tbm-dgm-arrow)" stroke-width="1.5" fill="none" marker-end="url(#tbm-ah)">
    <path d="M320 70 L320 84"/>
    <path d="M320 140 L320 154"/>
    <path d="M320 210 L320 224"/>
    <path d="M320 280 L320 294"/>
    <path d="M320 350 L320 364"/>
    <path d="M320 420 L320 448"/>
  </g>
  <line x1="40" y1="435" x2="600" y2="435" stroke="var(--tbm-dgm-border)" stroke-dasharray="4 4"/>
  <text x="596" y="431" text-anchor="end" font-size="9.5" fill="var(--tbm-dgm-faint)">browser ↑   server ↓</text>
</svg>
<template #caption>

**Assembled in the browser, translated on the server.** Steps 1–6 build a single flat message
array within a token budget entirely client-side; only step 7 (`prompt-converters.js`) reshapes
that array into each provider's wire format. The `PromptManager` order in step 3 is what lets
users reorder and toggle prompt sections per character.

</template>
</Figure>

Key files:
- `public/scripts/openai.js` (6996 lines) -- Core prompt assembly pipeline and ChatCompletion class
- `public/scripts/PromptManager.js` (2144 lines) -- Prompt ordering, UI, and per-character configuration
- `public/scripts/macros.js` (746 lines) -- Legacy macro/template engine
- `public/scripts/macros/` -- New experimental macro engine (lexer, parser, registry)
- `public/scripts/instruct-mode.js` (870 lines) -- Instruct mode wrapping
- `public/scripts/power-user.js` -- Context templates and story string rendering
- `src/prompt-converters.js` (1445 lines) -- Server-side provider-specific format conversion


## 1. Prompt Assembly Pipeline

### 1.1 Entry Point: `Generate()` in `script.js`

The entire flow starts in `Generate()` (line 4207 of `public/script.js`). For the Chat Completion API (`main_api === 'openai'`), it calls:

```js
let [prompt, counts] = await prepareOpenAIMessages({
    name2, charDescription, charPersonality, scenario,
    worldInfoBefore, worldInfoAfter, extensionPrompts,
    bias, type, quietPrompt, quietImage, cyclePrompt,
    systemPromptOverride, jailbreakPromptOverride,
    messages: oaiMessages, messageExamples: oaiMessageExamples,
}, dryRun);
```

At this point, the character data has already been extracted and macro-substituted by the caller. `oaiMessages` is the chat history, preprocessed by `setOpenAIMessages()`.

### 1.2 Core Assembly: `prepareOpenAIMessages()` (line 1513)

This is the primary orchestrator. It performs the following steps:

1. Creates a `ChatCompletion` instance
2. Sets the token budget: `context_max - response_max`
3. Calls `preparePromptsForChatCompletion()` to merge system prompts with user-configured prompt ordering
4. Calls `populateChatCompletion()` to fill the ChatCompletion with messages within the token budget
5. Optionally squashes consecutive system messages (`squashSystemMessages`)
6. Emits the `CHAT_COMPLETION_PROMPT_READY` event
7. Returns the flat message array via `chatCompletion.getChat()`

### 1.3 Prompt Preparation: `preparePromptsForChatCompletion()` (line 1338)

This function creates the "system prompts" array -- prompt objects with identifiers that will be merged into the user-configured prompt order. These include:

| Identifier | Source | Role |
|---|---|---|
| `worldInfoBefore` | World Info entries (before character) | system |
| `worldInfoAfter` | World Info entries (after character) | system |
| `charDescription` | Character card description field | system |
| `charPersonality` | Character card personality field | system |
| `scenario` | Character card scenario field | system |
| `impersonate` | Impersonation instruction prompt | system |
| `quietPrompt` | Background/quiet generation instruction | system |
| `groupNudge` | Group chat nudge (forces specific character) | system |
| `bias` | Logit bias text | assistant |
| `summary` | Extension: memory/summary (key `1_memory`) | configurable |
| `authorsNote` | Extension: Author's Note (key `2_floating_prompt`) | configurable |
| `vectorsMemory` | Extension: vector DB memory (key `3_vectors`) | system |
| `vectorsDataBank` | Extension: data bank vectors (key `4_vectors_data_bank`) | configurable |
| `smartContext` | Extension: ChromaDB context (key `chromadb`) | system |
| `personaDescription` | User persona description | system |

These are then merged with the `PromptManager`'s ordered prompt collection. The merge logic (line 1444-1464):

```js
systemPrompts.forEach(prompt => {
    const collectionPrompt = prompts.get(prompt.identifier);
    if (collectionPrompt) {
        prompt.injection_position = collectionPrompt.injection_position ?? prompt.injection_position;
        prompt.injection_depth = collectionPrompt.injection_depth ?? prompt.injection_depth;
        prompt.injection_order = collectionPrompt.injection_order ?? prompt.injection_order;
        prompt.role = collectionPrompt.role ?? prompt.role;
    }
    const newPrompt = promptManager.preparePrompt(prompt);
    const markerIndex = prompts.index(prompt.identifier);
    if (-1 !== markerIndex) prompts.collection[markerIndex] = newPrompt;
    else prompts.add(newPrompt);
});
```

Character-specific overrides for the main prompt and jailbreak are applied at lines 1467-1484 if the character card provides `system_prompt` or `post_history_instructions` fields and the prompt does not have `forbid_overrides` set.

### 1.4 Population: `populateChatCompletion()` (line 1156)

This is the function that actually fills the `ChatCompletion` object with messages, respecting the token budget. The order of operations:

1. **Reserve 3 tokens** for the assistant priming (`<|start|>assistant<|message|>`)
2. **Add character-definition prompts** in configured order:
   - `worldInfoBefore`, `main`, `worldInfoAfter`, `charDescription`, `charPersonality`, `scenario`, `personaDescription`
3. **Reserve budget for control prompts** (impersonate, quiet prompt) -- these are always placed last
4. **Add system prompts** (`nsfw`, `jailbreak`) and user-relative prompts
5. **Add `enhanceDefinitions`** prompt (if present)
6. **Add `bias`** prompt (if present)
7. **Inject extension prompts** (`summary`, `authorsNote`, `vectorsMemory`, etc.) relative to the `main` prompt
8. **Reserve budget for tool calls** if tool calling is supported
9. **Handle continue mode** -- displaces the continued message, optionally adds assistant prefill
10. **Populate in-chat injections** via `populationInjectionPrompts()` (absolute-positioned prompts)
11. **Populate chat history** via `populateChatHistory()` -- fills messages newest-first until budget is exhausted
12. **Populate dialogue examples** via `populateDialogueExamples()` -- adds example dialogues if budget allows
13. **Free control prompt reservation** and add control prompts at the end

The `pin_examples` setting controls whether dialogue examples are added before or after chat history. If pinned, examples are always included (budget permitting); otherwise, chat history gets priority.


## 2. Prompt Manager

### 2.1 Architecture

The `PromptManager` class (`PromptManager.js`, line 300) manages:
- A list of **prompts** (stored in `serviceSettings.prompts`)
- Per-character **prompt ordering** (stored in `serviceSettings.prompt_order`)
- Token counting via the shared `TokenHandler`
- UI rendering for prompt list management

### 2.2 Prompt Ordering System

Each prompt has an `identifier` and an `enabled` flag. The ordering is maintained as an array of `{identifier, enabled}` entries per character. A "global" strategy uses a dummy character ID (`100001`) for the shared order.

The default prompt order (line 2087-2136):

```
1. main              (enabled)
2. worldInfoBefore    (enabled)
3. personaDescription (enabled)
4. charDescription    (enabled)
5. charPersonality    (enabled)
6. scenario           (enabled)
7. enhanceDefinitions (disabled by default)
8. nsfw               (enabled)
9. worldInfoAfter     (enabled)
10. dialogueExamples  (enabled, marker)
11. chatHistory       (enabled, marker)
12. jailbreak         (enabled)
```

Users can reorder prompts via drag-and-drop in the UI. The `getPromptCollection()` method (line 1516) assembles a `PromptCollection` from this order:

```js
getPromptCollection(generationType) {
    const promptCollection = new PromptCollection();
    const promptOrder = this.getPromptOrderForCharacter(this.activeCharacter);
    promptOrder.forEach(entry => {
        const prompt = this.getPromptById(entry.identifier);
        const allowedTrigger = entry.enabled && this.shouldTrigger(prompt, generationType);
        if (allowedTrigger) {
            promptCollection.add(this.preparePrompt(prompt));
        }
    });
    return promptCollection;
}
```

### 2.3 Prompt Properties

Each `Prompt` object (line 80-196) has:
- `identifier` -- Unique string ID
- `role` -- `system`, `user`, or `assistant`
- `content` -- Prompt text (macro-expanded at assembly time)
- `name` -- Display name
- `system_prompt` -- Whether it is a built-in system prompt
- `marker` -- Whether it is a placeholder/marker (no editable content)
- `injection_position` -- `RELATIVE` (0) or `ABSOLUTE` (1)
- `injection_depth` -- Depth in chat for absolute injections (default: 4)
- `injection_order` -- Priority ordering for absolute injections (default: 100)
- `injection_trigger` -- Array of generation types that trigger this prompt (e.g., `["normal"]`)
- `forbid_overrides` -- Prevents character card override

### 2.4 Injection Positions

Two modes of injection:

- **RELATIVE (0)**: The prompt is placed at its position in the prompt ordering list, among other relative prompts. This means it appears in the "system prompt" area.
- **ABSOLUTE (1)**: The prompt is injected into the chat history at a specific depth. Depth 0 means just before the last message, depth 4 means 4 messages from the end. This is used for Author's Note-style injections.


## 3. Macro / Template Engine

### 3.1 Dual Engine Architecture

SillyTavern has two macro engines:

1. **Legacy engine** (default): Regex-based substitution in `evaluateMacros()` (`macros.js`, line 609)
2. **Experimental engine**: A full lexer/parser-based system under `macros/engine/` with `MacroEngine`, `MacroRegistry`, `MacroLexer`, `MacroParser`, and `MacroCstWalker`

The experimental engine is behind a feature flag (`power_user.experimental_macro_engine`). Both are invoked through `substituteParams()` in `script.js` (line 2907).

### 3.2 Macro Evaluation Flow (Legacy)

`evaluateMacros(content, env, postProcessFn)` processes macros in three phases:

**Phase 1 - Pre-environment macros** (`preEnvMacros`):
```
<USER>, <BOT>, <CHAR>              -- Legacy angle-bracket aliases
<CHARIFNOTGROUP>, <GROUP>          -- Legacy group macros
{{roll:NdM}}                       -- Dice rolling via droll library
{{instructInput}}, {{instructOutput}}, etc. -- Instruct template sequences
{{newline}}, {{trim}}, {{noop}}, {{input}} -- Utility macros
```

**Phase 2 - Environment variable macros** (`envMacros`):
Built from the `env` object passed to `evaluateMacros`. Key variables:
```
{{user}}            -- Current persona name (name1)
{{char}}            -- Current character name (name2)
{{group}}           -- Group member names (or char name in solo)
{{charIfNotGroup}}  -- Alias for {{group}}
{{description}}     -- Character description
{{personality}}     -- Character personality
{{scenario}}        -- Character scenario
{{persona}}         -- User persona description
{{charPrompt}}      -- Character's system prompt override
{{charInstruction}} -- Character's jailbreak override (alias: charJailbreak)
{{mesExamples}}     -- Formatted dialogue examples
{{model}}           -- Current model name
{{original}}        -- Original prompt text (for override contexts)
{{notChar}}         -- All participants except current speaker
```

**Phase 3 - Post-environment macros** (`postEnvMacros`):
```
{{maxPrompt}}, {{maxContext}}, {{maxResponse}}   -- Token limits
{{lastMessage}}, {{lastUserMessage}}, {{lastCharMessage}} -- Chat accessors
{{lastMessageId}}, {{firstIncludedMessageId}}    -- Message IDs
{{lastSwipeId}}, {{currentSwipeId}}              -- Swipe tracking
{{time}}, {{date}}, {{weekday}}                  -- Date/time (moment.js)
{{isotime}}, {{isodate}}                         -- ISO format variants
{{datetimeformat <format>}}                      -- Custom moment.js format
{{idle_duration}}                                -- Time since last user message
{{time_UTC+N}}                                   -- UTC offset time
{{random::item1::item2::...}}                    -- Random selection (non-deterministic)
{{pick::item1::item2::...}}                      -- Seeded random selection (deterministic per chat)
{{roll:NdM}}                                     -- Dice roll
{{timeDiff::time1::time2}}                       -- Human-readable time difference
{{banned "word"}}                                -- Add word to ban list
{{reverse:text}}                                 -- Reverse a string
{{//comment}}                                    -- Comment (removed)
{{outlet::key}}                                  -- World Info custom outlet
```

### 3.3 New Macro Engine Categories

The experimental engine organizes macros into categories (registered in `macros/definitions/`):

| File | Category | Examples |
|---|---|---|
| `core-macros.js` | Utilities | `newline`, `trim`, `noop`, `random`, `pick`, `roll`, `banned` |
| `env-macros.js` | Names/Character | `user`, `char`, `group`, `description`, `personality`, `scenario`, `persona`, `model` |
| `state-macros.js` | Runtime state | `lastGenerationType`, `isMobile` |
| `chat-macros.js` | Chat inspection | `lastMessage`, `lastUserMessage`, `lastCharMessage`, message IDs, swipe IDs |
| `time-macros.js` | Date/Time | `time`, `date`, `weekday`, `isotime`, `isodate`, `idle_duration`, `timeDiff` |
| `variable-macros.js` | STscript vars | `getvar`, `setvar`, `getglobalvar`, `setglobalvar` |
| `instruct-macros.js` | Instruct sequences | `instructInput`, `instructOutput`, `systemPrompt`, `chatStart`, etc. |

### 3.4 Handlebars for Story Strings

The story string template (used for text completion APIs and context templates) uses Handlebars for conditional logic:

```handlebars
{{#if system}}{{system}}
{{/if}}{{#if description}}{{description}}
{{/if}}{{#if personality}}{{char}}'s personality: {{personality}}
{{/if}}{{#if scenario}}Scenario: {{scenario}}
{{/if}}{{#if persona}}{{persona}}
{{/if}}
```

This is compiled via `Handlebars.compile(storyString, { noEscape: true })` in `renderStoryString()` (`power-user.js`, line 2254). The compiled template receives a `params` object with character fields, then the output is further processed through `substituteParams()` for macro expansion.


## 4. System Prompt Construction

### 4.1 Default Prompts

The system prompt is assembled from multiple components. The defaults (defined at the top of `openai.js`):

```js
const default_main_prompt = 'Write {{char}}\'s next reply in a fictional chat between {{charIfNotGroup}} and {{user}}.';
const default_nsfw_prompt = '';      // Empty by default
const default_jailbreak_prompt = ''; // Empty by default
const default_impersonation_prompt = '[Write your next reply from the point of view of {{user}}, using the chat history so far as a guideline for the writing style of {{user}}. Don\'t write as {{char}} or system. Don\'t describe actions of {{char}}.]';
const default_new_chat_prompt = '[Start a new Chat]';
const default_new_group_chat_prompt = '[Start a new group chat. Group members: {{group}}]';
const default_new_example_chat_prompt = '[Example Chat]';
const default_continue_nudge_prompt = '[Continue your last message without repeating its original content.]';
const default_group_nudge_prompt = '[Write the next reply only as {{char}}.]';
```

### 4.2 Character Card Override Mechanism

Character cards can override the main prompt and jailbreak via their `system_prompt` and `post_history_instructions` fields. The override logic (line 1467-1484) checks `forbid_overrides` before applying:

```js
if (systemPromptOverride && systemPrompt && systemPrompt.forbid_overrides !== true) {
    systemPrompt.content = systemPromptOverride;
    const mainReplacement = promptManager.preparePrompt(systemPrompt, mainOriginalContent);
    prompts.override(mainReplacement, prompts.index('main'));
}
```

When overridden, the `{{original}}` macro inside the replacement prompt resolves to the original preset's main prompt content.


## 5. Component Ordering

### 5.1 Default Order

The final prompt is assembled in this default order (from top of context to bottom):

```
[worldInfoBefore]        -- World Info entries with "before character" placement
[main]                   -- Main system prompt
   [summary]             -- Injected into main (at position configured by extension)
   [authorsNote]         -- Injected into main (if "In Prompt" position)
   [vectorsMemory]       -- Injected into main
   [vectorsDataBank]     -- Injected into main
   [smartContext]         -- Injected into main
[personaDescription]     -- User's persona description
[charDescription]        -- Character description
[charPersonality]        -- Character personality
[scenario]               -- Character scenario
[enhanceDefinitions]     -- (Disabled by default)
[nsfw]                   -- Auxiliary/NSFW prompt
[worldInfoAfter]         -- World Info entries with "after character" placement
[dialogueExamples]       -- Example dialogue blocks (if pinned)
   [newExampleChat]      -- "[Example Chat]" separator per block
   [example messages]    -- Individual example exchanges
[chatHistory]            -- Chat history messages
   [newMainChat]         -- "[Start a new Chat]" at the top of history
   [chat messages...]    -- Newest-first insertion until budget exhausted
   [depth injections]    -- Absolute-positioned prompts at configured depths
   [groupNudge]          -- Group nudge at end of history (if group chat)
[jailbreak]              -- Post-History Instructions
[controlPrompts]         -- Impersonation and/or quiet prompts (always last)
```

### 5.2 User Customization

Users can fully reorder all prompts via the Prompt Manager UI. They can:
- Drag-and-drop to reorder
- Toggle individual prompts on/off
- Change injection position (Relative vs Absolute/In-Chat)
- Set depth and priority for absolute injections
- Set role (system/user/assistant) for any prompt
- Filter prompts by generation type trigger (e.g., only activate during "normal" or "impersonate")


## 6. Token Budget Management

### 6.1 TokenHandler Class (line 3185)

The `TokenHandler` class tracks token counts by category:

```js
this.counts = {
    'start_chat': 0,
    'prompt': 0,
    'bias': 0,
    'nudge': 0,
    'jailbreak': 0,
    'impersonate': 0,
    'examples': 0,
    'conversation': 0,
};
```

Token counting is asynchronous and uses `countTokensOpenAIAsync()` from `tokenizers.js`, which calls the server-side tokenizer endpoint.

### 6.2 ChatCompletion Budget System (line 3682)

The `ChatCompletion` class manages a token budget with a reserve/free pattern:

```js
setTokenBudget(context, response) {
    this.tokenBudget = context - response;
}
```

**Budget allocation flow:**

1. **Set budget**: `max_context - max_response_tokens`
2. **Reserve 3 tokens**: Assistant message priming overhead
3. **Add mandatory prompts**: Each prompt added decreases the budget by its token count. If a prompt cannot be afforded, `TokenBudgetExceededError` is thrown.
4. **Reserve control prompts**: Budget for impersonation/quiet prompts is reserved before chat history insertion, then freed and added at the end.
5. **Reserve chat-history bookends**: New chat message and group nudge are reserved, filled after history, then freed and inserted.
6. **Fill chat history greedily**: Messages are inserted newest-first until the budget runs out:
   ```js
   if (chatCompletion.canAfford(chatMessage)) {
       chatCompletion.insertAtStart(chatMessage, 'chatHistory');
   } else {
       break;
   }
   ```
7. **Fill dialogue examples**: Entire example blocks (separator + all messages) are added only if the full block fits in the remaining budget.

### 6.3 Token Counting per Message

Each `Message` tracks its own token count (line 3276). Token counts are computed asynchronously on creation:

```js
static async createAsync(role, content, identifier) {
    const message = new Message(role, content, identifier);
    if (typeof message.content === 'string' && message.content.length > 0) {
        message.tokens = await tokenHandler.countAsync({ role: message.role, content: message.content });
    }
    return message;
}
```

Images add token overhead: 85 tokens per image by default, or calculated based on resolution. Videos use Gemini's estimate of 263 tokens/second.


## 7. Instruct Mode

### 7.1 Purpose

Instruct mode wraps messages with model-specific prefix/suffix sequences to match the expected chat template format (e.g., `<|im_start|>system\n...` for ChatML, `[INST]...[/INST]` for Llama, etc.). This is primarily used for text completion APIs but can also be applied to Chat Completion APIs.

### 7.2 Configuration Properties

Defined in `instruct-mode.js` (line 23-48), each instruct preset has:

| Property | Description |
|---|---|
| `input_sequence` | Prefix for user messages |
| `input_suffix` | Suffix for user messages |
| `output_sequence` | Prefix for assistant messages |
| `output_suffix` | Suffix for assistant messages |
| `system_sequence` | Prefix for system/narrator messages |
| `system_suffix` | Suffix for system/narrator messages |
| `first_output_sequence` | Override prefix for first assistant message |
| `last_output_sequence` | Override prefix for last assistant message (generation prompt) |
| `first_input_sequence` | Override prefix for first user message |
| `last_input_sequence` | Override prefix for last user message |
| `last_system_sequence` | Override for quiet prompt system sequence |
| `stop_sequence` | Model-specific stop sequence |
| `story_string_prefix` | Wraps the beginning of the story string |
| `story_string_suffix` | Wraps the end of the story string |
| `user_alignment_message` | Filler message for user alignment |
| `activation_regex` | Auto-select based on model name regex |
| `wrap` | Whether to add newlines between sequences and content |
| `macro` | Whether to process `{{macros}}` inside sequences |
| `names_behavior` | `none`, `force` (groups only), or `always` |
| `skip_examples` | Whether to skip formatting example dialogues |
| `system_same_as_user` | Use user sequences for system messages |
| `bind_to_context` | Auto-select matching context template |
| `sequences_as_stop_strings` | Use sequences as stopping strings |

### 7.3 Message Formatting

`formatInstructModeChat()` (line 387) wraps each message:

```js
// Simplified logic:
const prefix = isUser ? instruct.input_sequence : instruct.output_sequence;
const suffix = isUser ? instruct.input_suffix : instruct.output_suffix;
const text = includeNames ? [prefix, `${name}: ${mes}` + suffix] : [prefix, mes + suffix];
return text.filter(x => x).join(separator);
```

The `{{name}}` macro inside sequences is replaced with the actual character name.

### 7.4 Instruct Macros

Instruct mode registers macros (line 673-784) that expose all sequence values:

```
{{instructInput}}, {{instructUserPrefix}}    -- input_sequence
{{instructOutput}}, {{instructAssistantPrefix}} -- output_sequence
{{instructSystemPrefix}}                     -- system_sequence
{{instructStop}}                             -- stop_sequence
{{systemPrompt}}                             -- System prompt (respects char override)
{{chatStart}}                                -- Context template chat start marker
{{chatSeparator}}                            -- Context template example separator
```


## 8. Context Templates

### 8.1 Story String

The "story string" is the context template that defines how character data is assembled for text completion APIs. It uses Handlebars template syntax.

Default story string (`power-user.js`, line 89):
```handlebars
{{#if system}}{{system}}
{{/if}}{{#if description}}{{description}}
{{/if}}{{#if personality}}{{char}}'s personality: {{personality}}
{{/if}}{{#if scenario}}Scenario: {{scenario}}
{{/if}}{{#if persona}}{{persona}}
{{/if}}
```

Rendering happens in `renderStoryString()` (`power-user.js`, line 2243):
1. Compile Handlebars template with `noEscape: true`
2. Execute with params object containing character fields
3. Run `substituteParams()` for macro expansion
4. Strip leading newlines
5. Optionally add trailing newline

### 8.2 Context Template Settings

Each context template preset configures:

| Setting | Default | Description |
|---|---|---|
| `story_string` | (Handlebars template) | How character data is assembled |
| `chat_start` | `***` | Marker inserted before chat history |
| `example_separator` | `***` | Separator between example dialogue blocks |
| `use_stop_strings` | `true` | Use chat_start and example_separator as stop strings |
| `story_string_position` | `IN_PROMPT` | Where the story string goes (in prompt or in chat) |
| `story_string_depth` | `1` | Depth for in-chat story string placement |
| `story_string_role` | `system` | Role for in-chat story string |
| `names_as_stop_strings` | - | Use character names as stop strings |

### 8.3 Chat Template Auto-Detection

SillyTavern can auto-detect the appropriate instruct/context template from the model's tokenizer chat template hash (`chat-templates.js`). Known hashes map to preset names:

```js
'e10ca381b1ccc5cf9db52e371f3b6651576caee0a630b452e2816b2d404d4b65': 'Llama 3 Instruct',
'e16746b40344d6c5b5265988e0328a0bf7277be86f1c335156eae07e29c82826': 'Mistral V2 & V3',
'ecd6ae513fe103f0eb62e8ab5bfa8d0fe45c1074fa398b089c93a7e70c15cfd6': 'Gemma 2',
```

The `autoSelectInstructPreset()` function (line 236) matches the model ID against activation regexes or bound context templates and auto-selects the correct preset.


## 9. Author's Note / Depth Prompts

### 9.1 Author's Note System

Author's Note (`authors-note.js`) is an extension stored in chat metadata under key `2_floating_prompt`. It supports:

- **Text**: The note content
- **Depth**: How many messages from the end to inject (default: 4)
- **Interval**: Inject every N messages (0 = always)
- **Position**: `after` (after scenario), `chat` (in-chat at depth), or `before` (before scenario)
- **Role**: `system`, `user`, or `assistant`

Character-specific Author's Notes can be merged with the global note in three modes: replace, prepend, or append.

### 9.2 Depth Injection Mechanism

Absolute/in-chat injections are processed by `populationInjectionPrompts()` (line 781):

```js
async function populationInjectionPrompts(prompts, messages) {
    const maxDepth = getExtensionPromptMaxDepth();
    for (let i = 0; i <= maxDepth; i++) {
        const depthPrompts = prompts.filter(prompt =>
            prompt.injection_depth === i && prompt.content
        );
        // Group by injection_order (priority)
        // Process in priority order (high to low)
        // For each priority group, process by role: system, user, assistant
        // Combine extension prompts at the same depth
        // Splice into messages array at the correct position
    }
    messages = messages.reverse();
    return messages;
}
```

The injection order determines priority. Within the same depth:
- Higher `injection_order` numbers are processed first
- Prompts are grouped by role (`system`, `user`, `assistant`)
- Extension prompts at the default order (100) are merged with depth-specific prompts


## 10. Provider-Specific Formatting

### 10.1 Architecture

The prompt is assembled client-side as a universal ChatML array (`[{role, content, name, tool_calls}, ...]`), sent to the SillyTavern server at `/api/backends/chat-completions/generate`, and then converted server-side by `src/prompt-converters.js` before being forwarded to the actual API.

### 10.2 Conversion Functions

Each provider has a dedicated converter:

**Claude / Anthropic** (`convertClaudeMessages`, line 197):
- Extracts leading system messages into `systemPrompt` array (text blocks for the `system` parameter)
- Converts all remaining system messages to `user` role
- Handles tool calls: `tool_calls` become `tool_use` content blocks, tool results become `tool_result` blocks
- Converts images: `image_url` becomes Anthropic's `{type: 'image', source: {type: 'base64', ...}}` format
- Merges consecutive same-role messages (Anthropic requires strict alternation)
- Moves images from assistant messages to the next user message
- Adds prefill as a final assistant message (trimmed of trailing whitespace)
- Applies prompt caching at configured depth via `cachingAtDepthForClaude()`

**Google / Gemini** (`convertGooglePrompt`, line 432):
- Extracts leading system messages into `system_instruction.parts`
- Converts roles: `system`/`tool` to `user`, `assistant` to `model`
- Converts content to Gemini `parts` format: `{text}`, `{inlineData}`, `{functionCall}`, `{functionResponse}`
- Handles thought signatures for Gemini 3+ and Gemini 2.5 models
- Merges consecutive same-role messages
- Supports video and audio inline data

**Cohere** (`convertCohereMessages`, line 384):
- No names support -- prepends character name to message content
- Returns `{chatHistory: messages}` format

**MistralAI** (`convertMistralMessages`, line 699):
- Sanitizes tool call IDs (SHA-512 hash, first 9 chars)
- Fixes tool message ordering (user messages after tool messages get merged)
- Changes system-after-assistant to user role
- Supports `prefix` flag on last assistant message for prefilling

**xAI** (`convertXAIMessages`, line 781):
- Prepends character names to messages that need them
- Handles group name prefixing

**Generic Merge** (`mergeMessages`, line 823):
- Used for Custom API / OpenAI-compatible endpoints
- Modes controlled by `custom_prompt_post_processing` setting:
  - `merge` -- Merge consecutive same-role messages, prepend names
  - `semi` -- Same as merge + force mid-prompt system to user role
  - `strict` -- Semi + add placeholder user messages where needed
  - `single` -- Everything becomes user role (for single-role APIs)
  - `*_tools` variants -- Preserve tool messages during merging

**Text Completion** (`convertTextCompletionPrompt`, line 957):
- Flattens messages into `"Role: content\nassistant:"` format

### 10.3 Post-Processing Modes

The `custom_prompt_post_processing` setting (line 215-226) controls how the prompt is adapted for custom/compatible endpoints:

| Mode | Behavior |
|---|---|
| `(none)` | Send raw ChatML messages as-is |
| `merge` | Merge consecutive same-role messages, prepend names |
| `semi` | Merge + convert mid-prompt system messages to user |
| `strict` | Semi + insert placeholder user messages for alternation |
| `single` | All messages become user role |

### 10.4 Squash System Messages

When `oai_settings.squash_system_messages` is enabled, the `ChatCompletion.squashSystemMessages()` method (line 3687) combines consecutive system messages (without names) into a single message, joined by newline. This reduces the total message count and can improve model behavior.

Messages with identifiers `newMainChat`, `newChat`, and `groupNudge` are excluded from squashing.


## 11. Data Flow Summary

```
Character Card + Chat History + World Info + Extensions
                         |
                         v
            Generate() [script.js:4207]
                         |
        setOpenAIMessages() -- Convert chat to {role, content, name, media}
        setOpenAIMessageExamples() -- Parse example dialogue blocks
                         |
                         v
        prepareOpenAIMessages() [openai.js:1513]
                         |
        +-- preparePromptsForChatCompletion() -- Merge system prompts with PM order
        |       |
        |       +-- substituteParams() -- Macro expand all prompt content
        |       +-- Apply character card overrides (main, jailbreak)
        |
        +-- populateChatCompletion() -- Fill ChatCompletion within token budget
                |
                +-- Add world info, main, char data, persona (relative)
                +-- Add nsfw, jailbreak, user prompts (relative)
                +-- Inject extensions into main (summary, AN, vectors)
                +-- populationInjectionPrompts() -- In-chat depth injections
                +-- populateChatHistory() -- Fill chat messages newest-first
                +-- populateDialogueExamples() -- Fill example dialogues
                +-- Add control prompts (impersonate, quiet)
                         |
                         v
            chatCompletion.getChat() -- Flatten to [{role, content, name}]
                         |
            (Optional) squashSystemMessages()
                         |
                         v
            sendOpenAIRequest() [openai.js:2904]
                         |
            createGenerationParameters() -- Build request body
                         |
                         v
            POST /api/backends/chat-completions/generate
                         |
                         v
            Server-side conversion [prompt-converters.js]
                |
                +-- Claude: convertClaudeMessages() -> {messages, systemPrompt}
                +-- Gemini: convertGooglePrompt() -> {contents, system_instruction}
                +-- Cohere: convertCohereMessages() -> {chatHistory}
                +-- Mistral: convertMistralMessages() -> messages[]
                +-- Custom: postProcessPrompt() -> merged messages[]
                         |
                         v
                    Provider API
```


## 12. Key Design Observations

1. **Client-side assembly**: The entire prompt assembly pipeline runs in the browser. The server only handles format conversion and API proxying. This means prompt logic is fully visible and modifiable by users.

2. **Greedy budget allocation**: Mandatory prompts (main, character data, world info) are added first and must fit. Chat history fills the remaining space newest-first. This means older messages are dropped first, which is the expected behavior for chat context windows.

3. **Reserve/free pattern**: The budget system uses a reserve-then-free pattern for messages that need guaranteed placement at specific positions (new chat marker, group nudge, continue nudge, control prompts). This ensures they always fit regardless of how much chat history is loaded.

4. **Universal intermediate format**: All prompts are assembled into OpenAI's ChatML format (`{role, content}`) regardless of the target API. Server-side converters handle the provider-specific transformations.

5. **Extensibility via injection points**: Extensions can register prompts at any depth in the chat history or relative to the main system prompt, with configurable priority ordering and role assignment.

6. **Two-level ordering**: The prompt order defines the macro structure (what goes where), while within the chat history, message ordering is chronological. Depth injections provide a third axis for placing content at specific positions within the conversation.

7. **Macro evaluation timing**: Macros are evaluated at assembly time by `preparePrompt()` calling `substituteParams()`. This means macros have access to the current character, chat state, and extension data at generation time -- not at configuration time.
