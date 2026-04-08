# Candlekeep UI — Implementation Plan

> Last updated: 2026-04-08
> Backend: `candlekeep-core` (FastAPI, PostgreSQL, 88 API endpoints)
> Frontend: `candlekeep-ui` (Vue 3.5, Nuxt UI v4, Vite 8, TypeScript 6)
> Schema: `schema.d.ts` regenerated from `../candlekeep-core/openapi.json` via `bun run api:gen`

---

## Current State Summary

**All pages built and functional with full CRUD.** Chat has rename/delete/edit/swipe. Character library has import flow and full detail page. Data Bank has RAG semantic search. Personas have full CRUD with avatar upload and set-default. Lorebook API composable ready. All dependencies at latest stable.

**Pages:** Home, Chat (SSE + edit/swipe/rename/delete), Discover (filters + import), Character Detail (full profile), Creator (CRUD + lorebook), Connections (6 tabs + 3 detail pages), Settings (3 tabs + persona CRUD), Data Bank (CRUD + RAG search)
**Composables:** 19 total
**MSW handlers:** 55+ endpoints

---

## Integration Status by Feature

### Legend
- [x] Implemented & integrated
- [ ] Not implemented

---

### Characters

| Item | Status | Notes |
|------|--------|-------|
| Character CRUD mocks | [x] | Full CRUD via MSW |
| Character import mock | [x] | POST /api/characters/import with FormData |
| `useCharacters` + `useCharacterForm` | [x] | Page-based pagination, FormData mapping |
| Discover page | [x] | Grid/list views, search, category/sort filters, import button |
| Home character grid | [x] | Fetches 6 latest |
| Creator page | [x] | Create/edit/delete with avatar upload |
| Character detail page | [x] | Full profile: avatar, description, personality, first_message (NarrativeText), metadata, "Start Tale" button |
| Character import flow | [x] | File input → FormData upload → refresh list → toast |

### Chats & Messages

| Item | Status | Notes |
|------|--------|-------|
| Chat CRUD mocks | [x] | GET/POST/PUT/DELETE for chats |
| Message CRUD mocks | [x] | GET/POST/PUT + SSE streaming + regenerate |
| Alternatives mocks | [x] | GET alternatives + PUT activate |
| Composables | [x] | useChatSessions (+ updateChat/deleteChat), useChatMessages (+ editMessage/fetchAlts/activateAlt) |
| Chat page | [x] | Session list, messages, send, typing indicator |
| Swipe/alternatives UI | [x] | Left/right arrows on hover, lazy-load alts, counter badge |
| Message editing UI | [x] | Inline textarea + Save/Cancel for user messages |
| Chat rename/delete | [x] | 3-dot menu dropdown, inline rename, two-click delete |
| Message actions | [x] | Inline bottom-right icons (regen/copy/bookmark for AI, edit/delete for user) |

### Providers & Models

| Item | Status | Notes |
|------|--------|-------|
| Provider mocks | [x] | GET list/detail, PUT update, PATCH flags |
| Model mocks | [x] | GET (paginated + provider_id filter), PUT, PATCH flags, DELETE |
| Model family mocks | [x] | GET (paginated), PUT, DELETE |
| Composables | [x] | useProviders, useProvider, useModels, useModel, useModelFamilies, useModelFamily |
| Connections list tabs | [x] | 6 card grids with SVG brand icons, search, provider filter |
| ProviderView (edit) | [x] | Name, base URL, enabled toggle, API key status |
| ModelView (edit) | [x] | Identity, provider selector (filtered by family), inference params editor |
| ModelFamilyView (edit) | [x] | Name, identifier, description, param schema display, delete |
| ParamInput (recursive) | [x] | Boolean/enum/slider/number/string/list/object/json types |
| ModelInferenceParams | [x] | 3 groups, override detection, docs tooltips, 2-col sliders |

### Presets

| Item | Status | Notes |
|------|--------|-------|
| Preset list/detail mock | [x] | GET paginated, 3 seeded presets |
| Presets tab | [x] | Card grid with parameter count, default badge |
| Preset detail/edit page | [ ] | Cards clickable but no detail page yet |
| Preset CRUD mocks | [ ] | POST/PUT/DELETE not mocked |

### Prompt Templates

| Item | Status | Notes |
|------|--------|-------|
| Template list/detail mock | [x] | GET paginated, 4 seeded templates |
| Templates tab | [x] | Card grid with default badge |
| Template detail/edit page | [ ] | Cards clickable but no detail page yet |
| Template CRUD mocks | [ ] | POST/PUT/DELETE not mocked |

### Prompt Fragments

| Item | Status | Notes |
|------|--------|-------|
| Fragment list/detail mock | [x] | GET with filters, 3 seeded fragments |
| Fragments tab | [x] | Card grid with type badge, global indicator |
| Fragment detail/edit page | [ ] | Cards clickable but no detail page yet |
| Fragment CRUD mocks | [ ] | POST/PUT/DELETE not mocked |

### Settings & Personas

| Item | Status | Notes |
|------|--------|-------|
| Interface tab | [x] | Dark mode, stream responses, typing indicator (localStorage) |
| About tab | [x] | App info from constants |
| Persona list | [x] | Fetches from API, avatar/name/default badge |
| Persona CRUD | [x] | Inline create/edit form, avatar upload, delete, set-default |
| Persona mocks | [x] | GET list, POST create, PUT update, DELETE, POST set-default |

### Data Bank & RAG

| Item | Status | Notes |
|------|--------|-------|
| Data Bank CRUD | [x] | GET (scope filter), POST, PUT, DELETE, 5 seeded entries |
| RAG search mock | [x] | POST /api/rag/search (3 results with scores), GET /api/rag/status |
| RAG search UI | [x] | Search input + results with relevance scores in MemoryView |

### Lorebooks

| Item | Status | Notes |
|------|--------|-------|
| Lorebook mocks | [x] | 8 endpoints: CRUD for lorebooks + CRUD for entries, 2 seeded lorebooks |
| `useLorebooks` composable | [x] | Full CRUD for lorebooks and entries |
| Wire Creator editor to API | [ ] | Composable ready, Creator still uses local state |

### Admin & Logging

| Item | Status | Notes |
|------|--------|-------|
| Admin mocks | [ ] | Not mocked |
| Admin UI | [ ] | No page exists |

---

## Remaining Work

### Detail/Edit Pages (Low priority)
- Preset detail/edit page + CRUD mocks
- Template detail/edit page + CRUD mocks (component ordering, Jinja2 preview)
- Fragment detail/edit page + CRUD mocks

### Wiring
- Wire Creator lorebook editor to `useLorebooks` composable (local state → API calls)

### Infrastructure
- Mobile responsive layout — drawer/bottom nav
- Admin logging UI — log queries, LLM usage stats

### Backend TODOs
- **`order_by` query param** — Models, Model Families, Characters list endpoints need server-side sorting
- **`model_family_id` filter** — Models list endpoint needs this for family-based filtering

### Frontend TODOs
- **Tailwind theme token cleanup** — `border-[var(--border)]`, `bg-[var(--card)]` etc. are arbitrary value workarounds. Should register tokens properly so `border-border`, `bg-card` work natively.

---

## Resolved Issues

- **Type alignment** — All pages use API schema types directly
- **Schema sync** — Regenerated from backend, `bun run api:gen`
- **Vite proxy / MSW** — `VITE_USE_MOCKS=true` disables proxy
- **Avatar strategy** — Unsplash portraits, direct URLs from API response
- **Theme state** — Singleton `useTheme` composable
- **Dependencies** — All at latest stable (Vite 8.0.7, Vue 3.5.32, TS 6.0.2, Nuxt UI 4.6.1, vue-router 5.0.4)

---

## Composables Summary (19 total)

| Composable | API Endpoint | Used By |
|-----------|-------------|---------|
| `useChatSessions` | GET/PUT/DELETE /api/chats | ChatView, HomeView |
| `useChatMessages` | GET/POST/PUT /api/chats/:id/messages + alternatives | ChatView |
| `useCharacters` | GET /api/characters | CharactersView, HomeView |
| `useCharacterForm` | GET/POST/PUT/DELETE /api/characters | CharacterCreateView |
| `useProviders` | GET /api/providers | ProvidersTab, ModelsTab |
| `useProvider` | GET/PUT /api/providers/:id | ProviderView |
| `useModels` | GET /api/models (+ filters) | ModelsTab |
| `useModel` | GET/PUT/DELETE/PATCH /api/models/:id | ModelView |
| `useModelFamilies` | GET /api/model-families | ModelFamiliesTab, ModelsTab |
| `useModelFamily` | GET/PUT/DELETE /api/model-families/:id | ModelFamilyView |
| `usePresets` | GET /api/presets | PresetsTab |
| `usePromptTemplates` | GET /api/prompt-templates | TemplatesTab |
| `usePromptFragments` | GET /api/prompt-fragments | FragmentsTab |
| `useDataBank` | GET/POST/PUT/DELETE /api/data-bank | MemoryView |
| `useLorebooks` | GET/POST/PUT/DELETE /api/lorebooks + entries | (ready, not wired to Creator yet) |
| `useLibraryFilters` | (local filtering) | CharactersView |
| `useSidebar` | (localStorage) | AppSidebar |
| `useTheme` | (localStorage, singleton) | AppSidebar, InterfaceTab, App |
| `useAppToast` | (Nuxt UI toast) | All edit pages |
