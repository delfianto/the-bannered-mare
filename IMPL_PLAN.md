# Candlekeep UI — Implementation Plan

> Last updated: 2026-04-07
> Backend: `candlekeep-core` (FastAPI, PostgreSQL, 88 API endpoints)
> Frontend: `candlekeep-ui` (Vue 3, Nuxt UI v3, Vite, TypeScript)

---

## Current State Summary

Three main pages (Home, Chat, Discover) are **wired to the API** via composables + MSW mocks. The Creator page still uses hardcoded sample data. All pages use API types (`CharacterResponse`, `ChatResponse`, `MessageResponse`) directly — no more parallel type systems for wired pages.

**Wired pages:** Home, Chat (with SSE streaming), Discover (with filters)
**Not yet wired:** Creator, Connections, Settings, Data Bank, World Lore

---

## Integration Status by Feature

### Legend
- [x] Implemented & integrated
- [~] Implemented but not connected (hardcoded data)
- [ ] Not implemented

---

### Characters

| Item | Status | Notes |
|------|--------|-------|
| Character list API mock | [x] | `GET /api/characters` — 20 chars with tags, gender, creator |
| Character detail API mock | [x] | `GET /api/characters/:id` |
| Character create API mock | [ ] | `POST /api/characters` — not mocked |
| Character update API mock | [ ] | `PUT /api/characters/:id` — not mocked |
| Character delete API mock | [ ] | `DELETE /api/characters/:id` — not mocked |
| Character import API mock | [ ] | `POST /api/characters/import` — not mocked |
| Avatar serve mock | [ ] | `GET /api/characters/:id/avatar` — not mocked (using Unsplash URLs directly) |
| `useCharacters` composable | [x] | Fetches `GET /api/characters` with page-based pagination |
| Discover page UI | [x] | **Wired to API** — grid/list views, search, category/sort filters |
| Home character grid | [x] | **Wired to API** — fetches 6 latest characters |
| Creator page UI | [~] | Built, uses `SAMPLE_CHARACTER` constant. Not wired to API |
| Character detail page | [ ] | Placeholder only |
| ~~Wire Discover → API~~ | [x] | **DONE** |
| ~~Wire Home characters → API~~ | [x] | **DONE** |
| ~~Unify character data~~ | [x] | **DONE** — all pages use `CharacterResponse` type, constants removed |
| **Wire Creator → API** | [ ] | Next: POST/PUT for create/edit |

### Chats & Messages

| Item | Status | Notes |
|------|--------|-------|
| Chat list API mock | [x] | `GET /api/chats` — 20 chats, cursor pagination |
| Chat create API mock | [x] | `POST /api/chats` |
| Chat detail API mock | [x] | `GET /api/chats/:chatId` |
| Chat update API mock | [ ] | `PUT /api/chats/:chatId` — not mocked |
| Chat delete API mock | [ ] | `DELETE /api/chats/:chatId` — not mocked |
| Messages list API mock | [x] | `GET /api/chats/:chatId/messages` — 19 YAML scenarios |
| Message send (stream) mock | [x] | `POST /api/chats/:chatId/messages?stream=true` — SSE |
| Message send (block) mock | [x] | `POST /api/chats/:chatId/messages` — JSON |
| Message regenerate mock | [x] | `POST ...?stream=true&regenerate=true` |
| Message edit API mock | [ ] | `PUT .../messages/:id` — not mocked |
| Message alternatives mock | [ ] | `GET .../messages/:id/alternatives` — not mocked |
| `useChatSessions` composable | [x] | **Wired** — fetches chat list with cursor pagination |
| `useChatMessages` composable | [x] | **Wired** — fetches messages, SSE streaming for send |
| Chat page UI | [x] | **Wired to API** — session list, messages, send, typing indicator |
| Home recent tales | [x] | **Wired to API** — fetches 8 recent chats |
| ~~Wire ChatView → composables~~ | [x] | **DONE** |
| ~~Wire Home chats → API~~ | [x] | **DONE** |
| **Swipe/alternatives UI** | [ ] | Backend supports, no UI yet |
| **Message editing UI** | [ ] | Backend supports, no UI yet |

### Providers & Models

| Item | Status | Notes |
|------|--------|-------|
| Providers list API mock | [x] | `GET /api/providers` — 6 providers |
| Provider CRUD mocks | [ ] | POST/PUT/PATCH not mocked |
| Models list API mock | [x] | `GET /api/models` — 24 models, paginated |
| Model detail API mock | [x] | `GET /api/models/:id` — joins ModelFamily |
| Model CRUD mocks | [ ] | POST/PUT/DELETE/PATCH not mocked |
| Model families list mock | [x] | `GET /api/model-families` — 20 families |
| Model family detail mock | [x] | `GET /api/model-families/:id` |
| Model family CRUD mocks | [ ] | POST/PUT/DELETE not mocked |
| Parameter docs mock | [x] | `GET /api/model-families/parameter-docs` |
| Settings page UI | [~] | Placeholder only |
| Connections page UI | [~] | Placeholder only |
| **Build Connections page** | [ ] | Models, providers, templates management UI |
| **Build Settings page** | [ ] | Interface prefs, about, persona management |

### Personas

| Item | Status | Notes |
|------|--------|-------|
| Persona list API mock | [x] | `GET /api/personas/` — 3 personas |
| Persona detail API mock | [x] | `GET /api/personas/:id` |
| Persona CRUD mocks | [ ] | POST/PUT/DELETE not mocked |
| Persona avatar mock | [ ] | Not mocked |
| Set default persona mock | [ ] | Not mocked |
| Persona page UI | [~] | Placeholder only |

### Prompt Templates (no UI or mocks)

| Item | Status | Notes |
|------|--------|-------|
| Template list mock | [ ] | `GET /api/prompt-templates/` |
| Template CRUD mocks | [ ] | POST/PUT/DELETE |
| Template preview mock | [ ] | `POST .../preview` — renders Jinja2 |
| Template fragment attach | [ ] | POST/DELETE fragment associations |
| Template management UI | [ ] | Needed in Connections page |

### Prompt Fragments (no UI or mocks)

| Item | Status | Notes |
|------|--------|-------|
| Fragment list mock | [ ] | `GET /api/prompt-fragments/` |
| Fragment CRUD mocks | [ ] | POST/PUT/DELETE |
| Fragment management UI | [ ] | Needed in Connections page |

### Presets (no UI or mocks)

| Item | Status | Notes |
|------|--------|-------|
| Preset list mock | [ ] | `GET /api/presets/` |
| Preset CRUD mocks | [ ] | POST/PUT/DELETE |
| Set default preset mock | [ ] | POST |
| Preset management UI | [ ] | Needed in Connections page |

### Lorebooks (no UI or mocks)

| Item | Status | Notes |
|------|--------|-------|
| Lorebook list mock | [ ] | `GET /api/lorebooks` |
| Lorebook CRUD mocks | [ ] | POST/PUT/DELETE |
| Lore entry CRUD mocks | [ ] | Nested under lorebook |
| Lorebook UI in Creator | [~] | Creator has basic lorebook editor but no API calls |
| **Wire Creator lorebook → API** | [ ] | |

### Data Bank & RAG (no UI or mocks)

| Item | Status | Notes |
|------|--------|-------|
| Data Bank list mock | [ ] | `GET /api/data-bank/` |
| Data Bank CRUD mocks | [ ] | POST/PUT/DELETE |
| RAG search mock | [ ] | `POST /api/rag/search` |
| RAG status mock | [ ] | `GET /api/rag/status` |
| Data Bank page UI | [ ] | Route exists (`/memory`), placeholder only |

### Admin & Logging (no UI or mocks)

| Item | Status | Notes |
|------|--------|-------|
| Error logs mock | [ ] | `GET /admin/logs/errors` |
| HTTP logs mock | [ ] | `GET /admin/logs/http` |
| LLM logs mock | [ ] | `GET /admin/logs/llm` |
| LLM stats mock | [ ] | `GET /admin/logs/llm/stats` |
| Admin UI | [ ] | No page exists |

---

## Priority Tasks (Highest → Lowest)

### P0 — Critical Path (Wire existing UI to API) — COMPLETE

All P0 items are done:
1. ~~Unify character fixture data~~ — **DONE.** All pages use `CharacterResponse` API type. Old constants (`homeData.ts`, `types/home.ts`) removed.
2. ~~Wire ChatView → composables~~ — **DONE.** Uses `useChatSessions` + `useChatMessages` with SSE streaming.
3. ~~Wire CharactersView (Discover) → API~~ — **DONE.** Uses `useCharacters` composable. Filters work with API data.
4. ~~Wire HomeView → API~~ — **DONE.** Fetches recent chats + characters from API.
5. **Add missing character API mocks** — Still needed for Creator integration.

### P1 — High Priority (Complete core features) — CURRENT

6. **Wire Creator → API** — `POST /api/characters` for create, `PUT /api/characters/:id` for edit. Add MSW mock handlers for create/update/delete. Handle multipart form upload for avatar. Map `CharacterData` type to `CharacterCreateRequest`.

7. **Build Connections page** — UI for managing providers, models, model families, presets, prompt templates, prompt fragments. This is the `/connections` route. Backend APIs exist and most list endpoints are already mocked.

8. **Add chat CRUD mocks** — Update and delete handlers for chats. Needed for session management (rename, delete from sidebar).

9. **Add message edit mock** — `PUT /api/chats/:chatId/messages/:id`. Needed for inline message editing.

10. **Add swipe/alternatives mock** — List alternatives + activate. Unique Candlekeep feature for browsing AI response variations.

### P2 — Medium Priority (New features)

11. **Build Data Bank page** — `/memory` route. CRUD UI for global, character-scoped, and chat-scoped knowledge entries.

12. **Build Settings page** — Interface preferences, persona management, about info.

13. **Add preset mocks + UI** — In Connections page.

14. **Add prompt template mocks + UI** — In Connections page.

15. **Add prompt fragment mocks + UI** — In Connections page.

### P3 — Lower Priority (Polish & advanced)

16. **Add lorebook API integration** — Wire Creator's lorebook editor to API.
17. **Add RAG integration** — Search UI in Data Bank page.
18. **Add admin logging UI** — Log queries, LLM usage stats.
19. **Character import flow** — TavernCard PNG/JSON import.
20. **Mobile responsive layout** — Mobile drawer/bottom nav.

---

## Removed / Resolved Issues

### Type Alignment — RESOLVED
All wired pages now use API schema types directly:
- `Chat` = `components["schemas"]["ChatResponse"]`
- `Message` = `components["schemas"]["MessageResponse"]`
- `Character` = `components["schemas"]["CharacterResponse"]`
- `ChatCharacterInfo` = `components["schemas"]["ChatCharacterResponse"]`

No more parallel type systems for Home, Chat, or Discover pages. Creator still has its own `CharacterData` type that will need mapping to `CharacterCreateRequest` when wired.

### Vite Proxy / MSW Conflict — RESOLVED
`VITE_USE_MOCKS=true` disables the Vite `/api` proxy so MSW service worker intercepts browser fetch calls. Without the flag, proxy forwards to `localhost:8000` for real backend.

### Avatar Strategy — RESOLVED
Mock data uses direct Unsplash URLs (face-cropped portraits). Components use `avatar` (full size) for cards, `avatar_thumbnail` for small list items, with fallback to `ui-avatars.com` initials. When connected to real backend, `getAvatarUrl()` helper generates `/api/characters/:id/avatar` endpoints.

---

## Architecture Notes

### Streaming Protocol
Backend emits typed SSE events:
```
data: {"type":"start","message_id":"abc123"}
data: {"type":"text","content":"Hello"}
data: {"type":"reasoning","content":"...thinking..."}
data: {"type":"usage","input_tokens":100,"output_tokens":50}
data: {"type":"done","finish_reason":"stop"}
```
The `useChatMessages` composable currently parses simple `{"text":"..."}` chunks. Needs update to handle the full event schema.

### Pagination
- **Cursor-based:** Chats, messages (infinite scroll)
- **Page-based:** Characters, models, model families, presets, templates, fragments

### Multi-Provider Support
Backend supports 7 provider types: OpenAI, Anthropic, Google, xAI, OpenRouter, Ollama, Custom. Each has different auth, payload format, and streaming protocol — all abstracted behind the adapter pattern.
