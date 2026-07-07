# Presets: SillyTavern vs. The Bannered Mare

The Bannered Mare can **import** SillyTavern (ST) chat-completion presets, but it does not
model them the way ST does. This document explains what an ST preset is, how
The Bannered Mare represents the same ideas, and exactly what the importer
(`POST /api/presets/import`) does with each part.

> See also: the sibling `PROMPTING.md` (ST↔The Bannered Mare prompt-system comparison) and
> `docs/st_analysis/PRESET.md` (deeper ST preset-format analysis). This file is the
> **comparison + import contract**.

## TL;DR

- An ST "preset" bundles **two unrelated concerns** in one file: sampler settings
  and a prompt-assembly recipe. The Bannered Mare keeps them as **separate** first-class
  objects (`Preset` vs. `PromptTemplate` + fragments).
- The importer **splits** an ST preset accordingly, is faithful where the models
  line up, and **emits warnings** for everything that doesn't.
- The Bannered Mare is intentionally **not 1:1 with ST**. It keeps ST's one genuinely
  valuable idea — depth-anchored injection — and drops the GPT-3.5-era machinery
  (marker placeholders, per-prompt role juggling, format-string plumbing) that
  modern long-context models don't need.

The importer's core job is a split: one ST preset bundles two unrelated concerns that
The Bannered Mare models as separate first-class objects.

<Figure tag="Figure 1" title="One preset file → two objects" id="fig-cmp-presets">
<svg viewBox="0 0 760 280" role="img" aria-label="Importing an ST preset splits it into a Preset and a PromptTemplate" style="font-family:var(--vp-font-family-base)">
  <defs>
    <marker id="tbm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-arrow)"/>
    </marker>
  </defs>
  <rect x="24" y="36" width="300" height="208" rx="12" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <rect x="24" y="36" width="300" height="40" rx="12" fill="var(--tbm-dgm-provider-soft)"/><rect x="24" y="56" width="300" height="20" fill="var(--tbm-dgm-provider-soft)"/>
  <text x="174" y="61" text-anchor="middle" font-size="12.5" font-weight="800" fill="var(--tbm-dgm-ink)">SillyTavern preset — one file</text>
  <rect x="44" y="90" width="260" height="60" rx="9" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
  <text x="174" y="112" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--tbm-dgm-ink)">Sampler block</text>
  <text x="174" y="130" text-anchor="middle" font-size="10" fill="var(--tbm-dgm-ink-2)">temperature · top_p · penalties · max_tokens</text>
  <rect x="44" y="162" width="260" height="66" rx="9" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
  <text x="174" y="184" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--tbm-dgm-ink)">prompts[] + prompt_order[]</text>
  <text x="174" y="202" text-anchor="middle" font-size="10" fill="var(--tbm-dgm-ink-2)">assembly recipe —</text>
  <text x="174" y="216" text-anchor="middle" font-size="10" fill="var(--tbm-dgm-ink-2)">markers · built-ins · custom</text>
  <rect x="470" y="66" width="266" height="66" rx="10" fill="var(--tbm-dgm-data-soft)" stroke="var(--tbm-dgm-data)"/>
  <text x="603" y="94" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">Preset</text>
  <text x="603" y="112" text-anchor="middle" font-size="10" fill="var(--tbm-dgm-ink-2)">sampler settings, first-class</text>
  <rect x="470" y="160" width="266" height="76" rx="10" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/>
  <text x="603" y="186" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">PromptTemplate + fragments</text>
  <text x="603" y="204" text-anchor="middle" font-size="10" fill="var(--tbm-dgm-ink-2)">component_order + attached fragments</text>
  <text x="603" y="220" text-anchor="middle" font-size="10" fill="var(--tbm-dgm-ink-2)">keeps depth-anchored injection</text>
  <g stroke="var(--tbm-dgm-arrow)" stroke-width="1.6" fill="none" marker-end="url(#tbm-ah)">
    <path d="M304 120 L468 99"/>
    <path d="M304 195 L468 198"/>
  </g>
  <text x="392" y="104" text-anchor="middle" font-size="9.5" fill="var(--tbm-dgm-faint)">split on import</text>
</svg>
<template #caption>

**Unbundle, then map.** `POST /api/presets/import` separates the sampler block (→ a `Preset`)
from the prompt-assembly recipe (→ a `PromptTemplate` plus fragments), staying faithful where the
models line up and emitting warnings where they don't. It keeps ST's depth-anchored injection and
drops the marker/role plumbing modern long-context models don't need.

</template>
</Figure>

## What an ST chat-completion preset is

A single JSON file carrying (all optional unless noted):

- **Sampler block** — `temperature`, `top_p`, `top_k`, `top_a`, `min_p`,
  `frequency_penalty`, `presence_penalty`, `repetition_penalty`,
  `openai_max_tokens`, `seed`, `n`. (Connection fields like
  `chat_completion_source`, model names, and proxy are environment config, not tuning.)
- **`prompts[]`** — a library of prompt entries: `identifier`, `name`, `role`,
  `content`, `system_prompt`, `marker`, `injection_position`, `injection_depth`,
  `enabled`. Three kinds:
  - **markers** (`marker: true`, no content) — placeholders ST fills at assembly:
    `charDescription`, `charPersonality`, `scenario`, `personaDescription`,
    `worldInfoBefore/After`, `dialogueExamples`, `chatHistory`;
  - **built-ins** — `main`, `nsfw`, `jailbreak`, `enhanceDefinitions`;
  - **custom** — UUID-keyed creator fragments (CoT blocks, anti-slop rules, etc.).
- **`prompt_order[]`** — per-character assembly order; `character_id` `100001`/`100000`
  is the global one. Its `enabled` flags are what creators' "toggles" actually flip.
- **Format / nudge strings** — `scenario_format`, `wi_format`, `new_chat_prompt`,
  `group_nudge_prompt`, etc.

Notes: ST presets have **no `name`** — the name is the filename. The same JSON
shape is reused by ST for *non-presets* (regex scripts, character cards); the
importer detects and rejects those.

## How The Bannered Mare models the same ideas

| ST concept | The Bannered Mare home | Notes |
|---|---|---|
| Sampler block | `Preset.parameters` (JSON) | A The Bannered Mare `Preset` is **only** samplers. |
| `main` system prompt | `PromptTemplate.system_template` (Jinja2) | The base instruction. |
| Markers (charDescription, scenario, chatHistory, worldInfo…) | `PromptTemplate.component_order` + `components_enabled` | The Bannered Mare **generates** this content from the Character / Persona / lore at build time; markers just toggle and order components. |
| Built-in & custom content prompts | `PromptFragment` + `TemplateFragment` | Reusable blocks attached to a template at a position. |
| `injection_position` / `injection_depth` | `TemplateFragment.position` + `depth` | RELATIVE → `after_system`/`pre_history`/`post_history`; ABSOLUTE → `at_depth` + `depth`. |
| `prompt_order[].enabled` | included / skipped at import | Disabled entries don't transfer. |
| Format/nudge strings, `forbid_overrides`, `injection_order` | — | No equivalent; dropped with a warning. |

## What the importer does (`POST /api/presets/import`)

Upload a `.json` ST preset. The importer:

1. **Validates** it's a chat-completion preset — rejecting malformed JSON,
   text-completion presets (`temp`/`rep_pen`/`instruct`), regex scripts
   (`findRegex`), and character cards (`spec: chara_card`) with a clear `400`.
2. **Names** everything from the filename stem (ST has none), auto-suffixing
   `" (2)"`, `" (3)"` on collision so an import never clobbers existing data.
3. Builds, in **one transaction**:
   - a `PromptTemplate` — `system_template` from `main`; components toggled and
     ordered from the markers in `prompt_order`;
   - one `PromptFragment` + `TemplateFragment` per enabled content prompt, with
     position/depth derived from its injection settings (an existing fragment with
     identical content is reused rather than duplicated);
   - a `Preset` **only if** sampler fields are present;
   - a `Profile` that ties the template and (optional) preset into one selectable
     unit, tagged `source="sillytavern"` with the original `source_filename`.
4. Returns the created IDs/names (`template`, `fragment_ids`, optional `preset`,
   `profile`) plus a `warnings[]` list.

It deliberately **does not** route through the normal template/fragment services:
those validate content as strict Jinja2 and would reject ST's `:`-style macros
(e.g. `{{roll:1d6}}`, `{{random::a::b}}`). The importer stores content verbatim and
only warns.

## Faithful vs. approximated vs. dropped

**Faithful**
- Sampler values (`openai_max_tokens` → `max_tokens`).
- `main` → system prompt.
- **Depth-anchored prompts** (`injection_position: 1`) → `at_depth` + `depth` — the
  one ST mechanism The Bannered Mare fully embraces.
- Enable/disable toggles; custom-prompt content and ordering relative to chat history.

**Approximated**
- ST's fine-grained ordering between markers collapses onto Bannered Mare's coarse
  four-slot fragment positions (`after_system` / `pre_history` / `post_history` /
  `at_depth`).
- `charDescription` + `charPersonality` both fold into one `character_context` component.

**Dropped (with a warning)**
- **Prompt roles** — The Bannered Mare fragments are system-only, so ST `user`/`assistant`
  prompts import as system fragments. (Community presets use these heavily for CoT.)
- **Format / nudge strings** (`scenario_format`, `wi_format`, `new_chat_prompt`, …) —
  The Bannered Mare renders these concerns inside its own templates.
- `forbid_overrides`, `injection_order`, and connection/model/proxy fields.

## Why the differences

ST's prompt manager grew up in the GPT-3.5 era of 4–8K context, where every token
was contested — hence marker placeholders, aggressive per-prompt ordering, role
juggling, and format-string plumbing to wedge structure into tiny windows.
The Bannered Mare targets modern 256K–1M context models, so it:

- **Separates samplers from prompt structure** — they change independently;
  bundling them was an ST UI convenience, not a data model.
- **Generates character / persona / lore content itself** rather than treating them
  as orderable prompt slots — fewer moving parts, no marker bookkeeping.
- **Keeps depth injection** — putting a short instruction *near the generation point*
  (N messages from the end) is the most reliable anti-drift lever, and The Bannered Mare
  uses the same mechanism for both activated lore and drift-reminder fragments.

The net effect: importing an ST preset preserves the creator's **intent** — base
instruction, custom CoT/style fragments, depth reminders, and samplers — re-expressed
in The Bannered Mare's leaner model, with a warnings list naming precisely what didn't carry over.
