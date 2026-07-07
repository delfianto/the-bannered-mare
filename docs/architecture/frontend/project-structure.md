# Project Structure

The frontend is a **Vue 3 single-page app** organized by **feature**, not by file type.
Where the backend groups code into vertical domain slices, the frontend groups it into
layers that each feature moves through: a routed **view** composes **components**, which
lean on a feature-scoped **composable** for state and data, which is the only layer that
talks to the **typed API client**. Keeping that one direction of dependency is what stops
a Vue app of this size from turning into a tangle of components that all fetch their own
data.

## 1. Directory Structure Atlas

Everything ships under `src/`:

```text
frontend/
├── src/
│   ├── api/                # Typed backend client
│   │   ├── client.ts       # openapi-fetch client + avatar-URL helpers + APIError
│   │   └── schema.d.ts     # GENERATED from the root openapi.json — never hand-edit
│   ├── assets/             # Global CSS (Tailwind v4 entry + theme tokens), fonts, provider icons
│   ├── components/         # Reusable SFCs, grouped by feature (chat/, creator/, discover/, …)
│   │   └── shared/         # Cross-feature building blocks (Modal, DataTable, SearchBar, …)
│   ├── composables/        # Feature-scoped state + data fetching (use* functions)
│   ├── constants/          # Static, non-reactive data (app info, dropdown options, placeholders)
│   ├── locales/            # vue-i18n catalogs: en, fr, de, es, pt (JSON)
│   ├── mocks/              # MSW mock harness — handlers, fixtures, YAML chat scenarios
│   ├── router/             # Vue Router 5 route table (index.ts)
│   ├── stores/             # Pinia — truly global state only (settings.ts)
│   ├── types/              # Hand-written TS types: API aliases from schema + UI-only shapes
│   ├── utils/              # Framework-agnostic helpers (pure functions)
│   ├── views/              # Routed pages (*View.vue), incl. chat/ and settings/ sub-trees
│   ├── App.vue             # Root component — wraps the app in Nuxt UI's <UApp>
│   ├── main.ts             # Entrypoint — installs Pinia, Router, i18n; boots MSW in mock mode
│   └── i18n.ts             # vue-i18n setup (locale detection + localStorage persistence)
├── package.json            # Scripts, dependencies
└── vite.config.ts          # Vite+ / Nuxt UI / Tailwind config
```

Three things are worth calling out before the layer-by-layer tour. `api/schema.d.ts` is
**generated** from the repo-root `openapi.json` and must never be edited by hand — it is
the single source of truth for every request and response shape (see
[Keeping the API contract in sync](/guide/#keeping-the-api-contract-in-sync)). The
`mocks/` tree is a complete, offline stand-in for the backend and is documented on its own
in [Mock Harness](/architecture/frontend/mock-harness). And `stores/` holds a single Pinia
store on purpose — most state is feature-scoped and lives in composables, not in a global
store.

## 2. The Layering Pattern

Every feature is built from the same four layers, and dependencies only ever point
downward. A view never calls `fetch`; a component never imports the API client; the API
client never imports a component. Data flows up as reactive state, and intent flows down
as function calls.

<Figure tag="Figure 1" title="How a feature is layered" id="fig-fe-layers">
<svg viewBox="0 0 760 470" role="img" aria-label="Frontend feature layering" style="font-family:var(--vp-font-family-base)">
  <defs>
    <marker id="tbm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-arrow)"/>
    </marker>
  </defs>
  <rect x="250" y="16" width="260" height="40" rx="10" fill="var(--tbm-dgm-surface-3)" stroke="var(--tbm-dgm-border-strong)"/>
  <text x="380" y="41" text-anchor="middle" font-size="13" font-weight="700" fill="var(--tbm-dgm-ink)">Vue Router — /chats/:id</text>
  <rect x="150" y="86" width="460" height="60" rx="10" fill="var(--tbm-dgm-frontend-soft)" stroke="var(--tbm-dgm-frontend)"/>
  <text x="380" y="111" text-anchor="middle" font-size="13" font-weight="700" fill="var(--tbm-dgm-ink)">views/ — routed page (ChatView.vue)</text>
  <text x="380" y="130" text-anchor="middle" font-size="11" fill="var(--tbm-dgm-ink-2)">reads route params · composes components · owns page layout</text>
  <rect x="150" y="172" width="460" height="60" rx="10" fill="var(--tbm-dgm-frontend-soft)" stroke="var(--tbm-dgm-frontend)"/>
  <text x="380" y="197" text-anchor="middle" font-size="13" font-weight="700" fill="var(--tbm-dgm-ink)">components/ — presentational SFCs</text>
  <text x="380" y="216" text-anchor="middle" font-size="11" fill="var(--tbm-dgm-ink-2)">props in · events out · Nuxt UI primitives · no data fetching</text>
  <rect x="150" y="258" width="460" height="60" rx="10" fill="var(--tbm-dgm-accent-soft)" stroke="var(--tbm-dgm-accent)"/>
  <text x="380" y="283" text-anchor="middle" font-size="13" font-weight="700" fill="var(--tbm-dgm-ink)">composables/ — useChatMessages()</text>
  <text x="380" y="302" text-anchor="middle" font-size="11" fill="var(--tbm-dgm-ink-2)">reactive feature state · CRUD + SSE streaming · the only caller of the client</text>
  <rect x="150" y="344" width="460" height="60" rx="10" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/>
  <text x="380" y="369" text-anchor="middle" font-size="13" font-weight="700" fill="var(--tbm-dgm-ink)">api/client.ts — typed openapi-fetch</text>
  <text x="380" y="388" text-anchor="middle" font-size="11" fill="var(--tbm-dgm-ink-2)">every call typed against schema.d.ts · returns { data, error }</text>
  <rect x="250" y="428" width="260" height="34" rx="8" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <text x="380" y="450" text-anchor="middle" font-size="12" font-weight="600" fill="var(--tbm-dgm-ink)">→ backend (HTTP · JSON · SSE)</text>
  <g stroke="var(--tbm-dgm-arrow)" stroke-width="1.6" fill="none" marker-end="url(#tbm-ah)">
    <path d="M380 56 L380 84"/>
    <path d="M380 146 L380 170"/>
    <path d="M380 232 L380 256"/>
    <path d="M380 318 L380 342"/>
    <path d="M380 404 L380 426"/>
  </g>
  <g font-size="11" fill="var(--tbm-dgm-frontend)" text-anchor="start">
    <rect x="628" y="196" width="118" height="122" rx="9" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
    <text x="640" y="218" font-weight="700" fill="var(--tbm-dgm-ink)">Pinia store</text>
    <text x="640" y="238" fill="var(--tbm-dgm-ink-2)">global state</text>
    <text x="640" y="254" fill="var(--tbm-dgm-ink-2)">only (settings)</text>
    <text x="640" y="286" font-weight="700" fill="var(--tbm-dgm-ink)">constants/</text>
    <text x="640" y="304" fill="var(--tbm-dgm-ink-2)">static data</text>
  </g>
</svg>
<template #caption>

**One direction down, reactive state back up.** A routed **view** composes
**components** and wires them to a **composable**; the composable is the only layer that
imports the **API client**, and the client is fully typed against `schema.d.ts`.
Presentational components take props and emit events — they never fetch. Truly global,
app-wide state (parameter docs, the provider list) lives in the single Pinia store off to
the side; everything else is feature-scoped in composables.

</template>
</Figure>

### Views (`views/`)

The 20 routed pages, one per top-level surface, named `*View.vue` and wired up in
[`router/index.ts`](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/router/index.ts).
A view reads route params, composes components, and manages page-level layout — it holds no
business logic and makes no API calls of its own. Two sub-trees group related pages:
`views/chat/` (the chat workspace) and `views/settings/` (app settings plus the detail and
edit pages opened from the Connections and Loadouts tables). The screens themselves are
walked through in [Main Screens](/architecture/frontend/main-screens).

### Components (`components/`)

63 single-file components, grouped into folders that mirror the app's feature areas:

| Folder | What lives there |
|--------|------------------|
| `chat/` | The conversation canvas — `MessageBubble`, `ChatHeader`, `ChatSessionList`, the typing indicator, narrative text rendering |
| `connections/` | Provider / model / family / template / preset / fragment management tabs and their inputs |
| `creator/` | The character creator — tabs, avatar upload, dialogue and tag editors, live preview |
| `discover/` | The character library — cards, list rows, filter bar, category pills, bulk actions |
| `profiles/` | Loadout ("profile") cards, forms, and the picker modal |
| `lorebooks/` | Lore entry cards and their edit form |
| `settings/` | Settings tabs (interface, persona, logs, about) and the log detail modal |
| `layout/` | App shell, navigation sidebar, page container |
| `shared/` | Cross-feature building blocks used everywhere — `Modal`, `ConfirmModal`, `DataTable`, `AppPagination`, `SearchBar`, `EmptyState`, the toast container |

Components are presentational: they receive props and emit events, build on
[Nuxt UI v4](/architecture/frontend/design-system) primitives, and defer all state and data
work to composables. The reusable ones are detailed in
[Core Components](/architecture/frontend/core-components).

### Composables (`composables/`)

28 feature-scoped `use*` functions — the heart of the app's logic. Each owns the reactive
state and the data operations for one feature and is the **only** layer permitted to import
the API client. They come in a few recognizable shapes: list/CRUD pairs (`useCharacters` +
`useCharacterForm`, `useModels` + `useModel`, `usePromptTemplates` + `usePromptTemplate`),
the chat trio (`useChatSessions`, `useChatMessages` — which also drives SSE streaming — and
`useCreateChat`), pure client-side helpers (`useLibraryFilters`), and small UI-state
singletons persisted to `localStorage` (`useTheme`, `useSidebar`, `useToast`). Every API
call goes through the typed client and returns `{ data, error }`, so error handling is
explicit at the call site. See
[Backend Connection](/architecture/frontend/backend-connection) for the client and stream
parser, and [LLM Harness](/architecture/frontend/llm-harness) for driving live inference.

### API client (`api/`)

A thin, two-file layer. `client.ts` instantiates the `openapi-fetch` client against the
`paths` type exported by `schema.d.ts`, exposes an `APIError` class, and provides small
helpers for building avatar URLs. `schema.d.ts` is generated from the repo-root
`openapi.json` — it is the contract, and regenerating it is how the frontend stays honest
about what the backend actually offers.

### Everything else

The remaining folders are supporting cast. `stores/` holds the single global Pinia store
(`settings` — parameter docs and the provider list, both lazy-loaded and cached).
`constants/` holds static, non-reactive data such as app info and dropdown options.
`types/` splits into API-type aliases (re-exported from `schema.d.ts`, never duplicated)
and UI-only shapes for form and filter state. `locales/` and `i18n.ts` cover
five languages; `assets/` holds the Tailwind entry, theme tokens, fonts, and provider
icons. Pinia, i18n, and localization are covered in
[State & Localization](/architecture/frontend/state-and-localization); the
[Design System](/architecture/frontend/design-system) covers the visual language; and the
offline [Mock Harness](/architecture/frontend/mock-harness) covers `mocks/`.
