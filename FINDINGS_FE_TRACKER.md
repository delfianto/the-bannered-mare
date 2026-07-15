# Frontend Fix Tracker — The Bannered Mare

**Living execution tracker** for the findings in [FINDINGS_FE.md](FINDINGS_FE.md). That file is the immutable *diagnosis* (evidence, `file:line`, rationale); **this file is the mutable *treatment*** — the source of truth for what's done, in flight, and next. When context is summarized on a long run, resume from **this file + the code + git**, never from chat memory.

---

## STATE

- **Updated:** 2026-07-15
- **Active:** — (Wave 2 in progress)
- **Next up:** FE-H1 (toggles 🤖), then FE-C2 (SSE tests 🤖); pause before BE-H1 (structural) + the FE 🧵 migrations (FE-H4, FE-M1/M2/M3) and FE-M5
- **Progress:** 4 / 29 done (FE-C1, FE-H6, FE-H7, FE-C3 ✓; FE-L8 folded in)

---

## How to use this tracker (read once per session)

1. **Re-read this file and the specific item before touching code.** Chat history is not the source of truth; this file is.
2. **One item in flight at a time = one atomic commit**, with the ID in the message: `test(chat): SSE readStream characterization — FE-C2`. Then `git log --grep=FE-C2` reconstructs state even without this file.
3. **Definition of done** = acceptance criteria *actually run* + gates green + this file updated (move the item to §Completed with its commit hash + a candor note) + committed. No "should work."
4. **Write decisions/surprises into the item the moment they happen.** A decision left only in chat is lost.
5. **Update the STATE block** (Active / Next / Progress) on every status change.

**Legend** — Status: `[ ]` todo · `[~]` in progress / partial · `[!]` blocked · `[x]` done.
Exec: **🧵 main** = interdependent/structural, do sequentially in the main thread with full gate runs · **🤖 sub** = self-contained, safe to delegate to a fresh subagent.

## Gate baseline (must stay green after every item)

| Gate | Command |
|---|---|
| Format + lint + type | `cd frontend && vp check` |
| Build (authoritative) | `cd frontend && bun run build` (`vue-tsc -b && vp build`) |
| Tests | `cd frontend && bun test` |
| Tailwind canonical | `cd frontend && bun run lint:tailwind && bun run lint:canonical` |

> `vp` lives in `~/.vite-plus/bin`; prepend it to `PATH` if a fresh shell can't find it.

---

## Wave 1 — Establish a safety net (unblocks everything else)

### FE-C1 · Make the runner able to test the UI layer · [x] DONE (see §Completed) · 🧵 main · blocks: FE-C2, FE-H5, FE-M9, all component tests
- **Ref:** FINDINGS_FE.md §2 FE-C1
- **Files:** `package.json` (`"test"`, devDeps); `vite.config.ts` (add a `test` block); new `src/test/setup.ts`
- **Problem:** wired `bun test` has no DOM, no `@vue/test-utils`/`happy-dom`, and `.vue` imports resolve to a path string — no component can be mounted (0% of ~24K LOC UI reachable).
- **Fix:** switch `"test"` to **`vp test`** (the dormant `vitest` = `@voidzero-dev/vite-plus-test` alias, which applies `vite.config.ts`); add `@vue/test-utils` + `happy-dom`; set `test.environment: "happy-dom"` + a setup file that registers the 3 global components (`AppIcon`/`SelectMenu`/`AppToggle`) and i18n for mounts.
- **Accept:** a trivial smoke test **mounts** a real component (e.g. `MessageBubble.vue`) under `mount(...)` and asserts rendered text; the 4 existing tests still pass; `bun run build` + the new `test` command green in CI.
- **Commit:** —
- **Notes:** the single highest-leverage change — everything in Waves 2–3 test-writing depends on it. Keep it main-thread.

### FE-H6 · Reuse the MSW harness for tests via `msw/node` · [x] DONE (see §Completed) · 🤖 sub · dep: FE-C1
- **Ref:** FINDINGS_FE.md §3 FE-H6
- **Files:** new `src/mocks/server.ts`; the test setup file from FE-C1
- **Fix:** `export const server = setupServer(...handlers)`; wire `beforeAll(server.listen)`/`afterEach(server.resetHandlers)`/`afterAll(server.close)` in setup. The 2,173-line handler set + 38 fixtures then back all API-coupled composable tests.
- **Accept:** a composable test hits a real handler via unpatched `fetch` and asserts typed data (no `global.fetch` monkeypatch); resolves most of FE-H5; gates green.
- **Commit:** —

### FE-H7 · Make the CI test gate honest · [x] DONE (see §Completed) · 🤖 sub · dep: FE-C1
- **Ref:** FINDINGS_FE.md §3 FE-H7 · **Files:** `.github/workflows/frontend-ci.yml`
- **Fix:** run the new `vp test` in CI with coverage reporting + a low floor, ratchet upward as coverage lands.
- **Accept:** CI reports coverage and fails below the floor; green means something.
- **Commit:** —

---

## Wave 2 — Fix the confirmed bugs, then lock them with tests

### FE-C3 · Reconcile the optimistic user-message id · [x] DONE (see §Completed) · 🧵 main · dep: none
- **Ref:** FINDINGS_FE.md §2 FE-C3 (**verified live**)
- **Files:** `useChatMessages.ts:262-270` (user msg), `:158-166` (`start` arm), `:303-321` (`editMessage`)
- **Problem:** the user message keeps its `crypto.randomUUID()`; only the assistant placeholder id is reconciled → `editMessage` PUTs a non-existent id → 404 before the optimistic update.
- **Fix:** on the stream `start` event, reconcile the trailing user-message id too (backend includes it), or refetch the tail after send; alternatively gate the edit action off until the message has a server id.
- **Accept:** after a send with no reload, the last **user** message's `id` equals the backend id; a test drives send→edit-user-message and asserts 200 (not 404); `bun run build` + `bun test` green.
- **Commit:** —
- **Notes:** residual of audit V2-A2, which fixed the **assistant** side only. Verified by direct code read this session.

### FE-H1 · Wire or delete the "Stream Responses" / "Typing Indicator" toggles · [ ] · 🤖 sub · dep: none
- **Ref:** FINDINGS_FE.md §3 FE-H1 · **Files:** `InterfaceTab.vue:70-93`; `useChatMessages.ts:231,278`
- **Fix:** either pass a `stream` flag into `sendMessage`/`regenerate` and branch on it (lift the setting into a `useChatSettings` singleton so the chat can read it), or delete the two toggles.
- **Accept:** toggling "Stream Responses" off measurably changes request behavior, **or** the dead toggles are removed; gates green.
- **Commit:** —

### FE-C2 · Characterization tests for the SSE state machine · [ ] · 🤖 sub · dep: FE-C1
- **Ref:** FINDINGS_FE.md §2 FE-C2 · **Files:** `useChatMessages.ts:122-212` (+ new test)
- **Fix:** mock `global.fetch` → streaming `Response(new ReadableStream(...))` emitting `data: {...}\n\n` chunks.
- **Accept:** tests assert partial-chunk reassembly across reads, `[DONE]`, malformed-JSON tolerance, `error` event → throw + placeholder removed, abort mid-stream → quiet return + no blank bubble, chat-switch mid-stream → tokens don't land in the new chat; catches FE-C3-class + FE-L-latent regressions; gates green.
- **Commit:** —

### FE-M5 · Expose a stop button + fix regen-abort restore · [ ] · 🧵 main · dep: none · pairs-with: FE-L-latent
- **Ref:** FINDINGS_FE.md §4 FE-M5 + §5 FE-L-latent · **Files:** `useChatMessages.ts:64-68,201,219-222`; `ChatView.vue:40-54`
- **Fix:** destructure/expose `stop()` and render a stop button while `isGenerating`; **and** ensure `regenerate`'s optimistically-removed assistant message is restored on `AbortError` (the catch currently never runs because `readStream` returns quietly on abort).
- **Accept:** a stop button halts generation mid-stream; stopping a regenerate restores the prior reply (no lost message); covered by an FE-C2-style test; gates green.
- **Commit:** —
- **Notes:** the two are entangled — adding the button *activates* the latent restore bug, so fix together.

---

## Wave 3 — Extend coverage to the risk surface (all 🤖 sub, dep: FE-C1/FE-H6)

### FE-H5 · Injectable/contract-true API seam for composables · [ ] · 🤖 sub · dep: FE-H6
- **Ref:** FINDINGS_FE.md §3 FE-H5 · **Files:** the 29 composables importing `client`; test setup
- **Fix:** largely resolved by FE-H6 (composables hit real MSW handlers via unpatched fetch); where a monkeypatch remains, enforce `afterEach` restore.
- **Accept:** composable tests assert the right endpoint/params via MSW with no unrestored global patching; gates green.
- **Commit:** —

### FE-M9 · Cover `useCharacterForm`'s gnarly paths + the `useCursorList` race guard · [ ] · 🤖 sub · dep: FE-C1
- **Ref:** FINDINGS_FE.md §4 FE-M9 (+ §6 roadmap) · **Files:** `useCharacterForm.ts:110-119,164-185,211-276`; `useCursorList.ts`
- **Fix:** tests for gender→`custom_gender` normalization, the dialogue regex round-trip, a non-empty lorebook entry-diff (delete/create/update); and the `requestSeq` last-request-wins guard (fire two loads, resolve the stale one last, assert discarded; `reset()` invalidates in-flight).
- **Accept:** the untested ~80% of `useCharacterForm` and the race guard are covered; gates green.
- **Commit:** —

### FE-3a · First component smoke tests (prove the mount harness) · [ ] · 🤖 sub · dep: FE-C1
- **Ref:** FINDINGS_FE.md §7 Wave 3 · **Files:** new tests for `MessageBubble.vue`, `ParamInput.vue`
- **Fix:** `mount(...)` with the global/i18n harness; assert render + emitted events (`edit`/`regenerate`) and recursive param types.
- **Accept:** two component tests pass under the new runner, proving the mount pattern for the rest of the layer; gates green.
- **Commit:** —

---

## Wave 4 — Maintainability debt

### FE-H2 · Move hardcoded English toasts/view text into vue-i18n · [ ] · 🤖 sub · dep: none
- **Ref:** FINDINGS_FE.md §3 FE-H2 · **Files:** 57 `toast.*("literal")` sites; `SetupWizardView.vue` (0 i18n); settings-detail headings/date labels (see finding)
- **Fix:** move literals to `en.json` keys + `t()`/`$t`; internationalize `SetupWizardView` wholesale; add an ESLint `vue-i18n/no-raw-text` (or a `toast.*` literal check) to CI.
- **Accept:** `toast.*("literal")` count → 0; `SetupWizardView` uses `$t`; a lint rule fails on new raw text; gates green.
- **Commit:** —

### FE-H3 · Fill the 4 non-English locale catalogs (~200 keys each) · [ ] · 🤖 sub · dep: FE-H2 (so keys are final)
- **Ref:** FINDINGS_FE.md §3 FE-H3 · **Files:** `locales/de.json`, `es.json`, `fr.json`, `pt.json`
- **Fix:** mirror the `en.json` structure (incl. `profiles`/`lorebooks`/`presetImport`/`chat.profile`/`nav.*`), preserving `{name}`/`{count}` tokens.
- **Accept:** each locale has the same key set as `en.json`; a key-parity check passes; gates green.
- **Commit:** —

### FE-H4 · Extract `AppCard`/`AppInput` + a `focus-ring` utility · [ ] · 🧵 main · dep: none
- **Ref:** FINDINGS_FE.md §3 FE-H4 · **Files:** new `components/shared/AppCard.vue`/`AppInput.vue`; `assets/main.css` (`@utility focus-ring`); ~68 Card + ~20 Input + 42 focus-ring sites
- **Fix:** build the two primitives + the utility; migrate call sites incrementally.
- **Accept:** the focus-ring magic shadow lives in one `@utility`; Card/Input inline copies materially reduced; `lint:tailwind`/`lint:canonical` clean; gates green.
- **Commit:** —
- **Notes:** large coordinated migration — main-thread, migrate in batches with a build between.

### FE-M3 · `useListCrud` factory · [ ] · 🧵 main · dep: none · pairs-with: FE-M4
- **Ref:** FINDINGS_FE.md §4 FE-M3 · **Files:** new `composables/useListCrud.ts`; `useProfiles`/`usePersonas`/`useDataBank`/`useLorebooks`/`usePresets`/`usePromptTemplates`
- **Fix:** extract a list+CRUD (+ optional single-default reconcile) factory; migrate the hand-rolled composables; delete the `usePresets`≈`usePromptTemplates` copy-paste.
- **Accept:** those composables reduce to thin config; the `err instanceof Error ? …` boilerplate (15×) collapses; behavior unchanged; gates green.
- **Commit:** —

### FE-M4 · Standardize the error contract (stop swallowing) · [ ] · 🤖 sub · dep: FE-M3
- **Ref:** FINDINGS_FE.md §4 FE-M4 · **Files:** `useProfiles.ts:52-118`; `usePersonas.ts`
- **Fix:** record failures on the shared `error` ref (optionally rethrow) as `useEntityCrud` does — no more `console.error`+return-null.
- **Accept:** a failed mutation sets `error`/surfaces a toast (never silent); gates green.
- **Commit:** —

### FE-M1 / FE-M2 · One state-cache strategy (kill provider split-brain) · [ ] · 🧵 main · dep: none
- **Ref:** FINDINGS_FE.md §4 FE-M1, FE-M2 · **Files:** `stores/settings.ts:19-62`; `useProvider.ts`; the per-instance-fetch composables
- **Fix:** pick one strategy — a small `useResource`/query cache keyed by endpoint, or promote shared lists to the store (like providers) with self-invalidating mutations.
- **Accept:** provider mutations no longer require manual `fetchProviders(true)` at each call site; no per-instance duplicate fetches for shared lists; gates green.
- **Commit:** —

### FE-M7 · Extract logic out of the over-large views · [ ] · 🤖 sub (one view per commit)
- **Ref:** FINDINGS_FE.md §4 FE-M7 · **Files:** `ProviderView.vue:111-164,238-274`; `ChatView.vue:268-310`
- **Fix:** `useProviderModelFilter`/`useLocalModelManagement` + a `ProviderModelRow` subcomponent; move ChatView swipe/alternatives logic into `useChatMessages`.
- **Accept:** no repository-layer/business logic left in these views; gates green. (Do `ProviderView` and `ChatView` as separate commits.)
- **Commit:** —

### Low items (batch as 🤖 sub)
- **FE-L1** `[ ]` one `utils/date.ts` (or vue-i18n `d()`); replace `formatDate` ×7 / `timeAgo` ×5.
- **FE-L2** `[ ]` replace native `confirm()` with `useConfirmAction` (`ProviderView.vue:250,263,277`; `FragmentCreateView.vue:66`; `TemplateCreateView.vue:64`).
- **FE-L3** `[ ]` implement or hide the stub `console.log` handlers (`CharactersView.vue:149,172`; `TemplateView.vue:159`).
- **FE-L4** `[ ]` drop `main.ts:87` prod `console.log`; route catch-block logs through `useAppToast`.
- **FE-L5** `[ ]` `ModelFamilyView.vue:373` → `error` token; reconcile MemoryView category-map exception wording.
- **FE-L6** `[ ]` type the recursive `ParamInput.vue:6`/`ModelInferenceParams.vue:18` schema (or document the `any`).
- **FE-L7** `[ ]` typed route-params helper for `ChatView.vue:24`/`ProviderView.vue:169` (low priority for a local app).
- **FE-M10** `[ ]` define `--text-2xs`/`--text-3xs` in `@theme`; replace the 153 arbitrary micro-rem sizes. *(Rem-based → not a scale-breaking bug; DRY only.)*
- **FE-L-latent** — folded into **FE-M5** (do not schedule separately).
- **FE-L8** — `[x]` resolved by **FE-C1** (`process.env.VITE_API_URL` hack removed; `import.meta.env` now injected by `vp test`).

---

## Completed

_(Move items here with `[x]`, the fixing commit hash, and a one-line note on what changed / what surprised you. Never delete.)_

- **[x] FE-C3** (commit tagged `FE-C3`) — verified the backend persists the user message but streams only the *assistant* id in `start` (`chat_message/service.py:419-420,508-516`), so a FE-only fix must refetch. Added `reconcileSentUserMessage()`: after `readStream` completes in `sendMessage`, GET the 2 newest messages and swap the just-sent user bubble's client uuid for the persisted id **in place** (mutates `messages` directly — no cursor-list reset, so pagination/scroll are preserved); best-effort (a failed reconcile keeps the pre-fix behavior, never breaks a successful send). Regression test `useChatMessages.test.ts` drives send → reconcile → edit and asserts the edit PUTs `/messages/user-real` (would've been a phantom uuid pre-fix). Verified: 7 files / 22 tests, coverage up to **4.73%**, build/lint/fmt green.
- **[x] FE-H7** (commit tagged `FE-H7`) — added `@vitest/coverage-v8@4.1.9`, a `coverage` block in `vite.config.ts` (v8, `all: true`, product-code include, `text-summary`+`json-summary` reporters), a `test:coverage` script, and switched the CI "Test" step to `bun run test:coverage`. Floor set just under the measured baseline — lines 2.5 / stmts 2.5 / fns 1.3 / branches 1.6 (actual 2.66/2.59/1.4/1.69) — so CI catches regressions and ratchets up as Wave 2/3 tests land. **Surprise + fix:** enabling `--coverage` made `localStorage` resolve to Node's experimental native binding (undefined) instead of happy-dom's on `globalThis`, so `i18n.ts`'s module-load `localStorage.getItem` threw and failed all suites (intermittently — it depends on which global wins). Added `src/test/setup-globals.ts` (a setupFile ordered BEFORE `setup.ts`, since ES imports hoist) that binds `localStorage` to happy-dom's `window.localStorage` or an in-memory stub. Confirmed happy-dom's `document` is otherwise intact under coverage (mount tests pass). Verified: coverage stable 3/3 (2.66% ≥ floor), plain `vp test run` + build + lint + fmt all green; `coverage/` already gitignored.
- **[x] FE-H6** (commit tagged `FE-H6`) — added `src/mocks/server.ts` (`setupServer(...handlers)` reusing the exact handler array `browser.ts` feeds `setupWorker`) and wired `beforeAll(server.listen({onUnhandledRequest:"error"}))` / `afterEach(resetHandlers)` / `afterAll(close)` into `src/test/setup.ts`. Demonstration test `useProviders.test.ts` drives the real composable → store → **unpatched** typed client and asserts the `/api/providers` fixture loads through MSW (no `global.fetch`/`client` monkeypatch). **No extra deps or config needed** — msw 2.14.6 was already present; happy-dom resolves the relative `/api/...` path against its default origin and msw/node matches by pathname. Verified independently: `vp test run` = 6 files / 21 tests; build/lint/fmt green. Note: setup now imports the full handler+fixture graph on every test file's critical path (~0.45s) — fine, but known.
- **[x] FE-C1** (commit tagged `FE-C1`) — switched `"test"` `bun test`→`vp test run`; **removed the `"vitest": "npm:@voidzero-dev/vite-plus-test"` override** — it exposes no `vitest` bin and broke `vp test`, while `vite-plus` already depends on real `vitest@4.1.9`, which now resolves. Added `@vue/test-utils` + `happy-dom`; added a `test` block to `vite.config.ts` (`happy-dom` env + `src/test/setup.ts` registering i18n + the 3 global primitives so `mount()` mirrors `main.ts`); migrated the 4 tests off `bun:test`→`vitest` (dropped the bun-only `process.env` hack → also closes FE-L8); deleted the obsolete `src/bun-test-env.d.ts`; added an `AppToggle` **smoke test that mounts a real SFC**. Verified: `vp test run` = **5 files / 20 tests pass**; `bun run build` + `vp lint` + `vp fmt --check` green; CI runs `bun run test`→`vp test run` (`vp` from `node_modules/.bin`) so it's unbroken. **Surprise:** the blocker was not missing deps — it was the pre-existing `vitest` override clobbering the real bin.
