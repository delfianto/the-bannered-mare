# Project Structure

The backend is a **modular monolith** built from **vertical slices**. Rather than
grouping code by technical layer — every router in one place, every model in another —
it is organized around **domains**: characters, chat sessions, providers, prompts, and
so on. Each domain owns its whole stack, top to bottom, in a single folder. The result
is high cohesion (everything about a feature lives together), easy navigation (one place
to look), and clean modularity (slices barely reach across each other).

## 1. Directory Structure Atlas

The codebase is organized as follows:

```text
backend/
├── alembic/                  # Database schema migrations (Alembic auto-managed)
├── src/                      # Source directory
│   ├── core/                 # Shared Kernel (Cross-cutting infrastructure)
│   │   ├── config.py         # Application configuration & Environment variable loading
│   │   ├── exceptions.py     # Centralized exceptions and HTTP handlers
│   │   ├── logging/          # Structured logging and auditing configuration
│   │   └── persistence/      # Base repository, DB session management, and base models
│   ├── [domain_module]/      # Vertical Slices (Domain slices)
│   │   ├── router.py         # API interface layer (routing, payload validation)
│   │   ├── service.py        # Business logic layer (orchestrating repo tasks)
│   │   ├── repository.py     # Data access layer (SQLAlchemy/SQL queries)
│   │   ├── models.py         # SQLAlchemy domain database models
│   │   ├── schemas.py        # Pydantic schemas (DTOs for requests and responses)
│   │   └── dependencies.py   # FastAPI dependencies (database session & service providers)
│   └── main.py               # Application entrypoint
├── tests/                    # Test suite mirroring the src/ structure
├── pyproject.toml            # Package, linter, formatting, and type-checker configs
└── alembic.ini               # Alembic configuration
```

Two things sit outside the domain slices: the **shared kernel** (`src/core/`), which
holds infrastructure every slice depends on, and `main.py`, which wires the application
together at startup. The rest of the tree is slices.

## 2. Shared Kernel (`src/core/`)

Cross-cutting infrastructure is grouped into `src/core/` so domain slices never repeat
boilerplate:

### Configuration (`config.py`)

Centralized environment and project settings powered by `pydantic-settings`. It loads and
validates configuration parameters like database URLs, log levels, allowed CORS origins,
token limits, and local asset storage paths.

### Exception Handler (`exceptions.py`)

Defines the base system exceptions (e.g., `EntityNotFoundError`, `ValidationError`,
`ProviderConnectionError`) and wires up FastAPI exception handlers, mapping service-layer
exceptions to the correct HTTP status codes in one central place.

### Persistence Foundation (`persistence/`)

Initializes the SQLAlchemy asynchronous and synchronous engines and manages request-scoped
database sessions. Contains the `BaseRepository` abstract class that implements common CRUD
logic. This layer is detailed in [Persistence Layer](/architecture/backend/persistence).

## 3. The Vertical-Slice Pattern

Each domain module (e.g., `character`, `chat_session`, `provider`) is an independent unit
whose files are single-responsibility layers. A request always travels the same path down
through them — and only the service layer is allowed to fan out sideways to external
providers:

<Figure tag="Figure 1" title="How a request travels through one slice" id="fig-slice-flow">
<svg viewBox="0 0 720 470" role="img" aria-label="Request flow through a vertical slice" style="font-family:var(--vp-font-family-base)">
  <defs>
    <marker id="tbm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-arrow)"/>
    </marker>
  </defs>
  <rect x="250" y="18" width="220" height="40" rx="20" fill="var(--tbm-dgm-surface-3)" stroke="var(--tbm-dgm-border-strong)"/>
  <text x="360" y="43" text-anchor="middle" font-size="13" font-weight="700" fill="var(--tbm-dgm-ink)">HTTP request</text>
  <!-- Router -->
  <rect x="170" y="92" width="380" height="58" rx="10" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/>
  <text x="360" y="116" text-anchor="middle" font-size="13" font-weight="700" fill="var(--tbm-dgm-ink)">router.py — API layer</text>
  <text x="360" y="135" text-anchor="middle" font-size="11" fill="var(--tbm-dgm-ink-2)">routing · Pydantic DTO validation · JSON serialization</text>
  <!-- Service -->
  <rect x="170" y="182" width="380" height="58" rx="10" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/>
  <text x="360" y="206" text-anchor="middle" font-size="13" font-weight="700" fill="var(--tbm-dgm-ink)">service.py — business layer</text>
  <text x="360" y="225" text-anchor="middle" font-size="11" fill="var(--tbm-dgm-ink-2)">domain rules · multi-repository orchestration</text>
  <!-- Repository -->
  <rect x="170" y="272" width="380" height="58" rx="10" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/>
  <text x="360" y="296" text-anchor="middle" font-size="13" font-weight="700" fill="var(--tbm-dgm-ink)">repository.py — data-access layer</text>
  <text x="360" y="315" text-anchor="middle" font-size="11" fill="var(--tbm-dgm-ink-2)">SQLAlchemy CRUD &amp; query building</text>
  <!-- DB -->
  <rect x="230" y="362" width="260" height="54" rx="12" fill="var(--tbm-dgm-data-soft)" stroke="var(--tbm-dgm-data)"/>
  <text x="360" y="386" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">PostgreSQL (prod)</text>
  <text x="360" y="404" text-anchor="middle" font-size="11" fill="var(--tbm-dgm-ink-2)">SQLite (test)</text>
  <!-- External -->
  <rect x="576" y="182" width="128" height="58" rx="10" fill="var(--tbm-dgm-provider-soft)" stroke="var(--tbm-dgm-provider)"/>
  <text x="640" y="206" text-anchor="middle" font-size="12" font-weight="700" fill="var(--tbm-dgm-ink)">External LLM</text>
  <text x="640" y="224" text-anchor="middle" font-size="11" fill="var(--tbm-dgm-ink-2)">providers</text>
  <!-- Arrows -->
  <g stroke="var(--tbm-dgm-arrow)" stroke-width="1.6" fill="none" marker-end="url(#tbm-ah)">
    <path d="M360 58 L360 90"/>
    <path d="M360 150 L360 180"/>
    <path d="M360 240 L360 270"/>
    <path d="M360 330 L360 360"/>
    <path d="M550 211 L574 211"/>
  </g>
  <text x="562" y="203" text-anchor="middle" font-size="10" fill="var(--tbm-dgm-ink-2)">LLM call</text>
</svg>
<template #caption>

**One direction down, one exit sideways.** The router only speaks HTTP; the service holds
all domain logic and is the sole layer allowed to call external providers; the repository
is the only layer that touches the database. `dependencies.py` injects the service and a
scoped session into the router via FastAPI `Depends`.

</template>
</Figure>

1. **Router layer (`router.py`)** — parses HTTP requests, verifies authorization, validates
   payloads via Pydantic schemas (`schemas.py`), and returns serialized JSON. It is strictly
   prohibited from containing raw database operations or multi-repository orchestration.
2. **Service layer (`service.py`)** — the home of business logic. Coordinates operations
   across repositories, applies domain validations, and drives work like building prompt
   messages or calling external LLM adapters. It is completely agnostic of the HTTP layer
   (no `Request` objects, no `JSONResponse`).
3. **Repository layer (`repository.py`)** — executes database queries, updates, and deletes.
   It maps to ORM models and returns SQLAlchemy entities rather than Pydantic schemas.
4. **Dependencies (`dependencies.py`)** — declares FastAPI `Depends` factories that inject
   repositories, services, and scoped database sessions into routers.

## 4. Initialization and Seeding (`src/main.py`)

`main.py` bootstraps the FastAPI application:

- Configures CORS middleware based on authorized origins.
- Wires up the exception-mapping handlers.
- Handles database startup tasks automatically:
  1. Runs any database migration checks.
  2. Seeds base metadata if missing — pre-defined `Provider` systems, `ModelFamily`
     templates, and the default `PromptTemplate` presets.
