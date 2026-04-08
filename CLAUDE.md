# Candlekeep UI — Developer Guide

## Project Overview

Candlekeep is an AI-powered roleplaying platform. This is the frontend — a Vue 3 SPA with a warm literary fantasy aesthetic (amber/gold, Cinzel headings, parchment tones). The backend is a separate FastAPI project at `../candlekeep-core`.

## Tech Stack

- **Runtime**: Bun (use `bun install`, `bun run dev`, `bun run build`)
- **Framework**: Vue 3.5 with `<script setup lang="ts">` Composition API
- **Build**: Vite 8
- **Language**: TypeScript 6 (strict mode)
- **UI Library**: Nuxt UI v4 via Vite plugin (`@nuxt/ui/vite`) — NOT Nuxt.js
- **Styling**: Tailwind CSS v4 with custom CSS variables
- **State**: Pinia for global state, composables for feature-scoped state
- **Routing**: Vue Router 5
- **API Client**: openapi-fetch (typed against `src/api/schema.d.ts`)
- **Mocking**: MSW (Mock Service Worker) with 40+ handlers
- **Icons**: Lucide via `@iconify-json/lucide`, always use `<UIcon name="i-lucide-*" />`

## Commands

```bash
bun install              # Install deps
bun run dev              # Dev server (port 5173, --host enabled)
bun run build            # Type check (vue-tsc) + production build
bun run typecheck        # Type check only
bun run api:gen          # Regenerate schema.d.ts from backend openapi.json
bun run lint             # Lint with oxlint
```

### MSW Mock Mode

```bash
VITE_USE_MOCKS=true bun run dev    # Enable MSW mocks (disables Vite proxy)
VITE_USE_MOCKS=true VITE_DEBUG_REQUEST=true bun run dev  # + log API calls
```

When `VITE_USE_MOCKS=true`, the Vite `/api` proxy is disabled so MSW's service worker intercepts browser fetch calls. Without it, requests proxy to `localhost:8000` (real backend).

**Important**: MSW only works on `localhost` (Service Workers require localhost or HTTPS). For remote access, use SSH tunnel: `ssh -L 5173:localhost:5173 user@host`.

## Directory Structure

```
src/
├── api/                    # openapi-fetch client + auto-generated schema
│   ├── client.ts           # Base client, avatar URL helpers
│   └── schema.d.ts         # Auto-generated from ../candlekeep-core/openapi.json
├── assets/
│   ├── main.css            # Tailwind entry, theme tokens, fonts, animations
│   ├── icons/              # SVG brand icons (openai, anthropic, google, etc.)
│   └── blackchancery.ttf   # Brand wordmark font
├── components/
│   ├── chat/               # Chat UI (MessageBubble, ParchmentInput, etc.)
│   ├── connections/        # Connections page tabs + ParamInput/InferenceParams
│   ├── creator/            # Character creator form components
│   ├── discover/           # Character library grid/list + filters
│   ├── layout/             # AppShell, AppSidebar
│   ├── settings/           # Settings page tabs
│   └── shared/             # Reusable (SearchBar, HomeCharacterCard, etc.)
├── composables/            # 18 composables (API fetchers + local state)
├── constants/              # Static data (app info, categories, creator options)
├── mocks/
│   ├── handlers.ts         # 40+ MSW request handlers
│   ├── data/               # Mock fixtures (characters, chats, models, etc.)
│   └── data/scenarios/     # 19 YAML conversation files
├── router/                 # Route definitions
├── stores/                 # Pinia stores (settings)
├── types/                  # TypeScript type definitions
├── views/                  # Page components (routed)
│   ├── chat/               # Chat page
│   ├── settings/           # Settings + detail pages (provider/model/family edit)
│   └── *.vue               # Home, Characters, Creator, Connections, Memory, etc.
├── App.vue                 # Root (wraps in UApp for Nuxt UI providers)
└── main.ts                 # Entry point (Pinia, Router, MSW init)
```

## Nuxt UI Usage

Components are auto-imported by the Vite plugin. Always use Nuxt UI components:

```vue
<UApp>           <!-- Root wrapper: provides TooltipProvider, Toaster -->
<UIcon>          <!-- ALWAYS use for icons, never bare <span class="i-lucide-*"> -->
<UButton>        <!-- Buttons with variants -->
<UBadge>         <!-- Status badges -->
<UTooltip>       <!-- Tooltips (require UApp ancestor) -->
<USelectMenu>    <!-- Dropdowns — use custom trigger + :ui overrides -->
<UNotifications> <!-- Toast container (provided by UApp) -->
```

### USelectMenu Pattern (custom styled)

The project uses a consistent pattern for dropdowns with warm Candlekeep borders:

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

## Design System

### Fonts
- **Cinzel** (`font-cinzel`): Display headings, section titles, character names
- **Inter** (default): Body text, UI labels
- **BlackChancery** (`font-medieval`): Brand wordmark "Candlekeep" only

### Colors (CSS Variables)
Light mode: parchment cream backgrounds (#FFFFFF), warm walnut text (#2C2418), amber primary (#C9922E)
Dark mode: deep walnut backgrounds (#0F0D0B), warm cream text (#E8DFD0), bright amber primary (#D4A544)

Nuxt UI plugin configured with `primary: "amber"`, `neutral: "stone"`.

### Common Patterns

**Card**: `rounded-xl border bg-card/50 p-4`
**Input**: `h-11 w-full rounded-lg border bg-muted/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]`
**Section heading**: `font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground`
**Toggle switch**: Custom div (not USwitch) — see `AppSidebar.vue` for pattern
**Entry animation**: `animate-fade-in-up` with staggered `animation-delay`

## API & Schema

Schema is auto-generated from the backend's `openapi.json`:
```bash
bun run api:gen  # Reads ../candlekeep-core/openapi.json → src/api/schema.d.ts
```

Use the typed client for all API calls:
```typescript
import { client } from "@/api/client";
const { data, error } = await client.GET("/api/characters", {
  params: { query: { page: 1, limit: 12 } },
});
```

For mutations that need FormData (character create/update), use `fetch()` directly since openapi-fetch doesn't handle multipart well.

## Composables (18 total)

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
| `useAppToast` | Toast wrapper around Nuxt UI's useToast |

## Mock Data

Mock fixtures in `src/mocks/data/` match the backend's seed data:
- **6 providers** (OpenAI, Anthropic, Google, xAI, OpenRouter, Ollama)
- **19 model families** with full parameter schemas
- **34 models** with correct provider/family cross-references
- **20 characters** (Elder Scrolls themed) with Unsplash portraits
- **20 chats** with 19 YAML conversation scenarios
- **3 personas**, **3 presets**, **4 templates**, **3 fragments**, **5 data bank entries**

## Key Architecture Decisions

- **No shadcn/ui**: Migrated to Nuxt UI v4. The old `src/components/ui/` directory no longer exists.
- **API types directly**: Components use `components["schemas"]["CharacterResponse"]` etc. from the schema. No parallel type systems.
- **Avatar URLs from API**: Use `avatar` / `avatar_thumbnail` fields directly. Don't route through `getAvatarUrl()` (that generates endpoints not mocked in MSW).
- **Singleton theme**: `useTheme()` shares a single `isDark` ref across all components.
- **Vite proxy conditional**: `vite.config.ts` reads `VITE_USE_MOCKS` env var to disable proxy when MSW is active.
- **Recursive ParamInput**: `src/components/connections/ParamInput.vue` handles all parameter schema types recursively (boolean, enum, slider, number, string, list, object, json).

## Coding Conventions

- Always `<script setup lang="ts">`
- PascalCase for components, camelCase for composables
- `UIcon` for ALL icons — never bare `<span class="i-lucide-*">`
- `border` alone for card borders (base layer sets `border-color: var(--color-border)` on all elements)
- `font-cinzel` for display headings
- Verify build passes: `bun run build` (vue-tsc + vite build)
