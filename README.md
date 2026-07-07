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

## Keeping the API Contract in Sync

The API contract lives at the repo root as `openapi.json` — the shared interface between the two halves. The frontend's `src/api/schema.d.ts` is generated from it using a fixed relative path (`frontend/../openapi.json`). Whenever the backend's API changes:

```bash
./scripts/openapi.sh              # regenerate ./openapi.json at the repo root
cd frontend && bun run api:gen    # regenerate frontend/src/api/schema.d.ts
```

The `/sync-schema` skill in `frontend/.claude/skills/` automates this and reports drift.

## Repository History

This repo was consolidated from two previously separate repositories (`candlekeep-core` and `candlekeep-ui`) via `git subtree`, preserving both projects' full commit history — `backend/` and `frontend/` are not fresh code, they carry their entire prior history as reachable ancestors. Product branding was renamed from "Candlekeep" to "The Bannered Mare" as part of the same move; a handful of infrastructure identifiers (the Postgres database name, Mongo log database name) were deliberately left unchanged since renaming live infrastructure was out of scope.

## License

[AGPL-3.0-or-later](LICENSE) — same license as SillyTavern, as this project includes derivative work inspired by their implementation.
