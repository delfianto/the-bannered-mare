# Candlekeep UI — Implementation Plan

> Last updated: 2026-04-07
> Backend: `candlekeep-core` (FastAPI, PostgreSQL, 88 API endpoints)
> Frontend: `candlekeep-ui` (Vue 3, Nuxt UI v3, Vite, TypeScript)

---

## Current State Summary

The UI has fully designed pages (Home, Chat, Discover, Creator) built with **hardcoded constant data**. The backend has a comprehensive API with 88 endpoints. MSW mock handlers exist for ~17 endpoints with rich fixture data (20 characters, 20 chats, 19 YAML conversations, 24 models, 20 model families, 6 providers). However, **no UI page currently calls the API** — they all use inline constants from `src/constants/`.

Two composables (`useChatSessions`, `useChatMessages`) are fully implemented with real API calls but **unused** by any component.

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
| Character list API mock | [x] | `GET /api/characters` — 20 Elder Scrolls chars |
| Character detail API mock | [x] | `GET /api/characters/:id` |
| Character create API mock | [ ] | `POST /api/characters` — not mocked |
| Character update API mock | [ ] | `PUT /api/characters/:id` — not mocked |
| Character delete API mock | [ ] | `DELETE /api/characters/:id` — not mocked |
| Character import API mock | [ ] | `POST /api/characters/import` — not mocked |
| Avatar serve mock | [ ] | `GET /api/characters/:id/avatar` — not mocked |
| Avatar thumbnail mock | [ ] | `GET /api/characters/:id/avatar_thumbnail` — not mocked |
| Discover page UI | [~] | Built, uses `LIBRARY_CHARACTERS` constants (12 items) |
| Creator page UI | [~] | Built, uses `SAMPLE_CHARACTER` constant |
| Home character grid | [~] | Built, uses `DISCOVER_CHARACTERS` constants (6 items) |
| Character detail page | [ ] | Placeholder only |
| **Wire Discover → API** | [ ] | Replace constants with `GET /api/characters` |
| **Wire Creator → API** | [ ] | POST/PUT to create/edit characters |
| **Unify character data** | [ ] | Constants use different characters than MSW fixtures |

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
| Activate alternative mock | [ ] | `PUT .../alternatives/:id/activate` — not mocked |
| `useChatSessions` composable | [x] | Fully implemented, **unused** |
| `useChatMessages` composable | [x] | Fully implemented with SSE parsing, **unused** |
| Chat page UI | [~] | Built, uses `CHAT_SESSIONS`/`MOCK_MESSAGES` constants |
| Home recent tales | [~] | Built, uses `RECENT_SESSIONS` constants |
| **Wire ChatView → composables** | [ ] | Replace constants with `useChatSessions` + `useChatMessages` |
| **Wire Home → API** | [ ] | Fetch recent chats for "Continue Your Tale" section |
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
| Settings page UI | [~] | Placeholder only (old shadcn views deleted) |
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

### Prompt Templates (NEW — no UI or mocks)

| Item | Status | Notes |
|------|--------|-------|
| Template list mock | [ ] | `GET /api/prompt-templates/` |
| Template CRUD mocks | [ ] | POST/PUT/DELETE |
| Template preview mock | [ ] | `POST .../preview` — renders Jinja2 |
| Template fragment attach | [ ] | POST/DELETE fragment associations |
| Template management UI | [ ] | Needed in Connections page |

### Prompt Fragments (NEW — no UI or mocks)

| Item | Status | Notes |
|------|--------|-------|
| Fragment list mock | [ ] | `GET /api/prompt-fragments/` |
| Fragment CRUD mocks | [ ] | POST/PUT/DELETE |
| Fragment management UI | [ ] | Needed in Connections page |

### Presets (NEW — no UI or mocks)

| Item | Status | Notes |
|------|--------|-------|
| Preset list mock | [ ] | `GET /api/presets/` |
| Preset CRUD mocks | [ ] | POST/PUT/DELETE |
| Set default preset mock | [ ] | POST |
| Preset management UI | [ ] | Needed in Connections page |

### Lorebooks (NEW — no UI or mocks)

| Item | Status | Notes |
|------|--------|-------|
| Lorebook list mock | [ ] | `GET /api/lorebooks` |
| Lorebook CRUD mocks | [ ] | POST/PUT/DELETE |
| Lore entry CRUD mocks | [ ] | Nested under lorebook |
| Lorebook UI in Creator | [~] | Creator has basic lorebook editor but no API calls |
| **Wire Creator lorebook → API** | [ ] | |

### Data Bank & RAG (NEW — no UI or mocks)

| Item | Status | Notes |
|------|--------|-------|
| Data Bank list mock | [ ] | `GET /api/data-bank/` |
| Data Bank CRUD mocks | [ ] | POST/PUT/DELETE |
| RAG search mock | [ ] | `POST /api/rag/search` |
| RAG status mock | [ ] | `GET /api/rag/status` |
| Data Bank page UI | [ ] | Route exists (`/memory`), placeholder only |

### Admin & Logging (NEW — no UI or mocks)

| Item | Status | Notes |
|------|--------|-------|
| Error logs mock | [ ] | `GET /admin/logs/errors` |
| HTTP logs mock | [ ] | `GET /admin/logs/http` |
| LLM logs mock | [ ] | `GET /admin/logs/llm` |
| LLM stats mock | [ ] | `GET /admin/logs/llm/stats` |
| Admin UI | [ ] | No page exists |

---

## Priority Tasks (Highest → Lowest)

### P0 — Critical Path (Wire existing UI to API)

1. **Unify character fixture data** — Replace 3 separate character constant files (homeData, chatData, discoverData) with a single source derived from MSW mock characters. Align types with API schema (`CharacterResponse`).

2. **Wire ChatView → composables** — Replace hardcoded `MOCK_MESSAGES`/`CHAT_SESSIONS` with `useChatSessions()` + `useChatMessages()`. This enables real streaming, pagination, and message send/regenerate through MSW.

3. **Wire CharactersView (Discover) → API** — Create `useCharacters()` composable that fetches `GET /api/characters`. Replace `LIBRARY_CHARACTERS` constants. Map `CharacterResponse` → discover card props.

4. **Wire HomeView → API** — Fetch recent chats (`GET /api/chats?limit=4`) for "Continue Your Tale" and characters (`GET /api/characters?limit=6`) for "Discover Characters".

5. **Add missing character API mocks** — Create, update, delete, import handlers needed for Creator page integration.

### P1 — High Priority (Complete core features)

6. **Wire Creator → API** — `POST /api/characters` for create, `PUT /api/characters/:id` for edit. Handle multipart form upload for avatar. Map `CharacterData` type to `CharacterCreateRequest`.

7. **Build Connections page** — UI for managing providers, models, model families, presets, prompt templates, prompt fragments. This is the `/connections` route. Backend APIs exist and most list endpoints are already mocked.

8. **Add chat CRUD mocks** — Update and delete handlers for chats. Needed for session management (rename, delete from sidebar).

9. **Add message edit mock** — `PUT /api/chats/:chatId/messages/:id`. Needed for inline message editing.

10. **Add swipe/alternatives mock** — List alternatives + activate. Unique Candlekeep feature for browsing AI response variations.

### P2 — Medium Priority (New features)

11. **Build Data Bank page** — `/memory` route. CRUD UI for global, character-scoped, and chat-scoped knowledge entries. Add MSW mocks for `GET/POST/PUT/DELETE /api/data-bank/`.

12. **Build Settings page** — Interface preferences, persona management (CRUD + avatar upload + set default), about info. Add missing persona CRUD mocks.

13. **Add preset mocks + UI** — List/create/edit/delete presets. UI in Connections page. Presets define parameter overrides (temperature, top_p, etc.).

14. **Add prompt template mocks + UI** — Template CRUD with Jinja2 preview. Component ordering editor. Fragment attachment. UI in Connections page.

15. **Add prompt fragment mocks + UI** — Fragment CRUD. Types: system, nsfw, jailbreak, instruction, context. UI in Connections page.

### P3 — Lower Priority (Polish & advanced)

16. **Add lorebook API integration** — Wire Creator's lorebook editor to `POST/PUT/DELETE /api/lorebooks` and lore entries. Add MSW mocks.

17. **Add RAG integration** — Mock `POST /api/rag/search` and `GET /api/rag/status`. UI for manual search in Data Bank page.

18. **Add admin logging UI** — Query error/HTTP/LLM logs. LLM usage stats dashboard.

19. **Character import flow** — `POST /api/characters/import` with PNG/JSON TavernCard support. UI in Discover page.

20. **Mobile responsive layout** — Current sidebar is desktop-only (`hidden lg:flex`). Need mobile drawer/bottom nav.

---

## Type Alignment Issues

| UI Type | API Schema Type | Mismatches |
|---------|----------------|------------|
| `Character` (home.ts) | `CharacterResponse` | UI has `imageUrl`, API has `avatar`/`avatar_thumbnail`. UI has `chatCount`/`creator`, API doesn't. |
| `LibraryCharacter` (discover.ts) | `CharacterResponse` | UI adds `source`, `lastUsed`, `sessionCount`, `createdAt` — not in API. |
| `ChatMessage` (chat.ts) | `MessageResponse` | UI has `sender` ("user"/"character"), API has `role` ("user"/"assistant"/"system"). UI has `characterName`/`characterAvatar`, API doesn't (must join from chat→character). |
| `ChatSession` (chat.ts) | `ChatResponse` | UI has `character` (full obj), `sessionTitle`, `unread`. API has `character` (id+name+avatar only), `title`, no `unread`. |
| `CharacterData` (creator.ts) | `CharacterCreateRequest` | UI has `greeting` → API `first_message`. UI has `responseStyle` → no API field. UI tags/lorebook structure differs. |

**Resolution approach:** Create adapter functions in `src/api/adapters.ts` that map API responses to UI types, keeping both layers clean.

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

### Avatar URLs
Characters and personas serve avatars via dedicated endpoints:
- `GET /api/characters/:id/avatar` — full image
- `GET /api/characters/:id/avatar_thumbnail` — thumbnail
- `getAvatarUrl()` / `getPersonaAvatarUrl()` helpers exist in `src/api/client.ts`

### Multi-Provider Support
Backend supports 7 provider types: OpenAI, Anthropic, Google, xAI, OpenRouter, Ollama, Custom. Each has different auth, payload format, and streaming protocol — all abstracted behind the adapter pattern.
