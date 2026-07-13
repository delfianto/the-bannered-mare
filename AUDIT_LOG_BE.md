# Backend Architectural Audit — The Bannered Mare

**Date:** 2026-07-14
**Scope:** `backend/` — Python 3.14 / FastAPI / SQLAlchemy 2.0 / Pydantic v2 / PostgreSQL + pgvector modular monolith.
**Method:** Read-only audit across four independent dimensions — (1) layering & dependency injection, (2) persistence, data modeling & async/transaction correctness, (3) API surface, error handling, config, logging & security, (4) duplication, complexity, dead code & test health. Findings confirmed independently by more than one dimension are marked **⊕** (higher confidence).

> **Nothing in this document has been changed yet.** It is a findings log for planning. Each finding carries a stable ID (`BE-n`), a severity, concrete `file:line` locations, the problem, its architectural cost, and a sized recommendation.

## Context — already addressed (excluded from findings)

A large prior refactor (tasks A1–N2) already landed and is deliberately **not** re-flagged here: the domain-exception hierarchy + global handler; a `BaseService` + pagination helper; sync/async base-repository de-duplication; extraction of `CompletionPipeline` / `GatewayFactory` / `MessageContextBuilder` / `AlternativesService` / `AuxiliaryGenerationService` out of `ChatMessageService`; removal of cross-domain SQL in character/model/provider via DI; offloading sync DB + CPU-bound image/card work off the event loop; capping unbounded history load; the `ModelService.update` partial-write fix; the Jinja2 SSTI sandbox; CUSTOM-provider hardening; bounded upload size; redaction-gap closure; stopping internal-error-text leakage (globally — but see BE-4/BE-13); and the per-family tokenization package under `src/core/tokenization`.

## Out of scope — authentication & network hardening (by decision, 2026-07-14)

This is a **single-user local experiment.** Authentication / login, network-exposure hardening (loopback binding, `/admin` access gating), credentialed-CORS tightening, and provider-URL SSRF validation are **intentionally deferred** until the app's core patterns are established and stable — comparable local-first tools (e.g. SillyTavern) also ship without login. Audits should **not** re-raise these as findings under the current deployment model; revisit only if the app is ever exposed to a network or made multi-user. (This is why former finding **BE-3** is withdrawn below.)

---

## Executive summary

The **intra-slice layering is genuinely clean**: no `HTTPException` in any service, no raw SQL/ORM in any router, no Pydantic in any repository, one global domain-exception handler. The remaining weaknesses live at the **module-boundary / shared-kernel level**, in a **base repository that stops just short** of the CRUD patterns every slice re-implements, and in a small number of **genuine correctness/perf issues** worth verifying and fixing first.

Three things to do before any big refactor:
1. **BE-1** — verify & fix RAG message-embedding scoping (a headline feature appears inert).
2. **BE-2** — add the missing `(chat_id, created_at)` index on the hottest table.
3. **BE-4** — stop the SSE path leaking raw exception text (regression of the leakage hardening on the most-used endpoint).

---

## Tier 1 — Correctness, security, hot path

### BE-1. RAG message embeddings are unretrievable by design (and leak forever)
- **Severity:** High · **Confidence:** verify against live DB before acting
- **Location:** `src/rag/retrieval_service.py:59,83,153-179`; `src/rag/repository_async.py:91-100`; `src/core/persistence/models/rag.py:20-49`
- **Problem:** `embeddings` is a polymorphic association keyed by `(source_type, source_id)`. `vectorize_message` writes rows with `source_id = message_id`, but `retrieve()` scopes the vector search to `source_ids = [chat_id] + [data_bank_entry.id, …]` (`WHERE source_id = ANY(:source_ids)`). A message's `source_id` is a *message* id, never in that list — so **message embeddings can never match a retrieval query**. `vectorize_messages` defaults to `True`, so every send writes an embedding no query can read. There is also no FK on `embeddings.source_id` and no `delete_by_source("message", …)` on message/chat deletion, so the rows accumulate permanently (storage + vchordrq index bloat).
- **Why it matters:** RAG-over-conversation-history — a headline feature — silently returns only data-bank hits while paying the embedding write cost every turn and leaking orphaned rows.
- **Recommendation (medium):** Add a nullable, indexed `chat_id` FK (`ON DELETE CASCADE`) to `embeddings` and scope message retrieval on it (or store message embeddings with `source_id = chat_id` + a separate `message_id`). Add cascade cleanup on message/chat delete. Confirm the code path against a live DB first.

### BE-2. Missing composite index `(chat_id, created_at)` on `messages`
- **Severity:** High · **Size:** small
- **Location:** `src/core/persistence/models/chat.py:30-36`; `src/chat_message/repository_async.py:54-93`; migration `alembic/versions/614c1c3b4343_consolidated_schema.py:380`
- **Problem:** `messages` has only the single-column `ix_messages_chat_id`. Every history load / send / regenerate / suggestion / title call runs `WHERE chat_id = ? ORDER BY created_at DESC LIMIT n`, forcing a sort each time. The exact composite index *was* added to the far colder `llm_audit_logs` (`ix_llm_audit_logs_chat_created`) but not to `messages`.
- **Why it matters:** This is the single most frequently executed query, on the latency-critical send path.
- **Recommendation (small):** Add `Index("ix_messages_chat_created", "chat_id", "created_at")` to the `Message` model + an Alembic migration.

### BE-3. ~~Security posture cluster~~ — WITHDRAWN (out of scope by decision)
- **Status:** Withdrawn 2026-07-14. Authentication/login, network-exposure hardening (loopback bind, `/admin` gating), credentialed-CORS, and provider-URL SSRF validation are **intentionally out of scope** for this single-user local experiment — auth is deferred until the app's patterns stabilize (comparable local tools such as SillyTavern also ship without login). See *Out of scope — authentication & network hardening* near the top of this document. Revisit only if the deployment model ever becomes multi-user or network-reachable, at which point binding, `/admin` access, CORS credentials, and `base_url` validation should all be reconsidered together.

### BE-4. SSE streaming path bypasses the global handler and mis-classifies every error
- **Severity:** Medium
- **Location:** `src/chat_message/router.py:107-110`
- **Problem:** Inside the SSE generator, `except Exception as e:` emits `StreamEvent(type="error", message=str(e), code="internal_error")`. Once the `StreamingResponse` has begun, the global `BanneredMareException` handler can't intervene, so this path doesn't go through the centralized error mapping the rest of the app uses. The code is hardcoded `"internal_error"` even though `classify_error()` (`src/chat_message/llm_audit.py:28`) already distinguishes rate-limit/timeout/provider errors — so the frontend sees the same generic failure for a transient 429 and a real fault, and can't react appropriately (retry vs surface vs switch model).
- **Why it matters:** This is the most-used endpoint; its error handling is inconsistent with the domain-exception architecture, and the flattened code degrades client UX. (Not a security/leakage concern under the local-experiment model — this is about error-handling consistency.)
- **Recommendation (small):** Reuse `classify_error()` for the `code` so the stream emits a meaningful error type; keep the human-readable `message` concise.

### BE-5. ⊕ Shared kernel (`core/`) depends on vertical slices
- **Severity:** High
- **Location:** `src/core/logging/request_logging.py:31` (imports `src.audit.writer.audit_logger` via a lazy in-body import to dodge a load-time cycle); `src/core/utils/template.py:11-13` (imports `character`, `chat_session`, `persona` models)
- **Problem:** The shared kernel is meant to be the generic, dependency-free base (CLAUDE.md §3). Instead `RequestLoggingMiddleware` (in `core/logging/`) reaches into the `audit` slice, and `TemplateService` (in `core/utils/`) knows three domains' ORM models.
- **Why it matters:** A shared kernel that imports domains inverts the dependency direction the whole modular monolith rests on, makes `core` un-extractable, and forces the lazy-import workarounds seen throughout.
- **Recommendation (medium):** Move `RequestLoggingMiddleware` to app-wiring (`main.py` or an `src/observability/` slice allowed to depend on `audit`); relocate `TemplateService`/`TemplateContext` into the domain that owns those models.

---

## Tier 2 — Architecture & maintainability

### BE-6. ⊕ Base repository stops one step short → 5–7 domains copy-paste the same queries
- **Severity:** Medium · **Size:** medium · **highest LOC leverage**
- **Location:**
  - `find_all_ordered` — `persona/repository.py:19`, `preset/repository.py:21`, `profile/repository.py:21`, `prompt_template/repository.py:27`, `character/repository.py:24`, `rag/repository.py:31`
  - `unset_all_defaults` — `persona:42`, `preset:41`, `profile:41`, `prompt_template:32`
  - `find_by_name` — `preset:16`, `profile:16`, `prompt_template:17`, `prompt_fragment:16`, `character:19`, `model_family:57`, `provider:17`
  - ordered+counted pagination — `persona/repository.py:24`, `preset/repository.py:26`, `profile/repository.py:26`
  - `set_default` service logic (verbatim ×4) — `persona/service.py:111`, `preset/service.py:84`, `profile/service.py:125`, `prompt_template/service.py:137`
  - two update conventions — `if x is not None` ladder (`persona:81`, `preset:65`, `prompt_fragment:101`, `character:158`) vs dict-driven `setattr` loop (`profile:97`)
- **Problem:** Byte-identical bodies differing only by model name. The generic `BaseRepository` already owns `find_all`/`find_paginated`/`find_paginated_with_count` but stops short of "ordered", "by-name", and "defaultable".
- **Why it matters:** A single filtering/ordering change must be made in N places; largest duplicated-LOC block in `src/`. Two update conventions raise the "which do I copy?" tax on every new domain.
- **Recommendation (medium):** Add `find_all_ordered(order_by=…)`, `find_paginated_ordered(...)`, `find_by_name` to the base repo; add a `DefaultableRepository` mixin with `unset_all_defaults(exclude_id=None)`; collapse `set_default` into one service helper; standardize on the dict-driven partial-update.

### BE-7. ⊕ `CharacterService.import_card` is a 166-line hotspot with misplaced logic
- **Severity:** High (cohesion) · **Size:** medium
- **Location:** `src/character/service.py:222-388` (worst at `292-365`)
- **Problem:** One method reads the upload, dispatches PNG-vs-JSON parse, maps gender, builds the `Character`, then — nested three deep in a `for` over `character_book["entries"]` — runs three fragile string-matching `if/elif` ladders to map `position`/`secondary_logic`/`role` enums (with silent fall-through), constructs a `LoreEntry` from ~18 `entry_dict.get(...)` calls, and re-wraps raw PNG bytes into a fresh `UploadFile` to save the avatar. It uses function-local imports (`294-295`, `369-372`) to dodge circular deps.
- **Why it matters:** Least testable, highest-branching method in the service layer; card→`LoreEntry` mapping is domain logic buried in an import routine (a home already exists in `card_parser.py`).
- **Recommendation (medium):** Extract `_map_card_lorebook(card, character_id)`; replace each ladder with a `dict[str, Enum]` lookup + default; move card→ORM mapping next to `card_parser.py`. Roughly halves the method and makes the enum maps unit-testable.

### BE-8. `UploadFile` (HTTP transport type) leaks into the service layer
- **Severity:** Medium
- **Location:** `src/character/service.py:8,78,141,222,368-385`; `src/persona/service.py:5,39,72`; `src/st_import/service.py:10,53`; `src/core/utils/storage.py:35,140,186`
- **Problem:** Service methods accept FastAPI's `UploadFile` (violating CLAUDE.md §4.2). The smell is proven by `import_card` fabricating a fake `UploadFile` from raw bytes purely to satisfy `save_character_avatar`.
- **Why it matters:** Couples services to the web framework and Starlette's multipart type; makes them awkward to unit-test.
- **Recommendation (medium):** Change `storage.py` avatar helpers to accept `bytes` (or filename + stream); routers do `await file.read()` and pass bytes down. Deletes the `FUpload`/`Headers`/`BytesIO` hack.

### BE-9. DI graph has real cycles masked by lazy imports
- **Severity:** Medium (trending High as the graph grows)
- **Location:** `src/model/dependencies.py:10,26-28`; `src/provider/router.py:26-47`; also `src/chat_session/dependencies.py:41-43`
- **Problem:** `model.dependencies` imports `provider.dependencies`, so `provider` can't import back — the provider router hand-rolls a private `_get_model_service` factory (manually newing up four repos, duplicating `ModelServiceDep`). `model.dependencies.get_model_service` uses an in-body `ChatRepository` import. Same lazy-import workaround recurs in `chat_session` (cycle `profile→preset→st_import→prompt_template→chat_session`).
- **Why it matters:** Genuine cycles papered over by lazy imports; duplicated factories drift; cycles block clean extraction.
- **Recommendation (medium):** Extract shared repository factories (`get_provider_repository`, `get_model_repository`, `get_chat_repository`) into a neutral DI module both slices import; let `provider.router` import the real `ModelServiceDep`.

### BE-10. Synchronous psycopg2 prompt-builder runs on the event loop
- **Severity:** Medium
- **Location:** `src/chat_message/context.py:62-71` (calls `build_api_messages` directly on the loop); `src/prompt_template/prompt_builder.py:69-73` (`find_default()` fallback); `src/prompt_template/dependencies.py:13-15`; `src/chat_message/dependencies.py:36-56`
- **Problem:** The fully-async `ChatMessageService` is given a *synchronous* (psycopg2) `PromptTemplateRepository`. When neither `chat.template` nor `chat.model.template` is eager-loaded, `build_api_messages` calls the blocking `find_default()` on the event-loop thread (violating §6.1). The surrounding lore/RAG sync queries *are* offloaded via `anyio.to_thread`, making this the odd one out. `preview_prompt` has the same exposure. (Secondary: the Jinja render + history token-count in `build_api_messages` is CPU-bound work also on the loop.)
- **Why it matters:** A single blocking DB round-trip on the loop stalls every other in-flight request/stream — exactly the class §6.1 exists to prevent, hidden on a fallback branch.
- **Recommendation (medium):** Give the prompt builder an async template lookup, or wrap the `build_api_messages` call in `to_thread.run_sync` as done for lore.

### BE-11. Send path over-commits and re-fetches
- **Severity:** Medium
- **Location:** `src/chat_message/service.py:164-171,250-290,362-393`
- **Problem:** `send_message` commits up to four transactions (user message, `_update_chat_metadata`, assistant reply, `_update_chat_metadata` again). `_update_chat_metadata` re-fetches the already-loaded chat via `find_by_id` and manually sets `chat.updated_at` (redundant with `onupdate=utc_now`). The pre-LLM user-message commit is a legitimate separate unit (so a failed generation leaves the user turn for retry); the two metadata commits are not.
- **Why it matters:** Extra round-trips and transactions on the latency-critical path; a redundant SELECT of an already-loaded row every turn.
- **Recommendation (medium):** Set `chat.preview` on the same object within the message-persist unit of work; drop the separate `find_by_id`, the extra commit, and the manual `updated_at`.

### BE-12. JSON columns: bare `json` + no mutation tracking
- **Severity:** Medium · **Size:** small (but needs a migration)
- **Location:** `src/core/persistence/models/model.py:69-74,183-197`, `preset.py:31-36`, `prompt.py:76-87`; contrast `_base.py:14` (`JsonDict = JSON().with_variant(JSONB, "postgresql")`); mutation site `src/model/service.py:258-260` (`flag_modified`)
- **Problem:** `JsonDict` (→ `jsonb`) is used only by audit tables. `ModelRegistry.parameters`, `ModelFamily.parameters`, `ModelFamily.extra_metadata`, `Preset.parameters`, `PromptTemplate.component_order`/`components_enabled` use bare `JSON` (→ text-based `json` on Postgres: reparsed each read, no containment/GIN). None are `MutableDict`/`MutableList` wrapped, so SQLAlchemy only detects reassignment, not in-place mutation — the lone `flag_modified` call is a tell someone already hit this; a future `model.parameters["x"]=y` will be silently dropped.
- **Why it matters:** `ModelFamily.extra_metadata` is read on hot paths (`reasoning_mode`/`context_window` properties); `jsonb` keeps future querying/indexing open at zero cost. The missing mutation tracking is a latent data-loss footgun on the most-edited columns.
- **Recommendation (small + migration):** Switch these columns to `JsonDict`; wrap with `MutableDict.as_mutable(...)` / `MutableList.as_mutable(...)` (or document + lint the reassign-only contract and drop the one-off `flag_modified`).

### BE-13. Routers still raise raw `HTTPException` instead of domain exceptions
- **Severity:** Medium
- **Location:** `src/prompt_template/router.py:116` (`detail=f"Template rendering error: {str(e)}"`), `src/rag/router.py:128`, `src/character/router.py:90-142`, `src/chat_message/router.py:74-79`
- **Problem:** §6.3 says services raise domain exceptions and the global handler maps them. Several routers raise `HTTPException` directly. The prompt-template preview also wraps a broad `except Exception` and returns `str(e)`, surfacing confusing internal detail (e.g. a sandbox `SecurityError` string) on an otherwise-normal error.
- **Why it matters:** Bypasses the centralized domain-exception mapping, producing inconsistent error provenance across endpoints and duplicating error-shaping logic in the interface layer.
- **Recommendation (small–medium):** Replace with domain exceptions (`NotFoundError`/`ValidationError`/`ConflictError`; a dedicated one for RAG-disabled); in the preview, catch the specific render error and return a concise, stable message.

### BE-14. `ModelService` writes into the chat aggregate through a foreign repository
- **Severity:** Medium
- **Location:** `src/model/service.py:31,35,247` (`self.chat_repo.update_model_name_for_model_id(...)`)
- **Problem:** `ModelService` takes a `ChatRepository` solely to denormalize a renamed model's name onto every chat row, reaching past `chat_session`'s service into its repository to mutate another aggregate.
- **Why it matters:** A rename in one domain silently rewrites another domain's rows with no seam for `chat_session` to validate/react; also drags a cross-domain repo into `ModelService` (feeding BE-9's cycle).
- **Recommendation (small/medium):** Expose the rename as `ChatService.refresh_model_name_snapshot(model_id, name)` (or a domain event), keeping the shared transaction while restoring the boundary.

### BE-15. Inconsistent list/pagination envelopes and weakly-typed responses in the contract
- **Severity:** Medium (contract) / Low (individual types)
- **Location:** `src/core/schemas.py:46-90` (`PaginatedResponse`/`page_response`) vs `src/lore/router.py:22`, `src/rag/router.py:48` (bare `list[...]`), `src/bookmarks/router.py:10-27` (untyped `{"items": [...]}`, no `response_model`), `src/audit/schemas.py:63-88` (`{logs, total, limit, skip}`); `src/provider/schemas.py:154` (`provider_type: str` on the response while the request uses the `ProviderType` enum); `src/audit/schemas.py:112` (`period: dict[str, str | None]`); `src/rag/router.py:141-160` (`rag_status` returns an untyped dict, no `response_model`); `src/chat_message/schemas.py:111` (`parameters: dict[str, Any]`)
- **Problem:** Four different list shapes coexist; response enums are stringly-typed; a couple of endpoints have no `response_model`.
- **Why it matters:** `openapi.json` is consumed by the frontend — each divergent shape forces bespoke client handling and defeats the generic paginated-list pattern; the frontend loses enum narrowing and gets `unknown`-shaped fields.
- **Recommendation (small–medium):** Standardize collection endpoints on `PaginatedResponse[T]`; give audit pages a `PaginationMeta`-consistent `meta`; type `ProviderResponse.provider_type` as `ProviderType`; model the stats `period`; add a `response_model` to `rag_status`. (`dict[str, Any]` for opaque sampler blobs is defensible.)

---

## Tier 3 — Polish & hygiene

### BE-16. Config: free-form strings where a `Literal` would fail fast
- **Severity:** Low · **Size:** small
- **Location:** `src/core/config.py:24` (`LoggingSettings.level: str`), consumed `src/core/logging/logger_config.py:52` (`getattr(logging, level.upper())`); `src/core/config.py:72` (`EmbeddingSettings.provider: str`), dispatched `src/rag/embedding_service.py:41-53`
- **Problem:** A typo in `LOGGING__LEVEL` raises `AttributeError` at import time; an unknown `EmbeddingSettings.provider` silently falls through to the OpenAI branch, sending traffic + the OpenAI key unexpectedly.
- **Recommendation (small):** `level: Literal["DEBUG","INFO","WARNING","ERROR","CRITICAL"]`; `provider: Literal["llamacpp","openai","ollama","huggingface"]` with an explicit `else: raise` in the dispatcher.

### BE-17. `alembic check` drift guard is weaker than documented
- **Severity:** Low · **Size:** small
- **Location:** `alembic/env.py:127-134,155-160`
- **Problem:** Neither `context.configure()` sets `compare_type=True` or `compare_server_default=True` (both default off). `db-check` (documented as "fails if models drifted") won't detect column *type* changes — including a `json`↔`jsonb` divergence (BE-12) or `String(100)`→`String(200)` — nor server-default drift.
- **Recommendation (small):** Add `compare_type=True` and `compare_server_default=True` to both `context.configure()` calls.

### BE-18. Native Postgres enum for an extensible set creates migration friction
- **Severity:** Medium
- **Location:** `src/core/persistence/enums.py:14-26`; `src/core/persistence/models/provider.py:144-148`; migration `providertype` at lines 23,169
- **Problem:** `ProviderType` is a native PG `ENUM`, so adding a provider needs an `ALTER TYPE ... ADD VALUE` migration (+ the `alembic_postgresql_enum` shim in `env.py`); `ADD VALUE` can't run in a transactional migration on older PG. Meanwhile `ModelFamily.provider_types` models the same concept as a `StringList` with app-level validation — the codebase already does it both ways.
- **Recommendation (medium):** Migrate `provider_type` to `String` + app-level validation (mirroring `provider_types`), reserving native enums for genuinely fixed sets (`MessageRole`, `Gender`, `InsertionPosition`).

### BE-19. Collaborators made optional / self-constructed to accommodate tests
- **Severity:** Medium
- **Location:** `src/chat_session/service.py:45-55,121` (`message_repo`/`persona_repo` are `| None = None`, then guarded — greeting seeding silently no-ops if under-wired); `src/character/service.py:54-55` (`LoreRepository(character_repo.db)` default); `src/provider/service.py:70` (`model_cache or ModelListCache()`)
- **Problem:** Optional-for-tests weakens the production contract (the type system no longer guarantees full wiring; a mis-wire degrades silently). Self-newing collaborators is DI-in-name-only.
- **Recommendation (small):** Make collaborators required; fix tests to inject fakes/None explicitly via the factory. Model genuinely optional capabilities (RAG/rerank) explicitly rather than as nullable repos.

### BE-20. Test-suite structure and gating inconsistencies
- **Severity:** Low
- **Location:** `tests/test_message_streaming.py`, `tests/test_concurrent_streaming.py`, `tests/test_regenerate_streaming.py`, `tests/test_async_message_repository.py` (stranded at `tests/` root instead of `tests/chat_message/`); `tests/integration/test_postgres_integration.py:27` (`pytest.mark.postgres`, not `integration`, so it's *collected* under the `-m "not integration"` gate and only avoids failing via runtime `pytest.skip` in `tests/integration/conftest.py:43-45`); per-test service construction in `tests/chat_message/test_service.py:53-58,103-108,…`; duplicated OpenAI usage-parse `provider/adapters/openai.py:158-178` vs `202-215`; whole suite on in-memory SQLite (`tests/conftest.py:77`) while prod is Postgres+pgvector.
- **Recommendation (small):** Move the four files under `tests/chat_message/`; add `integration` alongside `postgres` (or make the gate `-m "not integration and not postgres"`); add a `chat_message_service` fixture; extract `_token_usage_from(usage_dict, data)` used by both OpenAI parse paths. (Mock discipline itself is good — only the LLM/HTTP boundary is mocked; ~2.3 asserts/test; no assert-free tests.)

### BE-21. Dead / vestigial surface
- **Severity:** Low
- **Location:** `src/core/persistence/base_repository.py:57-63` + `base_repository_async.py:59-66` (`find_paginated` has no prod callers — only its own test at `tests/core/persistence/test_base_repository.py:60,63`); duplicated 404 helpers `src/core/base_service.py:15` (sync `get_or_404`) vs `src/chat_message/helpers.py:8` (async `get_chat_or_404`); `src/bookmarks/router.py:18-26` (hardcoded `{"items": []}` stubs shipped in the contract; router-only slice with no service/schema); `src/main.py:119-123` (`/demo` UI served unconditionally in all environments); `src/main.py:59` (`version="0.2.5"`) vs `:112` (`"version": "0.1.0"`); the ~19-field character payload spelled out four times across `character/router.py:34-75,147-191` and `character/service.py:71-91,133-154`.
- **Recommendation (small):** Remove `find_paginated` (or fold into the ordered variant from BE-6); add an async `get_or_404`; implement or remove the bookmark stubs; gate `/demo` behind `settings.environment == "development"`; source the root version from `app.version`; introduce a character payload DTO shared by router + service.

### BE-22. Base-repository write-path smells
- **Severity:** Low
- **Location:** `src/core/persistence/base_repository.py:100-120`; `base_repository_async.py:100-108`
- **Problem:** (a) `create`/`update` `flush()` then `refresh()` on every write; since `id`/`created_at`/`updated_at` are Python-side defaults, the `refresh` SELECT is usually redundant (only `is_bookmarked`/`version` server-defaults need it), doubling round-trips on the per-message write path. (b) The async `create` opens with `if self.db.in_transaction() and self.db.is_active: await self.db.flush()` *before* `add()` — a defensive hack that doesn't belong in a generic base and points at an ordering problem elsewhere.
- **Recommendation (small):** Drop the blanket `refresh` (refresh only where a server-generated value is needed); remove or precisely document the pre-flush guard.

### Note (not itemized): streaming holds the async session for the whole completion
The async session (and its asyncpg connection) is held for the entire duration of a streamed completion, so with `pool_size=10` a burst of concurrent streams can idle-hold the pool during token generation. Acceptable for a local single-user app, but a ceiling to remember if concurrency ever grows.

---

## Big picture

- **Domains are well-factored; the shared kernel is the weak seam.** `core/` isn't actually generic — it owns every domain's ORM (BE via the model registry), a domain-aware middleware, and a domain-aware template service (BE-5). Tightening what may live in `core/` is the highest-leverage structural improvement.
- **The base repository stops one step short.** Pushing `ordered`/`find_by_name`/`defaultable` into the base + a mixin (BE-6) dissolves the largest duplicated-code block and most of the CRUD-service repetition.
- **A few genuine correctness/perf issues deserve first attention** and are cheap: RAG message-embedding scoping (BE-1), the missing `messages` composite index (BE-2), and the SSE leakage (BE-4).
- **The DI graph has real cycles** masked by lazy in-body imports in ≥4 modules (BE-9); a small set of neutral factory modules removes most of them.
- **Auth / network hardening is intentionally out of scope** for this local single-user experiment (see the note near the top; former BE-3 withdrawn). Authentication, network binding, CORS, and SSRF are deferred until the patterns stabilize. Redaction on the audit write path is already solid.

## Suggested sequencing

1. **Verify-first correctness:** BE-1 (needs live DB), BE-2, BE-4.
2. **Highest-leverage structural:** BE-6 (base repo + mixin), then BE-5 (shared-kernel boundary) and BE-9 (DI cycles) together.
3. **Cohesion:** BE-7 + BE-8 (import_card + `UploadFile` out of services).
4. **Hot-path & data hygiene:** BE-10, BE-11, BE-12 (one migration pass with BE-17 enabled).
5. **Contract & error completion:** BE-13, BE-14, BE-15.
6. **Polish:** BE-16, BE-18, BE-19, BE-20, BE-21, BE-22.

> Authentication / network hardening (former **BE-3**) is intentionally excluded — see *Out of scope* near the top.
