# Architectural Audit v2 — The Bannered Mare (post-refactor adversarial pass)

**Date:** 2026-07-14
**Scope:** `backend/` + `frontend/`, re-audited **after** the refactoring wave that addressed [AUDIT_LOG_BE.md](AUDIT_LOG_BE.md) (BE-1…BE-22) and [AUDIT_LOG_FE.md](AUDIT_LOG_FE.md) (FE-1…FE-21).
**Method:** Adversarial verification — the v1 fixes were **not** taken on trust. Each claimed fix was re-checked against the current code; the gates were run independently; three headline bugs were confirmed by direct code reads. Findings fall into four tiers: **A** = real bugs the refactor *introduced or activated*, **B** = fixes that are *partial* (abstraction built, adoption incomplete), **C** = v1 items still *untouched* but in scope, **D** = *new* smells the v1 audit missed.

> **This is a living tracker.** Each finding has a stable ID (`V2-x`), a checkbox, `file:line` evidence, and explicit **acceptance criteria** so completion can be verified in any future session. Check the box and add the fixing commit hash when done. Do **not** delete completed items — move them to *§ Completed* at the bottom with their commit.

## Out of scope (unchanged from v1)

Authentication/login, network-exposure hardening (loopback bind, `/admin` gating), credentialed-CORS, and provider-URL SSRF validation remain **intentionally deferred** for this single-user local experiment (see AUDIT_LOG_BE.md). Do not re-raise them here.

---

## Gate baseline (verified 2026-07-14 — regression reference)

Any future change must keep these green:

| Gate | Command | Result at audit time |
|---|---|---|
| Backend lint | `cd backend && uv run ruff check .` | clean |
| Backend types | `uv run basedpyright` | 0 errors / 0 warnings / 0 notes |
| Backend tests | `uv run pytest -q` | 862 passed, 4 skipped |
| Migration drift | `uv run alembic check` (live PG, `compare_type`+`compare_server_default` on) | no drift |
| Contract sync | regenerate `openapi.json` → byte-identical; `frontend/src/api/schema.d.ts` in sync | in sync |
| Frontend build | `cd frontend && bun run build` (`vue-tsc -b && vp build`) | passes, 0 type errors |
| Frontend tests | `cd frontend && bun test` | 8 passed / 0 failed |
| Frontend lint | `cd frontend && vp lint` | clean |

> Note: memory — run backend Python tools via `uv run …`, not `.venv/bin/…`.

---

## Verified genuinely fixed — DO NOT re-flag

These v1 findings were confirmed as *real* structural fixes (not superficial) and should not be re-raised:

- **BE-1** message-embedding retrieval now works end-to-end (write/read agree on `chat_id`; FK `ON DELETE CASCADE`; dedup re-scoped). *Residual → V2-A1, V2-D5.*
- **BE-2** `ix_messages_chat_created (chat_id, created_at)` on the model + migration; hot queries are index-served.
- **BE-5** `core/` imports no vertical slice; `RequestLoggingMiddleware` → `audit/middleware.py`, `TemplateService` → `templating/` (TYPE_CHECKING-only model refs, true runtime leaf).
- **BE-6 / BE-22** base repo finished (`find_all_ordered`, `find_paginated_ordered`, `NamedRepository`, `DefaultableRepository`); `set_default` collapsed; blanket `refresh()` dropped safely (server-default cols also carry Python defaults); pre-flush guard gone.
- **BE-7** card→lore mapping extracted to `lore/card_import.py` with dict token maps + explicit defaults; unit-tested; `import_card` ~166→~92 lines.
- **BE-8** `UploadFile` out of services; `UploadedFile` NamedTuple; fake-UploadFile hack gone.
- **BE-9** DI cycles broken at the root (slimmed 13 `__init__.py`); `provider.router` imports the real `ModelServiceDep`; `import src.main` acyclic; no in-body import workarounds left.
- **BE-10** sync prompt builder + lore offloaded via `anyio.to_thread`; no blocking psycopg2 on the loop.
- **BE-11** send path commits twice (user turn + assistant turn); `chat.preview` folded into the message unit of work; re-fetch/extra-commit/manual `updated_at` gone.
- **BE-12** six JSON columns → JSONB + `MutableDict/MutableList` (own type instance per column); one-off `flag_modified` removed.
- **BE-13** no raw `HTTPException` in routers; preview returns a sanitized `BadRequestError`.
- **BE-14** `ChatModelSnapshotService` (chat_session-owned) does the rename; `ModelService` no longer holds `ChatRepository`; shared-session commit atomic.
- **BE-16** `Literal` config for level/provider/format/environment; dispatcher uses `match` + `assert_never`.
- **BE-17** both `alembic/env.py` `context.configure()` set `compare_type` + `compare_server_default`.
- **BE-18** `provider_type` is VARCHAR (`native_enum=False`); native `providertype` PG enum dropped; app-level validation.
- **BE-19** data collaborators required; no self-newed repos/caches (stateless `TemplateService()` excepted).
- **BE-20** stray test files relocated under `tests/chat_message/`; integration double-marked; OpenAI parser deduped.
- **FE-3** lorebook `as any` path bug fixed; param `lorebook_id` correct against schema; entries typed.
- **FE-4** `AbortController` per generation, wired to `signal`; `stop()` exposed; chat-switch aborts; `readStream` re-finds by id (no orphaned index writes). *Minor residual → V2-D8.*
- **FE-7** no `JSON.stringify(apiError)` throws; `extractApiError` reads `detail`; `APIError` adopted. *Residual → V2-D6.*
- **FE-11** dead `Array.isArray(data)` pagination branches gone; single provider source of truth with invalidation (`fetchProviders(true)` after save).
- **FE-14** `text-error-content` (no stale `-foreground` shadcn tokens remain anywhere).
- **FE-15** `StreamEvent` discriminated union in `types/chat.ts`. *But `start`/`usage`/`done` arms unused → V2-A2.*
- **FE-17** `.env.example` present; `VITE_API_URL` typed; dead avatar helpers removed.
- **FE-18** invisible-on-light hover overlays fixed (`hover:bg-white/*` gone; base-content tokens used).
- **FE-19** dead `components.json` + broken `test-messages.js` deleted.
- **FE-10 (avatar)** `utils/avatar.ts::fallbackAvatarUrl` adopted in all 10 sites; `ui-avatars.com` only appears there.
- **FE-2 (Modal, mostly)** focus-on-open, restore-on-close, `aria-labelledby`, close-button `aria-label`, listener cleanup on close + unmount. *Trap residual → V2-A3.*

---

## Tracker (check when done; add commit hash)

| ID | Tier | Half | Sev | Title | Done |
|---|---|---|---|---|---|
| V2-A1 | A | BE | Med | RAG history stale on edit/regenerate | [x] |
| V2-A2 | A | FE | Med | Streamed message never adopts backend `message_id` | [x] |
| V2-A3 | A | FE | Med | Modal focus trap leaks on first Shift+Tab | [x] |
| V2-A4 | A | FE | Med | SelectMenu combobox ARIA on wrong element | [x] |
| V2-B1 | B | FE | Med | 5 multipart sites bypass `VITE_API_URL` + `trackedFetch` | [x] |
| V2-B2 | B | FE | Low | `useModel`/`useProvider` still hand-roll (2/6 CRUD) | [x] |
| V2-B3 | B | FE | Med | ~44 leaf `any` casts remain in models/families/providers | [x] |
| V2-B4 | B | FE | Med | 149 raw palette hues across 17 files remain | [x] |
| V2-B5 | B | FE | Med | confirm-to-delete 5/11; `useOverlayTransition` never made | [x] |
| V2-B6 | B | FE | Med | tests not type-checked/gated; no lazy-chunk boundary | [x] |
| V2-B7 | B | BE | Low | mid-stream error still emits raw `str(e)` | [x] |
| V2-B8 | B | BE | Low | two collection endpoints still bare `list[...]` | [x] |
| V2-C1 | C | FE | High | `ChatDrawer.vue` 1087-line god component + monoliths | [ ] |
| V2-C2 | C | FE | Med | business logic stranded in views; `ChatHeader` relay | [ ] |
| V2-C3 | C | FE | Low | `useBookmarks` raw fetch, no `.ok`, `any[]` | [x] |
| V2-C4 | C | FE | Low | overlapping lint stacks + doc drift | [ ] |
| V2-C5 | C | BE | Low | no shared character DTO; no async `get_or_404` | [~] |
| V2-D1 | D | FE | Med | list factories have no request sequencing (race) | [x] |
| V2-D2 | D | FE | Low | `useEntityCrud` mutation errors don't set `error` ref | [x] |
| V2-D3 | D | FE | Low | silent error swallow (lorebook GETs, MemoryView) | [ ] |
| V2-D4 | D | BE | Low | `ProviderService.delete()` raises `NotImplementedError` | [x] |
| V2-D5 | D | BE | Low | data_bank embeddings orphan on cascade delete | [x] |
| V2-D6 | D | FE | Low | `extractApiError` dropped `statusCode` (can't branch) | [x] |
| V2-D7 | D | FE | Low | stacked modals double-trap keydown | [x] |
| V2-D8 | D | FE | Low | `stop()` before first token leaves empty bubble | [x] |
| V2-D9 | D | BE | Nit | cosmetic in-body import in `character/service.py` | [x] |

---

## Tier A — Real bugs introduced or activated (fix first)

### V2-A1. RAG history goes stale on message edit / regenerate  ·  Med · BE  · [x] DONE
- **Location:** `backend/src/chat_message/service.py:218-230` (`edit_message`), `:276-281` (regenerate-overwrite in `_persist_reply`); `_vectorize` called only at `:294` (new turn), `:398`, `:516`.
- **Problem:** BE-1 made message embeddings *retrievable* by scoping on `chat_id`. But `edit_message` and the regenerate-overwrite branch mutate `content` and commit **without re-vectorizing or deleting the prior embedding**. Confirmed by direct read.
- **Why it matters:** A user edits a message to correct a fact; RAG-over-history keeps retrieving the **pre-edit / pre-regen** text as context on later turns — silent, wrong context injection on a now-live feature.
- **Fix:** On edit and on overwrite-regenerate, re-vectorize the message (delete-by-source then re-embed, or upsert by `(source_type='message', source_id=message_id)`). Reuse the existing `_vectorize` path.
- **Acceptance:** editing or regenerating a message replaces its stored embedding; a test asserts the embedding row's vector/content changed and that retrieval no longer returns stale text. Gates stay green.

### V2-A2. Streamed message never adopts its backend id  ·  Med · FE  · [x] DONE
- **Location:** `frontend/src/composables/useChatMessages.ts:107-118` (`addAssistantPlaceholder` → `crypto.randomUUID()`), `:161-175` (`readStream` handles only `text`/`reasoning`/`error`); union field at `frontend/src/types/chat.ts:20` (`start` → `message_id`).
- **Problem:** The assistant bubble keeps a client-generated UUID; `readStream` ignores the `start` event that carries the real `message_id`. Confirmed by direct read.
- **Why it matters:** Edit or fetch-alternatives on a freshly-streamed reply **before any reload** sends `PUT/GET /api/chats/{id}/messages/{client-uuid}` → **404**. The FE-15 union already models the exact field needed.
- **Fix:** In `readStream`, add a `start` arm that rewrites the placeholder message's `id` (re-find by `placeholderId`, swap in `event.message_id`) and continue matching subsequent writes against the new id. Verify the backend actually emits a `start`/id event; if not, emit it or fetch the id on stream completion.
- **Acceptance:** after streaming completes (no reload), the message's `id` equals the backend id; editing/alternatives succeed. Guard remains abort-safe.

### V2-A3. Modal focus trap leaks on the first Shift+Tab  ·  Med · FE  · [x] DONE
- **Location:** `frontend/src/components/shared/Modal.vue:88` (focuses panel container, `tabindex=-1`), trap at `:53-71` (only reverses when `active===first/last || !inPanel`).
- **Problem:** With focus on the panel container, Shift+Tab satisfies none of the reversal conditions, so the browser moves focus backward out of the teleported dialog to the obscured page — the exact escape FE-2 aimed to prevent. Confirmed by direct read.
- **Fix:** On open, focus the **first focusable child** (fall back to the panel only when empty); OR treat "active is the panel / not a tabbable child" as a trap endpoint in `handleKeyDown`.
- **Acceptance:** opening any modal and immediately pressing Shift+Tab keeps focus inside the dialog; Tab from the last and Shift+Tab from the first both wrap; empty-dialog case still guarded.

### V2-A4. SelectMenu combobox ARIA on a non-focusable wrapper  ·  Med · FE  · [x] DONE
- **Location:** `frontend/src/components/shared/SelectMenu.vue:143-147` (`role=combobox`/`aria-expanded`/`aria-controls`/`aria-activedescendant` on a `<div>` with no `tabindex`), `:74` (focus moves to the search `<input>` on open).
- **Problem:** ARIA sits on an element that never receives focus; screen readers track ARIA on the focused element, so expanded-state and active-option are never announced and arrow-key highlighting is silent to AT.
- **Fix:** Put `role=combobox` + `aria-*` (especially `aria-activedescendant` pointing at the highlighted `option` id) on the actually-focused control — the search `<input>` when open, or a focusable trigger — with `aria-controls` → the listbox id.
- **Acceptance:** with a screen reader (or the a11y tree), the focused control announces combobox/expanded and the active option changes as you arrow; `aria-activedescendant` resolves to a rendered option id.

---

## Tier B — Fixes that are only partial (abstraction built, adoption incomplete)

### V2-B1. Multipart sites bypass the base URL + reachability tracking  ·  Med · FE  · [x] DONE
- **Location:** `useCharacterForm.ts:202`, `usePersonas.ts:43`, `usePresetImport.ts:22`, `CharactersView.vue:233`, `PersonaTab.vue:100,118` — all raw `fetch("/api/…")`. SSE got `client.ts:28 streamFetch`; multipart got no equivalent.
- **Problem:** FE-1 migrated JSON calls but left 5 multipart mutations hardcoding relative `/api/...`, skipping `VITE_API_URL` and `trackedFetch`. Also layering: `PersonaTab.vue` (component) and `CharactersView.vue`/`MemoryView.vue` (views) speak HTTP directly (AGENTS §4.2).
- **Fix:** Add a shared `multipartFetch(path, formData, opts)` wrapper in `api/client.ts` that applies `VITE_API_URL` + `trackedFetch` (mirroring `streamFetch`); route all 5 sites through it; move the component/view fetches into composables.
- **Acceptance:** grep for `fetch("/api` in `src/` returns only the wrappers in `client.ts`; a split-origin (`VITE_API_URL`) run exercises character/persona/import successfully; a 502 on any flips `useServerStatus`.

### V2-B2. `useModel` / `useProvider` still hand-roll the CRUD skeleton  ·  Low · FE  · [x] DONE
- **Location:** `frontend/src/composables/useModel.ts`, `useProvider.ts` (own `loading/saving/deleting/error` + try/finally); factory at `useEntityCrud.ts` (with `runSaving` for extra mutations).
- **Fix:** Migrate both onto `useEntityCrud`, using `runSaving` for their route-specific mutations (as the other 4 CRUD twins do).
- **Acceptance:** neither composable declares its own `saving`/`deleting` refs; behavior unchanged; build + tests green.

### V2-B3. `any` cluster relocated from store to leaves  ·  Med · FE  · [x] DONE
- **Location:** `ModelForm.vue:11-13` (hand-rolled structural prop types instead of schema types), forcing `providersForFamily(props.providers as any, …)` at `:35`; `(p:any)`/`(f:any)`/`(row:any)` casts in `ModelForm.vue:32,42-53`, `ModelView.vue:77-83`, `ModelsTab.vue:171,177`, `ModelFamiliesTab.vue:111`, `ModelFamilyView.vue:70-80,337-340`; `DataTable.vue:19,32` (`readonly any[]`/`row:any`); creator `update:field` contract `[keyof CharacterData, any]` in `CharacterTab/BehaviorTab/WorldTab.vue:16-18`, forwarded `(field:any,val:any)` in `CharacterCreateView.vue:268,276,284`.
- **Problem:** FE-8 typed the store root but left every downstream leaf cast; the models/families/providers area holds ~44 of the app's real-code `any`s.
- **Fix:** Type component props from `components["schemas"][...]`; make `DataTable` generic over its row type; make `update:field` generic `<K extends keyof CharacterData>(field: K, value: CharacterData[K])` end-to-end so field/value stay correlated.
- **Acceptance:** real-code `any` count in `src/` (excluding `schema.d.ts`, mocks, tests, `vite-env.d.ts`) drops to a documented minimum; no `as any` on `client`/schema data; build green.

### V2-B4. Raw palette hues still bypass semantic tokens  ·  Med · FE  · [x] DONE (guard → V2-C4)
- **Location:** 149 occurrences across 17 files; genuine *status* offenders incl. `ProvidersTab.vue:128,143,146`, `AppSidebar.vue:152,185`. (Category/scale colors — TemplateView position badges, MemoryView score scale — are defensible; provider *brand* chips in `LogsTab.vue:80-82` are intentional.)
- **Fix:** Map status hues to tokens (`emerald→success`, `red→error`, `amber→warning`, `blue→info`) keeping tint-bg + solid-text contrast pairing; add a lint rule (extend `canonical-classes.mjs` or the eslint-tailwind path) banning raw palette classes for status. Leave documented category/brand exceptions.
- **Acceptance:** status indicators render correctly across all 12 themes + Custom; a lint check fails on new raw status hues; count of raw-hue status uses → 0.

### V2-B5. Confirm-to-delete + overlay transition still duplicated  ·  Med · FE  · [x] DONE (overlay → V2-C1)
- **Location:** `useConfirmAction` adopted only in the 5 settings views; still hand-rolled in `ChatDrawer.vue:393-424`, `PersonaTab.vue:144-166`, `ProfilesTab.vue:93-106`, `LorebooksView.vue:122-175`, `MemoryView.vue:152-164` (+ `ProfileCard`/`LoreEntryCard` props). No `useOverlayTransition` exists; `ChatDrawer.vue:58,155` duplicates Modal's `visible/entered/closeTimer/DURATION`.
- **Fix:** Adopt `useConfirmAction` in the remaining 6 sites (gets auto-disarm timers for free — see V2-D-adjacent NEW-4). Extract `useOverlayTransition({duration})` and consume it in both `Modal` and `ChatDrawer` (folds into V2-C1's split).
- **Acceptance:** no hand-rolled `confirmDelete`+`setTimeout` outside the composable; overlay transition/scroll-lock logic exists in one place.

### V2-B6. Tests not type-checked or gated; no lazy-chunk error boundary  ·  Med · FE  · [x] DONE
- **Location:** `frontend/tsconfig.json:23` (`"exclude": ["src/**/__tests__/**"]`); `package.json` (`"test": "bun test"` exists but the authoritative gate is only `vue-tsc -b && vp build`); `AppShell.vue:13` (bare `<RouterView>`; no `Suspense`/`errorCaptured`/`router.onError` anywhere).
- **Problem:** FE-13 added the route + script but left tests outside `vue-tsc` (drift uncaught) and outside the build gate (silent rot), and never added the lazy-chunk boundary it named.
- **Fix:** Remove the `__tests__` exclude (or add a test tsconfig project to the build); add `bun test` to the gate/CI; wrap `<RouterView>` in an error/loading boundary and add `router.onError` to prompt reload on chunk-load failure.
- **Acceptance:** `bun run build` (or CI) fails if a test doesn't type-check or fails; a forced chunk-load error shows a recovery UI, not a blank pane.

### V2-B7. Mid-stream errors still emit raw `str(e)`  ·  Low · BE  · [x] DONE
- **Location:** `backend/src/chat_message/service.py:489` (inner SSE handler emits `message=str(e)` for any exception); router boundary at `router.py:110-112` genericizes non-`ProviderException`.
- **Problem:** BE-4 fixed the code classification and the router-boundary text, but a fault during mid-stream persist (e.g. asyncpg error) still streams raw internal text — inconsistent with the pre-stream path.
- **Fix:** Apply the same genericize-unless-`ProviderException` treatment at `:489`.
- **Acceptance:** a simulated non-provider mid-stream error streams a generic message + a `classify_error()` code, not raw exception text.

### V2-B8. Two collection endpoints still return bare lists  ·  Low · BE  · [x] DONE
- **Location:** `backend/src/provider/router.py:23` (`GET /api/providers` → `list[ProviderResponse]`), `backend/src/prompt_fragment/router.py:102` (`GET /api/prompt-templates/{id}/fragments/` → `list[TemplateFragmentResponse]`).
- **Problem:** BE-15 unified everything else onto `PaginatedResponse[T]`/`collection_response`; these two were missed, forcing the frontend to special-case two shapes.
- **Fix:** Wrap both in `collection_response` (or `PaginatedResponse[T]`); regenerate `openapi.json` (`scripts/openapi.sh`) + `frontend` `bun run api:gen`; update MSW handlers + any frontend consumers.
- **Acceptance:** all collection endpoints share one envelope; contract regenerated + committed; frontend builds against the new shape.

---

## Tier C — In scope but untouched

### V2-C1. `ChatDrawer.vue` is still a 1087-line god component  ·  High (cohesion) · FE  · [ ]
- **Location:** `frontend/src/components/chat/ChatDrawer.vue` (whole file, four tab bodies inline, ~10 inline formatters, confirm/rename logic); other monoliths: `ProviderView.vue` (774), `ModelView.vue` (618), `ChatView.vue` (530), `TemplateView.vue` (527).
- **Fix:** Split into `ChatDrawerCharacterTab/…SettingsTab/…SessionTab/…LogsTab.vue`, each owning its composable + `v-if`-gated lazy fetch; keep `ChatDrawer` as the shell. Move log formatters to `formatLog.ts`. **Also (moved here from V2-B5): extract `useOverlayTransition({duration})`** and have both `Modal` and the `ChatDrawer` shell consume it, so the `visible`/`entered`/`closeTimer`/`DURATION` + scroll-lock logic lives in one place.
- **Acceptance:** `ChatDrawer.vue` < ~250 lines; each tab is its own SFC; formatters unit-tested; per-tab lazy fetch preserved.

### V2-C2. Business logic stranded in views; `ChatHeader` prop-drilling  ·  Med · FE  · [ ]
- **Location:** `CharacterCreateView.vue:61-118` (inline ensure-lorebook + per-entry sync, 14-field default at `:90-104`), `:131-139` (manual Blob/anchor export); `ChatHeader.vue:13-33` (10 props / 7 emits forwarding `models`/`profiles`/`currentPersonaId` it never renders).
- **Fix:** Move the sync loop into `useCharacterForm` as `syncLorebook(characterId, entries)`; hoist entry defaults to `constants/`; extract `downloadJson()`. Source `models`/`profiles`/`personas` in `ChatDrawer` from composables; lift per-chat mutations into `useChatSession(chatId)`; reduce `ChatHeader` to `character`/`sessionTitle` + a `back` emit.
- **Acceptance:** no raw multi-step API orchestration in views (AGENTS §4.2); `ChatHeader` prop/emit count materially reduced.

### V2-C3. `useBookmarks` raw fetch, no `.ok`, `any[]`  ·  Low · FE  · [x] DONE
- **Location:** `frontend/src/composables/useBookmarks.ts:14-15,29-37`.
- **Problem:** Three `fetch(...).then(r=>r.json())` with no `response.ok` check → a 4xx/5xx body renders as an empty (not errored) page; `characters`/`sessions` are `any[]`.
- **Fix:** Move to `client.GET`, branch on `error` (+ `extractApiError`), type refs from the schema.
- **Acceptance:** failures surface an error state (toast) not a blank list; refs typed; no raw fetch here.

### V2-C4. Overlapping lint stacks contradict the docs  ·  Low · FE  · [ ]
- **Location:** `package.json` scripts `lint`/`lint:tailwind`/`lint:canonical`; devDeps `eslint@10`, `typescript-eslint`, `eslint-plugin-vue`, `eslint-plugin-tailwindcss@4`; `eslint.config.js` + `scripts/canonical-classes.mjs`; AGENTS §4.1 / README claim "Oxlint/Oxfmt … no standalone devDeps."
- **Fix:** Pick one story — consolidate on Oxlint + the `.mjs` (drop the ESLint stack) or document ESLint as the canonical Tailwind linter — and update AGENTS/README to match. Verify `eslint-plugin-tailwindcss@4` actually parses the v4 CSS-first config.
- **Acceptance:** exactly one enforcement path for canonical/Tailwind classes; docs match reality.

### V2-C5. BE-21 residuals  ·  Low · BE  · [~] PARTIAL (get_or_404 done; DTO not viable)
- **Location:** character payload enumerated in both `character/router.py` and `character/service.py` (no shared DTO); only a specialized `get_chat_or_404` exists (no generic async `get_or_404`).
- **Fix:** Introduce a shared character payload DTO consumed by router + service; add a generic async `get_or_404` in the async base service and fold `get_chat_or_404` onto it.
- **Acceptance:** the ~19-field payload is declared once; one async 404 helper.

---

## Tier D — New smells the v1 audit missed

### V2-D1. List factories have no request sequencing  ·  Med · FE  · [x] DONE
- **Location:** `usePaginatedList.ts` (`loadPage`, ~`:56-76`), `useCursorList.ts` (`load`, ~`:62-82`) — no `AbortController`, no in-flight guard; `useModels.filter` calls `loadPage(1)` on each change.
- **Problem:** Fast filter/search changes race; a slower earlier response can resolve last and clobber the newer list (last-response-wins).
- **Fix:** Add per-load `AbortController` (abort the previous in-flight) and/or a request-sequence guard in the factories (one place fixes all callers).
- **Acceptance:** rapid filter changes always render the newest query's results; earlier responses are discarded.

### V2-D2. `useEntityCrud` mutation errors don't populate `error`  ·  Low · FE  · [x] DONE
- **Location:** `frontend/src/composables/useEntityCrud.ts:41-42` (only `fetchItem` sets `error`); `createItem`/`updateItem`/`removeItem`/`runSaving` rethrow without touching it.
- **Fix:** Set `error.value = extractApiError(...)` in the write paths (or document that writes throw and `error` tracks reads only).
- **Acceptance:** after a failed save, the returned `error` ref reflects it, or the contract is documented + consistent.

### V2-D3. Silent error swallow  ·  Low · FE  · [ ]
- **Location:** `useCharacterForm.ts:214,238,298,304` (lorebook GETs destructure `{ data }`, ignore `error`); `MemoryView.vue:27,42` (`/api/rag/status`, `/api/rag/search` ignored + view speaks HTTP).
- **Problem:** Violates AGENTS §6.5 ("don't swallow errors"); a failed lorebook load silently skips entry sync / renders empty.
- **Fix:** Branch on `error` and surface via `useAppToast`; move the MemoryView calls into a composable.
- **Acceptance:** these failures produce a visible error, not a silent empty state.

### V2-D4. `ProviderService.delete()` raises `NotImplementedError`  ·  Low · BE  · [x] DONE
- **Location:** `backend/src/provider/service.py:405`.
- **Problem:** Not a `BanneredMareException`, so the global handler won't map it → unhandled 500 if ever routed. Currently unrouted (no `DELETE /providers/{id}`), so latent only.
- **Fix:** Raise a domain exception (`ValidationError`/405-style) or remove the method until the feature lands.
- **Acceptance:** no `NotImplementedError` reachable from any route; if kept, it maps to a clean 4xx.

### V2-D5. data_bank embeddings orphan on cascade delete  ·  Low · BE  · [x] DONE
- **Location:** `backend/src/rag/` — `embeddings` rows with `source_type='data_bank'` have `chat_id=NULL` and no FK on `source_id`; purged only by `DELETE /data-bank/{id}` (`rag/router.py:118`).
- **Problem:** Deleting a chat/character cascades its `DataBankEntry` rows but their embeddings orphan permanently (index/storage bloat). Same leak class BE-1 closed for messages, still open here. Not a correctness bug (orphans never re-enter `find_by_scope`).
- **Fix:** Add cleanup on data-bank/scope deletion (delete-by-source), or a nullable FK + cascade mirroring the message fix.
- **Acceptance:** deleting a data-bank entry (or its owning scope) removes its embedding rows; a test asserts no orphans remain.

### V2-D6. `extractApiError` dropped `statusCode`  ·  Low · FE  · [x] DONE
- **Location:** `frontend/src/api/client.ts` `APIError` + `extractApiError`.
- **Problem:** FE-7's helper reads `detail` but not HTTP status, so callers can't branch 404 vs 409 vs 422.
- **Fix:** Thread the `response.status` from the `{ error, response }` openapi-fetch result into `APIError.statusCode`.
- **Acceptance:** a caller can read `err.statusCode` and branch on it; at least one consumer uses it.

### V2-D7. Stacked modals double-trap keydown  ·  Low · FE  · [x] DONE
- **Location:** `frontend/src/components/shared/Modal.vue:82` (each open Modal adds its own `window` keydown listener).
- **Problem:** A Modal open over another (e.g. ConfirmModal atop an editor) means both handlers fire on Tab and fight over focus. Rare today; latent if stacking is introduced.
- **Fix:** Track a modal stack and only let the topmost trap handle keys (or scope the listener to the panel with capture + a depth check).
- **Acceptance:** with two stacked modals, only the top one traps focus.

### V2-D8. `stop()` before first token leaves an empty bubble  ·  Low · FE  · [x] DONE
- **Location:** `frontend/src/composables/useChatMessages.ts` (only the error path filters empty placeholders at `:190`).
- **Fix:** On explicit `stop()` with empty content, drop the placeholder (or mark it stopped) as the error path does.
- **Acceptance:** stopping before the first token leaves no blank assistant message.

### V2-D9. Cosmetic in-body import  ·  Nit · BE  · [x] DONE
- **Location:** `backend/src/character/service.py:328` (`from src.core.config import settings` inside a method).
- **Problem:** `core.config` is a leaf (not a cycle workaround like the old BE-9 cases); the in-body import is purely stylistic.
- **Fix:** Move to module scope.
- **Acceptance:** import at module top; no cycle reintroduced.

---

## Suggested sequencing

1. **Tier A** (four small, confirmed bugs): V2-A1, V2-A2, V2-A3, V2-A4.
2. **Finish half-done abstractions** (highest cleanup value): V2-B1, V2-B2, V2-B3, V2-B6; then V2-B4, V2-B5.
3. **Contract/back-end polish:** V2-B7, V2-B8, V2-D4, V2-D5, V2-C5.
4. **Structure (feature-paced):** V2-C1 (+ fold V2-B5 overlay), V2-C2; quick wins V2-C3, V2-D1, V2-D2, V2-D3, V2-D6.
5. **Housekeeping:** V2-C4, V2-D7, V2-D8, V2-D9.

---

## Completed

_(Move items here with `[x]` and the fixing commit hash as they're finished — keep the record; don't delete.)_

- **[x] V2-A1** — `vectorize_message` now uses delete-then-insert replace semantics (mirrors `vectorize_data_bank_entry`); `_vectorize` re-runs on every `_persist_reply` branch (new turn, overwrite, alternatives-store), on `edit_message`, and on `activate_alternative` (swipe) — every message-content mutation. New test `test_vectorize_message_replaces_prior_embedding` asserts the old vector is always deleted even on a dedup hit. Validated: ruff clean, basedpyright 0/0/0, 863 passed. Commit: `048fef0`.
- **[x] V2-A2** — `readStream` now handles the backend's `start` event: it swaps the placeholder's client UUID for `event.message_id` and tracks the swapped id (`currentId`) through every subsequent write and both cleanup paths, so a freshly-streamed reply can be edited/re-rolled without a reload. Backend already emitted `StreamEvent(type="start", message_id=…)` (service.py:420); only the FE was ignoring it. Validated: `bun run build` passes (vue-tsc + Rolldown), 8 tests pass. Commit: `f324b23`.
- **[x] V2-A3** — Modal now focuses the first focusable child on open (fallback panel) and the tab trap recaptures whenever the active element isn't a tabbable child (`onTabbable` includes-check replaces the `inPanel` contains-check), so the first Shift+Tab can't escape. Validated: `bun run build` passes. Commit: `26b469d`.
- **[x] V2-A4** — combobox semantics (`role=combobox`, `aria-autocomplete=list`, `aria-expanded`, `aria-controls`, `aria-activedescendant`) moved from the non-focusable trigger wrapper onto the search input (the focused control when open); `role=listbox` + `listboxId` moved onto the actual `<ul>` so `aria-controls` resolves to the option container; `aria-activedescendant` guarded to unset when the filtered list is empty. Known residual: `searchInput=false` mode focuses the consumer-slotted trigger button (outside this component's control), so activedescendant can't be conveyed there — default mode is correct. Validated: `bun run build` passes. Commit: `40a8ba8`.
- **[x] V2-B1** — added `multipartFetch<T>(path, {method, body, signal})` to `client.ts` (applies `VITE_API_URL` + `trackedFetch`, returns openapi-fetch-shaped `{data, error}`). Routed all five multipart sites through it: `usePresetImport`, `useCharacterForm.saveCharacter`, `usePersonas` (now a full CRUD composable: `savePersona`/`createPersona`/`deletePersona`/`setDefaultPersona`), new `useCharacters.importCharacter` (view now calls it), and `PersonaTab.vue` fully consolidated onto `usePersonas` (no more raw fetch/`client` in the component). Grep confirms no `fetch("/api` outside `client.ts` except `useBookmarks` (own item V2-C3). Validated: `bun run build`, 8 tests, `vp lint` all pass. Commit: `85ae834`.
- **[x] V2-B2** — `useModel` and `useProvider` now build on `useEntityCrud` for the shared item/loading/saving/deleting/error refs. `useProvider`'s core CRUD maps directly onto `fetchItem`/`createItem`/`updateItem`; its model-discovery/sync/filter state stays local. `useModel`'s route/flag mutations return a `ModelResponse` that must merge into (not clobber) the detail, so they run through `runSaving` + `mergeIntoDetail`. No hand-rolled `saving`/`deleting`/`loading` refs remain. Validated: `bun run build`, 8 tests, `vp lint` all pass. Commit: `9e0e76d`.
- **[x] V2-B3** — `DataTable.vue` made generic (`generic="T extends Record<string, unknown>"`), typing `rows`/`rowClick`/slots for all consumers; `ModelsTab`/`ModelFamiliesTab`/`FragmentsTab` row handlers now use `(typeof list.value)[number]` instead of `any`. `ModelForm` props typed from schema (`ProviderResponse[]`/`ModelFamilyListResponse[]`), dropping `providersForFamily(... as any)`. `ModelView` selectedFamily/familyItems casts removed. `ModelFamilyView` param helpers take `unknown` + a typed `ParamSchema` cast (opaque JSON blob) instead of `any`. Creator `update:field` emit value typed as `CharacterData[keyof CharacterData]`, letting `CharacterCreateView` drop its `(field: any, val: any)` handlers. `ChatView` alternatives cache typed from `fetchAlternatives`' return. **The generic DataTable surfaced a real dead-code bug the `any` hid**: `ModelFamiliesTab` read `row.extra_metadata?.supports_prompt_caching`, a field absent from `ModelFamilyListResponse`, so the cache badge never rendered — removed (spawned a follow-up task to restore it properly via a contract change if wanted). Remaining `any` are defensible: the dynamic param-schema in `ParamInput`/`ModelInferenceParams`, `useBookmarks`/`AppSidebar` (deferred to V2-C3), and infra (`i18n`/`main`). Validated: `bun run build`, 8 tests, `vp lint` all pass. Commit: `5fb9d6f`.
- **[x] V2-B4** — migrated every genuine semantic-status hue to DaisyUI tokens (`success`/`error`/`warning`/`info`): online dots (AppSidebar, ChatHeader), provider/model enabled+key+state status (ProvidersTab, ModelView, ProviderView, SetupWizardView), log status pills + user role (LogDetailModal), active/enabled badges (PresetView, TemplateView), fragment Global/Unused/filter (FragmentsTab), and import result panels + warning callouts (ImportPresetModal, ProfileForm). Census confirms **0 status hues remain** outside documented exceptions. Kept (and documented in AGENTS §6.3) as intentional non-status exceptions: category colors (FragmentsTab type badges, TemplateView position badges, ModelFamilyView capability badges incl. `purple`), the MemoryView relevance-score scale, provider brand chips (LogsTab/LogDetailModal), and the tuned ToastContainer light/dark shade ramp. **Mechanical lint guard deferred to V2-C4** (which owns the lint stack reconciliation) — status-vs-category can't be auto-distinguished, so the convention is documented instead of a false-positive-prone blanket rule. Validated: `bun run build`, 8 tests, `vp lint` pass; themed visual check folded into the end-of-run browser smoke test. Commit: `077f4b6`.
- **[x] V2-B5** — added `useKeyedConfirmAction` (per-row armed key + shared auto-disarm timer) alongside `useConfirmAction`, and adopted two-step confirm everywhere it was hand-rolled: `PersonaTab`, `ProfilesTab`, `MemoryView`, `LorebooksView` (two lists) now use the keyed variant (**several previously had no auto-disarm at all** — now fixed), and `ChatDrawer` uses the plain variant (dropping its manual `deleteTimer` + unmount cleanup). Child cards (`ProfileCard`/`LoreEntryCard`) keep their `pendingDelete` prop, driven by the parent's armed key. `onConfirm` widened to `() => unknown` so delete callbacks returning `Promise<boolean>` type-check. **`useOverlayTransition` extraction is moved into V2-C1** (the ChatDrawer split): the drawer is the other overlay consumer, so both `Modal` and `ChatDrawer` will adopt it there with less rework. Validated: `bun run build`, 8 tests, `vp lint` all pass. Commit: `6a57680`.
- **[x] V2-B6** — removed the `tsconfig.json` `__tests__` exclude and added `src/bun-test-env.d.ts` (`/// <reference types="bun-types" />`) so `vue-tsc` type-checks the test files (local `build` + CI Type Check) — this immediately caught a **real drift** the exclusion hid: `useCharacterForm.test.ts`'s `CharacterResponse` mock was missing `created_at`/`updated_at` (fixed). CI already runs `bun run test` as its own step, so tests are both type-checked and executed in the gate. Added lazy-chunk recovery: `router.onError` does a one-shot hard reload on a "failed to fetch dynamically imported module" error (sessionStorage-guarded against loops), and `AppShell` wraps `<RouterView>` in an `onErrorCaptured` boundary that renders a recoverable fallback (new `common.errorBoundary.*` i18n keys) instead of a blank pane. Validated: `bun run build`, typecheck (tests included, 0 errors), 8 tests, `vp lint` all pass. Commit: `edd17e5`.
- **[x] V2-B7** — the inner SSE handler (`service.py`) now mirrors the router boundary: `message = str(e) if isinstance(e, ProviderException) else "An unexpected error occurred."` (raw detail still logged), keeping `classify_error(e)` for the code. New test `test_stream_internal_error_is_generic` asserts a non-provider mid-stream fault yields the generic message (no leaked internals) + a classified code. Validated: ruff clean, basedpyright 0/0/0, 864 passed. Commit: `f7f6da7`.
- **[x] V2-B8** — `GET /api/providers` and `GET /api/prompt-templates/{id}/fragments/` now return `PaginatedResponse[T]` via `collection_response(...)`, matching every other collection endpoint. Regenerated `openapi.json` (`scripts/openapi.sh`) + `frontend/src/api/schema.d.ts` (`bun run api:gen`). Updated consumers to read `data.items` (`stores/settings.ts` fetchProviders, `usePromptTemplate.fetchAttachedFragments`) and both MSW handlers to emit the `{items, meta}` envelope. Backend `test_list_providers_empty` updated to assert the envelope. Validated: backend ruff/basedpyright/238 tests pass; contract regenerated; `bun run build`, 8 tests, `vp lint` pass. Commit: `1409529`.
- **[x] V2-C3** — `useBookmarks` now uses `client.GET` for all three endpoints, branches on `error` (surfaces via the shared `error` ref instead of resolving 4xx/5xx bodies as "data"), and types refs from the schema (`CharacterResponse[]`/`ChatResponse[]`/`MessageResponse[]`), dropping `any[]`. This also resolved the deferred `AppSidebar` `session: any`. Typing surfaced that `BookmarksView` rendered enriched fields (`msg.character`/`msg.chat`/`session.bookmarked_at`) absent from the contract — the messages/characters endpoints are backend stubs returning `[]`, so the message card was simplified to `MessageResponse` fields and `bookmarked_at` → `updated_at`; nullable avatars coerced. Spawned a follow-up task to implement real message-bookmarking + restore the enriched card. Validated: `bun run build`, 8 tests, `vp lint` all pass. Commit: `402f46e`.
- **[~] V2-C5 (partial)** — **async `get_or_404` DONE**: added `async_get_or_404(repo, id, name, finder=…)` to `core/base_service.py` (optional `finder` for relations-eager variants) and folded `get_chat_or_404` onto it — one async 404 helper. Validated: ruff clean, basedpyright 0/0/0, 864 passed. **Character payload DTO NOT viable / won't-fix**: attempted a `CharacterFormBase`/`CharacterCreateForm` consumed by both router and service, but FastAPI treats `Annotated[Model, Form()]` **alongside** a `File()` param (the avatar) as a single embedded body field named `data` (422s on flat form posts) rather than spreading the model's fields — so a multipart-with-file endpoint genuinely requires enumerated `Form()` params. The "declared once" DTO isn't achievable here without dropping the avatar from the same request; reverted that attempt. (Pydantic field-narrowing also fought pyright's `reportIncompatibleVariableOverride`.) Left the enumerated Form fields as the necessary shape. Commit: `1de55f9`.
- **[x] V2-D4** — `ProviderService.delete()` now raises the domain `ConflictError` (→ 409) instead of `NotImplementedError`, so if ever routed it maps cleanly through the global handler rather than becoming an unhandled 500. Tests updated to assert `ConflictError`/409. Validated: ruff clean, 28 provider tests pass. Commit: `0220f06`.
- **[x] V2-D9** — moved `from src.core.config import settings` from inside `export_as_png` to module scope in `character/service.py` (`core.config` is a leaf, not a cycle workaround). Validated: ruff clean, basedpyright 0/0/0, 42 character tests pass. Commit: `23eaa77`.
- **[x] V2-D5** — added a nullable `data_bank_entry_id` FK on `embeddings` → `data_bank_entries.id` `ON DELETE CASCADE` (mirroring BE-1's `chat_id` fix), stamped in `vectorize_data_bank_entry`. Now deleting an entry — directly or when its chat/character cascades — removes its embeddings instead of orphaning them. Migration `33655fb747cf` adds the column/index/FK, backfills existing data_bank embeddings from `source_id`, and purges pre-existing orphans. New test asserts the FK is stamped. Validated: ruff clean, basedpyright 0/0/0, migration applied + `alembic check` clean, 865 passed. Commit: `fb27f1f`.
- **[x] V2-D6** — `APIError` regained `statusCode?: number`; `extractApiError(error, fallback, status?)` sets it. `multipartFetch` passes `response.status`, and `useEntityCrud`'s `ClientResult` now carries `response` so all four CRUD paths + `runSaving` thread `response?.status` into the error — so any caller catching an `APIError` from those central paths can branch on 404 vs 409 vs 422. Validated: `bun run build`, 8 tests, `vp lint` pass. Commit: `4afa9ae`.
- **[x] V2-D2** — `useEntityCrud` `createItem`/`updateItem`/`removeItem`/`runSaving` now clear `error` at the start and record it via a shared `recordError()` on failure (still rethrowing), so the returned `error` ref reflects failed writes — consistent with `fetchItem`. Validated: `bun run build`, 8 tests, `vp lint` pass. Commit: `6a70628`.
- **[x] V2-D1** — added a monotonic request-token guard to `usePaginatedList.loadPage` and `useCursorList.load`: each call captures `++requestSeq` and only applies its result/error/loading if still the latest, so a slower earlier response can't clobber a newer one (fast filter/search or chat switch = last-request-wins). `useCursorList.reset()` bumps the token to invalidate an in-flight load mid-switch. Chose a sequence guard over `AbortController` to avoid threading a signal through every `fetchPage` closure. Validated: `bun run build`, 8 tests, `vp lint` pass. Commit: `1f9d973`.
- **[x] V2-D8** — `readStream`'s catch now drops the empty placeholder on **any** exit (abort included) when nothing streamed yet, so hitting stop before the first token no longer leaves a blank assistant bubble. Validated: `bun run build`, 8 tests pass. Commit: `72c7a38`.
- **[x] V2-D7** — added a module-level `modalStack` (shared across `Modal` instances via a plain `<script>` block); each modal pushes/pops its `Symbol` on open/close/unmount, `handleKeyDown` no-ops unless it's the top of the stack, and body-scroll-lock stays engaged while any modal remains open beneath. Stacked modals no longer fight over focus/keys. Validated: `bun run build`, 8 tests, `vp lint` pass. Commit: `<pending>`.
