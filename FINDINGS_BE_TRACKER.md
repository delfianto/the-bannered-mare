# Backend Fix Tracker — The Bannered Mare

**Living execution tracker** for the findings in [FINDINGS_BE.md](FINDINGS_BE.md). That file is the immutable *diagnosis* (evidence, `file:line`, rationale); **this file is the mutable *treatment*** — the source of truth for what's done, in flight, and next. When context is summarized on a long run, resume from **this file + the code + git**, never from chat memory.

---

## STATE

- **Updated:** 2026-07-15
- **Active:** ✅ **BE-H6 DONE** — RAG persist+index orchestration moved out of the router into `rag/write_service.py::DataBankWriteService` (async; composes sync persist + async index/purge, owns the best-effort try/except). Router write endpoints are one call each; internal-only (openapi byte-identical). 950 green. **Next up:** BE-H5 (BaseCrudService — unify the 3 `update()` idioms + `list/get/delete` across ~11 services), then BE-L3/L5/L7/L9. Deferred: BE-M10 (user), BE-H3 part 2 + BE-M12(c) (need Docker/live PG).
- **Next up:** BE-H5 (BaseCrudService), then the remaining BE-L items (L3/L5/L7/L9).
- **Progress:** 21 / 30 done (BE-H1, **BE-H2**, BE-H4, **BE-H6**, **BE-H7**, BE-H8, BE-H9, BE-M1, **BE-M2**, **BE-M3**, BE-M4, BE-M5, BE-M6, BE-M7, BE-M8, BE-M9, BE-L1, BE-L2, BE-L4, BE-L6, BE-L8 ✓; **BE-M11 resolved by BE-H2**) + BE-H3 part 1 (CI gate) + BE-M12 parts a/b. **Deferred:** BE-M10 (user), BE-H3 part 2 + BE-M12(c) (need Docker/live PG). **Remaining active: BE-H5, BE-L3, BE-L5, BE-L7, BE-L9.**

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

### BE-H1 · Introduce a Unit of Work; stop `repo.commit()` committing the shared session · [x] DONE (all 6 steps) · 🧵 main · dep: none

**Design (chosen):** a thin service-owned `UnitOfWork` (`core/persistence/unit_of_work.py`) wrapping the request session; a service holds one and commits its work ONCE via `uow.commit()`; repos keep only `flush()`. Behavior-identical (`uow.commit()` ≡ the old `repo.commit()` on the same session), but the boundary is explicit and singular. Migrates incrementally — `repo.commit()` stays on `BaseRepository` until every service is moved, so nothing breaks mid-rollout. Services take `uow: UnitOfWork | None = None` with a `uow or UnitOfWork(<repo>.db)` fallback (the BE-L1 idiom) → zero test edits.

**Rollout checklist:**
- [x] **Step 1 — foundation + proof:** `UnitOfWork` class + export; `set_as_default(repo, entity, uow=None)` transitional shim; migrated the `profile` cluster (service + DI). Verified: ruff/basedpyright clean, profile 22 + full suite **937**.
- [x] **Step 2 — 7 sync CRUD services** (persona, preset, model_family, prompt_fragment, prompt_template, model, provider): injected UoW, 30 `repo.commit()`→`uow.commit()` (1:1, no consolidation); `set_as_default` finalized to require `uow` (all 4 callers pass it). Verified: ruff/basedpyright clean, 937, zero test edits.
- [x] **Step 3 — orchestrating sync services** (character, lore, st_import, chat_session, `rag/service.py`): injected UoW, 19 sites (17 commit + 2 rollback) → `uow.*`, 1:1. All sync service layer now migrated (only the async `chat_message` `await ...commit()` remain → Step 5). Verified: ruff/basedpyright clean, 937, zero test edits.
- [x] **Step 4 — removed `commit`/`rollback` from `BaseRepository`** (kept `flush`/`refresh`). Grep-verified no sync caller remained; migrated the 5 fixture seeders + 2 repo tests (`test_base_repository`, `test_model_family/test_repository`) from `repo.commit()`→`repo.db.commit()` (behavior-identical). Verified: ruff/basedpyright clean, full suite 3/3 green.
- [x] **Step 5 — async path:** added `AsyncUnitOfWork`; migrated `ChatMessageService` (5 sites) + its `AlternativesService`/`AuxiliaryGenerationService` sub-services (passed `self.uow`, all sharing the one request `AsyncSession`) + `RetrievalService` (3 sites); the deliberate two-commit send sequence preserved 1:1; migrated the 2 async repo tests (+ 3 RAG rerank mocks: `embedding_repo.commit`→`embedding_repo.db.commit` since the service now commits via the uow's session); removed `commit`/`rollback` from `AsyncBaseRepository`. `audit/writer.py` untouched. Verified: ruff/basedpyright clean, 939, **concurrency 10/10 non-flaky**.
- [x] **Step 6 — atomicity test:** `tests/core/persistence/test_unit_of_work.py` — two repos share one UoW; `uow.rollback()` after both flush discards BOTH writes (and `uow.commit()` persists both). Directly asserts the finding's "mid-orchestration failure rolls back all writes in the unit."
- **Out of scope (own sessions):** `audit/writer.py` (isolated best-effort session), `fixtures/seed_*` (startup seeding outside request scope).
- **Ref:** FINDINGS_BE.md §3 BE-H1
- **Files:** `core/persistence/base_repository.py:184-191,206-212`; `core/base_service.py:57`; every `*/dependencies.py` that shares `DbSession`; every `*/service.py` calling `repo.commit()`
- **Problem:** `repo.commit()` commits the whole per-request session, not "the repo's work"; the transaction boundary is invisible/non-local.
- **Fix:** introduce an explicit `UnitOfWork`/transaction context owned by the service and shared by the repos it coordinates; remove `commit`/`rollback` from `BaseRepository` (keep `flush`); make the request-scoped commit explicit and singular.
- **Accept:** no `commit`/`rollback` on repositories; services own an explicit transaction boundary; a test asserts a mid-orchestration failure rolls back *all* writes in the unit; full gates green.
- **Commit:** —
- **Notes:** large blast radius — do first in this wave, one service cluster at a time, gates between.

### BE-H2 · Encapsulate modules — stop services depending on other domains' repositories · [x] DONE (all 4 steps; resolves BE-M11) · 🧵 main · dep: BE-H1 · pairs-with: BE-M11

**Design (chosen):** cross-module READS depend on a thin structural read `Port` (`core/persistence/ports.py`: `ExistsPort` = `exists(id)`, `ReadPort[T]` adds `find_by_id`); the target repo satisfies it structurally so DI passes the concrete repo unchanged (zero test edits). Cross-module WRITES go through the target slice's published `Service`. The enforced rule: **a `service.py` never imports another slice's `repository.py`** (custom AST lint, since ruff can't express a per-slice contextual ban).

**Rollout checklist:**
- [x] **Step 1 — proof:** `ExistsPort`/`ReadPort` + migrated `profile` (4 foreign repos → `ExistsPort`, used only for `.exists()`). Verified: ruff/basedpyright clean (structural satisfaction holds), profile 22 + full 939, zero test edits, no foreign repo import in `profile/service.py`.
- [x] **Step 2 — entangled reads** (all reads migrated: `model`, `prompt_template`, `chat_session`). Design: simple reads → thin `Port`; complex reads → target **Service**; foreign-session access → caller's OWN session. (The one WRITE that surfaced en route — chat_session's greeting seed — is carried into Step 3.)
  - [x] **`model`** (commit tagged `BE-H2`) — (a) `provider` → `provider_reader: ReadPort[Provider]` (sole use: `get_or_404` in `_validate_route`); (b) `model_family` → injected `ModelFamilyService`: `_get_family`→`family_service.get_by_id`, discovery fallback → `resolve_family(self.model_repo.db, id) or self.family_service.get_first()` (new thin `ModelFamilyService.get_first()` wraps `find_first`; `resolve_family` now takes model's OWN session — same request session, behavior identical); (c) enabler `get_or_404(repo: ReadPort[T])` in `base_service.py` (dropped the now-unused `BaseRepository` import). DI rewired to inject `ModelFamilyService` + `ProviderRepository`-as-`ReadPort`. **Candor — NOT zero-test-edits:** the service-injection (part b) forced the 2 direct `ModelService(...)` constructions (`tests/model/test_service.py`, `tests/chat_session/test_loose_coupling.py`) to swap `ModelFamilyRepository(db)`→`ModelFamilyService(ModelFamilyRepository(db))` — repos lack `get_by_id`/`get_first`, so the "zero test edits" property holds only for the pure-`Port` swaps (provider part-a needed none). +2 `get_first` unit tests. No foreign `repository.py` import remains in `model/service.py`. Verified: ruff clean, basedpyright 0/0/0, pytest **941** (939 + 2).
  - [x] **`prompt_template`**→`prompt_fragment` (commit tagged `BE-H2`) — classified: the sole use (`delete_orphaned` on template delete) is a **write**, so per the design it now goes through the published `FragmentService` (new `FragmentService.delete_orphaned` delegating to the repo — **flush-only, participates in the caller's UoW**, never self-commits, preserving BE-H1 single-commit atomicity). Added `FragmentService.from_session(db)` classmethod so `prompt_template/service.py`'s default fallback builds the service without importing the fragment repos (keeps the boundary). DI injects `FragmentService` via `get_fragment_service`. Test churn: only the 3 orphan tests swapped `FragmentRepository(db)`→their already-built `fragment_service` var; +2 fragment-service tests (delegation + a rollback test pinning the no-self-commit contract). No foreign `repository.py` import remains in `prompt_template/service.py`. Verified: ruff clean, basedpyright 0/0/0, pytest **943**.
  - [x] **`chat_session`** reads (commit tagged `BE-H2`) — character/model/profile/persona are all pure reads (`get_or_404`/`find_by_id`) → typed `ReadPort[…]`, keeping the param NAMES so DI + all ~13 `ChatService(...)` test constructions pass concrete repos unchanged (**zero test/DI edits**, the profile idiom). Removed 3 runtime + 1 TYPE_CHECKING foreign repo import. **Deferred (→ Step 3 / BE-H7):** the sole WRITE — `message_repo.create()` seeding the greeting on chat create — stays on the sync `MessageRepository` (the one foreign repo import still in the file). It's a cross-async-boundary write into chat_message tangled with the BE-H7 chat_message↔chat_session cycle, so it moves behind a chat_message seam there, not bolted on here. Verified: ruff clean, basedpyright 0/0/0, pytest 943.
- [~] **Step 3 — writes via services** (target slices' published services, not their repos; flush-only methods participate in the caller's UoW — pattern proven by `FragmentService.delete_orphaned`). Watch for service→service cycles.
  - [x] **`character`→`lore`** (commit tagged `BE-H2`) — both the import WRITE (create lorebook + entries) and the export READ (`find_for_character_with_entries`) go through `LoreService`: new `LoreService.import_character_book(book, char_id, name)` (flush-only; owns the `build_lorebook`/`map_lore_entry` logic moved out of CharacterService) + `list_for_character_with_entries()`. `character/service.py` drops both lore-repo imports AND the `lore.card_import` import; the `_import_character_book` helper is inlined away. ctor `(character_repo, lore_service)`; DI injects `LoreService` via `get_lore_service`. Test churn: ~20 identical `CharacterService(repo, LoreRepository, LoreEntryRepository)` → wrapped in `LoreService(...)` (one replace_all). Verified: ruff clean, basedpyright 0/0/0, pytest 943.
  - [x] **`st_import`→{preset, profile, fragment, template}** (commit tagged `BE-H2`) — **user-decided: route through services** (over the exempt-as-application-service alternative). Added flush-only, validation-skipping import seams to all 4 domain services: `PromptTemplateService.create_imported`; `FragmentService.create_imported` + `attach_imported` (with `depth`, ST `at_depth`) + `find_by_content`; `PresetService.create_imported`; `ProfileService.create_imported` (with `source`/`source_filename`, skips `_validate_refs`) — plus `find_by_name` on each (unique-naming reads). st_import depends on the 4 services and owns the single `uow` (commits once; the seams only flush). DI wires the 4 `get_*_service` providers on one session; the test factory uses `get_profile_service(db)` + direct construction. **Atomicity preserved & proven:** `test_failure_mid_persist_rolls_back` (patches the underlying preset repo's `create` to raise) still shows template+fragments+preset+profile all rolled back. No foreign `repository.py` import remains in `st_import/service.py`. Verified: ruff clean, basedpyright 0/0/0, pytest 943.
  - [x] **`chat_session`→`chat_message`** (greeting seed) — done under **BE-H7 Part B** (commit tagged `BE-H7`): new sync `chat_message/seeding.py::MessageSeedService.seed_greeting` (flush-only, participates in the caller's UoW) injected into `ChatService` (`message_repo`→`message_seeder`; the seam is imported under TYPE_CHECKING, so it's a service import, not a `repository.py` one). **`chat_session/service.py` now has zero foreign `repository.py` imports.** ~13 `ChatService(...)` test constructions wrapped the arg in `MessageSeedService(...)`; +1 test asserting the greeting is actually seeded. Verified: 944 green.
- [x] **Step 4 — import-boundary lint** (commit tagged `BE-H2`) — implemented as a pytest guard `tests/test_service_import_boundaries.py` that AST-walks every `src/<slice>/service.py` and fails on any import of another slice's `repository`/`repository_async` (incl. under `TYPE_CHECKING`, all import forms). **Chosen as a test, not a standalone CI step**, so it runs in the already-protected test gate AND locally — strictly harder to silently skip than a separate job (cf. BE-H3). Verified non-vacuous (its detector sees the real couplings). 945 green.
- **Out of scope → now the lint's documented allowlist:** `fixtures/service.py` (startup seeding, legitimately wires every slice); `(chat_message → chat_session)` (a message loads its parent chat — intrinsic sub-aggregate coupling on the async streaming hot path). Add to the allowlist only with a WHY.
- **Ref:** FINDINGS_BE.md §3 BE-H2 + §4 BE-M11
- **Files:** `chat_session/service.py:9,17,18,25,26`; `profile/service.py:8-13`; `st_import/service.py:22-25`; `character/service.py:28`
- **Fix:** define a thin published port/facade per module (`exists(id)`/`get(id)`); cross-module callers depend on that, not the concrete Repository. Standardize on **one** integration style (published-service or published-port) — resolves BE-M11's inconsistency. Add a lint boundary forbidding imports of another slice's `repository.py`.
- **Accept:** no service imports another slice's `repository.py`; one documented integration style used everywhere; import-boundary check in CI; gates green.
- **Commit:** —

### BE-H7 · Break the `model` ↔ `chat_session` structural coupling · [x] DONE · 🧵 main · dep: BE-H2
- **Part A** (commit tagged `BE-H7`) — the model→chat_session snapshot coupling is inverted via a `ChatSnapshotPort` Protocol in `model/ports.py`: `model/service.py` now depends on that port (its own slice), NOT `chat_session.model_snapshot` — the TYPE_CHECKING import is gone. `chat_session`'s `ChatModelSnapshotService` satisfies the port structurally (it does NOT import the port → no reverse coupling), so DI passes it unchanged → **zero test edits**; the rename-snapshot test (`test_update_display_name_snapshots_onto_chats`) still green.
- **Part B** (commit tagged `BE-H7`) — the folded-in greeting-seed write: new sync `chat_message/seeding.py::MessageSeedService.seed_greeting` (flush-only) injected into `ChatService`; chat_session/service.py drops its last foreign repo reference. +1 seeding test.
- **Result:** neither `model` nor `chat_session` imports the other in domain logic (service.py / model_snapshot.py) — even under TYPE_CHECKING. Cross-slice wiring stays in the DI composition roots (`*/dependencies.py`), which is the accepted single point of contact (the BE-H2 Step 4 lint targets `service.py`, not `dependencies.py`). Gates green (944).
- **Note / still open (→ BE-H2 Step 4):** `chat_message/service.py` still imports `chat_session.repository_async` (the async READ path, chat_message→chat_session). That's a separate coupling outside BE-H7's model↔chat_session scope; Step 4 decides fix-vs-allowlist.
- **Ref:** FINDINGS_BE.md §3 BE-H7
- **Files:** `chat_session/service.py:17,21-26`; `chat_session/dependencies.py:14`; `model/dependencies.py:5`; `chat_session/model_snapshot.py:14-17`
- **Problem:** bidirectional dep managed by `TYPE_CHECKING` deferral + the snapshot service; audit BE-9 removed the *runtime* cycle but the structural coupling remains.
- **Fix:** dependency-inversion seam — `model` publishes a "chats need re-snapshot on rename" event/callback that `chat_session` subscribes to, or move the snapshot concern into a small coordinating module depending on both.
- **Accept:** neither domain imports the other (even under `TYPE_CHECKING`); rename-snapshot still works with a test; gates green.
- **Also owns (folded in from BE-H2 Step 3):** the `chat_session`→`chat_message` greeting-seed write. Plan: a sync `chat_message/seeding.py::MessageSeedService.seed_greeting` (flush-only, participates in the caller's UoW), injected into `ChatService` (rename `message_repo`→`message_seeder`, typed under `TYPE_CHECKING`; construct in `chat_session/dependencies.py` as `MessageSeedService(MessageRepository(db))`). This removes chat_session/service.py's last foreign `repository.py` import — the prerequisite for BE-H2 Step 4's lint. Watch the bidirectional import order (mirror the existing MessageRepository TYPE_CHECKING+DI pattern). ~13 `ChatService(...)` test constructions across `tests/chat_session/test_service.py`, `test_loose_coupling.py`, `tests/profile/test_apply.py` need the arg wrapped in `MessageSeedService(...)`.
- **Commit:** —

### BE-H6 · Move RAG persist+index orchestration out of the HTTP router · [x] DONE · 🧵 main · dep: none · ⚠ contract (no, internal)
- **Ref:** FINDINGS_BE.md §3 BE-H6
- **Files:** `src/rag/router.py:65-121`; `src/rag/service.py`
- **Problem:** the router owns the two-phase "persist then (re)index / purge embeddings" workflow + its own try/except because the DataBank service is sync and embedding is async.
- **Fix:** give the RAG write-path an async service that owns persist+index as one operation (async repo variant, like chat); the router calls one method.
- **Accept:** `rag/router.py` create/update/delete each call a single service method with no `await _index_*` in the router; a service test covers persist+index and delete+purge; gates green.
- **DONE** (commit tagged `BE-H6`) — new `rag/write_service.py::DataBankWriteService` (async) composes the sync `DataBankService` (persist) + the async `RetrievalService | None` (index/purge) and owns the two-phase workflow + best-effort try/except that used to live in the router. The router's `_index_entry` helper + `logger` are gone; `create`/`update`/`delete` are now one `await service.{create,update,delete}(...)` each (list/get stay on `DataBankServiceDep`, search on `RetrievalServiceDep`). Kept the persist path **sync** (composition, not a new async repo) — behavior-identical to the old async-endpoint-calls-sync-service flow, and lighter than the "(async repo variant)" hint. DI: `get_data_bank_write_service` depends on `get_data_bank_service` + `get_retrieval_service`, so the router tests' `get_retrieval_service` override still flows into the orchestrator → **27 router tests pass unchanged** + 4 new `TestDataBankWriteService` tests (persist+index, index-failure-survival, delete+purge, RAG-disabled skip). **No contract change** (Depends params aren't in the schema): regenerated `openapi.json` → byte-identical. Verified: ruff/basedpyright clean, pytest **950**.
- **Commit:** `BE-H6`

---

## Wave 3 — Finish the DRY job + kill the hotspots

### BE-H5 · Build `BaseCrudService` and unify the 3 `update()` idioms · [~] IN PROGRESS · 🧵 main · dep: BE-H1
- **Ref:** FINDINGS_BE.md §3 BE-H5
- **Files:** `core/base_service.py`; the ~11 domain services (`persona/preset/profile/model_family/character/prompt_fragment/prompt_template/model/provider/chat_session/rag`)
- **Problem:** `list_all`/`get_by_id`/`delete` re-declared in 9–12 services; partial-update done 3 incompatible ways (kwargs+None, Pydantic+None, dict+setattr) with different null-clearing semantics.
- **Fix:** `BaseCrudService[T]` exposing `list_all`/`list_paginated`/`get_by_id`/`delete` + one `apply_update(entity, patch, editable)` with a single agreed null-semantics (recommend the profile-style explicit-patch dict). Domain services keep only non-generic logic.
- **Accept:** the 3 idioms collapse to one; a test proves null-clearing behaves consistently; no behavior change on existing CRUD tests; gates green.
- **User decision:** full `BaseCrudService[T, R]` base class (not the helper-only alternative).
- **Design notes:** base is `BaseCrudService[T: BaseModel, R: BaseRepository[Any]]` (two params so `self.repo` keeps the subclass's concrete repo type; the self-referential bound `R: BaseRepository[T]` tripped basedpyright, so R is bound to `BaseRepository[Any]` — callers still see precise `-> T`). Provides `list_all` (→ `find_all_ordered`), `get_by_id`, `delete` (plain); subclasses override where behavior differs. `apply_update(entity, patch, editable)` is a free helper (usable by non-inheriting services too); null policy stays per-endpoint via how the caller builds `patch` (skip-on-None services omit None keys → **no behavior change**; profile/chat pass explicit-present). Renames each service's `self.<x>_repo` → `self.repo`.
- **Rollout (gates between each):**
  - [x] **base + `apply_update` + `preset`** (commit `BE-H5`) — proof: generics validated by basedpyright, 950 green, zero behavior change. `preset` inherits list_all/get_by_id/delete; keeps list_paginated/create/update(apply_update, skip-on-None)/set_default/import-seam. (1 test ref `service.preset_service.preset_repo`→`.repo`.)
  - [x] **model_family, profile, persona** (commit `BE-H5`) — all inherit get_by_id; model_family overrides list_all(→find_all)/list_paginated/delete(in-use guard) + update via `apply_update(model_dump(exclude_none=True))`; profile inherits list_all/delete, keeps clearable dict-patch update via apply_update + 4 foreign ExistsPorts + import seam; persona inherits list_all, overrides list_paginated/delete(files), async create/update (apply_update). Base `get_by_id`/`delete` made **positional-only** so descriptive override param names (`persona_id`, `family_id`) stay LSP-compatible. Renamed `self.<x>_repo`→`self.repo`; no external refs. 950 green.
  - [x] **prompt_template, prompt_fragment** (commit `BE-H5`) — prompt_template inherits list_all/get_by_id, overrides list_paginated + delete (orphan cleanup), update via apply_update (skip-on-None) after Jinja validate, keeps import seam + set_default. FragmentService inherits get_by_id + plain delete; overrides list_all (optional filter params — LSP-safe) + list_paginated; keeps `from_session`, template-fragment ops, all import seams; update via apply_update. 950 green.
  - [x] **model, provider** (commit `BE-H5`) — both inherit get_by_id; override list_all (find_all). model inherits plain delete, overrides list_paginated, keeps its **bespoke validate-then-mutate update** (display_name→chat snapshot, family-change revalidation) — genuinely non-generic, NOT forced through apply_update — plus all route/create/persist logic. provider overrides delete (raises — providers aren't deletable), has no list_paginated, keeps update_flags + discovery; its update() now uses apply_update (skip-on-None) after the api-key-env validation. Renamed repo attr → self.repo. 950 green.
  - [ ] **rag (DataBank), character, chat_session** (selective inherit for the async/cursor/complex ones)
  - [ ] **null-clearing test** proving `apply_update` semantics (profile clear vs skip-on-None)
- **Commit:** —
- **Notes:** completes audit BE-6's own recommendation (repo layer was done; service layer never was). Do after BE-H1 so the transaction boundary is settled.

### BE-M1 · Bring `AsyncBaseRepository` to parity with the sync base · [x] DONE (see §Completed) · 🤖 sub · dep: none
- **Ref:** FINDINGS_BE.md §4 BE-M1 (⊕ found by 2 lenses)
- **Files:** `core/persistence/base_repository_async.py` vs `base_repository.py:78-102,215-242`
- **Fix:** port `find_all_ordered`/`find_paginated_ordered`/`_column` + the `NamedRepository`/`DefaultableRepository` mixins to the async base (or factor shared statement-building from the execute step). If a subset is intentional, document why.
- **Accept:** async base exposes the same ordered/paginated/mixin surface; an async repo test exercises `find_all_ordered`; gates green.
- **Commit:** —
- **Notes:** residual of audit BE-6 (fixed sync side only).

### BE-H9 · Decompose `import_card()` + consolidate gender parsing · [x] DONE (see §Completed) · 🤖 sub · dep: none
- **Ref:** FINDINGS_BE.md §3 BE-H9
- **Files:** `character/service.py:193,222-239,305,331-337,33`
- **Fix:** extract `_map_card_gender`, `_build_character_from_card`, `_import_character_book`, `_maybe_set_png_avatar`; route all gender parsing through the existing `_parse_gender`; drop the `hasattr(enum,"value")` guards.
- **Accept:** `import_card` cyclomatic complexity materially reduced; one gender-parse path with a unit test covering `non-binary`; existing character tests green.
- **Commit:** —

### BE-M7 · Refactor `build_import_plan()` (135 LOC / cx 37) · [x] DONE (see §Completed) · 🤖 sub · dep: none
- **Ref:** FINDINGS_BE.md §4 BE-M7
- **Files:** `st_import/mapper.py:135`
- **Fix:** split into `_classify_order_items(...)` + `_build_template/_build_preset/_build_profile`; turn the `nonlocal` closure state into a small `_OrderState` dataclass.
- **Accept:** no single function > ~60 LOC in the file; existing 29 mapper tests green; add a test for a new marker type.
- **Commit:** —

### BE-M3 · Shared pagination constants + one default page size · [x] DONE (see §Completed) · 🤖 sub · dep: none · ⚠ contract
- **Ref:** FINDINGS_BE.md §4 BE-M3
- **Files:** `base_repository.py:21-22`; 9 service signatures (`limit: int = 10`); ~10 routers (`le=100`); `chat_session/router.py:25`, `prompt_fragment/router.py:29`, `chat_message/router.py:48` (default 20); `admin/router.py:23` (le=1000)
- **Fix:** export pagination bounds from one place; reference in both service defaults and `Query(..., le=MAX_LIMIT)`; pick one default page size.
- **Accept:** no hardcoded `10`/`100` page constants; one default; **regenerate `openapi.json` + `bun run api:gen`** (default-page changes alter the contract); gates green.
- **Commit:** —

### BE-M2 · Cursor pagination tie-breaker + same-timestamp test · [x] DONE (see §Completed) · 🤖 sub · dep: none
- **Ref:** FINDINGS_BE.md §4 BE-M2
- **Files:** `chat_message/repository_async.py:63,86,89`; `core/persistence/models/base_model.py:34-39`
- **Fix:** add a secondary `id` tie-breaker to the ORDER BY / cursor WHERE.
- **Accept:** a test inserts messages with equal `created_at` and asserts stable order + no page-boundary skip/dupe; gates green.
- **Commit:** —

---

## Wave 4 — Correctness/hardening + cleanup

### BE-M4 · Fix filesystem/DB write ordering in character create/delete · [x] DONE (see §Completed) · 🤖 sub
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

### BE-M10 · Implement or remove the `bookmarks` stub endpoints · [!] DEFERRED (user decision) · 🤖 sub · ⚠ contract
- **Ref:** FINDINGS_BE.md §4 BE-M10 (⊕ all 3 lenses) · **Files:** `bookmarks/router.py:20,26`
- **Fix:** remove the two empty stub routes until the feature lands (keep `/sessions`); document the module-shape deviation; add a test for the working endpoint.
- **Accept:** no endpoint returns a hardcoded `[]`; **regenerate contract + `bun run api:gen`** + update MSW; frontend builds; gates green.
- **DEFERRED (user decision):** the plan assumed the two stubs were unused, but the **frontend actively consumes all three** — `useBookmarks.ts` fetches `/characters`, `/sessions`, `/messages` in parallel and `BookmarksView.vue` renders a section per type (characters/messages only `v-if length > 0`, so they never show while the stubs return `[]`; the `:190` comment already documents the stub nature). Removing the routes would break the typed-client build and require ripping out the built-out characters/messages UI scaffolding intended for a soon-to-land favoriting/pinning feature. User chose to **keep the stubs and defer** rather than remove that scaffolding. Revisit when favoriting/pinning actually lands (then implement, not remove). **No code changed.**

### BE-M12 · Strengthen weak/thin test assertions · [~] PARTIAL — (a)+(b) done; (c) audit-writer deferred (see §Completed) · 🤖 sub · dep: BE-H8 (for cross-path)
- **Ref:** FINDINGS_BE.md §4 BE-M12 · **Files:** `tests/chat_message/test_concurrent_streaming.py:30-52`; repo-layer tests; `audit/writer.py` + `tests/conftest.py:9`
- **Fix:** (a) assert each of the 10 concurrent streams ends `done`, has no `error`, reconstructs expected text, yields 10 distinct persisted messages; (b) isolated repo tests for eager-load option sets + cursor boundaries (in the PG job); (c) a scoped test that enables the audit writer and asserts rows persist *and* a writer failure never propagates to the request.
- **Accept:** the concurrency test fails if streams error; audit-write path has a real test; gates green.

### Low items (batch as 🤖 sub; one commit each or a small grouped commit)
- **BE-L1** `[x]` DONE (see §Completed) — `TemplateService` injected via a new `templating/dependencies.py` provider into all 5 sites; `| None = None` ctor default keeps ~40 test constructions valid.
- **BE-L2** `[x]` DONE (see §Completed) — sync `find_by_chat_id` → `find_all_by_chat_id` (0 callers; behavior-preserving rename to disambiguate from the bounded async method).
- **BE-L3** `[ ]` move large model-catalog fixtures out of `.py` into validated JSON/TOML (or generate) — `fixtures/parameter_definitions.py`, `fixtures/models/*`.
- **BE-L4** `[x]` DONE — removed the crash-prone branch A, kept the `isinstance`-guarded B (valid cards unchanged); docstring refreshed.
- **BE-L5** `[ ]` rename `ChatApplyProfile`; even out `list_all`/`list_models` naming.
- **BE-L6** `[x]` DONE — `@pytest.mark.anyio`→`asyncio` (`test_service.py:405`); zero anyio markers remain.
- **BE-L7** `[ ]` document that only 1 of the "6 integration files" runs in CI; optionally add a nightly keyed job.
- **BE-L8** `[x]` DONE — WHY carve-out comments at `health/service.py` (liveness probe) + `seed_model_families.py` (startup seeding outside the DI lifecycle).
- **BE-L9** `[ ]` document that module shapes intentionally vary (router-only `admin`/`bookmarks`, etc.) so nobody enforces a false uniform template.

---

## Completed

_(Move items here with `[x]`, the fixing commit hash, and a one-line note on what changed / what surprised you. Never delete.)_

- **[x] BE-M3** (commit tagged `BE-M3`) — new `core/pagination.py` is the single home for `DEFAULT_PAGE_SIZE=10`, `MAX_PAGE_SIZE=100`, `ADMIN_DEFAULT_PAGE_SIZE=100`, `ADMIN_MAX_PAGE_SIZE=1000`. Both base repos alias `DEFAULT_LIMIT`/`MAX_LIMIT` to them; the 10 routers, 10 services, and the chat_session/prompt_fragment repo defaults all reference the constants (no hardcoded 10/20/100/1000 page ints left in those layers). **Chosen single default = 10** (the existing `DEFAULT_LIMIT` + majority): the 3 conversation endpoints (chats list, messages, prompt-fragments) moved 20→10. **Contract impact = 3 lines** in `openapi.json` (`default: 20→10`); `schema.d.ts` **byte-identical** (openapi-typescript doesn't encode query-param defaults into TS types), so the regen was a no-op there. **Low real-world risk:** the frontend always passes an explicit `limit` (`useCursorList` pageSize=20), so the default is doc-level for the app — only direct-API callers omitting `limit` see it. Kept MSW mocks faithful (handlers for chats/messages/fragments + the loader default → 10). Admin bounds (100/1000) unchanged, just centralized. Updated 2 backend tests asserting the old default (20→10). **Process scar:** an accidental repo-root `ruff format .` reformatted 8 out-of-scope files (scripts + drift files) — reverted; always run backend tools from `backend/`. Verified: **backend** ruff/basedpyright clean + pytest 946; **frontend** `bun run build` + 60 tests green.
- **[x] BE-M2** (commit tagged `BE-M2`) — gave message cursor pagination a total order. Added an `id` tie-breaker to the ORDER BY of both `find_by_chat_id` and `find_latest_by_chat_id` (`created_at desc, id desc`), and made the cursor a **composite** `(created_at, id)`: the WHERE became `created_at < before OR (created_at == before AND id < before_id)` (explicit form, not a SQL row-value, so it's portable to SQLite too). The service now encodes/parses the cursor as `"<iso8601>|<id>"` — **not a contract change** (the `cursor` field stays an opaque `string`; verified the frontend stores & replays it verbatim in `useCursorList.ts`, never parsing it) so no openapi regen. Legacy timestamp-only cursors still parse (id tie-breaker absent → old strict-`<` behavior for that one in-flight request). **Replaced** the BE-M12 test that pinned the buggy behavior (`..._current_behavior`) with two asserting the fix: a total-order check across a shared instant, and a 5-rows-same-`created_at` composite-cursor walk proving no boundary skip/dupe. Deliberately did NOT add a DB index (correctness-only per scope; would need a migration). Verified: ruff clean, basedpyright 0/0/0, pytest **946**.
- **[x] concurrency-test flake FIX** (commit tagged `BE-M12`) — the BE-M12 rewrite of `test_concurrent_streaming` was **~1-in-6 flaky**: the 10 concurrent streams each offload the sync prompt build (`find_default`) to a worker thread, and they raced on BE-H8's single shared SQLite connection (`StaticPool`) → `IndexError` in SQLAlchemy's result proxy → an `error` event → assertion fail. **Root cause: test-harness only** (prod gives each request its own connection). Fixed by binding the test's sync sessions to a `NullPool` engine over the same DB file (per-connection reads mirroring prod; writes go async so no single-writer lock). Verified: **15/15 isolation + 6/6 full-suite** (was failing ~1/6).
- **[x] BE-M4** (commit tagged `BE-M4`) — reordered filesystem vs DB writes in `character/service.py`: `delete` now `repo.delete()`→`commit()`→**then** `delete_character_files()` (a failed commit no longer leaves a fileless entity); `create`/`import` keep write-before-commit (forced by a tested `save_character_avatar()`-returns-paths → DB-column contract) but wrap the commit in `_commit_or_purge_avatar_files`, removing the just-written files if the commit fails (closes the finding's "no compensating cleanup" defect). `update` intentionally untouched (overwrites in place — cleanup there would delete a valid avatar). Success-path file layout byte-identical. Residual (documented): a narrow write→commit window remains, fully closeable only via temp-stage-and-move in `storage.py` (too invasive for MEDIUM). Verified: 57 character/storage tests + pytest 937.
- **[x] BE-L1 + BE-L2** (commit tagged `BE-L1`, `BE-L2`) — **BE-L1:** new `templating/dependencies.py` (`get_template_service` + `TemplateServiceDep`, a shared home since 3 domains consume the stateless `TemplateService`); injected into all 5 inline-`new` sites (prompt_builder, prompt_template/service, prompt_fragment/service, chat_session/service, prompt_template/router) via `Depends` + ctor `template_service: TemplateService | None = None` (mirrors the existing `fragment_repo` pattern → **zero test edits** for ~40 positional constructions). **BE-L2:** sync `find_by_chat_id` → `find_all_by_chat_id` — 0 callers (all 6 sites `await` the async repo; the sync repo is used only for `.create()`), so a behavior-preserving rename disambiguating from the bounded async method. Verified: ruff clean, basedpyright 0/0/0, pytest 937.
- **[~] BE-M12 — (a)+(b) done; (c) deferred** (commit tagged `BE-M12`) — **(a):** discovered the concurrency test was **fully vacuous** — it POSTed to `/messages/stream` (not a route → matched `PUT /{id}` → **405**, a 1-line body), so `all(count>0)` passed trivially and the mock gateway was never invoked. Rewrote it to drive the real `?stream=true` endpoint over 10 concurrent `asyncio.gather` requests (each its own sync+async session, as prod does), asserting per stream: 200 + `text/event-stream`, opens with `start`+`message_id`, reconstructs the mocked reply, terminates `done`, **zero `error` events**, 10 distinct streamed ids, persisted ⊆ streamed (non-empty). Stress-tested 15/15. (Exact 10/10 persistence isn't reliably assertable — the test harness's `StaticPool` single SQLite connection races concurrent writes; documented as a harness artifact, not endpoint behavior.) **(b):** +9 repo tests — async message cursor boundaries (incl. a same-`created_at` case pinning the BE-M2 gap), and eager-load guards on `ModelRepository`/`AsyncChatRepository` (verified **non-vacuous** — they raise `MissingGreenlet`/`DetachedInstanceError` without the `joinedload`). **(c) audit-writer test deferred:** `writer.py` opens its own global `AsyncSessionLocal` → the live remote Postgres; needs the writer wired to the test session first. No production code / conftest touched. Verified: ruff clean, basedpyright 0/0/0, pytest **937** (928 + 9).
- **[x] BE-H9** (commit tagged `BE-H9`) — decomposed `import_card()` **92 LOC/cx-42/depth-5 → 29 LOC/cx-4/depth-2** via 4 extracted helpers (`_map_card_gender`, `_build_character_from_card`, `_import_character_book`, `_maybe_set_png_avatar`). Consolidated gender parsing to ONE path — `_map_card_gender` delegates to the existing `_parse_gender` and applies the import-only `OTHERS`+custom-label fallback (the hand-maintained `["male","female","non-binary"]` ladder is gone; `non-binary` output unchanged — the "disagreement" was structural duplication). Dropped the `hasattr(enum,"value")` guards in `_character_to_card` (enum columns always carry `.value`). Behavior preserved exactly (two-phase commit ordering untouched per BE-M4 scope; the `"others"`-literal and whitespace-tolerance edges pinned by new tests). +11 `TestMapCardGender` tests; all 4 import/export round-trips unchanged. Verified: ruff clean, basedpyright 0/0/0, pytest **928**.
- **[x] BE-M7** (commit tagged `BE-M7`) — decomposed `build_import_plan()` **135 LOC/cx-30 → 30 LOC/cx-9**: an `_OrderState` dataclass replaces the nested `nonlocal`-mutating `enable_component` closure (owns the counters/seen-sets + branch-handler methods), plus extracted `_index_prompts`, `_classify_order_items`, `_build_template`, `_build_profile`, `_build_preset`. Behavior byte-identical (shared `warnings` list + same object aliasing threaded through). All **38** existing mapper tests unchanged + 1 new test for the marker-in-`prompt_order`-but-absent-from-`prompts[]` branch. Verified: ruff clean, basedpyright 0/0/0, pytest 928.
- **[x] BE-L4 + BE-L6 + BE-L8** (commit tagged `BE-L4`, `BE-L6`, `BE-L8`) — **BE-L4:** collapsed `card_parser.parse_card_json`'s redundant branch (removed the `spec`+non-dict-`data` path that crashed `_parse_v2_data`; kept the `isinstance`-guarded branch), verified no test relied on it — valid V1/V2 cards parse identically; docstring refreshed. **BE-L6:** `@pytest.mark.anyio`→`asyncio` (the sole anyio marker under `--strict-markers`). **BE-L8:** WHY carve-out comments at `health/service.py` (`SELECT 1` liveness probe needs a raw round-trip) + `seed_model_families.py` (startup seeding runs outside the request/DI lifecycle). Verified: ruff clean, basedpyright 0/0/0, pytest **916** unchanged.
- **[x] BE-M1** (commit tagged `BE-M1`) — ported the missing surface to `AsyncBaseRepository`: `_column`, `find_all_ordered`, `find_paginated_ordered`, and the new `AsyncNamedRepository` (`find_by_name`) / `AsyncDefaultableRepository` (`unset_all_defaults`/`set_default`) mixins (exported alongside the sync ones). Reused `_apply_filters`→`statements.apply_filters` for WHERE construction (no SQL copy-paste; only the `await execute/.scalars()` wrapper differs). Adding the base methods surfaced the predicted drift: `AsyncChatRepository` had narrower bespoke `find_all_ordered`/`find_paginated_ordered` (eager-load, no `order_by`) → basedpyright flagged incompatible overrides; **resolved exactly as the sync `ChatRepository` already does** — accept `order_by` for signature compat but ignore it (fixed eager-loaded query), documented in the docstring. Verified diff: signature-only widening, method bodies unchanged. New `test_base_repository_async.py` (7 tests over a mixin-combining mock, mirroring the sync test). Verified: ruff clean, basedpyright 0/0/0, pytest **916** (909 + 7).
- **[x] BE-M9** (commit tagged `BE-M9`) — closed both router suppressions by refactor (no behavior change). Made `TemplateService.build_variables` **public** (the method actually lives in `templating/__init__.py`, not `prompt_template/service.py` as the finding guessed — grep was authoritative; 1 def + 2 callers updated) and dropped the `pyright: ignore[reportPrivateUsage]` in `prompt_template/router.py`. Threaded validated `content: str | None` through `_handle_blocking`/`_handle_streaming` (dropped the now-redundant `regenerate` param — `content is None ⟺ regenerate`), removing **both** bare `# type: ignore` in `chat_message/router.py` **plus** the annotated `:96` one. (basedpyright wouldn't narrow through the compound `and`-guard in a ternary, so used explicit `if/elif/else`.) Verified: ruff clean, **basedpyright 0/0/0**, pytest 909 unchanged; grep confirms zero suppressions in both routers.
- **[x] BE-M5** (commit tagged `BE-M5`) — extracted the placeholder DSN to a module constant (`_PLACEHOLDER_DATABASE_URL`) used as BOTH the `database_url` field default and the validator's compare target (can't drift), and extended `_forbid_insecure_production_defaults` to raise (after the existing CORS check) when `environment=production` + the placeholder DSN. Added 3 tests (prod-placeholder raises / prod-real boots / dev-placeholder fine) and made the pre-existing `test_production_with_explicit_origins_boots` pass an explicit DSN so it's env-independent. Verified: ruff/basedpyright clean, pytest **909** (906 + 3). **Env note:** `backend/.env` supplies a real remote DSN + `CORS_ORIGINS=["*"]` that pytest loads. Config-validation only (no auth/network/SSRF, per scope).
- **[x] BE-M8** (commit tagged `BE-M8`) — removed **21** play-by-play/restatement comments across 8 files (`provider/service.py` ×4, `character/service.py` ×4, `persona/service.py` ×2, `model_family/service.py` ×2, `prompt_template/router.py` ×1, `audit/middleware.py` ×3, `fixtures/seed_*` ×5); `git numstat` confirms **deletion-only** (comment lines only), zero executable/test changes. Deliberately KEPT `prompt_template/router.py:97` (`# Mock chat object …` — a genuine WHY). Stayed within the curated list (no un-cited sweeps). Verified: ruff/basedpyright clean, pytest 909 unchanged.
- **[~] BE-H3 — part 1 done, part 2 deferred** (commit tagged `BE-H3`) — **Part 1 (headline): added a `ci-gate` job** to `backend-ci.yml` that `needs: [lint, typecheck, test, integration]` with `if: always()` and fails unless every result is `success`, so a skipped/failed Postgres `integration` job turns the pipeline **red** instead of silently passing (point branch protection at `ci-gate`). Validated: workflow parses, all needed jobs exist. **Part 2 (expand PG tests — vchordrq tuning, message `chat_id` scoping, threshold-equality edge, empty results) DEFERRED**: authoring + verifying these needs a live VectorChord container, and **Docker is not available in this environment** — committing unverified integration tests would violate evidence-before-assertions. Follow-up: add them to `tests/integration/test_postgres_integration.py` (which already covers extension/index presence, cosine ranking + threshold, mocked-embedding retrieval, seed data) when a container is available, and confirm `uv run pytest -m postgres` green.
- **[x] BE-M6** (commit tagged `BE-M6`) — added `tests/lore/test_router.py` (24 tests: all 8 lore endpoints, happy + 404 + validation) and `tests/rag/test_router.py` (27 tests: data-bank CRUD, `POST /rag/search`, `GET /rag/status`). Hermetic via an autouse override of `get_retrieval_service` → `MagicMock(spec=RetrievalService)` with `AsyncMock` methods — no embedding backend or pgvector SQL touched; covered the documented "indexing failure swallowed → CRUD still 2xx" behavior. **Env caveat surfaced:** this machine's `.env` has RAG enabled pointing at a live embedder (`10.0.10.2:4001`), so un-mocked search would hit it — hence the autouse override. No shared conftest touched. Verified independently: ruff/basedpyright clean, pytest **906 passed / 1 skipped**.
- **[x] BE-H4** (commit tagged `BE-H4`) — added 13 HTTP-level tests to `tests/chat_message/test_router.py` via `AsyncClient(ASGITransport)`: blocking send (200 + both turns persisted / 422 / provider-fault 502), suggestions, title (+persisted), edit (200/404), alternatives list + activate (200/404/wrong-chat). Gateway mocked exactly like `test_service.py` (`patch ProviderGateway`→AsyncMock, `has_api_key` patched) — no real provider. Avoided the BE-H8 single-writer caveat by keeping the sync `get_db` override read-only. **Oddity reported (not fixed):** the blocking path collapses every upstream error to a flat 502 via `ProviderException`, losing the `classify_error` code the streaming path preserves (looks intentional — candidate for a future item). No shared conftest touched. Verified independently: ruff/basedpyright clean, pytest 906 passed.
- **[x] BE-H8** (commit tagged `BE-H8`) — replaced the two separate `sqlite:///:memory:` engines with a session-scoped `_shared_db_path` temp file that **both** the sync (`sqlite`) and async (`sqlite+aiosqlite`) engines bind to (empirically verified: two `:memory:` engines don't share; one on-disk file shares both directions). Schema created once via a setup engine; per-test isolation unchanged (existing row-cleanup teardown); removed the now-dead `_async_create_tables`. New regression test `test_cross_session_db.py` writes via the sync repo + commits, then reads via the async session. **Deliberately kept** the `get_db` overrides in the streaming tests — they isolate the sync path from the real remote Postgres in `.env`, which is orthogonal to the two-DB trap (removing them risks hanging on the remote host). Verified independently: ruff clean, basedpyright 0/0/0, pytest **842 passed / 1 skipped** (was 841, +1). **Residual → flag for BE-H4:** SQLite's single-writer limit means an *uncommitted* sync write held open across an async write raises "database is locked" (inherent, unfixable via WAL; not exercised by suite/prod) — keep sync-side writes committed before the async path writes in the same flow.
