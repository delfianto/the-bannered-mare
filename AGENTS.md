# The Bannered Mare — AI Developer Instructions (Root)

This is a monorepo with two independent halves. This file only covers what spans both — for anything specific to one side, read that side's own `AGENTS.md`/`CLAUDE.md` first.

- **`backend/`** — Python 3.14 / FastAPI / SQLAlchemy 2.0 / PostgreSQL + pgvector. Full instructions: [backend/AGENTS.md](backend/AGENTS.md).
- **`frontend/`** — Vue 3.5 / TypeScript 6 / Nuxt UI v4 / Vite+. Full instructions: [frontend/AGENTS.md](frontend/AGENTS.md).

A single `.claude/` config at the **repo root** holds the merged permissions and path-scoped hooks for both halves. **Launch Claude Code from the repo root** so it loads — Claude Code reads `.claude/settings.json` only from the launch directory, not from subdirectories (unlike `CLAUDE.md`, which is hierarchical), so a `backend/.claude` or `frontend/.claude` settings file would be inert. Each hook self-guards to files of its own half (`ruff` only touches `backend/*.py`, `vp fmt` only `frontend/*`). Each half still keeps its own `AGENTS.md`/`CLAUDE.md` instructions, and the frontend keeps its own `.claude/skills/`.

## Cross-Cutting Rules

- **Work on `main`:** Commit directly to `main` in this repo. Do not create feature branches or open PRs unless the user asks.
- **Commit Freely:** Commit each completed unit of work with a clear, conventional message.
- **Never Push Unprompted:** Do NOT run `git push` unless the user explicitly asks.
- **API contract changes:** Any change to a backend router/schema requires regenerating the root `openapi.json` (`backend/scripts/openapi.sh`) and then `frontend/src/api/schema.d.ts` (`bun run api:gen` in `frontend/`). See the root [README.md](README.md#keeping-the-api-contract-in-sync).

## Repository Structure

```text
the-bannered-mare/
├── .claude/     # Shared Claude Code config — merged permissions + path-scoped hooks
├── .mcp.json    # Shared MCP servers (nuxt-ui)
├── backend/     # FastAPI backend — own AGENTS.md, pyproject.toml
├── docs/        # VitePress documentation site (deployed to GitHub Pages)
├── frontend/    # Vue 3 SPA — own AGENTS.md, package.json, .claude/skills/
├── openapi.json # Shared API contract (generated from backend, consumed by frontend)
├── LICENSE      # AGPL-3.0-or-later, covers the whole repo
└── README.md    # Overview + quick start for both halves
```

This repo was consolidated from two previously separate repositories via `git subtree` — `backend/` and `frontend/` each carry their full prior commit history as reachable ancestors, not just a snapshot.
