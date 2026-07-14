---
title: World & Lore
---

# World & Lore

A **lorebook** is a collection of world knowledge; a **lore entry** is one fact in it,
gated by keywords so it's injected into the prompt only when relevant. A lorebook is either
attached to a character or marked global (applies to every chat). Entries are nested under
their lorebook — there is no top-level entries collection. The activation model
(keyword scanning, insertion position, budgets) mirrors SillyTavern's; see the
[World & Lore analysis](/sillytavern/analysis/world-lore) for the design background and
[the data model](/architecture/backend/data-model#world-lore) for the relationships.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/lorebooks` | List lorebooks (filterable, paginated). |
| `POST` | `/api/lorebooks` | Create a lorebook. |
| `GET` | `/api/lorebooks/{id}` | Get a lorebook **with all its entries**. |
| `PUT` | `/api/lorebooks/{id}` | Update lorebook metadata. |
| `DELETE` | `/api/lorebooks/{id}` | Delete a lorebook and all its entries. |
| `POST` | `/api/lorebooks/{id}/entries` | Add an entry to a lorebook. |
| `PUT` | `/api/lorebooks/{id}/entries/{entry_id}` | Update an entry. |
| `DELETE` | `/api/lorebooks/{id}/entries/{entry_id}` | Delete an entry. |

## Lorebooks

`GET /api/lorebooks` returns a **paginated** `{ items, meta }` envelope of `LorebookResponse`
and accepts two filters: `character_id` and `is_global`. The list view omits entries; fetch a
single lorebook to get them.

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | 12-char nanoid. |
| `name` | string | **Required.** |
| `description` | string \| null | Optional. |
| `is_global` | boolean | Applies to every chat when `true`. |
| `character_id` | string \| null | Owning character; `null` for a global book. |
| `created_at`, `updated_at` | string | ISO 8601 UTC. |

`GET /api/lorebooks/{id}` returns `LorebookDetailResponse` — the same fields plus an
`entries` array. Create with `LorebookCreate` (`name` required; optional `description`,
`is_global`, `character_id`); update metadata with `LorebookUpdate`.

```bash
curl -X POST http://localhost:8000/api/lorebooks \
  -H "Content-Type: application/json" \
  -d '{ "name": "The Reach", "character_id": "V1StGXR8Z5jd" }'          # → 201 LorebookResponse

curl "http://localhost:8000/api/lorebooks/aB3dEf6hIjK0"                 # → LorebookDetailResponse (with entries)
```

## Lore entries

An entry is created and edited under its lorebook. Beyond `name` and `content`, its fields
control **when** it activates and **where** it lands in the prompt.

| Field | Type | Default | Controls |
|-------|------|---------|----------|
| `content` | string | — | **Required.** The text injected into the prompt. |
| `keys` | string[] | `[]` | Primary trigger keywords — a match arms the entry. |
| `secondary_keys` | string[] | `[]` | Secondary keywords, combined per `secondary_logic`. |
| `secondary_logic` | enum | `and_any` | `and_any` · `and_all` · `not_any` · `not_all`. |
| `constant` | boolean | `false` | Always active, ignoring keywords. |
| `enabled` | boolean | `true` | Whether the entry participates at all. |
| `case_sensitive`, `match_whole_words`, `use_regex` | boolean | `false` | Matching modifiers for the keys. |
| `position` | enum | `after_character` | Insertion slot: `before_character` · `after_character` · `at_depth` · `before_examples`. |
| `depth` | integer | `4` | Message depth when `position = at_depth`. |
| `role` | enum | `system` | Message role for `at_depth` insertion. |
| `priority` | integer | `100` | Higher inserts first when trimming to budget. |
| `scan_depth` | integer \| null | — | Per-entry override for how far back to scan. |
| `ignore_budget` | boolean | `false` | Exempt from the lore token budget. |
| `order` | integer | `0` | Tie-break ordering within a position. |

`LoreEntryResponse` returns all of the above plus `id`, `lorebook_id`, `created_at`, and
`updated_at`. `LoreEntryUpdate` makes every field optional for partial edits.

```bash
curl -X POST http://localhost:8000/api/lorebooks/aB3dEf6hIjK0/entries \
  -H "Content-Type: application/json" \
  -d '{
        "name": "Markarth",
        "content": "Markarth is a Dwemer city of stone, riddled with Forsworn intrigue.",
        "keys": ["Markarth", "the Reach"],
        "position": "before_character",
        "priority": 200
      }'                                                                 # → 201 LoreEntryResponse
```
