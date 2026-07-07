# Prompt System

The prompt system is a modular construction engine. Rather than concatenating a few strings,
it compiles a structured prompt from presets, templates, character context, lore entries, and
reusable instruction blocks (fragments) — each with its own place and ordering. This page
covers the data model that describes a prompt, and the builder that assembles one.

## 1. Core Models and Relationships

Four entities describe a prompt. A `PromptTemplate` sets the overall shape; `PromptFragment`s
are reusable instruction blocks; a `TemplateFragment` is the join that places a fragment into
a template at a specific position; and a `Preset` carries generation settings. Templates and
presets both attach to a `Chat`:

<Figure tag="Figure 1" title="Prompt data model" id="fig-prompt-model">
<svg viewBox="0 0 820 420" role="img" aria-label="Prompt system entity relationships" style="font-family:var(--vp-font-family-base)">
  <!-- PromptTemplate -->
  <g>
    <rect x="40" y="40" width="234" height="150" rx="9" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-backend)"/>
    <rect x="40" y="40" width="234" height="28" rx="9" fill="var(--tbm-dgm-backend-soft)"/>
    <rect x="40" y="54" width="234" height="14" fill="var(--tbm-dgm-backend-soft)"/>
    <text x="157" y="59" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">PromptTemplate</text>
    <g font-size="11" fill="var(--tbm-dgm-ink-2)">
      <text x="54" y="90">name</text>
      <text x="54" y="110">system_template · Jinja2</text>
      <text x="54" y="130">component_order</text>
      <text x="54" y="150">components_enabled</text>
      <text x="54" y="170">max_history_tokens</text>
    </g>
  </g>
  <!-- TemplateFragment (join) -->
  <g>
    <rect x="310" y="60" width="196" height="120" rx="9" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-provider)"/>
    <rect x="310" y="60" width="196" height="28" rx="9" fill="var(--tbm-dgm-provider-soft)"/>
    <rect x="310" y="74" width="196" height="14" fill="var(--tbm-dgm-provider-soft)"/>
    <text x="408" y="79" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">TemplateFragment</text>
    <text x="493" y="79" text-anchor="end" font-size="9" fill="var(--tbm-dgm-faint)">join</text>
    <g font-size="11" fill="var(--tbm-dgm-ink-2)">
      <text x="324" y="110">position</text>
      <text x="324" y="132">ordinal</text>
      <text x="324" y="154">depth</text>
    </g>
  </g>
  <!-- PromptFragment -->
  <g>
    <rect x="550" y="40" width="230" height="130" rx="9" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-backend)"/>
    <rect x="550" y="40" width="230" height="28" rx="9" fill="var(--tbm-dgm-backend-soft)"/>
    <rect x="550" y="54" width="230" height="14" fill="var(--tbm-dgm-backend-soft)"/>
    <text x="665" y="59" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">PromptFragment</text>
    <g font-size="11" fill="var(--tbm-dgm-ink-2)">
      <text x="564" y="90">name</text>
      <text x="564" y="110">content · Jinja2</text>
      <text x="564" y="130">fragment_type</text>
      <text x="564" y="150">is_global</text>
    </g>
  </g>
  <!-- Preset -->
  <g>
    <rect x="40" y="300" width="200" height="86" rx="9" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-data)"/>
    <rect x="40" y="300" width="200" height="28" rx="9" fill="var(--tbm-dgm-data-soft)"/>
    <rect x="40" y="314" width="200" height="14" fill="var(--tbm-dgm-data-soft)"/>
    <text x="140" y="319" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">Preset</text>
    <g font-size="11" fill="var(--tbm-dgm-ink-2)">
      <text x="54" y="350">name</text>
      <text x="54" y="372">parameters</text>
    </g>
  </g>
  <!-- Chat -->
  <g>
    <rect x="330" y="300" width="190" height="86" rx="9" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <rect x="330" y="300" width="190" height="28" rx="9" fill="var(--tbm-dgm-surface-3)"/>
    <rect x="330" y="314" width="190" height="14" fill="var(--tbm-dgm-surface-3)"/>
    <text x="425" y="319" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">Chat</text>
    <g font-size="11" fill="var(--tbm-dgm-ink-2)">
      <text x="344" y="350">template_id · nullable</text>
      <text x="344" y="372">preset_id · nullable</text>
    </g>
  </g>
  <!-- Relationships -->
  <g stroke="var(--tbm-dgm-arrow)" stroke-width="1.4" fill="none">
    <path d="M274 118 L310 118"/>
    <path d="M550 110 L506 118"/>
    <path d="M120 190 L120 344 L330 344"/>
    <path d="M240 344 L330 344"/>
  </g>
  <g font-size="10" fill="var(--tbm-dgm-faint)">
    <text x="292" y="112" text-anchor="middle">1 · *</text>
    <text x="524" y="104" text-anchor="middle">1 · *</text>
    <text x="200" y="336" text-anchor="middle">default template · 1 · *</text>
    <text x="285" y="358" text-anchor="middle">optional</text>
  </g>
</svg>
<template #caption>

**A template is placed, not pasted.** `TemplateFragment` is the join row that binds a
`PromptFragment` into a `PromptTemplate` with a `position`, an `ordinal`, and a `depth`. A
`Chat` may point at a template (via nullable `template_id`) and, optionally, a `Preset` for
generation settings. When a chat has no template, the builder falls back to the model's
template, then to the default template, then to a minimal built-in prompt.

</template>
</Figure>

1. **Preset** — general generation settings (`temperature`, `top_p`, `max_tokens`) that
   override model defaults. Contains no prompt strings.
2. **PromptTemplate** — the core system layout: default system template, token limits, and
   component ordering.
3. **PromptFragment** — reusable instructions (jailbreaks, formatting constraints, writing
   guidelines) written in Jinja2.
4. **TemplateFragment** — the join entity assigning fragments to templates, setting the
   injection location (`position`), order (`ordinal`), and history injection depth (`depth`).

## 2. Component Order & Toggles

A prompt is assembled by laying out modular sections in the order given by the template's
`component_order`. The default order is:

| Component Name | Description |
| :--- | :--- |
| `system_prompt` | Central system message defining assistant identity (Jinja2 rendered). |
| `world_lore_before_character` | Activated lorebook entries targeted before the character description. |
| `character_context` | The character's description and personality traits. |
| `world_lore_after_character` | Activated lorebook entries targeted after the character description. |
| `scenario` | General situational context of the roleplay scene. |
| `persona` | Description of the user's roleplay character. |
| `world_lore_before_examples` | Lore entries injected immediately before dialogue examples. |
| `example_dialogues` | Mock conversations that model the assistant's response style. |
| `rag_context` | Long-term memory snippets fetched from vector search. |
| `chat_history` | Recent messages, within the token limit. |
| `post_history_instructions` | Final system instructions placed after chat history to prevent instruction drift. |

Each component can be globally toggled on or off per template via `components_enabled`.

## 3. Fragment Injection Positions

Fragments are injected dynamically, relative to the core components:

- **`after_system`** — immediately after the system prompt message.
- **`pre_history`** — after the example dialogues, right before the main chat history starts.
- **`post_history`** — immediately after the chat history.
- **`at_depth`** — directly into the chat-history stream at a specified index (e.g., four
  messages from the end). Used for persistent style instructions and drift-prevention
  reminders.

## 4. Prompt Construction (`PromptBuilder`)

The construction pipeline is owned by
[PromptBuilder](https://github.com/delfianto/the-bannered-mare/blob/main/backend/src/prompt_template/prompt_builder.py).
It runs in a fixed sequence, resolving context first, rendering the system layer, then
budgeting and assembling the history before ordering everything into the final message array:

<Figure tag="Figure 2" title="The PromptBuilder pipeline" id="fig-prompt-pipeline">
<svg viewBox="0 0 560 636" role="img" aria-label="PromptBuilder step sequence" style="font-family:var(--vp-font-family-base)">
  <defs>
    <marker id="tbm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-arrow)"/>
    </marker>
  </defs>
  <g font-size="12">
    <!-- step template repeated -->
    <rect x="40" y="16" width="480" height="48" rx="10" fill="var(--tbm-dgm-surface-3)" stroke="var(--tbm-dgm-border-strong)"/>
    <circle cx="66" cy="40" r="13" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/><text x="66" y="44" text-anchor="middle" font-size="11" font-weight="700" fill="var(--tbm-dgm-backend)">1</text>
    <text x="92" y="44" fill="var(--tbm-dgm-ink)" font-weight="600">Request completion</text>
    <rect x="40" y="84" width="480" height="48" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <circle cx="66" cy="108" r="13" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/><text x="66" y="112" text-anchor="middle" font-size="11" font-weight="700" fill="var(--tbm-dgm-backend)">2</text>
    <text x="92" y="112" fill="var(--tbm-dgm-ink)">Load template context — character, persona, chat</text>
    <rect x="40" y="152" width="480" height="48" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <circle cx="66" cy="176" r="13" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/><text x="66" y="180" text-anchor="middle" font-size="11" font-weight="700" fill="var(--tbm-dgm-backend)">3</text>
    <text x="92" y="180" fill="var(--tbm-dgm-ink)">Group activated lore by position</text>
    <rect x="40" y="220" width="480" height="48" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <circle cx="66" cy="244" r="13" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/><text x="66" y="248" text-anchor="middle" font-size="11" font-weight="700" fill="var(--tbm-dgm-backend)">4</text>
    <text x="92" y="248" fill="var(--tbm-dgm-ink)">Render system template (Jinja2)</text>
    <rect x="40" y="288" width="480" height="48" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <circle cx="66" cy="312" r="13" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/><text x="66" y="316" text-anchor="middle" font-size="11" font-weight="700" fill="var(--tbm-dgm-backend)">5</text>
    <text x="92" y="316" fill="var(--tbm-dgm-ink)">Assemble depth injections — AT_DEPTH lore + fragments</text>
    <rect x="40" y="356" width="480" height="48" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <circle cx="66" cy="380" r="13" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/><text x="66" y="384" text-anchor="middle" font-size="11" font-weight="700" fill="var(--tbm-dgm-backend)">6</text>
    <text x="92" y="384" fill="var(--tbm-dgm-ink)">Count tokens in reverse — build history within budget</text>
    <rect x="40" y="424" width="480" height="48" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <circle cx="66" cy="448" r="13" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/><text x="66" y="452" text-anchor="middle" font-size="11" font-weight="700" fill="var(--tbm-dgm-backend)">7</text>
    <text x="92" y="452" fill="var(--tbm-dgm-ink)">Splice depth injections into the history array</text>
    <rect x="40" y="492" width="480" height="48" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <circle cx="66" cy="516" r="13" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/><text x="66" y="520" text-anchor="middle" font-size="11" font-weight="700" fill="var(--tbm-dgm-backend)">8</text>
    <text x="92" y="520" fill="var(--tbm-dgm-ink)">Loop over component_order, append active elements</text>
    <rect x="40" y="560" width="480" height="48" rx="10" fill="var(--tbm-dgm-data-soft)" stroke="var(--tbm-dgm-data)"/>
    <circle cx="66" cy="584" r="13" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-data)"/><text x="66" y="588" text-anchor="middle" font-size="11" font-weight="700" fill="var(--tbm-dgm-data)">9</text>
    <text x="92" y="588" fill="var(--tbm-dgm-ink)" font-weight="600">Return final array of messages</text>
  </g>
  <g stroke="var(--tbm-dgm-arrow)" stroke-width="1.5" fill="none" marker-end="url(#tbm-ah)">
    <path d="M280 64 L280 82"/>
    <path d="M280 132 L280 150"/>
    <path d="M280 200 L280 218"/>
    <path d="M280 268 L280 286"/>
    <path d="M280 336 L280 354"/>
    <path d="M280 404 L280 422"/>
    <path d="M280 472 L280 490"/>
    <path d="M280 540 L280 558"/>
  </g>
</svg>
<template #caption>

**Budget before you build.** History is counted in reverse (newest first) so the builder can
stop exactly at `max_history_tokens`; depth injections are spliced in afterward, and only then
does the component loop assemble the final ordered message array.

</template>
</Figure>

### Depth Splicing Mechanism

To keep critical guidelines inside the model's attention window, `at_depth` fragments and
`AT_DEPTH` lore entries are spliced directly into the conversation history:

1. The builder resolves the active depth injections.
2. It sorts them by depth in descending order (deeper/older entries first) so that inserting
   one doesn't shift the offsets of the insertions still to come.
3. It inserts each injection into the chat-history array at index `len(history) - depth`.

### Token Budgeting

To prevent context overflow, the builder reads the chat session's messages in reverse,
tallies their token count with the `TokenizerService`, and grows the active history slice
until it reaches the `max_history_tokens` limit.
