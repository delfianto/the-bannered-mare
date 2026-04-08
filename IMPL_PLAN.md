# Candlekeep UI — Implementation Plan

> Last updated: 2026-04-07
> Backend: `candlekeep-core` (FastAPI, PostgreSQL, 88 API endpoints)
> Frontend: `candlekeep-ui` (Vue 3.5, Nuxt UI v4, Vite 8, TypeScript 6)
> Schema: `schema.d.ts` regenerated from `../candlekeep-core/openapi.json` via `bun run api:gen`

---

## Current State Summary

**All pages are built and functional.** No more placeholders. Every route has working UI with MSW mock data and API composables. Mock data matches backend fixtures exactly. All dependencies at latest stable versions.

**Pages:** Home, Chat (SSE), Discover (filters), Creator (CRUD), Connections (6 tabs + 3 detail pages), Settings (3 tabs), Data Bank (CRUD)
**Composables:** 18 total
**MSW handlers:** 40+ endpoints

---

## Integration Status by Feature

### Legend
- [x] Implemented & integrated
- [~] Implemented but not wired to API
- [ ] Not implemented

---

### Characters

| Item | Status | Notes |
|------|--------|-------|
| Character list API mock | [x] | 20 chars with tags, gender, creator, Unsplash avatars |
| Character detail/create/update/delete mocks | [x] | Full CRUD via MSW |
| `useCharacters` + `useCharacterForm` | [x] | Page-based pagination, FormData mapping |
| Discover page | [x] | Grid/list views, search, category/sort filters |
| Home character grid | [x] | Fetches 6 latest |
| Creator page | [x] | Create/edit/delete with avatar upload |
| Character import | [ ] | `POST /api/characters/import` — not mocked |
| Character detail page | [ ] | Route exists, placeholder |

### Chats & Messages

| Item | Status | Notes |
|------|--------|-------|
| Chat CRUD mocks | [x] | GET/POST/PUT/DELETE for chats |
| Message CRUD mocks | [x] | GET/POST/PUT + SSE streaming + regenerate |
| Alternatives mocks | [x] | GET alternatives + PUT activate |
| `useChatSessions` + `useChatMessages` | [x] | Cursor pagination, SSE streaming |
| Chat page | [x] | Session list, messages, send, typing indicator |
| Home recent tales | [x] | Fetches 8 recent chats |
| **Swipe/alternatives UI** | [ ] | Mock ready, no UI component yet |
| **Message editing UI** | [ ] | Mock ready, no UI component yet |
| **Chat rename/delete UI** | [ ] | Mock ready, no UI component yet |

### Providers & Models

| Item | Status | Notes |
|------|--------|-------|
| Provider mocks | [x] | GET list/detail, PUT update, PATCH flags |
| Model mocks | [x] | GET (paginated + provider_id filter), PUT, PATCH flags, DELETE |
| Model family mocks | [x] | GET (paginated), PUT, DELETE |
| Parameter docs mock | [x] | GET /api/model-families/parameter-docs |
| Composables | [x] | useProviders, useProvider, useModels, useModel, useModelFamilies, useModelFamily |
| Connections list tabs | [x] | 3 card grids with SVG brand icons, search, provider filter |
| ProviderView (edit) | [x] | Name, base URL, enabled toggle, API key status |
| ModelView (edit) | [x] | Identity, provider selector (filtered by family), inference params editor |
| ModelFamilyView (edit) | [x] | Name, identifier, description, param schema display, delete |
| ParamInput (recursive) | [x] | Boolean/enum/slider/number/string/list/object/json types |
| ModelInferenceParams | [x] | 3 groups, override detection, docs tooltips, 2-col sliders |

### Presets

| Item | Status | Notes |
|------|--------|-------|
| Preset list mock | [x] | GET paginated, 3 seeded presets |
| Preset detail mock | [x] | GET by ID |
| `usePresets` composable | [x] | List fetch |
| Presets tab in Connections | [x] | Card grid with parameter count, default badge |
| Preset detail/edit page | [ ] | Cards clickable but no detail page yet |
| Preset CRUD mocks | [ ] | POST/PUT/DELETE not mocked |

### Prompt Templates

| Item | Status | Notes |
|------|--------|-------|
| Template list mock | [x] | GET paginated, 4 seeded templates matching backend |
| Template detail mock | [x] | GET by ID |
| `usePromptTemplates` composable | [x] | List fetch |
| Templates tab in Connections | [x] | Card grid with default badge, max_history_tokens |
| Template detail/edit page | [ ] | Cards clickable but no detail page yet |
| Template CRUD mocks | [ ] | POST/PUT/DELETE not mocked |
| Template preview | [ ] | POST .../preview not mocked |

### Prompt Fragments

| Item | Status | Notes |
|------|--------|-------|
| Fragment list mock | [x] | GET with type/global filters, 3 seeded fragments |
| Fragment detail mock | [x] | GET by ID |
| `usePromptFragments` composable | [x] | List fetch |
| Fragments tab in Connections | [x] | Card grid with type badge, global indicator |
| Fragment detail/edit page | [ ] | Cards clickable but no detail page yet |
| Fragment CRUD mocks | [ ] | POST/PUT/DELETE not mocked |

### Settings

| Item | Status | Notes |
|------|--------|-------|
| Interface tab | [x] | Dark mode, stream responses, typing indicator (localStorage) |
| Persona tab | [x] | Fetches from API, avatar/name/default badge |
| About tab | [x] | App info from constants |
| Persona CRUD | [ ] | Create/edit/delete not implemented |

### Data Bank

| Item | Status | Notes |
|------|--------|-------|
| Data Bank CRUD mocks | [x] | GET (scope filter), POST, PUT, DELETE, 5 seeded entries |
| `useDataBank` composable | [x] | Fetch/create/update/delete with scope filter |
| Data Bank page | [x] | Scope filter pills, inline create/edit form, two-click delete |
| RAG search | [ ] | POST /api/rag/search not mocked |

### Lorebooks

| Item | Status | Notes |
|------|--------|-------|
| Lorebook mocks | [ ] | Not mocked |
| Lorebook UI in Creator | [~] | Editor exists but no API calls |

### Admin & Logging

| Item | Status | Notes |
|------|--------|-------|
| Admin mocks | [ ] | Not mocked |
| Admin UI | [ ] | No page exists |

---

## Priority Tasks

### P0 — COMPLETE
### P1 — COMPLETE
### P2 — COMPLETE

### P3 — Remaining (Polish & Advanced)

**Chat enhancements:**
- Swipe/alternatives UI — browse AI response variations in message bubbles
- Message editing UI — inline edit mode
- Chat rename/delete UI — context menu in session list

**Detail/edit pages for new entities:**
- Preset detail/edit page + CRUD mocks
- Template detail/edit page + CRUD mocks (with component ordering, Jinja2 preview)
- Fragment detail/edit page + CRUD mocks

**Advanced features:**
- Lorebook API integration — wire Creator editor to API
- RAG search UI in Data Bank
- Character import flow — TavernCard PNG/JSON
- Character detail page — full profile view
- Persona CRUD — create/edit/delete with avatar upload

**Infrastructure:**
- Mobile responsive layout — drawer/bottom nav
- Admin logging UI — log queries, LLM usage stats

### Backend TODOs

- **`order_by` query param** — Models, Model Families, Characters list endpoints need server-side sorting
- **`model_family_id` filter** — Models list endpoint needs this for family-based filtering

### Frontend TODOs

- **Tailwind theme token cleanup** — `border-[var(--border)]`, `bg-[var(--card)]` etc. are arbitrary value workarounds. The `@theme inline` block in `main.css` should properly register tokens so `border-border`, `bg-card` work natively. Audit and fix so we don't need the CSS variable escape hatch.

---

## Resolved Issues

- **Type alignment** — All pages use API schema types directly
- **Schema sync** — Regenerated from backend, `bun run api:gen`
- **Vite proxy / MSW** — `VITE_USE_MOCKS=true` disables proxy
- **Avatar strategy** — Unsplash portraits, direct URLs from API response
- **Theme state** — Singleton `useTheme` composable
- **Dependency versions** — All at latest stable (Vite 8.0.7, Vue 3.5.32, TS 6.0.2, Nuxt UI 4.6.1, vue-router 5.0.4)

---

## Composables Summary (18 total)

| Composable | API Endpoint | Used By |
|-----------|-------------|---------|
| `useChatSessions` | GET /api/chats | ChatView, HomeView |
| `useChatMessages` | GET/POST /api/chats/:id/messages | ChatView |
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
| `useLibraryFilters` | (local filtering) | CharactersView |
| `useSidebar` | (localStorage) | AppSidebar |
| `useTheme` | (localStorage, singleton) | AppSidebar, InterfaceTab, App |
| `useAppToast` | (Nuxt UI toast) | All edit pages |
