# Candlekeep UI — Implementation Plan

> Last updated: 2026-04-07
> Backend: `candlekeep-core` (FastAPI, PostgreSQL, 88 API endpoints)
> Frontend: `candlekeep-ui` (Vue 3, Nuxt UI v3, Vite, TypeScript)
> Schema: `schema.d.ts` regenerated from `../candlekeep-core/openapi.json` via `bun run api:gen`

---

## Current State Summary

All main pages are **built and wired to the API** via composables + MSW mocks. Mock data matches backend fixtures exactly (6 providers, 19 model families, 34 models). Connections page has full CRUD with detail/edit pages including a recursive inference parameter editor. Settings page has Interface, Persona, and About tabs.

**Wired pages:** Home, Chat (SSE streaming), Discover (filters), Creator (create/edit/delete), Connections (providers/models/families with detail pages), Settings (interface/persona/about)
**Placeholder pages:** Data Bank, World Lore

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
| Providers list API mock | [x] | `GET /api/providers` — 6 providers, SVG brand icons |
| Provider detail API mock | [x] | `GET /api/providers/:id` |
| Provider update API mock | [x] | `PUT /api/providers/:id` — merge fields |
| Provider flags API mock | [x] | `PATCH /api/providers/:id/flags` — toggle enabled |
| Models list API mock | [x] | `GET /api/models` — 34 models, paginated, provider_id filter |
| Model detail API mock | [x] | `GET /api/models/:id` — joins ModelFamily |
| Model update API mock | [x] | `PUT /api/models/:id` — merge + join family |
| Model flags API mock | [x] | `PATCH /api/models/:id/flags` — enabled, use_openrouter |
| Model delete API mock | [x] | `DELETE /api/models/:id` |
| Model families list mock | [x] | `GET /api/model-families` — 19 families, dynamic pagination |
| Model family detail mock | [x] | `GET /api/model-families/:id` |
| Model family update mock | [x] | `PUT /api/model-families/:id` — merge fields |
| Model family delete mock | [x] | `DELETE /api/model-families/:id` |
| Parameter docs mock | [x] | `GET /api/model-families/parameter-docs` |
| `useProviders` composable | [x] | Fetches provider list |
| `useProvider` composable | [x] | Single provider fetch + save |
| `useModels` composable | [x] | Pagination + search + provider_id filter |
| `useModel` composable | [x] | Single model fetch + save + delete + flags |
| `useModelFamilies` composable | [x] | Pagination |
| `useModelFamily` composable | [x] | Single family fetch + save + delete |
| Connections list tabs | [x] | 3 tabs: card grids with edit links, search, provider filter |
| ProviderView (edit) | [x] | Name, base URL, enabled toggle, API key status |
| ModelView (edit) | [x] | Identity, provider selector (filtered by family), inference params editor |
| ModelFamilyView (edit) | [x] | Name, identifier, description, param schema display, delete |
| **ParamInput** (recursive) | [x] | Handles boolean/enum/slider/number/string/list/object/json types |
| **ModelInferenceParams** | [x] | 3 groups (general/fine-tuning/advanced), override detection, docs tooltips |

### Settings

| Item | Status | Notes |
|------|--------|-------|
| Settings page UI | [x] | 3 tabs: Interface, Persona, About |
| Interface tab | [x] | Dark mode toggle, stream responses, typing indicator (localStorage) |
| Persona tab | [x] | Fetches from API, displays cards with avatar/name/default badge |
| About tab | [x] | App name, version, license, GitHub link from constants |
| Persona CRUD mocks | [ ] | POST/PUT/DELETE not mocked |
| Persona create/edit UI | [ ] | Buttons present but disabled |

### Prompt Templates (no UI or mocks)

| Item | Status | Notes |
|------|--------|-------|
| Template list mock | [ ] | `GET /api/prompt-templates/` |
| Template CRUD mocks | [ ] | POST/PUT/DELETE |
| Template preview mock | [ ] | `POST .../preview` |
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
| Preset management UI | [ ] | Could be a tab in Connections |

### Lorebooks (no UI or mocks)

| Item | Status | Notes |
|------|--------|-------|
| Lorebook list mock | [ ] | `GET /api/lorebooks` |
| Lorebook CRUD mocks | [ ] | POST/PUT/DELETE |
| Lorebook UI in Creator | [~] | Creator has lorebook editor but no API calls |

### Data Bank & RAG (no UI or mocks)

| Item | Status | Notes |
|------|--------|-------|
| Data Bank list mock | [ ] | `GET /api/data-bank/` |
| Data Bank CRUD mocks | [ ] | POST/PUT/DELETE |
| RAG search mock | [ ] | `POST /api/rag/search` |
| Data Bank page UI | [ ] | Route exists (`/memory`), placeholder only |

---

## Priority Tasks (Highest → Lowest)

### P0 — Critical Path — COMPLETE
### P1 — High Priority — COMPLETE
### P2 — Medium Priority — MOSTLY COMPLETE

Done:
- ~~Build Settings page~~ — **DONE.** Interface/Persona/About tabs.
- ~~Connections detail pages~~ — **DONE.** Provider/Model/ModelFamily edit with full inference param editor.
- ~~Mock data alignment~~ — **DONE.** 6 providers, 19 families, 34 models matching backend fixtures.

Remaining P2:
- **Build Data Bank page** — `/memory` route. CRUD UI + MSW mocks.
- **Add preset mocks + UI** — Tab in Connections.
- **Add prompt template mocks + UI** — Tab in Connections.
- **Add prompt fragment mocks + UI** — Tab in Connections.

### P3 — Lower Priority (Polish & advanced)

- **Swipe/alternatives UI** — Mock ready, need UI in chat bubbles.
- **Message editing UI** — Mock ready, need inline edit mode.
- **Chat rename/delete UI** — Mock ready, need context menu in session list.
- **Lorebook API integration** — Wire Creator editor to API.
- **Character import flow** — TavernCard PNG/JSON import.
- **Character detail page** — Full profile view.
- **Persona CRUD** — Create/edit/delete personas with avatar upload.
- **Admin logging UI** — Log queries, LLM usage stats.
- **Mobile responsive layout** — Drawer/bottom nav.

### Backend TODOs (needed for UI features)

- **`order_by` query param** — Models, Model Families, Characters list endpoints need server-side sorting. Currently no ordering in base repository.
- **`model_family_id` filter** — Models list endpoint needs this query param for family-based filtering.

---

## Resolved Issues

### Type Alignment — RESOLVED
All wired pages use API schema types directly.

### Schema Sync — RESOLVED
`schema.d.ts` regenerated from backend. Script: `bun run api:gen`. Local `openapi.json` removed.

### Vite Proxy / MSW — RESOLVED
`VITE_USE_MOCKS=true` disables Vite proxy. SSH tunnel for remote debugging.

### Avatar Strategy — RESOLVED
Mock data uses Unsplash portraits. Cards use `avatar` (full), lists use `avatar_thumbnail`.

### Theme State — RESOLVED
`useTheme` uses singleton pattern — shared across all components.

---

## Composables Summary

| Composable | API Endpoint | Used By |
|-----------|-------------|---------|
| `useChatSessions` | GET /api/chats | ChatView, HomeView |
| `useChatMessages` | GET/POST /api/chats/:id/messages | ChatView |
| `useCharacters` | GET /api/characters | CharactersView, HomeView |
| `useCharacterForm` | GET/POST/PUT/DELETE /api/characters | CharacterCreateView |
| `useProviders` | GET /api/providers | ProvidersTab, ModelsTab |
| `useProvider` | GET/PUT /api/providers/:id | ProviderView |
| `useModels` | GET /api/models (+ provider_id filter) | ModelsTab |
| `useModel` | GET/PUT/DELETE/PATCH /api/models/:id | ModelView |
| `useModelFamilies` | GET /api/model-families | ModelFamiliesTab, ModelsTab |
| `useModelFamily` | GET/PUT/DELETE /api/model-families/:id | ModelFamilyView |
| `useLibraryFilters` | (local filtering) | CharactersView |
| `useSidebar` | (localStorage) | AppSidebar |
| `useTheme` | (localStorage, singleton) | AppSidebar, InterfaceTab, App |
| `useAppToast` | (Nuxt UI toast) | All edit pages |
