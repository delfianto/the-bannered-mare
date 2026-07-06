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
| Database | PostgreSQL + VectorChord (vchordrq, built on pgvector) |
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
| Testing | pytest (300+ tests) |

## Quick Start

```bash
pip install -e ".[dev]"
cp .env.example .env        # Configure database URL and API keys
alembic upgrade head
uvicorn src.main:app --reload
```
