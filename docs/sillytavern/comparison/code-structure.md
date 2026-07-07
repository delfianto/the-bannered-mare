# Code Structure Comparison: SillyTavern v1.17.0 vs The Bannered Mare v0.2.5

A side-by-side engineering analysis of how each project organizes its codebase,
manages module boundaries, and enforces structural discipline. This is a neutral
comparison -- both approaches have legitimate trade-offs shaped by different
constraints (community-driven JS monolith vs. greenfield Python backend).


## 1. Codebase Scale

| Metric | SillyTavern | The Bannered Mare |
|--------|------------|-----------------|
| Primary language | JavaScript (ESM) | Python 3.14 |
| Total source LoC | ~185,000 | ~18,500 |
| Source files | ~340 `.js` | ~205 `.py` |
| Test LoC | ~5,000 | ~10,200 |
| Test files | ~14 | ~86 |
| Test-to-source ratio | ~2.7% | ~55% |
| Runtime dependencies | 96 | 19 |
| Dev dependencies | 24 | 10 |

SillyTavern is roughly 10x larger by line count. It is a full-stack application
(Express backend + jQuery SPA frontend), while The Bannered Mare is a headless
API backend only. Comparing raw LoC is therefore misleading without noting that
~141,000 of ST's lines are frontend code with no Bannered Mare equivalent.

Backend-only comparison: ST's `src/` is ~31,700 lines across ~80 files.
The Bannered Mare's `src/` is ~18,500 lines across ~205 files. The file count is
much higher in The Bannered Mare despite having roughly half the code, reflecting
its vertical-slice module structure (many small files vs. fewer large ones).

The two codebases have fundamentally different shapes — a large full-stack monolith with a
central god object versus a headless backend of small, uniform slices:

<Figure tag="Figure 1" title="Two shapes at a glance" id="fig-shape-compare">
<svg viewBox="0 0 760 430" role="img" aria-label="SillyTavern versus The Bannered Mare architecture" style="font-family:var(--vp-font-family-base)">
  <rect x="24" y="16" width="344" height="398" rx="14" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <rect x="392" y="16" width="344" height="398" rx="14" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <text x="196" y="46" text-anchor="middle" font-size="14" font-weight="800" fill="var(--tbm-dgm-ink)">SillyTavern v1.17.0</text>
  <text x="564" y="46" text-anchor="middle" font-size="14" font-weight="800" fill="var(--tbm-dgm-ink)">The Bannered Mare v0.2.5</text>
  <text x="196" y="64" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-faint)">full-stack JS monolith</text>
  <text x="564" y="64" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-faint)">headless Python backend</text>
  <rect x="44" y="80" width="304" height="92" rx="10" fill="var(--tbm-dgm-danger-soft)" stroke="var(--tbm-dgm-danger)"/>
  <text x="196" y="103" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">jQuery SPA frontend</text>
  <text x="196" y="123" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">script.js — 12,481-line god object</text>
  <text x="196" y="140" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">201 JS modules · index.html 8,176 lines</text>
  <text x="196" y="160" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">~141,000 LoC</text>
  <rect x="44" y="188" width="304" height="150" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
  <text x="196" y="211" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">Express backend</text>
  <text x="196" y="231" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">46 endpoint files — flat,</text>
  <text x="196" y="247" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">one file per domain</text>
  <text x="196" y="271" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">src/ ~31,700 LoC</text>
  <text x="196" y="308" text-anchor="middle" font-size="11" font-weight="600" fill="var(--tbm-dgm-ink)">~185,000 LoC total</text>
  <text x="196" y="326" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-faint)">96 deps · ~2.7% test ratio</text>
  <text x="196" y="372" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-faint)">community-driven, grown over years</text>
  <rect x="412" y="80" width="304" height="92" rx="10" fill="var(--tbm-dgm-frontend-soft)" stroke="var(--tbm-dgm-frontend)"/>
  <text x="564" y="103" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">Vue 3 SPA frontend</text>
  <text x="564" y="123" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">typed components · Pinia · Nuxt UI</text>
  <text x="564" y="143" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">separate repository</text>
  <rect x="412" y="188" width="304" height="150" rx="10" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/>
  <text x="564" y="209" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">FastAPI — modular monolith</text>
  <g font-size="9.5" text-anchor="middle" fill="var(--tbm-dgm-ink)">
    <rect x="426" y="220" width="80" height="22" rx="6" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="466" y="235">character</text>
    <rect x="514" y="220" width="80" height="22" rx="6" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="554" y="235">chat</text>
    <rect x="602" y="220" width="88" height="22" rx="6" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="646" y="235">provider</text>
    <rect x="426" y="248" width="80" height="22" rx="6" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="466" y="263">prompt</text>
    <rect x="514" y="248" width="80" height="22" rx="6" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="554" y="263">rag</text>
    <rect x="602" y="248" width="88" height="22" rx="6" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="646" y="263">… + more</text>
  </g>
  <text x="564" y="292" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">each slice: router · service · repository</text>
  <text x="564" y="316" text-anchor="middle" font-size="11" font-weight="600" fill="var(--tbm-dgm-ink)">~18,500 LoC (backend)</text>
  <text x="564" y="334" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-faint)">19 deps · ~55% test ratio</text>
  <text x="564" y="372" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-faint)">greenfield, uniform slices</text>
</svg>
<template #caption>

**Grown vs. designed.** SillyTavern is ~10× larger by line count — a single full-stack repo
whose frontend centres on one 12,481-line file. The Bannered Mare is a headless backend of many
small, identically-shaped slices, with a far higher test ratio and a fraction of the
dependencies. Neither is "wrong": they answer different constraints.

</template>
</Figure>


## 2. Top-Level Layout

### SillyTavern

```
SillyTavern/
├── server.js              # Entry point (18 lines)
├── package.json           # 96 runtime deps, 24 dev deps
├── webpack.config.js      # Bundles public/lib.js
├── src/                   # Backend: Express server (~31,700 LoC)
│   ├── endpoints/         # 46 route files, flat one-file-per-domain
│   ├── middleware/         # 9 small middleware files
│   ├── vectors/           # 9 vector embedding providers
│   └── *.js               # Top-level modules (util, users, constants, etc.)
├── public/                # Frontend: jQuery SPA (~141,000 LoC)
│   ├── script.js          # 12,481-line god object
│   ├── scripts/           # 201 JS modules
│   └── index.html         # 8,176-line monolithic HTML
├── default/               # Config scaffolds, bundled content
├── tests/                 # Jest + Playwright
└── docker/                # Docker configs
```

### The Bannered Mare

```
backend/
├── src/
│   ├── main.py            # Entry point (101 lines)
│   ├── core/              # Shared kernel: config, persistence (incl. models/), logging, utils
│   ├── character/         # Vertical slice: router, service, repository, models, schemas
│   ├── chat_session/      # Same internal structure
│   ├── chat_message/      # Same internal structure
│   ├── provider/          # + adapters/ sub-package
│   ├── model/             # Same internal structure
│   ├── model_family/      # Same internal structure
│   ├── persona/           # Same internal structure
│   ├── preset/            # Same internal structure
│   ├── prompt_template/   # + prompt_builder.py
│   ├── prompt_fragment/   # Same internal structure
│   ├── profile/           # Template + preset bundle (used by ST import)
│   ├── st_import/         # SillyTavern preset importer (parser, mapper, service)
│   ├── lore/              # + activation_engine.py
│   ├── rag/               # + embedding_service.py, retrieval_service.py, rerank_service.py, chunker.py
│   ├── audit/             # PostgreSQL-backed HTTP/LLM/error logging
│   ├── bookmarks/         # Session bookmark listing (router only)
│   ├── health/            # Minimal: router + service
│   ├── admin/             # Minimal: log-query router only
│   └── fixtures/          # Seed data definitions + per-provider families
├── tests/                 # Mirrors src/ structure
├── alembic/               # Database migrations
└── pyproject.toml         # All tool config in one file
```

**Key difference:** SillyTavern's backend is a flat directory with functional
grouping (`endpoints/`, `middleware/`, `vectors/`). The Bannered Mare uses vertical
slices where each domain is a self-contained package with a consistent internal
structure.


## 3. Module Organization

### 3.1 Domain Module Structure

| Aspect | SillyTavern | The Bannered Mare |
|--------|------------|-----------------|
| Pattern | One file per domain (`endpoints/characters.js`) | One package per domain (`character/`) |
| Internal layers | None -- handler functions inline validation, logic, and I/O | 3 layers: `router.py` / `service.py` / `repository.py` |
| Schema definitions | JSDoc typedefs scattered across files | Dedicated `schemas.py` per module (Pydantic) |
| ORM models | N/A (filesystem storage) | `models.py` per module (re-exports from `core/persistence/models/`) |
| Dependency wiring | Implicit via Express `req` object | Explicit `dependencies.py` with FastAPI `Depends` |

A typical The Bannered Mare domain module contains 7-8 files:

```
character/
├── __init__.py          # Public exports
├── router.py            # HTTP endpoints (218 lines)
├── service.py           # Business logic (489 lines)
├── repository.py        # Database queries (45 lines)
├── models.py            # Model re-export (5 lines)
├── schemas.py           # Request/response DTOs (130 lines)
├── dependencies.py      # DI factories (25 lines)
└── card_parser.py       # Domain-specific utility (244 lines)
```

A typical ST endpoint file contains everything in one file:

```
endpoints/characters.js  # 1,543 lines: routes, validation, file I/O, logic
```

### 3.2 Shared Infrastructure

| Component | SillyTavern | The Bannered Mare |
|-----------|------------|-----------------|
| Utility hub | `src/util.js` (1,565 lines, 40+ exports) | `src/core/utils/` (6 files, ~530 lines total) |
| Constants/Enums | `src/constants.js` (558 lines) | `src/core/persistence/enums.py` (50 lines) |
| Config | `config.yaml` + CLI args + env vars (multi-source merge) | Pydantic Settings: `.env` + env vars (185 lines) |
| Logging | Minimal (console + `accessLogWriter.js`) | Structured: structlog + PostgreSQL audit (420 lines) |
| Base patterns | None (each endpoint is standalone) | `BaseRepository` (225 lines), `BaseModel` (47 lines) |

ST's `util.js` is the universal dependency -- imported by nearly every file in
the project. The Bannered Mare splits equivalent functionality into focused utility
modules (`storage.py`, `template.py`, `tokenizer.py`, `validators.py`,
`reasoning.py`), each under 180 lines.


## 4. File Size Discipline

### 4.1 Size Distribution

| Range | SillyTavern (backend) | The Bannered Mare |
|-------|----------------------|-----------------|
| > 2,000 lines | 1 file (`chat-completions.js`: 2,683) | 0 files |
| 1,000-2,000 lines | 5 files | 0 files |
| 500-1,000 lines | ~8 files | 1 file (`chat_message/service.py`: 718) |
| 200-500 lines | ~15 files | ~12 files |
| < 200 lines | ~50 files | ~190 files |

### 4.2 Largest Files

**SillyTavern backend (top 5):**

| File | Lines |
|------|------:|
| `endpoints/backends/chat-completions.js` | 2,683 |
| `util.js` | 1,565 |
| `prompt-converters.js` | 1,445 |
| `characters.js` | 1,543 |
| `users.js` | 1,100 |

**The Bannered Mare (top 5):**

| File | Lines |
|------|------:|
| `chat_message/service.py` | 718 |
| `character/service.py` | 489 |
| `fixtures/parameter_definitions.py` | 421 |
| `fixtures/models/openrouter.py` | 396 |
| `model/service.py` | 387 |

The former largest persistence file (`core/persistence/models.py`, 788 lines) was
split into 12 per-domain modules under `core/persistence/models/`. The Bannered Mare's
largest file is now `chat_message/service.py` at 718 lines -- still smaller than
several of ST's large endpoint files. The trade-off is more files to navigate
(~205 source files vs. ~80 in ST's backend).

### 4.3 Median File Size

Excluding `__init__.py` files:
- **SillyTavern backend:** ~250-350 lines (estimated from distribution)
- **The Bannered Mare:** ~80-100 lines


## 5. Dependency Patterns

### 5.1 Import Graph Shape

**SillyTavern:** Hub-and-spoke with a dominant center.

```
util.js  <----  [almost everything]
constants.js <-- [almost everything]
users.js  <--  [endpoints that need user dirs]
```

- `util.js` exports 40+ symbols; it is the single most-imported module.
- Endpoint files are largely independent of each other, with notable exceptions
  (e.g., `characters.js` imports from `worldinfo.js`, `thumbnails.js`, `chats.js`).
- Frontend has bidirectional dependencies: `script.js` imports from `openai.js`
  and vice versa.

**The Bannered Mare:** Layered DAG with strict direction.

```
router.py  -->  service.py  -->  repository.py  -->  core/persistence/
     |               |
     v               v
dependencies.py   schemas.py
```

- `basedpyright` is configured with `reportImportCycles = true`, making
  circular imports a build error.
- Domain modules never import from each other's internal files. Cross-domain
  communication goes through service-layer injection.
- The only widely-imported module is `core/persistence/`, which provides
  base classes and the session factory.

### 5.2 Cross-Module Coupling

| Pattern | SillyTavern | The Bannered Mare |
|---------|------------|-----------------|
| Circular imports | Present in frontend (`script.js` <-> `openai.js`, etc.) | Blocked by tooling (`reportImportCycles`) |
| Cross-domain imports | Some (`characters.js` -> `worldinfo.js`) | None between domain modules |
| Shared mutable state | Frontend: `let characters = []` exported from `script.js` | None -- state lives in the database |
| Event-based decoupling | `EventEmitter` with 103 event types (frontend) | Not used (direct service calls) |
| God objects | `script.js` (12,481 lines, 217 exports) | None -- largest module export list is ~10 symbols |


## 6. Type System

| Aspect | SillyTavern | The Bannered Mare |
|--------|------------|-----------------|
| Language typing | Dynamic (JS) with opt-in checking | Static (Python with strict type checker) |
| Type checking tool | TypeScript language service via `checkJs: true` | `basedpyright` (standard mode) |
| Type annotation style | JSDoc `@typedef`, `@param`, `@returns` | Native Python type hints + `Mapped[]` |
| Strictness | `strictNullChecks`, `strictFunctionTypes` | `typeCheckingMode = "standard"`, import cycle detection |
| Schema validation | Manual in route handlers | Pydantic V2 models with automatic validation |
| Declaration files | 4 `.d.ts` files for global augmentation | N/A -- native types throughout |
| Runtime type safety | None (JSDoc is erased) | Pydantic enforces types at API boundaries |

SillyTavern's JSDoc approach provides editor tooling (autocomplete, hover info)
without a compilation step. The Bannered Mare's approach catches type errors at build
time via `basedpyright` and at runtime via Pydantic validation on every request.


## 7. Data Persistence Architecture

| Aspect | SillyTavern | The Bannered Mare |
|--------|------------|-----------------|
| Storage model | Flat files on disk (JSON, JSONL, PNG) | PostgreSQL via SQLAlchemy 2.0 |
| Query capability | `fs.readFile` + in-memory filtering | SQL with ORM query builder |
| Schema enforcement | Convention-based (file structure) | Alembic migrations + column constraints |
| Concurrent access | File locks (limited) | Database transactions + connection pooling |
| Abstraction layer | None (direct `fs` calls in handlers) | Repository pattern with generic `BaseRepository[T]` |
| Caching | `MemoryLimitedMap` (LRU, 100MB default) | Database connection pool (`QueuePool`) |
| Async I/O | Sync file operations in Express handlers | Sync for most domains, async (`asyncpg`) for chat messages |

SillyTavern's filesystem storage means zero database setup and simple backups
(copy the `data/` folder). The Bannered Mare's relational model enables structured
queries, referential integrity, and concurrent access at the cost of requiring
a running PostgreSQL instance.


## 8. Testing

| Aspect | SillyTavern | The Bannered Mare |
|--------|------------|-----------------|
| Framework | Jest (unit) + Playwright (E2E) | pytest + pytest-asyncio |
| Test files | ~14 | ~35 |
| Test LoC | ~5,000 | ~5,600 |
| Coverage focus | Macro engine (new subsystem) | Service layer across all domains |
| API endpoint tests | None | Present (router tests with TestClient) |
| Integration tests | Playwright E2E against running server | Provider integration tests with embedded PG |
| Test fixtures | Minimal | 401-line `conftest.py` with SQLite-based session fixtures |
| Test/source ratio | ~2.7% of source size | ~46% of source size |

The test-to-source ratio difference is striking: The Bannered Mare has nearly as many
test lines as source lines, while ST's tests cover a small fraction of its
codebase. This partly reflects project maturity (ST accumulated code faster
than tests; The Bannered Mare is writing tests alongside features) and partly reflects
the testability difference between layered architecture (injectable services)
and co-located handler logic (requires full server for testing).

### 8.1 Test Organization

**SillyTavern:** Flat `tests/` directory. Most tests are Playwright E2E tests
for the macro engine. No unit tests for API endpoints, character parsing, chat
operations, or provider logic.

**The Bannered Mare:** Mirrors `src/` structure. Each domain has its own test
directory with service-layer tests. Additional top-level test files for
streaming and async operations.

```
tests/
├── conftest.py                  # Shared fixtures (SQLite session, factories)
├── integration/                 # Provider integration tests
├── character/test_service.py    # 251 lines
├── character/test_card_parser.py
├── chat_message/test_service.py
├── chat_session/test_service.py
├── chat_session/test_loose_coupling.py
├── provider/test_adapters.py    # 385 lines (largest test file)
├── provider/test_service.py
├── prompt_template/test_prompt_builder.py
├── prompt_template/test_service.py
├── lore/test_activation_engine.py
├── model/test_service.py
├── model/test_router.py
├── ...
```


## 9. Build and Configuration

| Aspect | SillyTavern | The Bannered Mare |
|--------|------------|-----------------|
| Package management | npm (`package.json`) | uv/pip (`pyproject.toml`) |
| Build step | Webpack bundles `lib.js` at startup | None (Python runs source directly) |
| Config sources | 4-layer: env vars > CLI > config.yaml > defaults | 2-layer: env vars > `.env` defaults |
| Config file | YAML (349 lines) with migration system | Pydantic Settings (185 lines) |
| Linting | ESLint (`.eslintrc.cjs`) | Ruff (config in `pyproject.toml`) |
| Formatting | Not configured | Ruff format (config in `pyproject.toml`) |
| Type checking | `jsconfig.json` (2 configs: server + client) | `basedpyright` (config in `pyproject.toml`) |
| Tool config files | 5+ separate files | 1 file (`pyproject.toml` consolidates all tools) |
| CI/runtime targets | Node >= 20, experimental Deno/Bun | Python >= 3.14, Uvicorn ASGI server |

SillyTavern's config system is more sophisticated out of necessity -- it
supports multi-user deployments with per-user config migration. The Bannered Mare's
Pydantic Settings approach is simpler but handles the single-user local
deployment case cleanly, with nested config via `__` delimiter in env vars.


## 10. Provider Adapter Architecture

Both projects face the same core problem: normalizing requests and responses
across 10+ LLM provider APIs. They solve it very differently.

| Aspect | SillyTavern | The Bannered Mare |
|--------|------------|-----------------|
| Pattern | Procedural converter functions | OOP adapter pattern (ABC) |
| Central file | `chat-completions.js` (2,683 lines) + `prompt-converters.js` (1,445 lines) | `provider/adapters/base.py` (99 lines) |
| Per-provider code | Converter functions in shared files | Separate adapter classes (`openai.py`, `anthropic.py`, `gemini.py`, `ollama.py`, `lmstudio.py`) |
| HTTP client | `node-fetch` (inline in handler) | `httpx` (owned by `ProviderGateway`, not adapters) |
| Adapter responsibility | Format conversion + HTTP call + error handling | Format conversion only (stateless data transformers) |
| Streaming | Parsed inline in the endpoint handler | `ProviderGateway.chat_completion_stream()` delegates line parsing to adapters |
| Provider count | 20+ in chat-completions alone | 8 provider types via 5 adapters + OpenRouter routing |

SillyTavern's approach concentrates all provider logic in two large files,
making it easy to see all providers at once but harder to modify one without
risk of affecting others. The Bannered Mare separates the transport layer
(`ProviderGateway`) from the format translation layer (adapter classes),
at the cost of more indirection.


## 11. Entry Point and Startup

| Aspect | SillyTavern | The Bannered Mare |
|--------|------------|-----------------|
| Entry point | `server.js` (18 lines) -> `server-main.js` (466 lines) | `main.py` (119 lines) |
| Startup pattern | Promise chain waterfall (10 `.then()` calls) | FastAPI lifespan context manager |
| Middleware setup | Manual registration in `server-main.js` (16 middleware in sequence) | 2 middleware: CORS + request logging |
| Route mounting | `setupPrivateEndpoints()` mounts 44 routers | `app.include_router()` for 18 routers |
| Legacy compat | 30+ deprecated URL redirects (HTTP 308) | None (new project) |
| Database init | N/A (filesystem) | `seed_database()` loads fixture data on startup |
| Startup LoC | ~900 across 2 files | ~119 in 1 file |


## 12. Summary of Structural Trade-offs

| Dimension | SillyTavern's approach | The Bannered Mare's approach |
|-----------|----------------------|----------------------|
| Organization | Flat, functional grouping | Deep, vertical slices |
| File granularity | Fewer, larger files | Many small, focused files |
| Layer separation | None (handlers do everything) | Strict 3-layer (router/service/repository) |
| State management | Global mutable exports + events | Database as source of truth |
| Type safety | Opt-in JSDoc, no runtime checks | Mandatory static analysis + runtime Pydantic |
| Testing surface | Hard to unit test (co-located I/O) | Designed for unit testing (injectable deps) |
| Navigability | Grep-friendly (all domain logic in one file) | Structure-friendly (predictable file locations) |
| Onboarding | Read one file to understand a domain | Learn the layer convention, then any domain is familiar |
| Refactoring risk | Changes can ripple through shared mutable state | Layered isolation limits blast radius |
| Feature velocity | Fast to add (no ceremony) | Slower (must touch 5-7 files per feature) |

Neither approach is universally superior. ST's flat structure enabled rapid
feature accumulation by a distributed community of contributors who could work
on isolated endpoint files. The Bannered Mare's layered structure enforces consistency
and testability at the cost of more boilerplate per feature. The architectures
reflect their contexts: a mature community project vs. a greenfield system
designed with the benefit of hindsight.

---

**Tool & Version Info**
- SillyTavern: v1.17.0
- The Bannered Mare: v0.2.5
- Author: Claude Opus 4.6 (1M context)
- Date: 2026-04-07
