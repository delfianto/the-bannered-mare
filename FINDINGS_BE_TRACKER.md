# Backend Fix Tracker — The Bannered Mare

**Living execution tracker** for the findings in [FINDINGS_BE.md](FINDINGS_BE.md). That file is the immutable *diagnosis* (evidence, `file:line`, rationale); **this file is the mutable *treatment*** — the source of truth for what's done, in flight, and next. When context is summarized on a long run, resume from **this file + the code + git**, never from chat memory.

---

## STATE

- **Updated:** 2026-07-15
- **Active:** clearing the low-risk 🤖 backlog (structural refactors BE-H1/H2/H7/H6/H5 deferred per the autonomy setting)
- **Next up:** BE-M2 (cursor tie-breaker), BE-M3 (pagination constants ⚠ contract), BE-M9 (router escapes), then BE-L items.
- **Progress:** 6 / 30 done (BE-H8, BE-H4, BE-M6, BE-M5, BE-M8, BE-M9 ✓) + BE-H3 part 1 (CI gate); BE-H3 part 2 deferred (needs a VectorChord container)

---

## How to use this tracker (read once per session)

1. **Re-read this file and the specific item before touching code.** Chat history is not the source of truth; this file is.
2. **One item in flight at a time = one atomic commit**, with the ID in the message: `fix(rag): async persist+index service — BE-H6`. Then `git log --grep=BE-H6` reconstructs state even without this file.
3. **Definition of done** = acceptance criteria *actually run* + gates green + this file updated (move the item to §Completed with its commit hash + a candor note) + committed. No "should work."
4. **Write decisions/surprises into the item the moment they happen** (see how `AUDIT_LOG_v2.md` recorded its reversals). A decision left only in chat is lost.
5. **Update the STATE block** (Active / Next / Progress) on every status change.
6. **Contract footgun:** any item touching a router/schema must, in its acceptance criteria, run `scripts/openapi.sh` → `frontend: bun run api:gen` → update MSW handlers/fixtures, or the frontend silently drifts. Items with this need are marked **⚠ contract**.

**Legend** — Status: `[ ]` todo · `[~]` in progress / partial · `[!]` blocked · `[x]` done.
Exec: **🧵 main** = interdependent/structural, do sequentially in the main thread with full gate runs · **🤖 sub** = self-contained, safe to delegate to a fresh subagent.

## Gate baseline (must stay green after every item)

| Gate | Command |
|---|---|
| Lint | `cd backend && uv run ruff check .` |
| Types | `cd backend && uv run basedpyright` |
| Tests (unit) | `cd backend && uv run pytest -m "not integration"` |
| Tests (PG) | `cd backend && uv run pytest -m postgres` (needs the VectorChord container) |
| Migration drift | `cd backend && uv run alembic check` |
| Contract sync | `scripts/openapi.sh` → `openapi.json` byte-identical; `frontend: bun run api:gen` clean |

> Run backend Python tools via `uv run …` (the `.venv` shims can be stale).

---

## Wave 1 — Close the test-fidelity gaps (highest leverage; these hide everything else)

### BE-H8 · Unify the two-DB test harness · [x] DONE (see §Completed) · 🧵 main · blocks: BE-H4
- **Ref:** FINDINGS_BE.md §3 BE-H8
- **Files:** `tests/conftest.py:72,86,163-191`; `tests/chat_message/test_message_streaming.py:19-33`
- **Problem:** sync + async sessions bind to two *separate* in-memory SQLite DBs → phantom "not found" for any sync-write / async-read flow.
- **Fix:** bind both engines to **one** shared SQLite connection (shared `StaticPool` connection, or a shared temp-file DB); make the `client` fixture serve a single coherent DB.
- **Accept:** a new test writes via the sync path and reads it back via the async path in one DB and passes; all existing streaming tests still pass; `uv run pytest` green.
- **Commit:** —
- **Notes:** foundational — the two-DB trap caps what `client` can integration-test. Do before BE-H4.

### BE-H3 · SQLite hides all Postgres/pgvector behavior · [~] PARTIAL — part 1 done, part 2 deferred (see §Completed) · 🤖 sub · dep: none
- **Ref:** FINDINGS_BE.md §3 BE-H3
- **Files:** `tests/conftest.py:76,90`; `src/rag/repository_async.py:20-40,109`; `.github/workflows/backend-ci.yml:107`
- **Problem:** the 841-test unit suite runs on in-memory SQLite; all pgvector `<=>`/`ANY()`/`vchordrq`/JSONB behavior rests on ~2 integration tests behind one CI job that can silently skip.
- **Fix:** (1) add a CI status gate that **fails** the pipeline if the `integration` (Postgres) job is skipped/absent; (2) expand the PG integration tests to cover `_apply_vchordrq_tuning`, message `chat_id` scoping, threshold-equality edge, and empty results.
- **Accept:** CI fails when the PG job doesn't run; new PG tests assert vchordrq tuning is applied + message-scope + threshold edge; `uv run pytest -m postgres` green locally against the container.
- **Commit:** —
- **Notes:** re-raise of audit BE-20, which only fixed test-file location/markers, not the substance.

### BE-H4 · `chat_message` router HTTP contract untested · [x] DONE (see §Completed) · 🤖 sub · dep: BE-H8
- **Ref:** FINDINGS_BE.md §3 BE-H4
- **Files:** `src/chat_message/router.py` (10 endpoints); `tests/chat_message/test_router.py` (currently 1 test)
- **Problem:** blocking `send_message`, `_handle_blocking` error mapping, `suggest_next_turn`, `generate_chat_title`, `edit_message`, `list_alternatives`, `activate_alternative` have no HTTP-level test.
- **Fix:** add `AsyncClient(ASGITransport)` router tests reusing the existing async fixtures.
- **Accept:** tests cover blocking send (200 + persisted), edit (200/404), suggestions/title (shape), alternatives list/activate (200/404/wrong-chat), and blocking provider-error → correct HTTP status; `uv run pytest` green.
- **Commit:** —
- **Notes:** needs BE-H8's single-DB `client` fixture to be practical.

### BE-M6 · `lore` + `rag` routers have zero HTTP tests · [x] DONE (see §Completed) · 🤖 sub · dep: BE-H8
- **Ref:** FINDINGS_BE.md §4 BE-M6
- **Files:** `src/lore/router.py` (8 endpoints); `src/rag/router.py` (`:127` `/api/rag/search`, `/status`)
- **Fix:** router tests for lore CRUD/activation; for `/api/rag/search` mock `RetrievalService` and assert shape + validation; test `/status`.
- **Accept:** each endpoint has a request-validation + happy/error test; `uv run pytest` green.
- **Commit:** —

---

## Wave 2 — De-risk the architecture before it grows (sequential; full gate run each)

### BE-H1 · Introduce a Unit of Work; stop `repo.commit()` committing the shared session · [ ] · 🧵 main · dep: none
- **Ref:** FINDINGS_BE.md §3 BE-H1
- **Files:** `core/persistence/base_repository.py:184-191,206-212`; `core/base_service.py:57`; every `*/dependencies.py` that shares `DbSession`; every `*/service.py` calling `repo.commit()`
- **Problem:** `repo.commit()` commits the whole per-request session, not "the repo's work"; the transaction boundary is invisible/non-local.
- **Fix:** introduce an explicit `UnitOfWork`/transaction context owned by the service and shared by the repos it coordinates; remove `commit`/`rollback` from `BaseRepository` (keep `flush`); make the request-scoped commit explicit and singular.
- **Accept:** no `commit`/`rollback` on repositories; services own an explicit transaction boundary; a test asserts a mid-orchestration failure rolls back *all* writes in the unit; full gates green.
- **Commit:** —
- **Notes:** large blast radius — do first in this wave, one service cluster at a time, gates between.

### BE-H2 · Encapsulate modules — stop services depending on other domains' repositories · [ ] · 🧵 main · dep: BE-H1 · pairs-with: BE-M11
- **Ref:** FINDINGS_BE.md §3 BE-H2 + §4 BE-M11
- **Files:** `chat_session/service.py:9,17,18,25,26`; `profile/service.py:8-13`; `st_import/service.py:22-25`; `character/service.py:28`
- **Fix:** define a thin published port/facade per module (`exists(id)`/`get(id)`); cross-module callers depend on that, not the concrete Repository. Standardize on **one** integration style (published-service or published-port) — resolves BE-M11's inconsistency. Add a lint boundary forbidding imports of another slice's `repository.py`.
- **Accept:** no service imports another slice's `repository.py`; one documented integration style used everywhere; import-boundary check in CI; gates green.
- **Commit:** —

### BE-H7 · Break the `model` ↔ `chat_session` structural coupling · [ ] · 🧵 main · dep: BE-H2
- **Ref:** FINDINGS_BE.md §3 BE-H7
- **Files:** `chat_session/service.py:17,21-26`; `chat_session/dependencies.py:14`; `model/dependencies.py:5`; `chat_session/model_snapshot.py:14-17`
- **Problem:** bidirectional dep managed by `TYPE_CHECKING` deferral + the snapshot service; audit BE-9 removed the *runtime* cycle but the structural coupling remains.
- **Fix:** dependency-inversion seam — `model` publishes a "chats need re-snapshot on rename" event/callback that `chat_session` subscribes to, or move the snapshot concern into a small coordinating module depending on both.
- **Accept:** neither domain imports the other (even under `TYPE_CHECKING`); rename-snapshot still works with a test; gates green.
- **Commit:** —

### BE-H6 · Move RAG persist+index orchestration out of the HTTP router · [ ] · 🧵 main · dep: none · ⚠ contract (no, internal)
- **Ref:** FINDINGS_BE.md §3 BE-H6
- **Files:** `src/rag/router.py:65-121`; `src/rag/service.py`
- **Problem:** the router owns the two-phase "persist then (re)index / purge embeddings" workflow + its own try/except because the DataBank service is sync and embedding is async.
- **Fix:** give the RAG write-path an async service that owns persist+index as one operation (async repo variant, like chat); the router calls one method.
- **Accept:** `rag/router.py` create/update/delete each call a single service method with no `await _index_*` in the router; a service test covers persist+index and delete+purge; gates green.
- **Commit:** —

---

## Wave 3 — Finish the DRY job + kill the hotspots

### BE-H5 · Build `BaseCrudService` and unify the 3 `update()` idioms · [ ] · 🧵 main · dep: BE-H1
- **Ref:** FINDINGS_BE.md §3 BE-H5
- **Files:** `core/base_service.py`; the ~11 domain services (`persona/preset/profile/model_family/character/prompt_fragment/prompt_template/model/provider/chat_session/rag`)
- **Problem:** `list_all`/`get_by_id`/`delete` re-declared in 9–12 services; partial-update done 3 incompatible ways (kwargs+None, Pydantic+None, dict+setattr) with different null-clearing semantics.
- **Fix:** `BaseCrudService[T]` exposing `list_all`/`list_paginated`/`get_by_id`/`delete` + one `apply_update(entity, patch, editable)` with a single agreed null-semantics (recommend the profile-style explicit-patch dict). Domain services keep only non-generic logic.
- **Accept:** the 3 idioms collapse to one; a test proves null-clearing behaves consistently; no behavior change on existing CRUD tests; gates green.
- **Commit:** —
- **Notes:** completes audit BE-6's own recommendation (repo layer was done; service layer never was). Do after BE-H1 so the transaction boundary is settled.

### BE-M1 · Bring `AsyncBaseRepository` to parity with the sync base · [ ] · 🤖 sub · dep: none
- **Ref:** FINDINGS_BE.md §4 BE-M1 (⊕ found by 2 lenses)
- **Files:** `core/persistence/base_repository_async.py` vs `base_repository.py:78-102,215-242`
- **Fix:** port `find_all_ordered`/`find_paginated_ordered`/`_column` + the `NamedRepository`/`DefaultableRepository` mixins to the async base (or factor shared statement-building from the execute step). If a subset is intentional, document why.
- **Accept:** async base exposes the same ordered/paginated/mixin surface; an async repo test exercises `find_all_ordered`; gates green.
- **Commit:** —
- **Notes:** residual of audit BE-6 (fixed sync side only).

### BE-H9 · Decompose `import_card()` + consolidate gender parsing · [ ] · 🤖 sub · dep: none
- **Ref:** FINDINGS_BE.md §3 BE-H9
- **Files:** `character/service.py:193,222-239,305,331-337,33`
- **Fix:** extract `_map_card_gender`, `_build_character_from_card`, `_import_character_book`, `_maybe_set_png_avatar`; route all gender parsing through the existing `_parse_gender`; drop the `hasattr(enum,"value")` guards.
- **Accept:** `import_card` cyclomatic complexity materially reduced; one gender-parse path with a unit test covering `non-binary`; existing character tests green.
- **Commit:** —

### BE-M7 · Refactor `build_import_plan()` (135 LOC / cx 37) · [ ] · 🤖 sub · dep: none
- **Ref:** FINDINGS_BE.md §4 BE-M7
- **Files:** `st_import/mapper.py:135`
- **Fix:** split into `_classify_order_items(...)` + `_build_template/_build_preset/_build_profile`; turn the `nonlocal` closure state into a small `_OrderState` dataclass.
- **Accept:** no single function > ~60 LOC in the file; existing 29 mapper tests green; add a test for a new marker type.
- **Commit:** —

### BE-M3 · Shared pagination constants + one default page size · [ ] · 🤖 sub · dep: none · ⚠ contract
- **Ref:** FINDINGS_BE.md §4 BE-M3
- **Files:** `base_repository.py:21-22`; 9 service signatures (`limit: int = 10`); ~10 routers (`le=100`); `chat_session/router.py:25`, `prompt_fragment/router.py:29`, `chat_message/router.py:48` (default 20); `admin/router.py:23` (le=1000)
- **Fix:** export pagination bounds from one place; reference in both service defaults and `Query(..., le=MAX_LIMIT)`; pick one default page size.
- **Accept:** no hardcoded `10`/`100` page constants; one default; **regenerate `openapi.json` + `bun run api:gen`** (default-page changes alter the contract); gates green.
- **Commit:** —

### BE-M2 · Cursor pagination tie-breaker + same-timestamp test · [ ] · 🤖 sub · dep: none
- **Ref:** FINDINGS_BE.md §4 BE-M2
- **Files:** `chat_message/repository_async.py:63,86,89`; `core/persistence/models/base_model.py:34-39`
- **Fix:** add a secondary `id` tie-breaker to the ORDER BY / cursor WHERE.
- **Accept:** a test inserts messages with equal `created_at` and asserts stable order + no page-boundary skip/dupe; gates green.
- **Commit:** —

---

## Wave 4 — Correctness/hardening + cleanup

### BE-M4 · Fix filesystem/DB write ordering in character create/delete · [ ] · 🤖 sub
- **Ref:** FINDINGS_BE.md §4 BE-M4 · **Files:** `character/service.py:106-117,183-191,261-283`
- **Fix:** order "DB mutate → commit → then touch the filesystem" (stage to temp + move on commit for create/import).
- **Accept:** a simulated commit failure leaves no orphaned files and no fileless entity; character tests green.

### BE-M5 · Fail-fast on the placeholder `database_url` in production · [x] DONE (see §Completed) · 🤖 sub
- **Ref:** FINDINGS_BE.md §4 BE-M5 · **Files:** `core/config.py:157,202-215`
- **Fix:** extend the production validator to reject the known placeholder DSN / require an explicit `DATABASE_URL`.
- **Accept:** booting with `environment=production` + the placeholder DSN raises; a test covers it. *(Config validation, not network hardening — auth/CORS/SSRF stay out of scope.)*

### BE-M9 · Close the two router escapes · [x] DONE (see §Completed) · 🤖 sub
- **Ref:** FINDINGS_BE.md §4 BE-M9 · **Files:** `prompt_template/router.py:115`; `chat_message/router.py:129`
- **Fix:** make `build_variables` public (drop `reportPrivateUsage`); thread validated `content: str` into `_handle_blocking`/`_handle_streaming` to drop the bare `# type: ignore`.
- **Accept:** no `pyright: ignore`/bare `type: ignore` at those sites; `basedpyright` clean; gates green.

### BE-M8 · Purge banned play-by-play comments · [x] DONE (see §Completed) · 🤖 sub
- **Ref:** FINDINGS_BE.md §4 BE-M8 · **Files:** `provider/service.py:86` (delete outright) + ~24 more listed in the finding
- **Fix:** delete restatement comments; keep only WHY-comments.
- **Accept:** the listed comments gone; `ruff` clean; no logic change.

### BE-M10 · Implement or remove the `bookmarks` stub endpoints · [ ] · 🤖 sub · ⚠ contract
- **Ref:** FINDINGS_BE.md §4 BE-M10 (⊕ all 3 lenses) · **Files:** `bookmarks/router.py:20,26`
- **Fix:** remove the two empty stub routes until the feature lands (keep `/sessions`); document the module-shape deviation; add a test for the working endpoint.
- **Accept:** no endpoint returns a hardcoded `[]`; **regenerate contract + `bun run api:gen`** + update MSW; frontend builds; gates green.

### BE-M12 · Strengthen weak/thin test assertions · [ ] · 🤖 sub · dep: BE-H8 (for cross-path)
- **Ref:** FINDINGS_BE.md §4 BE-M12 · **Files:** `tests/chat_message/test_concurrent_streaming.py:30-52`; repo-layer tests; `audit/writer.py` + `tests/conftest.py:9`
- **Fix:** (a) assert each of the 10 concurrent streams ends `done`, has no `error`, reconstructs expected text, yields 10 distinct persisted messages; (b) isolated repo tests for eager-load option sets + cursor boundaries (in the PG job); (c) a scoped test that enables the audit writer and asserts rows persist *and* a writer failure never propagates to the request.
- **Accept:** the concurrency test fails if streams error; audit-write path has a real test; gates green.

### Low items (batch as 🤖 sub; one commit each or a small grouped commit)
- **BE-L1** `[ ]` inject `TemplateService` instead of inline-`new` (`prompt_template/router.py:106`, `chat_session/service.py:54`, +3).
- **BE-L2** `[ ]` reconcile `find_by_chat_id` semantics — bound the sync variant or rename (`chat_message/repository.py:17` vs `repository_async.py:54`).
- **BE-L3** `[ ]` move large model-catalog fixtures out of `.py` into validated JSON/TOML (or generate) — `fixtures/parameter_definitions.py`, `fixtures/models/*`.
- **BE-L4** `[ ]` collapse the redundant `card_parser.py:150-154` branch.
- **BE-L5** `[ ]` rename `ChatApplyProfile`; even out `list_all`/`list_models` naming.
- **BE-L6** `[ ]` flip `@pytest.mark.anyio`→`asyncio` (`tests/character/test_service.py:405`).
- **BE-L7** `[ ]` document that only 1 of the "6 integration files" runs in CI; optionally add a nightly keyed job.
- **BE-L8** `[ ]` add a carve-out comment where `health/service.py:20` + `fixtures/*` touch the session with raw SQL.
- **BE-L9** `[ ]` document that module shapes intentionally vary (router-only `admin`/`bookmarks`, etc.) so nobody enforces a false uniform template.

---

## Completed

_(Move items here with `[x]`, the fixing commit hash, and a one-line note on what changed / what surprised you. Never delete.)_

- **[x] BE-M9** (commit tagged `BE-M9`) — closed both router suppressions by refactor (no behavior change). Made `TemplateService.build_variables` **public** (the method actually lives in `templating/__init__.py`, not `prompt_template/service.py` as the finding guessed — grep was authoritative; 1 def + 2 callers updated) and dropped the `pyright: ignore[reportPrivateUsage]` in `prompt_template/router.py`. Threaded validated `content: str | None` through `_handle_blocking`/`_handle_streaming` (dropped the now-redundant `regenerate` param — `content is None ⟺ regenerate`), removing **both** bare `# type: ignore` in `chat_message/router.py` **plus** the annotated `:96` one. (basedpyright wouldn't narrow through the compound `and`-guard in a ternary, so used explicit `if/elif/else`.) Verified: ruff clean, **basedpyright 0/0/0**, pytest 909 unchanged; grep confirms zero suppressions in both routers.
- **[x] BE-M5** (commit tagged `BE-M5`) — extracted the placeholder DSN to a module constant (`_PLACEHOLDER_DATABASE_URL`) used as BOTH the `database_url` field default and the validator's compare target (can't drift), and extended `_forbid_insecure_production_defaults` to raise (after the existing CORS check) when `environment=production` + the placeholder DSN. Added 3 tests (prod-placeholder raises / prod-real boots / dev-placeholder fine) and made the pre-existing `test_production_with_explicit_origins_boots` pass an explicit DSN so it's env-independent. Verified: ruff/basedpyright clean, pytest **909** (906 + 3). **Env note:** `backend/.env` supplies a real remote DSN + `CORS_ORIGINS=["*"]` that pytest loads. Config-validation only (no auth/network/SSRF, per scope).
- **[x] BE-M8** (commit tagged `BE-M8`) — removed **21** play-by-play/restatement comments across 8 files (`provider/service.py` ×4, `character/service.py` ×4, `persona/service.py` ×2, `model_family/service.py` ×2, `prompt_template/router.py` ×1, `audit/middleware.py` ×3, `fixtures/seed_*` ×5); `git numstat` confirms **deletion-only** (comment lines only), zero executable/test changes. Deliberately KEPT `prompt_template/router.py:97` (`# Mock chat object …` — a genuine WHY). Stayed within the curated list (no un-cited sweeps). Verified: ruff/basedpyright clean, pytest 909 unchanged.
- **[~] BE-H3 — part 1 done, part 2 deferred** (commit tagged `BE-H3`) — **Part 1 (headline): added a `ci-gate` job** to `backend-ci.yml` that `needs: [lint, typecheck, test, integration]` with `if: always()` and fails unless every result is `success`, so a skipped/failed Postgres `integration` job turns the pipeline **red** instead of silently passing (point branch protection at `ci-gate`). Validated: workflow parses, all needed jobs exist. **Part 2 (expand PG tests — vchordrq tuning, message `chat_id` scoping, threshold-equality edge, empty results) DEFERRED**: authoring + verifying these needs a live VectorChord container, and **Docker is not available in this environment** — committing unverified integration tests would violate evidence-before-assertions. Follow-up: add them to `tests/integration/test_postgres_integration.py` (which already covers extension/index presence, cosine ranking + threshold, mocked-embedding retrieval, seed data) when a container is available, and confirm `uv run pytest -m postgres` green.
- **[x] BE-M6** (commit tagged `BE-M6`) — added `tests/lore/test_router.py` (24 tests: all 8 lore endpoints, happy + 404 + validation) and `tests/rag/test_router.py` (27 tests: data-bank CRUD, `POST /rag/search`, `GET /rag/status`). Hermetic via an autouse override of `get_retrieval_service` → `MagicMock(spec=RetrievalService)` with `AsyncMock` methods — no embedding backend or pgvector SQL touched; covered the documented "indexing failure swallowed → CRUD still 2xx" behavior. **Env caveat surfaced:** this machine's `.env` has RAG enabled pointing at a live embedder (`10.0.10.2:4001`), so un-mocked search would hit it — hence the autouse override. No shared conftest touched. Verified independently: ruff/basedpyright clean, pytest **906 passed / 1 skipped**.
- **[x] BE-H4** (commit tagged `BE-H4`) — added 13 HTTP-level tests to `tests/chat_message/test_router.py` via `AsyncClient(ASGITransport)`: blocking send (200 + both turns persisted / 422 / provider-fault 502), suggestions, title (+persisted), edit (200/404), alternatives list + activate (200/404/wrong-chat). Gateway mocked exactly like `test_service.py` (`patch ProviderGateway`→AsyncMock, `has_api_key` patched) — no real provider. Avoided the BE-H8 single-writer caveat by keeping the sync `get_db` override read-only. **Oddity reported (not fixed):** the blocking path collapses every upstream error to a flat 502 via `ProviderException`, losing the `classify_error` code the streaming path preserves (looks intentional — candidate for a future item). No shared conftest touched. Verified independently: ruff/basedpyright clean, pytest 906 passed.
- **[x] BE-H8** (commit tagged `BE-H8`) — replaced the two separate `sqlite:///:memory:` engines with a session-scoped `_shared_db_path` temp file that **both** the sync (`sqlite`) and async (`sqlite+aiosqlite`) engines bind to (empirically verified: two `:memory:` engines don't share; one on-disk file shares both directions). Schema created once via a setup engine; per-test isolation unchanged (existing row-cleanup teardown); removed the now-dead `_async_create_tables`. New regression test `test_cross_session_db.py` writes via the sync repo + commits, then reads via the async session. **Deliberately kept** the `get_db` overrides in the streaming tests — they isolate the sync path from the real remote Postgres in `.env`, which is orthogonal to the two-DB trap (removing them risks hanging on the remote host). Verified independently: ruff clean, basedpyright 0/0/0, pytest **842 passed / 1 skipped** (was 841, +1). **Residual → flag for BE-H4:** SQLite's single-writer limit means an *uncommitted* sync write held open across an async write raises "database is locked" (inherent, unfixable via WAL; not exercised by suite/prod) — keep sync-side writes committed before the async path writes in the same flow.
