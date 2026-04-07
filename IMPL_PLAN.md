# Candlekeep UI — Implementation Plan

> Last updated: 2026-04-07
> Backend: `candlekeep-core` (FastAPI, PostgreSQL, 88 API endpoints)
> Frontend: `candlekeep-ui` (Vue 3, Nuxt UI v3, Vite, TypeScript)
> Schema: `schema.d.ts` regenerated from `../candlekeep-core/openapi.json` via `bun run api:gen`

---

## Current State Summary

All main pages are **built and wired to the API** via composables + MSW mocks. The schema has been regenerated from the latest backend `openapi.json` adding message alternatives, presets, templates, fragments, lorebooks, and data bank endpoints.

**Wired pages:** Home, Chat (SSE streaming), Discover (filters), Creator (create/edit/delete), Connections (providers/models/families)
**Placeholder pages:** Settings, Data Bank, World Lore, Persona

---

## Integration Status by Feature

### Legend
- [x] Implemented & integrated
- [~] Implemented but not connected
- [ ] Not implemented

---

### Characters

| Item | Status | Notes |
|------|--------|-------|
| Character list API mock | [x] | `GET /api/characters` — 20 chars with tags, gender, creator, Unsplash avatars |
| Character detail API mock | [x] | `GET /api/characters/:id` |
| Character create API mock | [x] | `POST /api/characters` — multipart form, generates ID |
| Character update API mock | [x] | `PUT /api/characters/:id` — merges updates |
| Character delete API mock | [x] | `DELETE /api/characters/:id` — removes from DB |
| Character import API mock | [ ] | `POST /api/characters/import` — not mocked |
| `useCharacters` composable | [x] | Fetches with page-based pagination |
| `useCharacterForm` composable | [x] | save/load/delete via API, form↔API field mapping |
| Discover page UI | [x] | Wired — grid/list, search, category/sort filters |
| Home character grid | [x] | Wired — fetches 6 latest characters |
| Creator page UI | [x] | Wired — create (blank), edit (loads from API), save, delete |
| Character detail page | [ ] | Placeholder only |

### Chats & Messages

| Item | Status | Notes |
|------|--------|-------|
| Chat list API mock | [x] | `GET /api/chats` — 20 chats, cursor pagination |
| Chat create API mock | [x] | `POST /api/chats` |
| Chat detail API mock | [x] | `GET /api/chats/:chatId` |
| Chat update API mock | [x] | `PUT /api/chats/:chatId` — update title/model |
| Chat delete API mock | [x] | `DELETE /api/chats/:chatId` |
| Messages list API mock | [x] | `GET /api/chats/:chatId/messages` — 19 YAML scenarios |
| Message send (stream) mock | [x] | `POST ...?stream=true` — SSE |
| Message send (block) mock | [x] | `POST ...` — JSON |
| Message regenerate mock | [x] | `POST ...?stream=true&regenerate=true` |
| Message edit API mock | [x] | `PUT .../messages/:id` |
| Message alternatives mock | [x] | `GET .../messages/:id/alternatives` — returns 2 mock swipes |
| Activate alternative mock | [x] | `PUT .../alternatives/:id/activate` |
| `useChatSessions` composable | [x] | Wired — cursor pagination |
| `useChatMessages` composable | [x] | Wired — SSE streaming, send, regenerate |
| Chat page UI | [x] | Wired — session list, messages, send, typing indicator |
| Home recent tales | [x] | Wired — fetches 8 recent chats |
| **Swipe/alternatives UI** | [ ] | Mock ready, no UI component yet |
| **Message editing UI** | [ ] | Mock ready, no UI component yet |
| **Chat rename/delete UI** | [ ] | Mock ready, no UI component yet |

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
| `useProviders` composable | [x] | Fetches provider list |
| `useModels` composable | [x] | Fetches with pagination + search |
| `useModelFamilies` composable | [x] | Fetches with pagination |
| Connections page UI | [x] | Built — 3 tabs: Providers (cards), Models (list+search+pagination), Model Families (cards+pagination) |

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
| Template preview mock | [ ] | `POST .../preview` |
| Template fragment attach | [ ] | POST/DELETE fragment associations |
| Template management UI | [ ] | Could be a tab in Connections |

### Prompt Fragments (no UI or mocks)

| Item | Status | Notes |
|------|--------|-------|
| Fragment list mock | [ ] | `GET /api/prompt-fragments/` |
| Fragment CRUD mocks | [ ] | POST/PUT/DELETE |
| Fragment management UI | [ ] | Could be a tab in Connections |

### Presets (no UI or mocks)

| Item | Status | Notes |
|------|--------|-------|
| Preset list mock | [ ] | `GET /api/presets/` |
| Preset CRUD mocks | [ ] | POST/PUT/DELETE |
| Set default preset mock | [ ] | POST |
| Preset management UI | [ ] | Could be a tab in Connections |

### Lorebooks (no UI or mocks)

| Item | Status | Notes |
|------|--------|-------|
| Lorebook list mock | [ ] | `GET /api/lorebooks` |
| Lorebook CRUD mocks | [ ] | POST/PUT/DELETE |
| Lore entry CRUD mocks | [ ] | Nested under lorebook |
| Lorebook UI in Creator | [~] | Creator has lorebook editor but no API calls |

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

### P0 — Critical Path — COMPLETE

All done: unified types, wired Home/Chat/Discover to API, MSW proxy fix.

### P1 — High Priority — COMPLETE

All done:
6. ~~Wire Creator → API~~ — **DONE.** Create/edit/delete with FormData, field mapping, MSW handlers.
7. ~~Build Connections page~~ — **DONE.** Providers/Models/ModelFamilies tabs with composables.
8. ~~Chat CRUD mocks~~ — **DONE.** PUT/DELETE for chats.
9. ~~Message edit mock~~ — **DONE.** PUT for message content.
10. ~~Swipe/alternatives mock~~ — **DONE.** GET alternatives + PUT activate.

### P2 — Medium Priority — CURRENT

11. **Build Data Bank page** — `/memory` route. CRUD UI for global, character-scoped, and chat-scoped knowledge entries. Add MSW mocks.

12. **Build Settings page** — Interface preferences, persona management (CRUD + avatar + set default), about info. Add persona CRUD mocks.

13. **Add preset mocks + UI** — New tab in Connections. Presets define parameter overrides.

14. **Add prompt template mocks + UI** — New tab in Connections. Template CRUD with component ordering.

15. **Add prompt fragment mocks + UI** — New tab in Connections. Reusable prompt blocks.

### P3 — Lower Priority (Polish & advanced)

16. **Swipe/alternatives UI** — Mock handlers ready, need UI in chat message bubbles (left/right arrows to browse alternatives).
17. **Message editing UI** — Mock handler ready, need inline edit mode in message bubbles.
18. **Chat rename/delete UI** — Mock handlers ready, need context menu in chat session list.
19. **Add lorebook API integration** — Wire Creator's lorebook editor to API. Add MSW mocks.
20. **Add RAG integration** — Search UI in Data Bank page.
21. **Character import flow** — TavernCard PNG/JSON import.
22. **Character detail page** — Full character profile view at `/characters/:id`.
23. **Admin logging UI** — Log queries, LLM usage stats dashboard.
24. **Mobile responsive layout** — Mobile drawer/bottom nav.

---

## Resolved Issues

### Type Alignment — RESOLVED
All wired pages use API schema types directly. Creator has its own `CharacterData` type with bidirectional mapping to `CharacterResponse` via `buildFormData()` / `mapResponseToForm()`.

### Schema Sync — RESOLVED
`schema.d.ts` regenerated from `../candlekeep-core/openapi.json`. Script: `bun run api:gen`. Old local `openapi.json` removed. New schema includes `active_index`, `token_count`, `reasoning_content` on messages, plus alternatives/presets/templates/fragments/lorebooks/data-bank endpoints.

### Vite Proxy / MSW — RESOLVED
`VITE_USE_MOCKS=true` disables Vite proxy. MSW service worker requires `localhost` (not network IP). SSH tunnel for remote debugging.

### Avatar Strategy — RESOLVED
Mock data uses Unsplash face-cropped portraits. Cards use `avatar` (full), lists use `avatar_thumbnail`, fallback to `ui-avatars.com`.

---

## Architecture Notes

### Streaming Protocol
Backend SSE events: `start`, `text`, `reasoning`, `usage`, `done`, `error`.
Composable currently parses simple `{"text":"..."}` chunks — needs update for full event schema.

### Pagination
- **Cursor-based:** Chats, messages
- **Page-based:** Characters, models, model families, presets, templates, fragments

### Composables Summary
| Composable | API Endpoint | Used By |
|-----------|-------------|---------|
| `useChatSessions` | GET /api/chats | ChatView, HomeView |
| `useChatMessages` | GET/POST /api/chats/:id/messages | ChatView |
| `useCharacters` | GET /api/characters | CharactersView, HomeView |
| `useCharacterForm` | GET/POST/PUT/DELETE /api/characters | CharacterCreateView |
| `useProviders` | GET /api/providers | ProvidersTab |
| `useModels` | GET /api/models | ModelsTab |
| `useModelFamilies` | GET /api/model-families | ModelFamiliesTab |
| `useLibraryFilters` | (local filtering) | CharactersView |
| `useSidebar` | (localStorage) | AppSidebar |
| `useTheme` | (localStorage) | AppSidebar, App |
