# The Bannered Mare (Frontend) - AI Developer Instructions

This document outlines core instructions, tech stack conventions, and workflows for AI developers working on the **Bannered Mare frontend**.

For deep architectural details, refer to the following documentation files:

- [LLM Harness Agent & Connection Management](../docs/architecture/frontend/llm-harness.md)
- [Core & Shared Components](../docs/architecture/frontend/core-components.md)
- [Design System & Aesthetics](../docs/architecture/frontend/design-system.md)
- [MSW Mock Harness & Offline Development](../docs/architecture/frontend/mock-harness.md)
- [Backend Integration & Streaming Client](../docs/architecture/frontend/backend-connection.md)
- [View Architecture & Main Screens](../docs/architecture/frontend/main-screens.md)
- [State Management & Localization](../docs/architecture/frontend/state-and-localization.md)

---

## 1. Identity & Mission

You are "Bannered Mare UI Dev," an expert Vue 3 frontend architect. You are assisting in the development of the **Bannered Mare frontend**, the web client for **The Bannered Mare** — an AI-powered platform for **local Roleplay sessions** using LLMs.

Your goal is to build a fast, strictly typed, and component-driven SPA with a warm literary fantasy aesthetic (amber/gold, Cinzel headings, parchment tones). The client talks to a separate FastAPI backend located at `../backend`.

---

## 2. Core Operational Constraints (Non-Negotiable)

### 2.1 Version Control & File Handling

- **Work on `main`:** `main` is the only long-lived branch — commit directly to it. Do not create feature branches or open PRs unless the user asks.
- **Commit Freely:** Commit each completed unit of work with a clear, conventional message.
- **Never Push Unprompted:** Do NOT run `git push` unless the user explicitly asks.
- **File Retrieval:** Always read full file contents before editing. Do not rely on snippets or assumptions.
- **Shell Check:** This machine runs **zsh** (macOS), not always BASH. Check the running shell before assuming syntax; use shell-specific syntax to avoid command failure.

### 2.2 API Schema & Mock Data

- **Generated Schema is Read-Only:** `src/api/schema.d.ts` is auto-generated from the root `openapi.json` (the backend's OpenAPI contract). **Never hand-edit it.** Regenerate with `bun run api:gen` when the backend contract changes.
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
│   └── schema.d.ts         # AUTO-GENERATED from ../openapi.json (repo root)
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
│   ├── lorebooks/          # Lore entry cards + edit form
│   ├── profiles/           # Loadout ("profile") cards, forms, picker modal, persona tab
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
├── utils/                  # Framework-agnostic helpers (avatar, download, formatLog, modelProviderFilter)
├── views/                  # Routed page components
│   ├── chat/               # Chat page
│   ├── settings/           # Settings + detail pages (provider/model/family edit)
│   └── *.vue               # Home, Characters, Creator, Connections, Memory, etc.
├── App.vue                 # Root (mounts AppShell + ToastContainer)
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
- **UI Library:** DaisyUI 5 — a CSS-only Tailwind plugin (component _classes_, no JS runtime). Interactive behavior lives in shared Vue primitives under `src/components/shared/`; three are registered globally in `main.ts` (`AppIcon`, `SelectMenu`, `AppToggle`) and the rest (e.g. `AppTooltip`) are imported per-component.
- **Styling:** Tailwind CSS v4 via `@tailwindcss/vite`; DaisyUI themes (`tbm-*`) + retained CSS variables
- **State:** Pinia for global state, composables for feature-scoped state
- **Routing:** Vue Router 5
- **i18n:** vue-i18n
- **API Client:** openapi-fetch (typed against `src/api/schema.d.ts`)
- **Mocking:** MSW (Mock Service Worker)
- **Icons:** `lucide-vue-next` via the global `<AppIcon name="i-lucide-*" />` (registry: `src/components/shared/icons.ts`)
- **Lint / Format:** **Oxlint** (`vp lint`) is the JS/Vue linter and **Oxfmt** (`vp fmt`) the formatter — both from the Vite+ toolchain. Two small, non-overlapping Tailwind-canonicalization checks sit alongside them: **`bun run lint:tailwind`** (a minimal ESLint config — `eslint-plugin-tailwindcss` only, no vue/formatting rules, so it doesn't fight Oxfmt — enforcing `no-unnecessary-arbitrary-value` for _named_ scales like `text-[0.875rem]`→`text-sm`) and **`bun run lint:canonical`** (`scripts/canonical-classes.mjs`, for _dynamic spacing_ like `h-[62px]`→`h-15.5`). CI runs all three (see `.github/workflows/frontend-ci.yml`).

### 4.2 Layered Responsibilities

Data flows **View → Component → Composable → API Client**. Keep each layer's job narrow.

1. **View (`views/*.vue`)**:
   - **Responsibilities:** Routed page. Compose components, wire up composables, manage page-level layout and route params.
   - **Forbidden:** No inline `fetch`/API calls and no raw business logic — delegate to a composable.

2. **Component (`components/**/\*.vue`)\*\*:
   - **Responsibilities:** Presentation and interaction. Receive `props`, emit events, render DaisyUI classes and the shared primitives.
   - **Forbidden:** No direct API calls or global-state mutation — lift that into a composable or store.

3. **Composable (`composables/use*.ts`)**:
   - **Responsibilities:** Feature state, data fetching, orchestration. The analog of the backend's service+repository layer.
   - **Output:** Reactive `ref`/`computed` state plus action functions. Calls the API client; never returns raw `Response` objects.

4. **API Client (`api/client.ts`)**:
   - **Responsibilities:** The only place that speaks HTTP. Typed `openapi-fetch` calls returning `{ data, error }`.

**Global state** that outlives a feature (theme, settings, sidebar) lives in a Pinia store (`stores/`) or a singleton composable, persisted to `localStorage` where noted.

#### Composable Reference

For a complete breakdown of LLM interactions, see the [LLM Harness Agent & Connection Management](../docs/architecture/frontend/llm-harness.md) documentation.

| Composable                            | Purpose                                           |
| ------------------------------------- | ------------------------------------------------- |
| `useChatSessions`                     | Chat list with cursor pagination                  |
| `useChatMessages`                     | Messages with SSE streaming, send, regenerate     |
| `useCharacters`                       | Character list with page pagination               |
| `useCharacterForm`                    | Character CRUD with FormData mapping              |
| `useProviders` / `useProvider`        | Provider list / single CRUD                       |
| `useModels` / `useModel`              | Model list (+ filters) / single CRUD              |
| `useModelFamilies` / `useModelFamily` | Family list / single CRUD                         |
| `usePresets`                          | Preset list                                       |
| `usePromptTemplates`                  | Template list                                     |
| `usePromptFragments`                  | Fragment list                                     |
| `useDataBank`                         | Data bank CRUD with scope filter                  |
| `useLibraryFilters`                   | Client-side character filtering                   |
| `useSidebar`                          | Sidebar collapse state (localStorage)             |
| `useTheme`                            | Dark/light mode singleton (localStorage)          |
| `useAppToast`                         | Self-contained toast store (via `ToastContainer`) |

### 4.3 Key Architecture Decisions

- **DaisyUI, not a component runtime:** Migrated off Nuxt UI v4 to DaisyUI 5 (a CSS-only Tailwind plugin). Behavior lives in shared Vue primitives — three globally-registered (`AppIcon`, `SelectMenu`, `AppToggle`), the rest (e.g. `AppTooltip`) imported per-component; everything else is hand-rolled Tailwind using DaisyUI's token vocabulary.
- **TypeScript 7 deferred:** the code is TS7-clean (passes native `tsgo`), and `typescript-native-bridge` can even run `vue-tsc` on TS7 incl `.vue` — but TNB is macOS-only at v0.0.0 (no Linux binary; breaks `ubuntu-latest` CI), so we stay on `typescript@6` + `vue-tsc`. Revisit when TNB ships prebuilt binaries or `vue-tsc` supports native TS7.
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
3. **Code:** Apply changes, reusing existing patterns, DaisyUI classes, and the shared primitives.
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
bun run api:gen              # Regenerate schema.d.ts from the root openapi.json
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

Fixtures in `src/mocks/data/` mirror a faithful subset of the backend seed data: **9 providers** (incl. OpenCode Zen + OpenCode Go), **24 model families**, **38 canonical models** (registries — 23 enabled + 15 disabled; several are multi-route — every Claude / GPT-5.x-thinking / Gemini-3.5 = native + OpenRouter + OpenCode Zen, and DeepSeek V4, GLM-5.x, Kimi K2.6 = OpenRouter + OpenCode Go), **20 characters** (Elder Scrolls themed, Unsplash portraits), **20 chats** with YAML conversation scenarios, **3 personas**, **3 presets**, **4 templates**, **3 fragments**, **5 data bank entries**.

### 5.3 Claude Code Environment

Claude Code config lives at the **repo root** `.claude/` — Claude Code loads `.claude/settings.json` only from the launch directory, so **launch it from the repo root** (a `frontend/.claude/settings.json` would be inert from there). Only frontend-specific **skills** remain under `frontend/.claude/skills/` (skills are discovered from subdirectories).

- **Permissions** (root `.claude/settings.json`): a merged `allow` list for both halves' tooling (`vp`, `bun`, `uv`, `ruff`, read-only `git`/`gh`, file inspection, doc `WebFetch` domains), an `ask` list for destructive git ops (`reset`/`checkout`/`restore`/`clean`) and `rm`, and a `deny` list (`sudo`, force-push, `reset --hard`, `gh repo delete`/`archive`). Per §2.1 you commit directly to `main` and never `git push` unless the user asks — a `git-push-guard` PreToolUse hook enforces the push guard. `git commit`/`push` aren't pre-allowed; add them to `.claude/settings.local.json`'s `allow` per-machine to skip the prompt (rules evaluate deny→ask→allow).
- **Hooks** (root `.claude/hooks/`, `be-`/`fe-` prefix marks the half): the frontend hooks are `fe-linter` (PostToolUse — `vp fmt` + `vp lint --fix`, scoped to `frontend/*` source, skips generated files) and `fe-typecheck` (Stop — `vue-tsc --noEmit` gate against `frontend/`); they prepend `~/.vite-plus/bin` to PATH so `vp` resolves in their fresh shell. Backend hooks (`be-linter`, `be-typecheck`) sit alongside them and self-scope to `backend/`; `git-push-guard` (PreToolUse) and `session-context` (SessionStart) are repo-wide.
- **Skills** (`frontend/.claude/skills/`): `sync-schema`, `new-msw-handler`, `new-component`, `new-composable`, and the vendored `superdesign` — all tracked, so a fresh clone picks them up.
- **MCP** (root `.mcp.json`): none configured (`mcpServers: {}`). DaisyUI docs are reachable via `WebFetch(domain:daisyui.com)`.

Only `.claude/settings.local.json` (personal allowlist) is **gitignored**.

Vite+ can also wire up agent/editor integration via `vp migrate --agent` / `vp config`; this project drives that through the files above instead, so the migration was run with `--no-agent --no-editor --no-hooks`.

---

## 6. Coding Standards

### 6.1 Vue & Composition API

- Always `<script setup lang="ts">`.
- **PascalCase** for components, **camelCase** for composables with a `use*` prefix.
- Extract shared logic into composables; keep components focused on rendering and interaction.
- Prefer `computed`/`ref` reactivity over manual watchers where possible.

### 6.2 Components & DaisyUI

The UI layer is **DaisyUI 5** — CSS-only Tailwind component classes plus a handful of shared Vue primitives in `src/components/shared/`. Three are registered globally in `main.ts` and need **no import** — `AppIcon`, `SelectMenu`, `AppToggle`:

```vue
<AppIcon name="i-lucide-*" />
<!-- ALL icons (lucide-vue-next) -->
<SelectMenu v-model="v" :items="items" value-key="value"> <button>…</button> </SelectMenu>
<!-- searchable teleported dropdown -->
<AppToggle :model-value="on" @change="…" />
<!-- switch -->
```

Other shared primitives — notably **`AppTooltip`** (a teleported hover tooltip, `<AppTooltip :text="..." side="right">…</AppTooltip>`) — are **not** global; `import` them per-component from `@/components/shared/` (see `AppSidebar.vue`, `ModelInferenceParams.vue`). `vue-tsc` won't flag a missing import for these, but the running app logs "Failed to resolve component" and the element renders broken.

For everything else, use DaisyUI **classes** (`btn`, `badge`, `toggle`, `tabs`, `card`, …) and DaisyUI's token utilities (§6.3) on hand-rolled markup.

**SelectMenu pattern** — a searchable, teleported dropdown; the default slot is the trigger button, and the listbox styling/width are handled internally (no `:ui` overrides):

```vue
<SelectMenu v-model="value" :items="items" value-key="value" :search-input="false">
  <button class="flex h-9 items-center gap-1.5 rounded-lg border bg-base-300/40 px-3 text-sm text-muted-foreground outline-none">
    {{ label }}
  </button>
</SelectMenu>
```

- `AppIcon` for **ALL** icons — never a bare `<span class="i-lucide-*">`. Add new icons to `src/components/shared/icons.ts`.
- Use `border` alone for card borders (the base layer sets `border-color: var(--color-border)` on all elements).
- **Canonical classes over arbitrary values.** Always prefer a real scale/utility class over an equivalent arbitrary value: `h-15.5` not `h-[62px]`, `w-100` not `w-[400px]`, `size-5` not `size-[18px]`, `text-sm` not `text-[0.875rem]`, `tracking-widest` not `tracking-[0.1em]`. This is not just style — sizes on the rem spacing scale participate in the app-wide **Text Size** setting (root `font-size`, see §6.4 / `useFontSize.ts`), whereas a fixed `px` arbitrary value silently **won't scale**. Enforced by `tailwindcss/no-unnecessary-arbitrary-value` (run `bun run lint:tailwind`); editors' Tailwind IntelliSense flags the same ("The class `h-[62px]` can be written as `h-15.5`", messageId `suggestCanonicalClasses`). Reserve arbitrary `[...]` for values with **no** scale equivalent — custom shadows, `vh`/`%`, non-standard letter-spacing (`tracking-[0.08em]`), one-off colors.

### 6.3 Design System

**Fonts**

- **Cinzel** (`font-cinzel`): display headings, section titles, character names
- **Inter** (default): body text, UI labels
- **BlackChancery** (`font-medieval`): brand wordmark "The Bannered Mare" only

**Colors** — DaisyUI themes `tbm-<palette>` / `tbm-<palette>-dark` (`src/assets/themes.css`), switched by `useTheme()` via the `data-theme` attribute on `<html>` (6 palettes × light/dark). Use DaisyUI token utilities: `bg-base-100/200/300` (page → raised → recessed surfaces), `text-base-content`, `bg-primary` / `text-primary-content`, `text-error`; plus the retained `text-muted-foreground`, `text-foreground` (aliased to base-content), and bare `border`. Don't reintroduce the old shadcn names (`bg-card`, `bg-muted`, `bg-accent`, `text-destructive`).

- Light mode: parchment cream backgrounds (`#FFFFFF`), warm walnut text (`#2C2418`), amber primary (`#C9922E`)
- Dark mode: deep walnut backgrounds (`#0F0D0B`), warm cream text (`#E8DFD0`), bright amber primary (`#D4A544`)

**Semantic status → tokens (not raw palette hues).** Anything that conveys _status_ (enabled/online/success, error/failure, warning/pending, info) must use the DaisyUI semantic tokens so it re-themes across all 6 palettes + Custom: `success` / `error` / `warning` / `info` (`bg-*/10 text-*` for tint-pills, `bg-*` for dots). **Never** use raw palette shades (`text-emerald-500`, `bg-red-400`, `text-amber-500`, `bg-blue-500`) for status. Raw palette hues are reserved for **non-status** meaning and are the documented exceptions: **category** colors (fragment-type badges in `FragmentsTab`, prompt-component position badges in `TemplateView`, capability badges incl. `purple` in `ModelFamilyView`), **scale/gradient** colors (relevance-score ramp in `MemoryView`), **brand** colors (provider chips in `LogsTab`/`LogDetailModal`), and the **toast** surface ramp in `ToastContainer` (a tuned light/dark shade ladder, intentionally theme-independent).

**Common patterns**

- **Card:** the `app-card` `@utility` (= `rounded-xl border bg-base-200/50 p-4`, in `main.css`); add hover / extra padding at the call site
- **Input:** `h-11 w-full rounded-lg border bg-base-300/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:focus-ring` (the focus ring is the `focus-ring` `@utility`, see `main.css`)
- **Section heading:** `font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground`
- **Toggle switch:** the shared `AppToggle` primitive (a DaisyUI `toggle`) — see `AppSidebar.vue`
- **Entry animation:** `animate-fade-in-up` with staggered `animation-delay`

### 6.4 State Management

- **Pinia stores** (`stores/`) for truly global, app-wide state (e.g. settings).
- **Composables** for feature-scoped state, returned as reactive refs.
- **Singletons** (`useTheme`, `useSidebar`) share one ref module-wide and persist to `localStorage`.

### 6.5 Error Handling & User Feedback

- API calls return `{ data, error }` — always branch on `error` before using `data`.
- Surface user-facing errors and confirmations through `useAppToast` (a self-contained toast store); do not swallow errors silently.
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

- Build/extend components in `src/components/<area>/` using DaisyUI classes, the shared primitives, and the design-system patterns.

### Step 4: View / Route

- Wire components and composables into the routed view in `src/views/`; update `src/router/` if a new route is needed.

## Verification

- [ ] Run `vp check` (format + lint + type)
- [ ] Run `bun run build` (final gate — `vue-tsc -b && vp build`)

---

## 8. Outstanding TODOs

_No outstanding TODOs. Standing rule below._

### i18n parity (keep all 5 locales in lockstep)

All five catalogs (`en`, `de`, `es`, `fr`, `pt`) are at **full key parity** (~690 keys each). When you add or rename a key, add it to **`en.json` and mirror it into the other four** in the same run — don't leave en-only keys that silently fall back to English. Preserve interpolation tokens (`{name}`, `{count}`, `{model}`, `{mode}`, `{time}`, `{envVar}`) verbatim, and keep the brand ("The Bannered Mare") and technical placeholders (URLs, snake_case identifiers, `provider/model-family`, `N/A`, `Jinja2`) untranslated. Quick parity check:

```bash
# from frontend/ — prints missing/extra per locale vs en.json (should be 0/0)
python3 -c "import json;L=lambda o,p='':set().union(*[L(v,p+k+'.') for k,v in o.items()]) if isinstance(o,dict) else {p[:-1]};e=L(json.load(open('src/locales/en.json')));[print(l,'missing',len(e-L(json.load(open(f'src/locales/{l}.json')))),'extra',len(L(json.load(open(f'src/locales/{l}.json')))-e)) for l in ['de','es','fr','pt']]"
```

---

## 9. Design Tradeoffs & Quirks (read before "improving" anything)

Same runtime as the backend (see [backend/AGENTS.md](../backend/AGENTS.md) §8): **single-user, self-hosted, local**, small-ish datasets, and **sub-10ms latency to the backend** on the same host. The only slow/unreliable dependency is the **LLM provider** calls the backend proxies — so the effort goes into the streaming/generation path, and everything else stays simple. The living decision log (rationale + commit hashes for each item below) is [FINDINGS_FE_TRACKER.md](../FINDINGS_FE_TRACKER.md). Don't undo a listed tradeoff without a reason that applies to _this_ runtime.

- **Shared lists are Pinia singletons with a fetch-once cache (FE-M2 "Option A"), not a query-cache library.** `useProviders` / `usePresets` / `usePromptTemplates` / `usePersonas` / `useProfiles` read from a cached store singleton (the `stores/listStore.ts` factory); out-of-band mutators (`usePreset`, `usePromptTemplate`, `usePresetImport`) call `store.refresh()` to invalidate. A TanStack-Query-style keyed cache was considered and rejected as machinery this app won't benefit from. **`useDataBank` is the deliberate exception** — its list is scope-parameterized (scope/chat/character), which one global singleton would clobber, so it stays per-instance on `useListCrud`.
- **`useCharacterForm` lorebook sync stays sequential + non-atomic (FE-M6, won't-do).** It writes entries one awaited round-trip at a time with no rollback. Parallelizing is pointless at sub-10ms latency, and `Promise.all` wouldn't fix atomicity anyway (that needs a backend transactional bulk endpoint — disproportionate for a rare mid-save blip). Known limitation; don't "fix" it.
- **English is the i18n source of truth; the other four locales are machine-translated to key-parity.** All five catalogs share an identical key set (§8), but de/es/fr/pt were bulk-translated, not human-reviewed. There is intentionally **no `vue-i18n/no-raw-text` lint gate** — it would need a whole ESLint/vue-parser stack (this repo lints with oxlint only) and false-positives on inline punctuation.
- **Tests characterize the risk surface, not a coverage %.** The runner _can_ mount components (FE-C1, FE-3a), but effort targets code that can silently corrupt data — SSE stream parsing, FormData mapping, pagination race guards — not blanket coverage. Corollaries: the singleton composables (`useTheme`/`useToast`/`useServerStatus`) have no test-reset seam (FE-M8) because nothing tests them yet; the FE-M2 store cache has no dedicated invalidation test (matches the existing bar).
- **Design-system patterns ship as Tailwind `@utility` classes, not wrapper components (FE-H4).** `app-card` / `input-field` / `focus-ring` are `@apply` utilities in `main.css`, not `<AppCard>`/`<AppInput>` — a drop-in class swap with zero prop/binding churn for style-only patterns. (Interactive behavior still lives in the shared Vue primitives.)
- **Optimistic UI + refetch-on-mount lean on the low-latency backend; the streaming path is where the care goes.** SSE with `AbortController`, a wired stop button, and regen-abort restore (FE-M5) exist because generation is the one slow, cancellable, failure-prone interaction — mirroring the backend's "budget goes to the provider path."
- **Planned-feature `console.log` stubs are kept, not removed (FE-L3).** Three of them mark where unbuilt features will hook in; converting them to no-ops would only hide the seam.
