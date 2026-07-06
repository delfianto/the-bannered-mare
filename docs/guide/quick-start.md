---
title: Quick Start
---

# Quick Start

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
cd backend && ./scripts/openapi.sh   # regenerate ./openapi.json at the repo root
cd ../frontend && bun run api:gen    # regenerate frontend/src/api/schema.d.ts
```

The `/sync-schema` skill in `frontend/.claude/skills/` automates this and reports drift.
