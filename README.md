# Candlekeep UI

The web client for **Candlekeep** — an AI-powered platform for local Roleplay sessions using LLMs. Built as a fast, strictly typed Vue 3 SPA with a warm literary fantasy aesthetic (amber/gold, Cinzel headings, parchment tones).

Talks to [Candlekeep Core](https://github.com/delfianto/candlekeep-core), a FastAPI backend, via a typed `openapi-fetch` client.

## Tech Stack

| Layer | Choice |
|---|---|
| Framework | Vue 3.5 — `<script setup lang="ts">` Composition API |
| Toolchain | [Vite+](https://vite-plus.dev) (`vp` CLI) — Rolldown bundler, Oxc transforms, Lightning CSS |
| Package Manager | Bun |
| Language | TypeScript 6 (strict) |
| UI Library | [Nuxt UI v4](https://ui.nuxt.com) via `@nuxt/ui/vite` — **not** Nuxt.js |
| Styling | Tailwind CSS v4 with custom CSS variables |
| State | Pinia (global) + composables (feature-scoped) |
| Routing | Vue Router 5 |
| i18n | vue-i18n |
| API Client | openapi-fetch (typed against auto-generated `src/api/schema.d.ts`) |
| Mocking | MSW (Mock Service Worker) |
| Icons | Lucide via `@iconify-json/lucide` — `<UIcon name="i-lucide-*" />` |
| Lint / Format | Oxlint / Oxfmt via `vp lint` / `vp fmt` |

## Getting Started

```bash
# Install dependencies
vp install

# Start dev server (proxies /api to localhost:8000)
vp dev --host

# Start with MSW mock data (no backend required)
VITE_USE_MOCKS=true vp dev --host
```

> **`vp` on PATH:** the Vite+ installer adds `vp` to your shell profile (`~/.vite-plus/bin`). Restart your terminal after installation.

## Commands

```bash
# Development
vp dev --host                # Dev server on port 5173
vp install                   # Install deps (Bun under the hood)

# Quality gates
vp check                     # fmt + lint + type-check in one pass
vp lint                      # Lint with Oxlint
vp fmt .                     # Format with Oxfmt
bun run typecheck            # Type-check only (vue-tsc --noEmit)
bun run build                # FINAL GATE: vue-tsc -b && vp build

# Schema
bun run api:gen              # Regenerate src/api/schema.d.ts from backend openapi.json
```

`bun run build` is the authoritative quality gate — strict Vue type-check followed by the Rolldown production build.

## Project Structure

```text
src/
├── api/                    # openapi-fetch client + auto-generated schema
├── assets/                 # Tailwind entry, theme tokens, fonts, SVG icons
├── components/
│   ├── chat/               # Chat UI (MessageBubble, ParchmentInput, etc.)
│   ├── connections/        # Connections tabs + recursive ParamInput
│   ├── creator/            # Character creator form
│   ├── discover/           # Character library grid/list + filters
│   ├── layout/             # AppShell, AppSidebar
│   ├── settings/           # Settings page tabs
│   └── shared/             # Cross-feature reusable components
├── composables/            # Feature-scoped state + API fetchers (use* prefix)
├── constants/              # Static data (app info, categories, options)
├── locales/                # vue-i18n translation catalogs
├── mocks/
│   ├── handlers.ts         # 40+ MSW request handlers
│   └── data/               # Fixtures + YAML conversation scenarios
├── router/                 # Vue Router 5 route definitions
├── stores/                 # Pinia stores (settings, etc.)
├── types/                  # Hand-written TypeScript definitions
└── views/                  # Routed page components
```

## Architecture

Data flows **View → Component → Composable → API Client**. Each layer has a narrow responsibility:

- **View** (`views/`): compose components, wire composables, handle route params. No direct API calls.
- **Component** (`components/`): presentation and interaction only. No API calls or store mutations.
- **Composable** (`composables/use*.ts`): feature state, data fetching, orchestration.
- **API Client** (`api/client.ts`): the only layer that speaks HTTP.

## Mock Mode

MSW intercepts all API calls in the browser when `VITE_USE_MOCKS=true`. Fixtures in `src/mocks/data/` include 6 providers, 34 models across 19 families, 20 Elder Scrolls–themed characters, 20 chats with YAML conversation scenarios, and more.

```bash
VITE_USE_MOCKS=true vp dev --host                         # mock mode
VITE_USE_MOCKS=true VITE_DEBUG_REQUEST=true vp dev --host # + log requests
```

MSW requires `localhost` or HTTPS. For remote access: `ssh -L 5173:localhost:5173 user@host`.

## Claude Code Setup

A shared `.claude/` config is checked into the repo (permissions, hooks, skills, MCP). Personal overrides go in `.claude/settings.local.json` (gitignored). See `CLAUDE.md` for the full AI developer guide.
