# Sample SillyTavern presets (test fixtures)

Hand-authored, **SFW parody** SillyTavern chat-completion presets used by the
`st_import` integration tests. They mirror the real "Freaky Frankenstein" file
structure faithfully — only the prompt *text* is made up (and silly) — so this
folder doubles as a readable, runnable reference for the ST preset format.

> Real community presets live (gitignored) under `refs/preset/`. The ST↔The Bannered Mare
> mapping is documented in `../../../../docs/sillytavern/comparison/presets.md`.

## The structure, by example

An ST chat-completion preset is one JSON object:

```jsonc
{
  // (optional) sampler block — present only in "full" presets
  "temperature": 0.9, "top_p": 0.95, "openai_max_tokens": 800, "seed": -1,
  // (optional, ignored on import) connection config
  "chat_completion_source": "openai", "openai_model": "gpt-4o",
  // (optional) format / nudge strings — no Bannered Mare home, dropped with a warning
  "scenario_format": "{{scenario}}", "new_chat_prompt": "[...]",

  // the prompt library: markers, built-ins, and custom prompts
  "prompts": [
    { "identifier": "main", "name": "Main Prompt", "role": "system",
      "content": "...", "system_prompt": true, "marker": false,
      "injection_position": 0, "injection_depth": 4 },
    { "identifier": "chatHistory", "name": "Chat History",
      "system_prompt": true, "marker": true },          // marker: no content
    { "identifier": "<uuid>", "name": "My Rule", "role": "system",
      "content": "...", "system_prompt": false, "marker": false,
      "injection_position": 1, "injection_depth": 3 }   // absolute -> at_depth
  ],

  // the assembly order + on/off toggles (character_id 100001 = global)
  "prompt_order": [
    { "character_id": 100001, "order": [
      { "identifier": "main", "enabled": true },
      { "identifier": "chatHistory", "enabled": true }
    ]}
  ]
}
```

Three prompt kinds:
- **markers** (`marker: true`, no `content`) — placeholders for content The Bannered Mare
  generates itself (character, scenario, lore, chat history, examples);
- **built-ins** (`system_prompt: true`) — `main` (the system prompt), `nsfw`,
  `jailbreak`, `enhanceDefinitions`;
- **custom** (UUID `identifier`) — the creator's own fragments.

`injection_position`: `0` = relative (placed by `prompt_order`), `1` = absolute
(injected into the chat history at `injection_depth`).

## The samples

| File | Demonstrates |
|---|---|
| `freaky_frankenpurr.json` | The full Freaky-Frankenstein shape: prompts-only (no samplers), all markers, `main`/`nsfw`/`jailbreak` built-ins, custom CoT + anti-slop prompts, a depth-injected drift reminder (`injection_position: 1`), and two `enabled: false` toggles. A melodramatic cat saga. |
| `chef_dungeon_master.json` | A **full** preset *with* a sampler block + connection fields (so the importer also creates a `Preset`; connection fields are ignored). An abrasive Michelin-star DM. |
| `minimal_greeter.json` | The smallest valid preset — just `main` + the `chatHistory` marker. A haiku-prone golem. |
