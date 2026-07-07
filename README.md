# The Bannered Mare

An AI-powered platform for local roleplay sessions, inspired by [SillyTavern](https://github.com/SillyTavern/SillyTavern). Everyone plays Skyrim, and everyone knows this place.

📖 **Documentation site:** https://delfianto.github.io/the-bannered-mare/ (source in [`docs/`](docs/))

This is a monorepo containing both halves of the application:

| Directory | What it is | Docs |
|---|---|---|
| [`backend/`](backend/) | Headless FastAPI backend — providers, characters, prompts, RAG, streaming | [backend/README.md](backend/README.md) / [backend/AGENTS.md](backend/AGENTS.md) |
| [`frontend/`](frontend/) | Vue 3 SPA web client, talks to the backend via a typed `openapi-fetch` client | [frontend/README.md](frontend/README.md) / [frontend/AGENTS.md](frontend/AGENTS.md) |

Each half keeps its own tech stack and its own `AGENTS.md`/`CLAUDE.md` with domain-specific instructions. A single `.claude/` config at the repo root holds the shared permissions and path-scoped hooks for both halves — launch Claude Code from the repo root so it loads. This root file only covers what spans both.

## Quick Start

```bash
# Backend (Terminal 1)
cd backend
pip install -e ".[dev]"
cp .env.example .env        # Configure database URL and API keys
alembic upgrade head
uvicorn src.main:app --reload

# Frontend (Terminal 2)
cd frontend
bun install
bun run dev --host           # proxies /api to localhost:8000
```

Once set up, the [`justfile`](justfile) wraps day-to-day commands for both halves — see below.

## Task Runner

A root [`justfile`](justfile) ([`just`](https://github.com/casey/just)) is the single entrypoint for every surface. Run `just` (or `just --list`) to see all recipes, grouped by area:

```bash
# database
just db-init            # provision role/db + VectorChord + migrations (interactive)
just db-migrate         # alembic upgrade head
just db-check           # validate migrations (errors if models have drifted)
just db-status          # current revision + heads + history
just db-revision "msg"  # autogenerate a migration from model changes
just db-backup          # pg_dump → storage/backups/<db>-<timestamp>.dump
just db-restore <file>  # pg_restore from a dump
just db-seed [path]     # import character cards (default: ./characters)

# backend / frontend / docs
just be-dev             # backend, uvicorn --reload            (:8000)
just be-prod            # backend, 4 workers, no reload         (:8000)
just fe-dev             # frontend against the real backend     (:5173)
just fe-mock            # frontend with the MSW mock harness     (:5173)
just fe-prod            # build + preview the production bundle  (:4173)
just docs-dev           # documentation site (VitePress)        (:5174)

# stop
just status             # show which dev services are running
just be-stop            # stop one surface (also fe-stop / docs-stop)
just stop-all           # stop everything + sweep stray processes
```

Ports: backend `8000` · frontend dev `5173` · frontend preview `4173` · docs `5174` (docs is pinned off 5173 so it can run alongside the frontend). `db-*` recipes read `DATABASE_URL` from `backend/.env`. All binary/generated files — character & persona avatars, temp uploads, and `db-backup` dumps — live under a single `STORAGE_PATH` root (default `./storage` at the repo root; set an absolute path in Docker), which is gitignored.

## Keeping the API Contract in Sync

The API contract lives at the repo root as `openapi.json` — the shared interface between the two halves. The frontend's `src/api/schema.d.ts` is generated from it using a fixed relative path (`frontend/../openapi.json`). Whenever the backend's API changes:

```bash
./scripts/openapi.sh              # regenerate ./openapi.json at the repo root
cd frontend && bun run api:gen    # regenerate frontend/src/api/schema.d.ts
```

The `/sync-schema` skill in `frontend/.claude/skills/` automates this and reports drift.

## Repository History

This repo was consolidated from two previously separate `backend` and `frontend` repositories via `git subtree`, preserving both projects' full commit history — they are not fresh code, they carry their entire prior history as reachable ancestors.

## License

[AGPL-3.0-or-later](LICENSE) — same license as SillyTavern, as this project includes derivative work inspired by their implementation.
