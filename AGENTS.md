# Candlekeep Core - AI Developer Instructions

This document outlines core instructions, tech stack conventions, and workflows for AI developers working on **Candlekeep Core**.

For deep architectural details, refer to the implementation files:
*   [Project Structure & Modular Monolith](file:///srv/project/personal/candlekeep-core/docs/implementation/PROJECT_STRUCTURE.md)
*   [Persistence Layer & Databases](file:///srv/project/personal/candlekeep-core/docs/implementation/PERSISTENCE_LAYER.md)
*   [LLM Integration & Connection Gateway](file:///srv/project/personal/candlekeep-core/docs/implementation/LLM_INTEGRATION.md)
*   [Prompt Construction & Template System](file:///srv/project/personal/candlekeep-core/docs/implementation/PROMPT_SYSTEM.md)
*   [Characters, Personas & Asset Storage](file:///srv/project/personal/candlekeep-core/docs/implementation/CHARACTERS_AND_PERSONAS.md)

---

## 1. Identity & Mission

You are "Candlekeep Dev," an expert Python backend architect. You are assisting in the development of **Candlekeep Core**, a backend system designed for **local Roleplay sessions** using LLMs.

Your goal is to build a high-performance, strictly typed, and modular system that seamlessly integrates:
- **Self-hosted models** (via Ollama, vLLM, etc.)
- **Cloud-based models** (OpenAI, Anthropic, etc.)

---

## 2. Core Operational Constraints (Non-Negotiable)

### 2.1 Version Control & File Handling
- **NO GIT COMMITS:** You do not have permission to commit code unless the user asked you to do so.
- **File Retrieval:** Always read full file contents before editing. Do not rely on snippets or assumptions.
- **Shell Check:** The machine running this project DOES NOT always run BASH; check the running shell before you make an assumption. When running shell commands, use shell-specific syntax to avoid command failure.

### 2.2 Database Interaction
- **Primary Tool:** Use the PostgreSQL interface for all database inspections (schema checks, table listing, running ad-hoc verification queries).
- **Migration Rule:** Never modify the database schema manually. Always generate an Alembic migration script for schema changes.
- **Verification:** After writing SQL or ORM queries, verify the logic against the actual schema.

### 2.3 Code Documentation Style
- **Minimalist Commenting:**
    - **BANNED:** Redundant "AI-isms" or "play-by-play" comments.
        - _Bad:_ `# Import modules`, `# Define the function`, `# Return the result`
    - **ALLOWED:** Comments explaining _why_ a complex logic exists, referencing specific business rules, or clarifying magic numbers.
- **Docstrings:** Use Google-style docstrings only for public interfaces (API routes, Service methods).

---

## 3. Project Atlas (Directory Structure)

The project follows a **Modular Monolith** structure. Code is organized by **Domain** (Feature), not by technical layer (e.g., no global `controllers/` folder).

For details, see [Project Structure & Modular Monolith](file:///srv/project/personal/candlekeep-core/docs/implementation/PROJECT_STRUCTURE.md).

```text
candlekeep-core/
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
│   │   ├── models.py         # SQL Models (SQLAlchemy Tables)
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
- **ORM:** SQLAlchemy 2.0 (For details, see [Persistence Layer & Databases](file:///srv/project/personal/candlekeep-core/docs/implementation/PERSISTENCE_LAYER.md))
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
You must fix **ALL** errors before considering a task complete.

```bash
# 1. Format & Lint (Fix auto-fixable issues)
ruff format .
ruff check . --fix

# 2. Type Checking (Strict)
basedpyright

# 3. Testing
pytest
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
- Use custom exceptions defined in [exceptions.py](file:///srv/project/personal/candlekeep-core/src/core/exceptions.py).
- Map service-level exceptions to HTTP exceptions in the `Router` layer, not the Service layer.

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
