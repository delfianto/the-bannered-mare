# The Bannered Mare — AI Developer Instructions (Root)

This is a monorepo with two independent halves. This file only covers what spans both — for anything specific to one side, read that side's own `AGENTS.md`/`CLAUDE.md` first.

- **`backend/`** — Python 3.14 / FastAPI / SQLAlchemy 2.0 / PostgreSQL + pgvector. Full instructions: [backend/AGENTS.md](backend/AGENTS.md).
- **`frontend/`** — Vue 3.5 / TypeScript 6 / Nuxt UI v4 / Vite+. Full instructions: [frontend/AGENTS.md](frontend/AGENTS.md).

A single `.claude/` config at the **repo root** holds the merged permissions and path-scoped hooks for both halves. **Launch Claude Code from the repo root** so it loads — Claude Code reads `.claude/settings.json` only from the launch directory, not from subdirectories (unlike `CLAUDE.md`, which is hierarchical), so a `backend/.claude` or `frontend/.claude` settings file would be inert. Each hook self-guards to files of its own half (`ruff` only touches `backend/*.py`, `vp fmt` only `frontend/*`). Each half still keeps its own `AGENTS.md`/`CLAUDE.md` instructions, and the frontend keeps its own `.claude/skills/`.

## Cross-Cutting Rules

- **Work on `main`:** Commit directly to `main` in this repo. Do not create feature branches or open PRs unless the user asks.
- **Commit Freely:** Commit each completed unit of work with a clear, conventional message.
- **Never Push Unprompted:** Do NOT run `git push` unless the user explicitly asks.
- **API contract changes:** Any change to a backend router/schema requires regenerating the root `openapi.json` (`scripts/openapi.sh`) and then `frontend/src/api/schema.d.ts` (`bun run api:gen` in `frontend/`). See the root [README.md](README.md#keeping-the-api-contract-in-sync).

## Task Runner (`justfile`)

The root [`justfile`](justfile) is the canonical entrypoint for **running** every surface. Invoke recipes from the repo root as `just <recipe>`; `just --list` prints them grouped. Prefer these over ad-hoc commands so behavior stays consistent.

| Surface | Recipe | Runs |
|---|---|---|
| **database** | `db-init` / `db-init-auto` / `db-reset` | `scripts/init-backend-db.sh` (interactive / `--auto` / `--reset`) |
| | `db-migrate` | `alembic upgrade head` |
| | `db-check` | `alembic check` — fails if models drifted from the latest migration |
| | `db-status` | `alembic current` + `heads` + `history` |
| | `db-revision "msg"` | `alembic revision --autogenerate -m "msg"` |
| | `db-backup` / `db-restore <file>` | `pg_dump` → `$STORAGE_PATH/backups/` / `pg_restore` |
| | `db-seed [path]` | `scripts/import_card.py` (default `./characters`) |
| **backend** | `be-install` / `be-reinstall` | `uv sync --extra dev` → `backend/.venv` (reinstall wipes `.venv` first) |
| | `be-dev` / `be-prod` | `scripts/start-backend.sh` (uvicorn `--reload` / 4 workers) — `:8000` |
| **frontend** | `fe-install` / `fe-reinstall` | `bun install` (reinstall wipes `node_modules` first) |
| | `fe-dev` / `fe-mock` / `fe-prod` | `bun run dev` / `dev:mock` (MSW) / `build`+`preview` — `:5173`, preview `:4173` |
| **docs** | `docs-install` / `docs-dev` | `bun install` / VitePress dev — `:5174` |
| **stop** | `status` / `be-stop` / `fe-stop` / `docs-stop` / `stop-all` | report / kill by port / kill everything + sweep strays |

Agent notes:

- **`be-dev`/`be-prod`, `fe-dev`/`fe-mock`/`fe-prod`, and `docs-dev` are long-running (foreground) servers** — they block and never return. Launch them in the background (or a separate process) and use `just status` to confirm; use `just stop-all` to tear everything down. The `*-install` recipes run to completion normally.
- **The justfile does _not_ include lint/type/test gates.** Those live in each half's own `AGENTS.md` (`ruff` / `basedpyright` / `pytest` for backend; `vp check` / `bun run build` for frontend) — run them there.
- **`db-reset` and `db-restore` are destructive**, and all `db-*` recipes read `DATABASE_URL` from `backend/.env` (which may point at a remote host). Confirm the target before running.

## Repository Structure

```text
the-bannered-mare/
├── .claude/     # Shared Claude Code config — merged permissions + path-scoped hooks
├── .mcp.json    # Shared MCP servers (nuxt-ui)
├── backend/     # FastAPI backend — own AGENTS.md, pyproject.toml
├── docs/        # VitePress documentation site (deployed to GitHub Pages)
├── frontend/    # Vue 3 SPA — own AGENTS.md, package.json, .claude/skills/
├── scripts/     # Repo-level dev tooling (init-db, start-backend, openapi, card tools)
├── justfile     # Task runner — one entrypoint for db/backend/frontend/docs (see above)
├── openapi.json # Shared API contract (generated from backend, consumed by frontend)
├── LICENSE      # AGPL-3.0-or-later, covers the whole repo
└── README.md    # Overview + quick start for both halves
```

This repo was consolidated from two previously separate repositories via `git subtree` — `backend/` and `frontend/` each carry their full prior commit history as reachable ancestors, not just a snapshot.
