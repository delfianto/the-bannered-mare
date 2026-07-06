# Candlekeep Core: Project Context & Guidelines

## Project Overview
Candlekeep Core is a high-performance FastAPI backend designed for a roleplay (RP) platform. It manages character cards (NPCs), user personas, chat sessions, and multi-provider LLM integrations.

### Core Technologies
- **Framework:** FastAPI (Python 3.14)
- **Database:** PostgreSQL (Production) / SQLite (Testing)
- **ORM:** SQLAlchemy 2.0 (Declarative Mapping, Repository Pattern)
- **Migrations:** Alembic
- **Validation:** Pydantic v2
- **Logging:** Structured logging with `structlog`, audit logging in PostgreSQL
- **Templates:** Jinja2 for prompt construction
- **Image Processing:** Pillow (for avatar resizing and thumbnail generation)

## Architecture & Design Patterns
- **Repository Pattern:** Each domain (Character, Chat, Model, etc.) has a dedicated repository (`src/<domain>/repository.py`) extending `BaseRepository`.
- **Service Layer:** Business logic is encapsulated in services (`src/<domain>/service.py`), keeping routers thin.
- **Dependency Injection:** Database sessions, repositories, and services are injected using FastAPI's `Depends`.
- **Centralized Models:** SQLAlchemy models are centralized in `src/core/persistence/models.py` to prevent circular imports.
- **Base Model:** All entities inherit from `BaseModel` providing a 12-character Nanoid `id`, `created_at`, and `updated_at`.

## Key Commands

### Development
- **Run Server:** `uvicorn src.main:app --reload`
- **Linting & Formatting:** `ruff check .` and `ruff format .`
- **Type Checking:** `basedpyright`

### Database & Migrations
- **Create Migration:** `alembic revision --autogenerate -m "description"`
- **Apply Migrations:** `alembic upgrade head`
- **Revert Migration:** `alembic downgrade -1`
- **Seed Database:** The application automatically seeds providers, model families, and prompt templates on startup. Models are seeded only if the `models` table is empty and `SEED_MODELS=true`.

### Testing
- **Run All Tests:** `pytest`
- **Coverage:** `pytest --cov=src`

## Development Conventions

### Coding Style
- Follow PEP 8 and use `ruff` for enforcement.
- **Nanoid IDs:** Primary keys are 12-character Nanoids (e.g., `ch_1234567890`).
- **Pydantic Schemas:** Used for request validation and response serialization (`src/<domain>/schemas.py`).
- **Environment Variables:** Configuration is managed via `src/core/config.py` using `pydantic-settings`.

### LLM Provider Integration
- Models are grouped into **Model Families** which define parameters and supported providers.
- **OpenRouter Support:** Models can be routed directly to a provider or through OpenRouter via the `use_openrouter` toggle.
- **Immutability:** Providers and Model Families are considered seeded metadata; they should be enabled/disabled rather than deleted.

### Storage
- Avatars and assets are stored in the directory defined by `STORAGE_PATH` (default: `./storage`).
- Character avatars: `storage/characters/{id}/`
- Persona avatars: `storage/personas/{id}/`

## Integration Details
- **Database Connection:** Defined by `DATABASE_URL` environment variable.
- **Logging:** Audit logs (LLM calls, errors) are stored in PostgreSQL if enabled.
- **CORS:** Origins are configured via `CORS_ORIGINS`.
