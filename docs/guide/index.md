---
title: Getting Started
---

# Getting Started

The Bannered Mare is a self-hostable, AI-powered platform for local roleplay sessions,
inspired by [SillyTavern](https://github.com/SillyTavern/SillyTavern). It ships as a
**monorepo with two independent halves** that meet at a single, typed HTTP contract:

- a **backend** — a headless FastAPI service that owns providers, characters, prompts,
  RAG, and the streaming completion loop, and
- a **frontend** — a Vue 3 single-page app that talks to the backend exclusively through
  a generated `openapi-fetch` client.

The two never share a process or a database; the only thing between them is
`openapi.json`, the OpenAPI contract that lives at the repo root. This guide takes you
from a fresh clone to both halves running side by side. It assumes you are comfortable on
the command line but says exactly what each step does and why, so nothing is a black box.

## What you'll need

Before anything else, make sure the following are on your machine. The two halves have
almost no overlapping requirements — the backend is Python and Postgres, the frontend is
Bun — so you can set them up in either order.

| For | You need | Notes |
|-----|----------|-------|
| Backend | **Python 3.14+** | The service targets the current CPython. |
| Backend | **PostgreSQL with VectorChord** | Not plain Postgres — the `vchord` extension (VectorChord, which builds on pgvector) powers semantic search. The `tensorchord/vchord-postgres` Docker image is the easy path. |
| Frontend | **[Bun](https://bun.sh)** | The frontend's package manager and script runner. |
| Both (optional) | **[`just`](https://github.com/casey/just)** | The repo's task runner. Every command below has a raw form and a one-line `just` recipe; `just` is the recommended way to run things day to day. |

Clone the repository and launch your editor from the **repo root**, not from inside
`backend/` or `frontend/`. The shared `.claude/` configuration, the `justfile`, and the
`openapi.json` contract all live at the top level, and tooling expects to find them there.

```bash
git clone https://github.com/delfianto/the-bannered-mare.git
cd the-bannered-mare
```

## Standing up the backend

The backend is a Python/FastAPI service that handles everything a roleplay frontend needs
behind the scenes: connecting to LLM providers, managing characters, building prompts,
streaming responses, tracking world lore, and retrieving relevant context via semantic
search. It exposes a clean REST API that any client — web, desktop, or mobile — can
consume. Under the hood it is built from a focused, strictly typed stack:

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.14+ |
| Framework | FastAPI (ASGI) |
| Database | PostgreSQL + VectorChord (the `vchord` extension, on pgvector) |
| ORM | SQLAlchemy 2.0 (async + sync) |
| Migrations | Alembic |
| Validation | Pydantic V2 |
| HTTP client | httpx (async streaming) |
| Templating | Jinja2 (prompt construction) |
| Token counting | tiktoken |
| Image processing | Pillow (avatars, PNG metadata) |
| Type checking | basedpyright (strict mode) |
| Testing | pytest |

Start by installing the package with its development extras and creating your local
environment file. The `.env` is where you point the service at a database and register the
API keys for whichever providers you plan to use.

```bash
cd backend
pip install -e ".[dev]"
cp .env.example .env        # then edit DATABASE_URL and provider API keys
```

Next comes the database. The backend does **not** create or migrate schema at boot — that
is a deliberate, explicit step so a running server never silently rewrites your data. The
repo-root `scripts/init-backend-db.sh` helper bootstraps a local PostgreSQL database for
you, creating the role and enabling the `vchord` extension; skip it if you already have a
VectorChord-capable database provisioned. Once the database exists, apply the migrations
to build the schema:

```bash
../scripts/init-backend-db.sh   # provision role + db + VectorChord (skip if you have one)
alembic upgrade head            # build the schema from the migration history
```

With the schema in place, run the server. In development you want uvicorn's auto-reload so
edits take effect immediately:

```bash
uvicorn src.main:app --reload   # serves on http://localhost:8000
```

On startup the service seeds baseline data if it is missing — the built-in providers,
model families, models, and default prompt templates — so the API is usable immediately
rather than starting empty. Seeding is best-effort: a failure is logged but never aborts
startup.

::: tip Prefer the task runner
From the repo root, the same flow is three recipes: `just db-init` (provision the
database), `just db-migrate` (apply migrations), and `just be-dev` (run uvicorn with
`--reload` on `:8000`). See [Running both halves](#running-both-halves) below.
:::

Once it's up, two URLs are worth bookmarking straight away: FastAPI serves interactive API
docs at `http://localhost:8000/docs` (Swagger UI, with a "Try it out" console), and a
minimal HTML chat page at `http://localhost:8000/demo` for sanity-checking the streaming
loop without the frontend.

## Standing up the frontend

The frontend is the web client — a fast, strictly typed Vue 3 SPA with a warm literary
fantasy aesthetic (amber and gold, Cinzel headings, parchment tones). It never touches the
database or an LLM directly; it talks only to the backend, over the typed client, and
parses the server-sent event (SSE) stream that carries live completions. Its stack:

| Layer | Choice |
|-------|--------|
| Framework | Vue 3.5 — `<script setup lang="ts">` Composition API |
| Toolchain | [Vite+](https://vite-plus.dev) (`vp` CLI) — Rolldown bundler, Oxc transforms, Lightning CSS |
| Package manager | Bun |
| Language | TypeScript 6 (strict) |
| UI library | [Nuxt UI v4](https://ui.nuxt.com) via `@nuxt/ui/vite` — **not** Nuxt.js |
| Styling | Tailwind CSS v4 with custom CSS variables |
| State | Pinia (global) + composables (feature-scoped) |
| Routing | Vue Router 5 |
| i18n | vue-i18n |
| API client | openapi-fetch (typed against the generated `src/api/schema.d.ts`) |
| Mocking | MSW (Mock Service Worker) |

Installing dependencies and starting the dev server is two commands. The dev server
proxies `/api` to the backend on `localhost:8000`, so with the backend already running
from the previous section you have a working, end-to-end app:

```bash
cd frontend
bun install
bun run dev --host          # dev server on http://localhost:5173, proxying /api → :8000
```

The frontend's canonical quality gate is `bun run build` — a strict Vue type-check
(`vue-tsc -b`) followed by the Rolldown production build. `vp check` (format, lint, and
type-check in one pass) is the faster inner-loop check while you work.

### Developing without a backend

You don't actually need the backend running to work on the UI. The frontend ships an **MSW
mock harness** that intercepts every API call in the browser and answers from fixtures —
7 providers, 34 models across 19 families, 20 Elder Scrolls-themed characters, and 20
chats backed by YAML conversation scenarios. Turn it on with an environment flag:

```bash
VITE_USE_MOCKS=true bun run dev --host                          # mock mode, no backend
VITE_USE_MOCKS=true VITE_DEBUG_REQUEST=true bun run dev --host   # + log every request
```

Because MSW registers a service worker, mock mode requires `localhost` or HTTPS. For
remote access, forward the port over SSH: `ssh -L 5173:localhost:5173 user@host`. The mock
harness is described in full in
[Mock Harness](/architecture/frontend/mock-harness).

## Running both halves

Day to day, the root [`justfile`](https://github.com/delfianto/the-bannered-mare/blob/main/justfile)
is the single entrypoint for running every surface, so you don't have to remember the raw
commands or juggle working directories. Run `just` (or `just --list`) from the repo root to
see every recipe grouped by area. The ones you'll reach for most:

```bash
# database
just db-init            # provision role/db + VectorChord + migrations (interactive)
just db-migrate         # alembic upgrade head
just db-reset           # DROP and recreate the database, then re-migrate (destructive)

# servers (each is long-running — run in its own terminal)
just be-dev             # backend, uvicorn --reload            (:8000)
just fe-dev             # frontend against the real backend    (:5173)
just fe-mock            # frontend with the MSW mock harness    (:5173)
just docs-dev           # this documentation site (VitePress)  (:5174)

# lifecycle
just status             # show which dev services are running
just stop-all           # stop everything + sweep stray processes
```

A complete local setup is two terminals: `just be-dev` in one, `just fe-dev` in the other,
and the app is live at `http://localhost:5173`. The ports never
collide — backend `8000`, frontend `5173`, frontend preview `4173`, docs `5174` (the docs
site is deliberately pinned off `5173` so it can run alongside the frontend).

::: warning
`db-reset` and `db-restore` are destructive, and every `db-*` recipe reads `DATABASE_URL`
from `backend/.env` — which may point at a remote host. Confirm the target before running
them.
:::

## Keeping the API contract in sync

The two halves are only ever as compatible as `openapi.json`, the contract at the repo
root. The backend **produces** it from its routers and schemas; the frontend **consumes**
it to generate `src/api/schema.d.ts`, the types that make every API call end-to-end typed.
Whenever you change a backend router or schema, regenerate both so the frontend's types
match reality:

```bash
./scripts/openapi.sh              # regenerate ./openapi.json from the backend
cd frontend && bun run api:gen    # regenerate frontend/src/api/schema.d.ts from it
```

The `/sync-schema` skill in `frontend/.claude/skills/` automates this and reports any
drift between the two. Skipping this step is the single most common way the halves fall out
of sync — the frontend keeps compiling against stale types until something breaks at
runtime.

## Where to go next

You now have a running platform. To understand how it's built, read on:

- **[Architecture](/architecture/)** — the system map, the backend's modular-monolith and
  data model, and the frontend's structure and streaming client.
- **[API Reference](/api/)** — every endpoint the backend exposes, grouped by
  domain, with request and response shapes.
- **[LLM Providers](/providers/)** — how each provider (OpenAI, Anthropic, Google,
  OpenRouter, xAI, Ollama, LM Studio) is wired in, and their quirks.
- **[SillyTavern Study](/sillytavern/)** — the analysis of SillyTavern's internals that
  informed this project's design, and how the two compare.
