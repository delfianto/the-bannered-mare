# SillyTavern -- Chat Completion Preset System Analysis

> Analysis date: 2026-06-11
> Source: `/st/` (SillyTavern) + the example files in `/preset/`
> Purpose: understand the "Freaky Frankenstein"-style preset JSONs so we can build an import/compatibility bridge.

---

## 1. What's actually in the `preset/` drop

The folder is a grab-bag of **three unrelated SillyTavern artifact types** — only one is a "preset". Detecting the type by shape is the first job of any importer.

| Type | Detect by | Example files | Covered here |
|---|---|---|---|
| **Chat Completion preset** | has `prompts[]` + `prompt_order[]` | `Freaky Frankenstein *`, `FreaKy FranKIMstein *`, `Frankenstein 3.x` | ✅ this doc |
| **Regex script** | has `findRegex` + `replaceString` + `placement` | `tavo1_*`, `GFX from Context*` | §6 (brief) |
| **Character Card V2/V3** | has `spec` + `spec_version` + `data` | `The Necro Princesses and the Berserk` | see `CHARACTER_CARD.md` |

Empirically every Freaky Frankenstein file in the drop is a **prompts-only** Chat Completion preset: exactly 11 top-level keys, no sampler fields. ST presets *can* also carry samplers (temperature, top_p, max_tokens, `chat_completion_source`, …); these creators stripped them so users keep their own sampling. An importer must treat the sampler block as **optional**.

---

## 2. Chat Completion preset structure

### 2.1 Top-level keys (the prompts-only subset)

The 9 string fields are "utility prompts" / format templates; the two arrays are the actual prompt system.

| Key | Type | Meaning |
|---|---|---|
| `prompts` | array | Library of prompt fragments (definitions). See §2.2. |
| `prompt_order` | array | Per-character ordering + enabled flags. See §2.3. |
| `main_prompt`/`nsfw_prompt`/`jailbreak_prompt` | *(legacy, absent here)* | Old flat fields — migrated into `prompts[]`, see §4. |
| `scenario_format` | str | Template for the `{{scenario}}` macro, e.g. `"{{scenario}}"`. |
| `personality_format` | str | Template for `{{personality}}`, e.g. `"{{personality}}"`. |
| `wi_format` | str | World-info wrapper, e.g. `"{0}"`. |
| `new_chat_prompt` | str | Injected marker text, e.g. `"[Start a new Chat]"`. |
| `new_example_chat_prompt` | str | e.g. `"[Example Chat]"`. |
| `new_group_chat_prompt` | str | New-chat text in group mode. |
| `group_nudge_prompt` | str | e.g. `"[Write the next reply only as {{char}}.]"`. |
| `continue_nudge_prompt` | str | Nudge appended when continuing a message. |
| `impersonation_prompt` | str | Used by the "impersonate" action. |

A **full** preset additionally carries the sampler/source block: `chat_completion_source`, `temperature`, `frequency_penalty`, `presence_penalty`, `top_p`, `top_k`, `openai_max_context`, `openai_max_tokens`, `stream_openai`, `names_behavior`, `wrap_in_quotes`, reasoning settings, etc. (defined as `oai_settings` in `st/public/scripts/openai.js`).

### 2.2 `prompts[]` — the prompt library

Each entry is a prompt *definition*. Maps to the `Prompt` class at `st/public/scripts/PromptManager.js:80` (constructor `:182`).

| Field | Type | Meaning |
|---|---|---|
| `identifier` | str | Stable key. Either a UUID (custom prompts) or a well-known name (`main`, `nsfw`, `jailbreak`, `enhanceDefinitions`, or a **marker** like `chatHistory`). Referenced by `prompt_order`. |
| `name` | str | Display label (creators use emoji, e.g. `"👀3rd person POV🦅"`). |
| `role` | str | `system` \| `user` \| `assistant` — the message role emitted. |
| `content` | str | The actual prompt text. **Absent on markers.** |
| `system_prompt` | bool | `true` = a built-in/managed prompt (`main`/`nsfw`/`jailbreak`/`enhanceDefinitions` and all markers); `false` = a user-authored custom prompt. |
| `marker` | bool | `true` = a **positional placeholder** with no `content`; ST substitutes live content at assembly (see §5). |
| `injection_position` | int | `0` = RELATIVE (sits where `prompt_order` puts it); `1` = ABSOLUTE (injected into chat history at `injection_depth`). Enum at `PromptManager.js:37`. |
| `injection_depth` | int | Depth from the latest message when `injection_position == 1`. |
| `forbid_overrides` | bool | If `true`, a character's prompt-override can't replace this prompt. |
| `enabled` | bool | Whether the definition is active *(note: the per-position toggle in `prompt_order` is the authoritative one — see §2.3)*. |

**Three categories of prompt** (all live in the same array, distinguished by the two booleans):

1. **Markers** (`marker:true`, no content) — placeholders for dynamic content. The standard set: `worldInfoBefore`, `worldInfoAfter`, `charDescription`, `charPersonality`, `scenario`, `personaDescription`, `dialogueExamples`, `chatHistory`.
2. **Built-in system prompts** (`system_prompt:true, marker:false`) — `main`, `nsfw`, `jailbreak`, `enhanceDefinitions`. Defaults injected at `openai.js:681`.
3. **Custom prompts** (`system_prompt:false, marker:false`) — the creator's own fragments (CoT blocks, anti-slop rules, POV toggles, etc.), keyed by UUID.

> Example — `Freaky Frankenstein 4 MAX+ Updated.json`: 48 prompts in the library, a mix of all three categories; emoji names; many disabled by default (creator ships toggles the user turns on).

### 2.3 `prompt_order[]` — ordering & activation

```jsonc
"prompt_order": [
  {
    "character_id": 100001,                 // global "dummy" character (see below)
    "order": [
      { "identifier": "main",          "enabled": true  },
      { "identifier": "worldInfoBefore","enabled": true },
      { "identifier": "<uuid>",        "enabled": false },
      ...                                    // 45 entries in the FF 4 MAX+ example, 25 enabled
    ]
  }
]
```

- `order` is the **assembly sequence**: ST walks it top-to-bottom, and for each `identifier` looks up the definition in `prompts[]`.
- `enabled` here is the **authoritative on/off** for that position — this is what the creator's "toggles" actually flip.
- `character_id` scopes the order. ST's chat-completion manager uses `promptOrder: { strategy: 'global', dummyId: 100001 }` (`openai.js:687`), so **`100001` is the global/default order** applied to every character. (Per-character overrides would appear as additional array entries keyed by real character ids.)
- An identifier present in `prompts[]` but absent from `order` is simply not assembled.

---

## 3. How ST reads & assembles a preset

```
preset .json file
   │  (import) preset-manager.js  →  validates type, stores under the API's preset list
   ▼
openai.js  loadOpenAISettings()   →  merges into oai_settings; fires OAI_PRESET_CHANGED
   │                                 setupChatCompletionPromptManager() (openai.js:666)
   ▼
PromptManager  (PromptManager.js) →  holds prompts[] + prompt_order, renders the UI,
   │                                 owns the global dummyId 100001 order
   ▼
preparePromptsForChatCompletion() (openai.js:1358)
   │  walks prompt_order; for each enabled identifier:
   │    • marker      → replace with live content (§5)
   │    • non-marker  → emit { role, content } after macro substitution ({{char}}, {{scenario}}…)
   ▼
ChatCompletion / MessageCollection  →  final ordered messages[] array  →  provider request
```

Key references:
- **Import / save / per-API routing:** `st/public/scripts/preset-manager.js` (uses `presetApiMap`; chat-completion presets go into `openai_settings`/`openai_setting_names`). Backend file storage: `st/src/endpoints/presets.js`.
- **PromptManager wiring:** `openai.js:666` `setupChatCompletionPromptManager` → `new PromptManager()` (`:673`), `defaultPrompts` (`:681`), global order `dummyId 100001` (`:687`).
- **Assembly:** `openai.js:1358` `preparePromptsForChatCompletion`; markers added at `:1203-1206` (`worldInfoBefore`/`worldInfoAfter`/`charDescription`), `chatHistory` MessageCollection at `:877/:881`, `dialogueExamples` at `:1093`.

---

## 4. Why this design (and the legacy it replaced)

Older presets had flat `main_prompt` / `nsfw_prompt` / `jailbreak_prompt` strings. ST migrated to the **modular `prompts[]` + `prompt_order`** model (`registerPromptManagerMigration`, `openai.js:45-75`, which copies those flat fields into `prompts[]` on load).

The modular model exists because RP prompt engineering needs:
- **Reorderable fragments** — the exact position of system text vs. world info vs. char description vs. chat history materially changes model behavior; `prompt_order` makes ordering first-class.
- **Toggleable fragments** — creators ship many optional blocks (POV, tense, "Freaky vs Realism mode", anti-slop) disabled, and the user flips per-position `enabled`.
- **Markers for dynamic content** — the preset can't contain the character/chat/world-info (those come from the session), so markers reserve the *slot* and ST fills it at assembly. This is the crux of the format.
- **Depth injection** — `injection_position:1` + `injection_depth` lets a fragment be injected N messages deep into the chat (e.g. a "jailbreak at depth 4") rather than in the static preamble.

---

## 5. The marker set (what ST substitutes)

| Marker identifier | Replaced with |
|---|---|
| `charDescription` | Character card `description` (formatted) |
| `charPersonality` | Character `personality` via `personality_format` |
| `scenario` | Character/chat `scenario` via `scenario_format` |
| `personaDescription` | The active user persona description |
| `worldInfoBefore` / `worldInfoAfter` | Activated lorebook entries, wrapped by `wi_format`, before/after the rest |
| `dialogueExamples` | `mes_example` blocks, each prefixed by `new_example_chat_prompt` |
| `chatHistory` | The actual conversation messages (a `MessageCollection`); `new_chat_prompt`, group/continue nudges are injected around it |

Markers have **no `content`**; their entry only carries `identifier`, `name`, `system_prompt:true`, `marker:true`. They are pure ordering anchors.

---

## 6. The other two artifact types (for the importer's type-detector)

- **Regex scripts** (`tavo1_*`, `GFX from Context`): `{ id, scriptName, findRegex, replaceString, placement[], disabled, markdownOnly, promptOnly, runOnEdit, substituteRegex, trimStrings[], minDepth, maxDepth }`. ST's *Regex extension* runs find/replace over messages at configured `placement`s (user input / AI output / prompt). **Not a preset** — different subsystem; out of scope for the preset bridge.
- **Character Card V2/V3** (`The Necro Princesses…`): `{ spec, spec_version, data }`. Covered by `CHARACTER_CARD.md`.

A robust importer should sniff the shape and reject/redirect non-preset files rather than coercing them.

---

## 7. Comparison with The Bannered Mare & bridge approach

The Bannered Mare splits what ST bundles into **one** preset across **two** concerns:

| ST concept | The Bannered Mare equivalent | Gap |
|---|---|---|
| Sampler block (temperature, top_p, max_tokens, source…) | `Preset.parameters` (JSON) — `src/core/persistence/models/preset.py`; schema `src/preset/schemas.py` | Direct-ish: map ST sampler keys → `parameters`. Only present in *full* ST presets. |
| `prompts[]` + `prompt_order` + format strings + markers | Prompt-assembly layer: `PromptTemplate` + `prompt_fragments` / `template_fragments` tables (Jinja2 prompt construction) | **Structural mismatch** — The Bannered Mare's `Preset` models *only samplers*; the ST prompt system maps to templates/fragments, not to `Preset`. |

**Implication for the bridge:** a Freaky Frankenstein (prompts-only) preset has **no sampler data** and maps **entirely onto the prompt-template/fragment side**, not onto `Preset`. A faithful import needs to:

1. **Type-sniff** the JSON (§1) and reject regex/card files.
2. Translate each `prompts[]` entry → a prompt fragment (`identifier`, `role`, `content`, `injection_position`/`injection_depth`, `enabled`).
3. Translate `prompt_order[100001].order` → the fragment ordering + enabled flags (the authoritative toggles).
4. Map the **8 markers** to The Bannered Mare's own assembly slots (char description / persona / world-info / examples / chat history). This is the hard part — it requires The Bannered Mare's prompt builder to expose the same insertion points; markers without a target slot must be dropped or stubbed.
5. Carry the format strings (`scenario_format`, `wi_format`, nudges) into the corresponding template config.
6. If a *full* preset, additionally map the sampler block → a `Preset.parameters` row (and reconcile `chat_completion_source` against the provider/model, which The Bannered Mare models separately).

Recommended first milestone: a read-only **importer + validator** that parses a Chat Completion preset, classifies each prompt (marker / system / custom), resolves the `prompt_order`, and emits a normalized intermediate structure — *before* committing to the storage mapping. The marker→slot mapping (step 4) is the design decision that gates a truly faithful bridge.
