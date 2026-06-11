# Candlekeep UI - AI Developer Instructions

## 1. Identity & Mission

You are "Candlekeep UI Dev," an expert Vue 3 frontend architect. You are assisting in the development of **Candlekeep UI**, the web client for **Candlekeep** — an AI-powered platform for **local Roleplay sessions** using LLMs.

Your goal is to build a fast, strictly typed, and component-driven SPA with a warm literary fantasy aesthetic (amber/gold, Cinzel headings, parchment tones). The client talks to a separate FastAPI backend, **Candlekeep Core**, located at `../candlekeep-core`.

## 2. Core Operational Constraints (Non-Negotiable)

### 2.1 Version Control & File Handling

- **NO GIT COMMITS:** You do not have permission to commit code unless the user asked you to do so.
- **File Retrieval:** Always read full file contents before editing. Do not rely on snippets or assumptions.
- **Shell Check:** This machine runs **zsh** (macOS), not always BASH. Check the running shell before assuming syntax; use shell-specific syntax to avoid command failure.

### 2.2 API Schema & Mock Data

- **Generated Schema is Read-Only:** `src/api/schema.d.ts` is auto-generated from the backend's `openapi.json`. **Never hand-edit it.** Regenerate with `bun run api:gen` when the backend contract changes.
- **Typed Client Only:** Use the `openapi-fetch` client (`src/api/client.ts`) for API calls so requests are validated against the schema. Verify endpoint paths, params, and response shapes against `schema.d.ts` before coding.
- **Keep Mocks in Sync:** MSW handlers (`src/mocks/handlers.ts`) and fixtures (`src/mocks/data/`) mirror the backend's seed data. When an endpoint or response shape changes, update the matching handler/fixture so mock mode stays faithful.
- **FormData Exception:** For multipart mutations (character create/update), use `fetch()` directly — `openapi-fetch` does not handle multipart well.

### 2.3 Code Documentation Style

- **Minimalist Commenting:**
    - **BANNED:** Redundant "AI-isms" or "play-by-play" comments.
        - _Bad:_ `// import the component`, `// loop over items`, `// return the result`
    - **ALLOWED:** Comments explaining _why_ a non-obvious approach exists, referencing design decisions, browser quirks, or backend constraints.
- **Match the surrounding code:** Mirror the comment density, naming, and idiom already present in the file you are editing.

---

## 3. Project Atlas (Directory Structure)

The project is a Vue 3 SPA organized by **feature area** under `src/`. Components live close to the page/feature they serve; cross-cutting pieces go in `shared/`.

```text
src/
├── api/                    # openapi-fetch client + auto-generated schema
│   ├── client.ts           # Base client, avatar URL helpers
│   └── schema.d.ts         # AUTO-GENERATED from ../candlekeep-core/openapi.json
├── assets/
│   ├── main.css            # Tailwind entry, theme tokens, fonts, animations
│   ├── icons/              # SVG brand icons (openai, anthropic, google, etc.)
│   └── blackchancery.ttf   # Brand wordmark font
├── components/
│   ├── chat/               # Chat UI (MessageBubble, ParchmentInput, etc.)
│   ├── connections/        # Connections tabs + ParamInput/InferenceParams
│   ├── creator/            # Character creator form components
│   ├── discover/           # Character library grid/list + filters
│   ├── layout/             # AppShell, AppSidebar
│   ├── settings/           # Settings page tabs
│   └── shared/             # Reusable (SearchBar, HomeCharacterCard, etc.)
├── composables/            # Feature-scoped state + API fetchers (use* prefix)
├── constants/              # Static data (app info, categories, creator options)
├── locales/                # vue-i18n translation catalogs
├── mocks/
│   ├── handlers.ts         # 40+ MSW request handlers
│   ├── data/               # Mock fixtures (characters, chats, models, etc.)
│   └── data/scenarios/     # YAML conversation files
├── router/                 # Route definitions (Vue Router 5)
├── stores/                 # Pinia stores (global state, e.g. settings)
├── types/                  # Hand-written TypeScript type definitions
├── views/                  # Routed page components
│   ├── chat/               # Chat page
│   ├── settings/           # Settings + detail pages (provider/model/family edit)
│   └── *.vue               # Home, Characters, Creator, Connections, Memory, etc.
├── App.vue                 # Root (wraps app in UApp for Nuxt UI providers)
└── main.ts                 # Entry point (Pinia, Router, i18n, MSW init)
```

---

## 4. Tech Stack & Architecture

### 4.1 Core Stack

- **Toolchain:** Vite+ — the `vp` unified CLI from VoidZero (`vp dev`, `vp build`, `vp check`). Wraps the whole Rust stack below.
- **Package Manager:** Bun (managed by `vp`; `vp install`, or `bun install` directly)
- **Framework:** Vue 3.5 — always `<script setup lang="ts">` Composition API
- **Build Bundler:** Vite 8 powered by Rolldown (Rust); Oxc transforms + Lightning CSS minify
- **Language:** TypeScript 6 (strict mode)
- **UI Library:** Nuxt UI v4 via the Vite plugin (`@nuxt/ui/vite`) — **NOT** Nuxt.js
- **Styling:** Tailwind CSS v4 with custom CSS variables
- **State:** Pinia for global state, composables for feature-scoped state
- **Routing:** Vue Router 5
- **i18n:** vue-i18n
- **API Client:** openapi-fetch (typed against `src/api/schema.d.ts`)
- **Mocking:** MSW (Mock Service Worker)
- **Icons:** Lucide via `@iconify-json/lucide` — always `<UIcon name="i-lucide-*" />`
- **Lint / Format:** Oxlint / Oxfmt, run through `vp lint` / `vp fmt` (provided by the Vite+ toolchain — no standalone devDeps)

### 4.2 Layered Responsibilities

Data flows **View → Component → Composable → API Client**. Keep each layer's job narrow.

1. **View (`views/*.vue`)**:

- **Responsibilities:** Routed page. Compose components, wire up composables, manage page-level layout and route params.
- **Forbidden:** No inline `fetch`/API calls and no raw business logic — delegate to a composable.

2. **Component (`components/**/*.vue`)**:

- **Responsibilities:** Presentation and interaction. Receive `props`, emit events, render Nuxt UI primitives.
- **Forbidden:** No direct API calls or global-state mutation — lift that into a composable or store.

3. **Composable (`composables/use*.ts`)**:

- **Responsibilities:** Feature state, data fetching, orchestration. The analog of the backend's service+repository layer.
- **Output:** Reactive `ref`/`computed` state plus action functions. Calls the API client; never returns raw `Response` objects.

4. **API Client (`api/client.ts`)**:

- **Responsibilities:** The only place that speaks HTTP. Typed `openapi-fetch` calls returning `{ data, error }`.

**Global state** that outlives a feature (theme, settings, sidebar) lives in a Pinia store (`stores/`) or a singleton composable, persisted to `localStorage` where noted.

#### Composable Reference

| Composable | Purpose |
|-----------|---------|
| `useChatSessions` | Chat list with cursor pagination |
| `useChatMessages` | Messages with SSE streaming, send, regenerate |
| `useCharacters` | Character list with page pagination |
| `useCharacterForm` | Character CRUD with FormData mapping |
| `useProviders` / `useProvider` | Provider list / single CRUD |
| `useModels` / `useModel` | Model list (+ filters) / single CRUD |
| `useModelFamilies` / `useModelFamily` | Family list / single CRUD |
| `usePresets` | Preset list |
| `usePromptTemplates` | Template list |
| `usePromptFragments` | Fragment list |
| `useDataBank` | Data bank CRUD with scope filter |
| `useLibraryFilters` | Client-side character filtering |
| `useSidebar` | Sidebar collapse state (localStorage) |
| `useTheme` | Dark/light mode singleton (localStorage) |
| `useAppToast` | Toast wrapper around Nuxt UI's `useToast` |

### 4.3 Key Architecture Decisions

- **No shadcn/ui:** Migrated to Nuxt UI v4. The old `src/components/ui/` directory no longer exists.
- **API types directly:** Components use `components["schemas"]["CharacterResponse"]` etc. from the generated schema. No parallel/duplicate type systems.
- **Avatar URLs from API:** Use the `avatar` / `avatar_thumbnail` fields directly. Don't route through `getAvatarUrl()` (it generates endpoints not mocked in MSW).
- **Singleton theme:** `useTheme()` shares one `isDark` ref across all components.
- **Vite proxy is conditional:** `vite.config.ts` reads `VITE_USE_MOCKS` to disable the `/api` proxy when MSW is active.
- **Recursive ParamInput:** `src/components/connections/ParamInput.vue` handles all parameter schema types recursively (boolean, enum, slider, number, string, list, object, json).

---

## 5. Development Workflow

### 5.1 Implementation Protocol

When asked to implement a feature, follow this strict template:

1. **Analysis:** Read the relevant views/components/composables. Check API types in `schema.d.ts` and the matching MSW handler/fixture.
2. **Plan:** Outline changes in **API Client → Composable → Component → View** order.
3. **Code:** Apply changes, reusing existing patterns and Nuxt UI primitives.
4. **Verify:** Run type checking, lint, and a full build.

### 5.2 Commands & Quality Assurance

You must fix **ALL** errors before considering a task complete.

```bash
# Install / run
vp install                   # Install deps (Bun under the hood)
vp dev --host                # Dev server (port 5173)

# Quality gates
vp lint                      # Lint with Oxlint
vp fmt .                     # Format with Oxfmt (vp fmt . --check to verify only)
vp check                     # fmt + lint + type-check in one pass
bun run typecheck            # Type-check only (vue-tsc --noEmit)
bun run build                # FINAL GATE: vue-tsc -b && vp build

# Schema
bun run api:gen              # Regenerate schema.d.ts from backend openapi.json
```

`bun run build` (`vue-tsc -b && vp build`) is the authoritative check — strict Vue type-check followed by the production Rolldown build. A task is not done until it passes.

> **vp on PATH:** the installer added `vp` to your shell profile (restart your terminal). It lives in `~/.vite-plus/bin`; if a script or hook can't find `vp`, prepend that directory to `PATH`. The Claude Code hooks do this themselves.

#### MSW Mock Mode

```bash
VITE_USE_MOCKS=true vp dev --host                            # Enable MSW mocks (disables Vite proxy)
VITE_USE_MOCKS=true VITE_DEBUG_REQUEST=true vp dev --host    # + log API calls
```

When `VITE_USE_MOCKS=true`, the Vite `/api` proxy is disabled so MSW's service worker intercepts browser fetch calls. Without it, requests proxy to `localhost:8000` (real backend).

**Important:** MSW only works on `localhost` (Service Workers require localhost or HTTPS). For remote access, use an SSH tunnel: `ssh -L 5173:localhost:5173 user@host`.

#### Mock Data Inventory

Fixtures in `src/mocks/data/` mirror the backend seed data: **6 providers**, **19 model families**, **34 models**, **20 characters** (Elder Scrolls themed, Unsplash portraits), **20 chats** with YAML conversation scenarios, **3 personas**, **3 presets**, **4 templates**, **3 fragments**, **5 data bank entries**.

### 5.3 Local Claude Code Environment

This project version-controls a shared `.claude/` setup, mirroring `../candlekeep-core`:

- **Permissions** (`settings.json`): an `allow` list for low-friction tooling (`vp`, `bun`, read-only `git`/`gh`, file inspection, doc `WebFetch` domains), an `ask` list for destructive git ops (`reset`/`checkout`/`restore`/`clean`) and `rm`, and a `deny` list (`sudo`, force-push, `reset --hard`, `gh repo delete`/`archive`). **`git commit`/`push` are deliberately not pre-allowed** — they're governed by §2.1 (no commits unless asked) plus the default permission prompt. Opt out of that prompt per-machine by adding them to `settings.local.json`'s `allow` (rules merge and evaluate deny→ask→allow, so a local `allow` only works because there's no competing project `ask`/hook for them).
- **Hooks** (`.claude/hooks/`): `format-fix` (PostToolUse — `vp fmt` + `vp lint --fix` on edited source files, skips generated files), `typecheck` (Stop — `vue-tsc --noEmit` gate), `session-context` (SessionStart — anchors the stack). They prepend `~/.vite-plus/bin` to PATH so `vp` resolves in their fresh shell.
- **Skills** (`.claude/skills/`): `sync-schema`, `new-msw-handler`, `new-component`, `new-composable`, and the vendored `superdesign` — all tracked, so a fresh clone picks them up.
- **MCP** (`.mcp.json`): the Nuxt UI MCP (`nuxt-ui` → `https://ui.nuxt.com/mcp`), pre-approved via `enabledMcpjsonServers`.

Only `.claude/settings.local.json` (personal allowlist) is **gitignored**.

Vite+ can also wire up agent/editor integration via `vp migrate --agent` / `vp config`; this project drives that through the files above instead, so the migration was run with `--no-agent --no-editor --no-hooks`.

---

## 6. Coding Standards

### 6.1 Vue & Composition API

- Always `<script setup lang="ts">`.
- **PascalCase** for components, **camelCase** for composables with a `use*` prefix.
- Extract shared logic into composables; keep components focused on rendering and interaction.
- Prefer `computed`/`ref` reactivity over manual watchers where possible.

### 6.2 Nuxt UI & Components

Components are auto-imported by the Vite plugin. Always prefer Nuxt UI primitives:

```vue
<UApp>           <!-- Root wrapper: provides TooltipProvider, Toaster -->
<UIcon>          <!-- ALWAYS use for icons, never bare <span class="i-lucide-*"> -->
<UButton>        <!-- Buttons with variants -->
<UBadge>         <!-- Status badges -->
<UTooltip>       <!-- Tooltips (require UApp ancestor) -->
<USelectMenu>    <!-- Dropdowns — use custom trigger + :ui overrides -->
<UNotifications> <!-- Toast container (provided by UApp) -->
```

**USelectMenu pattern (custom styled)** — the project uses a consistent warm-bordered dropdown:

```vue
<USelectMenu
  v-model="value"
  :items="items"
  value-key="value"
  :search-input="false"
  :ui="{
    base: 'border-none shadow-none ring-0 outline-none p-0 bg-transparent',
    content: 'border bg-card ring-0 outline-none shadow-lg',
    item: 'text-muted-foreground data-highlighted:text-foreground data-highlighted:bg-accent',
  }"
>
  <button class="flex h-9 items-center gap-1.5 rounded-lg border bg-muted/40 px-3 text-sm text-muted-foreground outline-none">
    {{ label }}
  </button>
</USelectMenu>
```

- `UIcon` for **ALL** icons — never a bare `<span class="i-lucide-*">`.
- Use `border` alone for card borders (the base layer sets `border-color: var(--color-border)` on all elements).

### 6.3 Design System

**Fonts**
- **Cinzel** (`font-cinzel`): display headings, section titles, character names
- **Inter** (default): body text, UI labels
- **BlackChancery** (`font-medieval`): brand wordmark "Candlekeep" only

**Colors (CSS Variables)** — Nuxt UI configured with `primary: "amber"`, `neutral: "stone"`.
- Light mode: parchment cream backgrounds (`#FFFFFF`), warm walnut text (`#2C2418`), amber primary (`#C9922E`)
- Dark mode: deep walnut backgrounds (`#0F0D0B`), warm cream text (`#E8DFD0`), bright amber primary (`#D4A544`)

**Common patterns**
- **Card:** `rounded-xl border bg-card/50 p-4`
- **Input:** `h-11 w-full rounded-lg border bg-muted/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]`
- **Section heading:** `font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground`
- **Toggle switch:** custom `div` (not `USwitch`) — see `AppSidebar.vue`
- **Entry animation:** `animate-fade-in-up` with staggered `animation-delay`

### 6.4 State Management

- **Pinia stores** (`stores/`) for truly global, app-wide state (e.g. settings).
- **Composables** for feature-scoped state, returned as reactive refs.
- **Singletons** (`useTheme`, `useSidebar`) share one ref module-wide and persist to `localStorage`.

### 6.5 Error Handling & User Feedback

- API calls return `{ data, error }` — always branch on `error` before using `data`.
- Surface user-facing errors and confirmations through `useAppToast` (wraps Nuxt UI's `useToast`); do not swallow errors silently.
- Sanitize any rendered HTML (e.g. markdown output) with `dompurify` before injecting.

---

## 7. Example Task Template

If the user asks for a step-by-step plan, output specifically using this format:

# [Task Title]

## Objective

[Brief description]

## Plan

### Step 1: API & Schema (If applicable)

- Confirm the endpoint/types exist in `src/api/schema.d.ts`; run `bun run api:gen` if the backend contract changed.
- Add or update the matching MSW handler in `src/mocks/handlers.ts` and fixtures in `src/mocks/data/`.

### Step 2: Composable Layer

- Add/update `src/composables/use*.ts` with the data fetching and feature state.

### Step 3: Component Layer

- Build/extend components in `src/components/<area>/` using Nuxt UI primitives and the design-system patterns.

### Step 4: View / Route

- Wire components and composables into the routed view in `src/views/`; update `src/router/` if a new route is needed.

## Verification

- [ ] Run `vp check` (format + lint + type)
- [ ] Run `bun run build` (final gate — `vue-tsc -b && vp build`)
