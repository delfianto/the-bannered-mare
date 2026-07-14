---
title: Characters & Personas
---

# Characters & Personas

Two resources define *who* is in a scene: the **character** is the NPC the model roleplays,
and the **persona** is the user's own role. Both carry an avatar (uploaded as a file, served
back as an image), which is why their create/update endpoints use `multipart/form-data`
rather than JSON. Characters additionally support **import/export** in the TavernCard V1/V2
format used across the SillyTavern ecosystem. See the
[data model](/architecture/backend/data-model#characters-personas) for how they relate to
chats and lorebooks.

## Characters

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/characters` | List characters (paginated, filterable). |
| `POST` | `/api/characters` | Create a character, with optional avatar upload. |
| `POST` | `/api/characters/import` | Import from a TavernCard V1/V2 PNG or JSON file. |
| `GET` | `/api/characters/{id}` | Get one character. |
| `PUT` | `/api/characters/{id}` | Update a character (avatar optional). |
| `DELETE` | `/api/characters/{id}` | Delete a character (cascades to its chats & lorebooks). |
| `GET` | `/api/characters/{id}/avatar` | Serve the avatar image. |
| `GET` | `/api/characters/{id}/avatar_large` | Serve the large (≤512px) full portrait. |
| `GET` | `/api/characters/{id}/avatar_thumbnail` | Serve the generated thumbnail. |
| `GET` | `/api/characters/{id}/export/json` | Export as TavernCard V2 JSON. |
| `GET` | `/api/characters/{id}/export/png` | Export as a PNG with the card embedded in `tEXt`. |

### The character resource

`CharacterResponse` — the shape returned by get, list items, create, and update:

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | 12-char nanoid. |
| `name` | string | **Required.** Display name. |
| `description` | string \| null | Short tagline. |
| `personality` | string \| null | Traits and behavior. |
| `first_message` | string \| null | Opening greeting for a new chat. |
| `alternate_greetings` | string[] \| null | Additional opening messages. |
| `example_dialogues` | string[] \| null | Example exchanges that steer the style. |
| `scenario` | string \| null | The situational framing. |
| `post_history_instructions` | string \| null | Instructions injected *after* chat history (jailbreak slot). |
| `system_prompt` | string \| null | Per-character system-prompt override (V2 spec). |
| `tags` | string[] \| null | For categorizing and filtering. |
| `gender` | enum \| null | `male` · `female` · `non-binary` · `others`. |
| `custom_gender` | string \| null | Free text when `gender` is `others`. |
| `species`, `age`, `creator` | string \| null | Card metadata. |
| `creator_notes` | string \| null | Notes for humans — **never** sent to the LLM. |
| `character_version` | string \| null | Version string from the card spec. |
| `version` | integer | Internal card version (default `1`). |
| `avatar`, `avatar_large`, `avatar_thumbnail` | string \| null | Server paths; fetch the images via the avatar endpoints. |
| `created_at`, `updated_at` | string | ISO 8601 UTC. |

**Listing** is offset-paginated (`page`, `limit`) and filterable by `name__ilike`,
`gender`, `tags__ilike`, and `created_at__ge`:

```bash
curl "http://localhost:8000/api/characters?page=1&limit=10&name__ilike=lydia"
```

**Creating** posts form fields (not JSON); the avatar is an uploaded file, and the list
fields carry the card's string encodings. Only `name` is required:

```bash
curl -X POST http://localhost:8000/api/characters \
  -F "name=Lydia" \
  -F "description=Housecarl of Whiterun, sworn to carry your burdens." \
  -F "personality=Loyal, stoic, dry-humored." \
  -F "first_message=I am sworn to carry your burdens." \
  -F "avatar=@lydia.png"
# → 201 Created, CharacterResponse
```

### Import & export

`POST /api/characters/import` takes a single `file` (`multipart/form-data`) — either a
TavernCard **PNG** (JSON embedded in a `tEXt` chunk) or a raw **JSON** card, V1 or V2 — and
creates a character from it, returning the new `CharacterResponse`. The two export
endpoints are the inverse: `/export/json` returns a TavernCard V2 JSON document, and
`/export/png` returns the avatar PNG with that same JSON embedded, so a character round-trips
through other TavernCard-compatible tools.

```bash
curl -X POST http://localhost:8000/api/characters/import -F "file=@aela.png"    # → 201
curl -OJ "http://localhost:8000/api/characters/V1StGXR8Z5jd/export/png"          # download
```

## Personas

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/personas/` | List personas (paginated, filterable). |
| `POST` | `/api/personas/` | Create a persona, with optional avatar upload. |
| `GET` | `/api/personas/{id}` | Get one persona. |
| `PUT` | `/api/personas/{id}` | Update a persona. |
| `DELETE` | `/api/personas/{id}` | Delete a persona. |
| `GET` | `/api/personas/{id}/avatar` | Serve the avatar image. |
| `GET` | `/api/personas/{id}/avatar_large` | Serve the large (≤512px) full portrait. |
| `GET` | `/api/personas/{id}/avatar_thumbnail` | Serve the thumbnail. |
| `POST` | `/api/personas/{id}/set-default` | Mark this persona the default for new chats. |

### The persona resource

`PersonaResponse`:

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | 12-char nanoid. |
| `name` | string | **Required.** Unique. |
| `description` | string \| null | The user's role/characteristics for RP context. |
| `is_default` | boolean | Whether new chats adopt this persona automatically. |
| `avatar`, `avatar_large`, `avatar_thumbnail` | string \| null | Server paths; fetch via the avatar endpoints. |
| `created_at`, `updated_at` | string | ISO 8601 UTC. |

Listing is offset-paginated and filterable by `name__ilike` and `is_default`. Create and
update are `multipart/form-data` (fields `name`, `description`, `is_default`, and an
optional `avatar` file). Setting a default is a dedicated action so exactly one persona
holds the flag:

```bash
curl -X POST http://localhost:8000/api/personas/ \
  -F "name=Dovahkiin" -F "description=The Dragonborn." -F "is_default=true"

curl -X POST http://localhost:8000/api/personas/V1StGXR8Z5jd/set-default   # → PersonaResponse
```

> **Trailing slash:** the persona collection is `/api/personas/` (with a trailing slash),
> whereas characters use `/api/characters` (without). The frontend's generated client
> handles this for you; hand-written callers should match the spec exactly.
