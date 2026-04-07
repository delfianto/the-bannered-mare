# Candlekeep Core

A headless backend for local AI roleplay sessions, inspired by [SillyTavern](https://github.com/SillyTavern/SillyTavern).

## What This Is

Candlekeep Core is a Python/FastAPI backend that handles everything an RP frontend needs:
connecting to LLM providers, managing characters, building prompts, streaming responses,
tracking world lore, and retrieving relevant context via semantic search. It exposes a
clean REST API that any frontend — web, desktop, or mobile — can consume.

This project exists because of SillyTavern. ST proved what features matter for AI roleplay
and built the de facto standard that thousands of users rely on daily. The ST developers
deserve enormous credit for creating and maintaining such a feature-rich application as an
open-source, community-driven effort. Candlekeep Core draws heavily from their design
decisions and feature set.

## What This Is Not

This is **not** a 1:1 clone of SillyTavern. The two projects are architecturally very different:

| | SillyTavern | Candlekeep Core |
|---|---|---|
| Architecture | Monolithic SPA (Express backend + jQuery frontend) | Headless backend API (FastAPI) |
| Frontend | Built-in, tightly coupled | None — bring your own |
| Data storage | Filesystem (JSON, JSONL, PNG files) | PostgreSQL with SQLAlchemy ORM + pgvector |
| Language | JavaScript (~185K LOC) | Python (~13.5K LOC) |
| Target | Complete application, ready to use | Backend engine, needs a frontend |

Features that are deliberately **not** implemented:

- **Group chats** — Extremely complex (turn strategies, multi-character prompt assembly, talkativeness weighting) with high risk of getting wrong. Single-character RP is the focus.
- **Slash command scripting** — ST has a full scripting language (STscript) for power users. Candlekeep is an API — automation happens through HTTP calls, not an embedded scripting runtime.
- **Extension/plugin system** — ST needs plugins because it's a monolith. Candlekeep's extensibility comes from the API itself — build what you need in your frontend.
- **Smooth streaming** — Character-level typing delays are a frontend concern, not a backend one.
- **File attachment processing** — Document processing (PDF, EPUB, etc.) in chat is a niche feature better handled by specialized tools. The Data Bank accepts text directly.

## Features

### Implemented

- **Multi-provider LLM support** — OpenAI, Anthropic, Google Gemini, xAI Grok, OpenRouter, Ollama, and custom endpoints. Clean adapter pattern, not a giant switch statement.
- **TavernCard V1/V2 import/export** — Full PNG metadata and JSON support. Community character cards just work.
- **World lore system** — Keyword-activated lorebooks with primary/secondary logic, 4 insertion positions, AT_DEPTH injection, priority ordering, and token budgeting.
- **RAG / semantic search** — PostgreSQL + pgvector (vchord-upgradeable) vector search over chat history and Data Bank knowledge entries. Ollama + OpenAI-compatible embedding providers.
- **Data Bank** — Three-tier knowledge base (global, character, chat scope). Write knowledge once, retrieve semantically during conversations.
- **Prompt fragment library** — Reusable instruction blocks (NSFW rules, jailbreaks, writing style) that attach to templates. Write once, compose across any number of templates.
- **Prompt pipeline** — 11-component template system with Jinja2, per-character system prompt overrides, fragment injection at 3 positions, and data-driven component ordering.
- **Configured model variants** — Same upstream model, different templates/parameters. "Safe Sonnet" and "Naughty Sonnet" as separate model entries sharing `claude-sonnet-4-5`.
- **Streaming with typed events** — SSE with structured events (start, text, reasoning, usage, done, error). Abort-on-disconnect to stop wasting tokens.
- **Message alternatives (swipes)** — Regeneration preserves old responses. Switch between alternatives via API.
- **Message editing** — Edit any message, token count automatically recalculated.
- **Named presets** — Save parameter configurations independently. 3-tier merge: model family defaults, model overrides, preset overrides.
- **Prompt caching** — Anthropic explicit caching, automatic cache tracking for OpenAI/xAI/Gemini.
- **Reasoning content** — Parse and persist thinking from Claude, DeepSeek, Gemini. Auto-extract `<think>` tags from local models that embed reasoning in output.
- **Character management** — Full CRUD with avatar upload, thumbnail generation, filtering, pagination.
- **Persona system** — User personas with per-chat binding.
- **Structured logging** — structlog with optional MongoDB audit trail.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.13+ |
| Framework | FastAPI (ASGI) |
| Database | PostgreSQL + pgvector (vchord-upgradeable) |
| ORM | SQLAlchemy 2.0 (async + sync) |
| Migrations | Alembic |
| Validation | Pydantic V2 |
| HTTP Client | httpx (async streaming) |
| Templating | Jinja2 (prompt construction) |
| Token Counting | tiktoken |
| Image Processing | Pillow (avatars, PNG metadata) |
| Logging | structlog + MongoDB audit trail |
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

## Documentation

Detailed technical documentation, SillyTavern analysis, and engineering comparisons
are in the [`docs/`](docs/) directory.

## License

[AGPL-3.0-or-later](LICENSE) — Same license as SillyTavern, as this project includes
derivative work inspired by their implementation.

## Acknowledgments

This project would not exist without [SillyTavern](https://github.com/SillyTavern/SillyTavern)
and its community. The feature design, character card ecosystem, and overall understanding
of what makes AI roleplay work all come from studying their work. Thank you.
