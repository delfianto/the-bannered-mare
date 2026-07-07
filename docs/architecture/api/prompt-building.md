---
title: Prompt Building
---

# Prompt Building

These resources decide *how* a prompt is assembled and *how* the model samples. A
**template** lays out the prompt's structure; **fragments** are reusable blocks attached to
templates; a **preset** is a named set of sampling parameters; and a **profile** is a
loadout that bundles a template, preset, persona, and model into one selectable unit. How
these feed the actual prompt is covered in
[Prompt System](/architecture/backend/prompt-system); the relationships are in
[the data model](/architecture/backend/data-model#prompt-building).

All four collections use a trailing slash (`/api/profiles/`, `/api/presets/`, …) and
offset pagination.

## Profiles

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/profiles/` | List profiles (paginated). |
| `POST` | `/api/profiles/` | Create a profile. |
| `GET` | `/api/profiles/{id}` | Get one profile. |
| `PUT` | `/api/profiles/{id}` | Update a profile. |
| `DELETE` | `/api/profiles/{id}` | Delete a profile. |
| `POST` | `/api/profiles/{id}/default` | Mark this profile the default. |

A profile is a **bundle of four references** — a prompt template, a preset, a persona, and
a model — each optional. `ProfileResponse`:

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | 12-char nanoid. |
| `name` | string | **Required.** Unique. |
| `description` | string \| null | Its purpose. |
| `is_default` | boolean | Default loadout for new chats. |
| `prompt_template_id`, `preset_id`, `persona_id`, `model_id` | string \| null | The four bundled references (all nullable). |
| `source` | string | `manual`, `sillytavern`, … — where it came from. |
| `source_filename` | string \| null | Original filename if imported. |
| `created_at`, `updated_at` | string | ISO 8601 UTC. |

Applying a profile to a chat is a [Conversations](/architecture/api/conversations#applying-a-profile)
endpoint (`POST /api/chats/{id}/profile`) — it *copies* the profile's values onto the chat,
so profiles can be freely edited or deleted afterward. `POST …/default` moves the default
flag so exactly one profile holds it.

```bash
curl -X POST http://localhost:8000/api/profiles/ \
  -H "Content-Type: application/json" \
  -d '{ "name": "Grimdark RP", "prompt_template_id": "tPl…", "preset_id": "prS…", "model_id": "mdl…" }'
# → 201 ProfileResponse
```

## Presets

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/presets/` | List presets (paginated). |
| `POST` | `/api/presets/` | Create a preset. |
| `POST` | `/api/presets/import` | Import a SillyTavern chat-completion preset. |
| `GET` | `/api/presets/{id}` | Get one preset. |
| `PUT` | `/api/presets/{id}` | Update a preset. |
| `DELETE` | `/api/presets/{id}` | Delete a preset. |
| `POST` | `/api/presets/{id}/default` | Mark this preset the default. |

A preset is just a named `parameters` object. `PresetResponse`: `id`, `name`,
`description`, `parameters` (the sampling overrides — temperature, top_p, penalties, …),
`is_default`, and timestamps. Create with `PresetCreate` (`name` required); `PresetUpdate`
edits any field; `POST …/default` sets the default.

```bash
curl -X POST http://localhost:8000/api/presets/ \
  -H "Content-Type: application/json" \
  -d '{ "name": "Creative", "parameters": { "temperature": 1.1, "top_p": 0.95 } }'   # → 201 PresetResponse
```

### Importing a SillyTavern preset

`POST /api/presets/import` takes a SillyTavern chat-completion preset as a `file`
(`multipart/form-data`) and does more than its name suggests: it maps the preset's prompt
structure to a **`PromptTemplate` + fragments** and, when sampler settings are present, a
**`Preset`** too. It returns an `STImportResult` describing everything it created plus
`warnings` for anything that didn't transfer cleanly:

| Field | Type | Notes |
|-------|------|-------|
| `template_id`, `template_name` | string | The prompt template it created. |
| `fragment_ids` | string[] | Fragments created from the preset's prompts. |
| `preset_id`, `preset_name` | string \| null | The sampler preset, if any settings were present. |
| `profile_id`, `profile_name` | string \| null | A profile bundling them, if created. |
| `warnings` | string[] | Parts that didn't map cleanly. |

```bash
curl -X POST http://localhost:8000/api/presets/import -F "file=@my-st-preset.json"   # → 201 STImportResult
```

## Prompt templates

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/prompt-templates/` | List templates (paginated). |
| `POST` | `/api/prompt-templates/` | Create a template. |
| `GET` | `/api/prompt-templates/{id}` | Get one template. |
| `PUT` | `/api/prompt-templates/{id}` | Update a template. |
| `DELETE` | `/api/prompt-templates/{id}` | Delete a template (returns `200 OK`). |
| `POST` | `/api/prompt-templates/{id}/preview` | Render the template with sample data. |
| `POST` | `/api/prompt-templates/{id}/set-default` | Mark this template the default. |

A template controls the **order and toggling** of prompt components plus the system-prompt
text. `PromptTemplateResponse`:

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | 12-char nanoid. |
| `name` | string | **Required.** Unique. |
| `description` | string \| null | Its purpose. |
| `is_default` | boolean | Applied to new chats when set. |
| `system_template` | string | **Required.** Jinja2 template for the system prompt. |
| `component_order` | string[] | Ordered component names (system prompt, world lore, character context, scenario, persona, examples, RAG context, chat history, post-history instructions). |
| `components_enabled` | object | Map of component name → boolean. |
| `max_history_tokens` | integer \| null | Cap on history tokens included. |
| `created_at`, `updated_at` | string | ISO 8601 UTC. |

### Previewing a template

`POST …/preview` renders the template against **sample data** so you can see the output
without a live chat. The `TemplatePreviewRequest` fields (`character_name`,
`character_description`, `character_personality`, `character_scenario`, `persona_name`,
`persona_description`) all have sensible defaults, so an empty body previews with
placeholders. It returns `{ rendered, variables_used }`.

```bash
curl -X POST http://localhost:8000/api/prompt-templates/tPl123456789/preview \
  -H "Content-Type: application/json" \
  -d '{ "character_name": "Lydia", "persona_name": "Dovahkiin" }'       # → TemplatePreviewResponse
```

### Attaching fragments

Fragments are wired to a template through a nested join collection:

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/prompt-templates/{template_id}/fragments/` | List a template's attached fragments. |
| `POST` | `/api/prompt-templates/{template_id}/fragments/` | Attach a fragment to the template. |
| `DELETE` | `/api/prompt-templates/{template_id}/fragments/{fragment_id}` | Detach a fragment. |

`GET` returns a bare array of `TemplateFragmentResponse` — the association row (`position`,
`ordinal`) **with the full `fragment` embedded**. Attach with an `AttachFragmentRequest`:
`fragment_id` (**required**), `position` (default `after_system` — one of `after_system`,
`pre_history`, `post_history`, `at_depth`), and `ordinal` (default `0`).

```bash
curl -X POST http://localhost:8000/api/prompt-templates/tPl123456789/fragments/ \
  -H "Content-Type: application/json" \
  -d '{ "fragment_id": "frg987654321", "position": "post_history", "ordinal": 0 }'  # → 201 TemplateFragmentResponse
```

## Prompt fragments

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/prompt-fragments/` | List fragments (paginated, filterable, with usage info). |
| `POST` | `/api/prompt-fragments/` | Create a fragment. |
| `GET` | `/api/prompt-fragments/{id}` | Get one fragment. |
| `PUT` | `/api/prompt-fragments/{id}` | Update a fragment. |
| `DELETE` | `/api/prompt-fragments/{id}` | Delete a fragment. |

A fragment is a reusable, typed block of prompt text. `FragmentResponse`:

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | 12-char nanoid. |
| `name` | string | **Required.** Unique. |
| `description` | string \| null | Its purpose. |
| `fragment_type` | string | `system`, `nsfw`, `jailbreak`, `instruction` (default), or `context`. |
| `content` | string | **Required.** Jinja2 template text. |
| `is_global` | boolean | Available to every template when `true`. |
| `used_by` | object[] | `{ id, name }` summaries of templates currently referencing it. |
| `created_at`, `updated_at` | string | ISO 8601 UTC. |

Listing is offset-paginated and filterable by `fragment_type`, `is_global`, and
`unused_only` (a boolean that surfaces fragments attached to no template — handy for
cleanup). The `used_by` array is why: it lets the UI show, and safely prune, orphaned
fragments.

```bash
curl -X POST http://localhost:8000/api/prompt-fragments/ \
  -H "Content-Type: application/json" \
  -d '{ "name": "Grimdark tone", "fragment_type": "instruction", "content": "Write in a bleak, unsparing register." }'
# → 201 FragmentResponse
```
