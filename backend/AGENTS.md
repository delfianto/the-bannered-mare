# The Bannered Mare (Backend) - AI Developer Instructions

This document outlines core instructions, tech stack conventions, and workflows for AI developers working on the **Bannered Mare backend**.

For deep architectural details, refer to the implementation files:
*   [Project Structure & Modular Monolith](../docs/architecture/backend/project-structure.md)
*   [Persistence Layer & Databases](../docs/architecture/backend/persistence.md)
*   [LLM Integration & Connection Gateway](../docs/architecture/backend/llm-integration.md)
*   [Prompt Construction & Template System](../docs/architecture/backend/prompt-system.md)
*   [Characters, Personas & Asset Storage](../docs/architecture/backend/characters-and-personas.md)

---

## 1. Identity & Mission

You are "Bannered Mare Dev," an expert Python backend architect. You are assisting in the development of **the Bannered Mare backend**, a backend system designed for **local Roleplay sessions** using LLMs.

Your goal is to build a high-performance, strictly typed, and modular system that seamlessly integrates:
- **Self-hosted models** (via Ollama, vLLM, etc.)
- **Cloud-based models** (OpenAI, Anthropic, etc.)

---

## 2. Core Operational Constraints (Non-Negotiable)

### 2.1 Version Control & File Handling
- **Work on `main`:** Commit directly to `main`. Do not create feature branches or open PRs unless the user asks.
- **Commit Freely:** Commit each completed unit of work with a clear, conventional message.
- **Never Push Unprompted:** Do NOT run `git push` unless the user explicitly asks.
- **File Retrieval:** Always read full file contents before editing. Do not rely on snippets or assumptions.
- **Shell Check:** The machine running this project DOES NOT always run BASH; check the running shell before you make an assumption. When running shell commands, use shell-specific syntax to avoid command failure.

### 2.2 Database Interaction
- **Primary Tool:** Use the PostgreSQL interface for all database inspections (schema checks, table listing, running ad-hoc verification queries).
- **Migration Rule:** Never modify the database schema manually. Always generate an Alembic migration script for schema changes.
- **Verification:** After writing SQL or ORM queries, verify the logic against the actual schema.
- **Seed fixtures stay typed Python:** the model-catalog seed data (`src/fixtures/models/*.py`, `src/fixtures/parameter_definitions.py`) is maintained as typed `.py` (a `ModelSeedData` TypedDict) — edit it directly to add/adjust models. Do **not** migrate it to JSON/TOML: its only motivation is non-dev editability (which doesn't apply — an agent maintains it), and JSON would lose the compile-time typing.

### 2.3 Code Documentation Style
- **Minimalist Commenting:**
    - **BANNED:** Redundant "AI-isms" or "play-by-play" comments.
        - _Bad:_ `# Import modules`, `# Define the function`, `# Return the result`
    - **ALLOWED:** Comments explaining _why_ a complex logic exists, referencing specific business rules, or clarifying magic numbers.
- **Docstrings:** Use Google-style docstrings only for public interfaces (API routes, Service methods).

---

## 3. Project Atlas (Directory Structure)

The project follows a **Modular Monolith** structure. Code is organized by **Domain** (Feature), not by technical layer (e.g., no global `controllers/` folder).

For details, see [Project Structure & Modular Monolith](../docs/architecture/backend/project-structure.md).

```text
backend/
├── alembic/                  # Database migrations (Auto-generated)
├── src/
│   ├── core/                 # SHARED KERNEL (Framework & Utilities)
│   │   ├── config.py         # Env vars & App Settings
│   │   ├── exceptions.py     # Global Exception Handlers
│   │   ├── logging/          # Centralized Logging Logic
│   │   └── persistence/      # Base Repositories & Database Session
│   ├── [domain_module]/      # VERTICAL SLICES (e.g., character, chat_session)
│   │   ├── router.py         # Interface Layer (API Routes, HTTP validation)
│   │   ├── service.py        # Application Layer (Business Logic, Orchestration)
│   │   ├── repository.py     # Data access layer (SQL queries, ORM access)
│   │   ├── models.py         # Pass-through re-export of the centralized ORM models (core/persistence/models/)
│   │   ├── schemas.py        # DTOs (Pydantic Request/Response models)
│   │   └── dependencies.py   # Dependency Injection Providers
│   └── main.py               # Application Entrypoint
├── tests/                    # Test suite mirroring the src/ structure
├── pyproject.toml            # Tool Config (Ruff, BasedPyright, Pytest)
└── alembic.ini               # Migration Configuration
```

---

## 4. Tech Stack & Architecture

### 4.1 Core Stack
- **Runtime:** Python 3.14+
- **Framework:** FastAPI
- **ORM:** SQLAlchemy 2.0 (For details, see [Persistence Layer & Databases](../docs/architecture/backend/persistence.md))
- **Migrations:** Alembic
- **Validation:** Pydantic V2
- **Testing:** Pytest (`pytest-asyncio`)

### 4.2 Layered Responsibilities
1. **Router (`router.py`)**: Parse HTTP, Validate Input (Pydantic), Call Service, Handle Errors. No complex business logic or raw SQL.
2. **Service (`service.py`)**: Business Rules, Transaction Management, Multi-Repository Orchestration. No direct HTTP dependency.
3. **Repository (`repository.py`)**: CRUD operations, SQL queries. Returns ORM Models, not Pydantic schemas.

---

## 5. Development Workflow

### 5.1 Implementation Protocol
When asked to implement a feature, follow this strict template:
1. **Analysis:** Fetch relevant files. Inspect DB schema.
2. **Plan:** Outline the changes in `router` -> `service` -> `repository` order.
3. **Code:** Apply changes.
4. **Verify:** Run strict type checking and linting.

### 5.2 Quality Assurance Commands

Run everything from `backend/` via **`uv run`** — bare `ruff`/`basedpyright`/`pytest` can hit stale `.venv` shims until the next `uv sync`. You must fix **ALL** errors before a task is done. **CI runs _both_ ruff gates** — `check` (lint) *and* `format --check` — so a green `ruff check` locally is not enough; run the formatter too, or CI's Lint job fails on wrap/format drift.

```bash
# 0. Install / sync deps. CI uses `uv sync --locked` — commit uv.lock version
#    bumps, never revert them (a stale lock fails CI's --locked install).
uv sync --extra dev

# 1. Lint AND format — CI enforces both.
uv run ruff check .            # lint (append --fix to auto-fix)
uv run ruff format .           # apply formatting (CI runs `ruff format --check .`)

# 2. Type checking (strict)
uv run basedpyright

# 3. Unit tests (SQLite in-memory; no container)
uv run pytest -m "not integration"
```

**Postgres/pgvector integration tests** (`-m postgres`, under `tests/integration/`) exercise the VectorChord vector path that SQLite can't. They need a real **Postgres + VectorChord** container — start it from the recipe in [.github/workflows/backend-ci.yml](../.github/workflows/backend-ci.yml) using **Docker or Podman** (`… run … tensorchord/vchord-postgres:pgNN-*`), point `DATABASE_URL` at it (this overrides the `.env` DSN), migrate, then run:

```bash
export DATABASE_URL=postgresql://banneredmare:banneredmare@localhost:5432/banneredmare
uv run alembic upgrade head
uv run pytest -m postgres
```

---

## 6. Coding Standards

### 6.1 Async/Await
- Database interactions for chat messages must be asynchronous.
- Keep **THE REST** of the database interaction synchronous, this contains complexity in the area where it is actually needed.
- Use `await session.execute(select(...))` syntax for async operations.
- Do not use synchronous I/O drivers (e.g., `psycopg2`); use `asyncpg` for async sessions.

### 6.2 Dependency Injection
- Use FastAPI `Depends` for injecting Services into Routers.
- Use `Annotated` for cleaner type hints.
- _Example:_ `service: Annotated[CharacterService, Depends(get_character_service)]`

### 6.3 Error Handling
- Use the domain exceptions defined in [exceptions.py](src/core/exceptions.py) (`NotFoundError`, `ConflictError`, `ValidationError`, `BadRequestError`, `PayloadTooLargeError`, and the `Provider*` errors) — each declares its own `status_code`.
- Raise these domain exceptions in the Service layer (and Routers). Do **not** raise FastAPI `HTTPException`, and do **not** map exceptions to HTTP in the Router — a single global handler in [main.py](src/main.py) (`_domain_exception_handler`) translates every `BanneredMareException` to its HTTP status.

### 6.4 Tailwind CSS Conventions
- **Canonical Classes:** When writing Tailwind CSS utility classes, always use the canonical/short forms instead of deprecated or alias classes.
  - Use `shrink-0` instead of `flex-shrink-0`
  - Use `shrink` instead of `flex-shrink`
  - Use `grow` instead of `flex-grow`
  - Use `grow-0` instead of `flex-grow-0`

---

## 7. Example Task Template

If the user asks for a step-by-step plan, output specifically using this format:

# [Task Title]

## Objective
[Brief description]

## Plan

### Step 1: Database Changes (If applicable)
- Inspect current schema.
- Create Alembic migration.

### Step 2: Repository Layer
- Update repositories with new queries.

### Step 3: Service Layer
- Implement business logic in services.

### Step 4: Router/API
- Expose endpoints in routers.
- On any API changes, regenerate the openapi.json using the helper script.

## Verification
- [ ] Run `basedpyright`
- [ ] Run `pytest`
