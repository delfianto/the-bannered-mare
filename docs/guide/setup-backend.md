---
title: Backend Setup
---

# Backend Setup

The Bannered Mare backend is a Python/FastAPI backend that handles everything an RP frontend needs:
connecting to LLM providers, managing characters, building prompts, streaming responses,
tracking world lore, and retrieving relevant context via semantic search. It exposes a
clean REST API that any frontend — web, desktop, or mobile — can consume.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.14+ |
| Framework | FastAPI (ASGI) |
| Database | PostgreSQL + VectorChord (the `vchord` extension, on pgvector) |
| ORM | SQLAlchemy 2.0 (async + sync) |
| Migrations | Alembic |
| Validation | Pydantic V2 |
| HTTP Client | httpx (async streaming) |
| Templating | Jinja2 (prompt construction) |
| Token Counting | tiktoken |
| Image Processing | Pillow (avatars, PNG metadata) |
| Logging | structlog + PostgreSQL audit trail |
| Type Checking | basedpyright (strict mode) |
| Linting | ruff |
| Testing | pytest (500+ tests) |

## Quick Start

```bash
pip install -e ".[dev]"
cp .env.example .env        # Configure database URL and API keys
./scripts/init-db.sh        # Provision the Postgres database, role, and VectorChord (vchord) extension
alembic upgrade head
uvicorn src.main:app --reload
```

The `init-db.sh` helper bootstraps a local PostgreSQL database (creating the role and enabling
the `vchord` extension — VectorChord, which pulls in pgvector); skip it if you already have a
database provisioned. It expects a VectorChord-capable Postgres, e.g. the
`tensorchord/vchord-postgres` image. `scripts/start.sh` launches the server (uvicorn, with
`--reload` in dev) for day-to-day use.
