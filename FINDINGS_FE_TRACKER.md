# Frontend Fix Tracker — The Bannered Mare

**Living execution tracker** for the findings in [FINDINGS_FE.md](FINDINGS_FE.md). That file is the immutable *diagnosis* (evidence, `file:line`, rationale); **this file is the mutable *treatment*** — the source of truth for what's done, in flight, and next. When context is summarized on a long run, resume from **this file + the code + git**, never from chat memory.

---

## STATE

- **Updated:** 2026-07-15
- **Active:** structural/DRY tier essentially DONE — FE-M3/M4 (`useListCrud`), FE-H4 (utilities), FE-M1 (store self-invalidation), FE-M7 (view logic → composables). FE-M2 deferred by decision (lowest ROI for a local app). Next candidates: FE-M5 (correctness — stop button), i18n (FE-H2 b/c + FE-H3), low (FE-L2/L3).
- **Next up:** FE-M5 (correctness); then i18n FE-H2 b/c + FE-H3; low FE-L2/L3. (FE-M2 + ProviderModelRow deferred, documented.)
- **Progress:** 17 / 29 done (FE-C1, FE-H6, FE-H7, FE-C3, FE-H1, FE-C2, FE-M9, FE-L1, FE-L4, FE-L5, FE-M10, FE-L6, FE-L7, FE-M3, FE-M4, FE-H4, FE-M7 ✓; FE-L8 folded in) + FE-M1 (FE-M1/M2 half-done) + FE-H2 part-a. **Remaining:** FE-M5, FE-M2 (deferred), FE-L2/L3, FE-H2 b/c, FE-H3.

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

### FE-H1 · Wire or delete the "Stream Responses" / "Typing Indicator" toggles · [x] DONE — removed (see §Completed) · 🤖 sub · dep: none
- **Ref:** FINDINGS_FE.md §3 FE-H1 · **Files:** `InterfaceTab.vue:70-93`; `useChatMessages.ts:231,278`
- **Fix:** either pass a `stream` flag into `sendMessage`/`regenerate` and branch on it (lift the setting into a `useChatSettings` singleton so the chat can read it), or delete the two toggles.
- **Accept:** toggling "Stream Responses" off measurably changes request behavior, **or** the dead toggles are removed; gates green.
- **Commit:** —

### FE-C2 · Characterization tests for the SSE state machine · [x] DONE (see §Completed) · 🤖 sub · dep: FE-C1
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

### FE-M9 · Cover `useCharacterForm`'s gnarly paths + the `useCursorList` race guard · [x] DONE (see §Completed) · 🤖 sub · dep: FE-C1
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

### FE-H2 · Move hardcoded English toasts/view text into vue-i18n · [~] PARTIAL — toasts done; SetupWizard + settings-headings deferred (see §Completed) · 🤖 sub · dep: none
- **Ref:** FINDINGS_FE.md §3 FE-H2 · **Files:** 57 `toast.*("literal")` sites; `SetupWizardView.vue` (0 i18n); settings-detail headings/date labels (see finding)
- **Fix:** move literals to `en.json` keys + `t()`/`$t`; internationalize `SetupWizardView` wholesale; add an ESLint `vue-i18n/no-raw-text` (or a `toast.*` literal check) to CI.
- **Accept:** `toast.*("literal")` count → 0; `SetupWizardView` uses `$t`; a lint rule fails on new raw text; gates green.
- **Commit:** —

### FE-H3 · Fill the 4 non-English locale catalogs (~200 keys each) · [ ] · 🤖 sub · dep: FE-H2 (so keys are final)
- **Ref:** FINDINGS_FE.md §3 FE-H3 · **Files:** `locales/de.json`, `es.json`, `fr.json`, `pt.json`
- **Fix:** mirror the `en.json` structure (incl. `profiles`/`lorebooks`/`presetImport`/`chat.profile`/`nav.*`), preserving `{name}`/`{count}` tokens.
- **Accept:** each locale has the same key set as `en.json`; a key-parity check passes; gates green.
- **Commit:** —

### FE-H4 · Extract `AppCard`/`AppInput` + a `focus-ring` utility · [x] DONE — shipped as `@utility` classes (see §Completed) · 🧵 main · dep: none
- **Ref:** FINDINGS_FE.md §3 FE-H4 · **Files:** new `components/shared/AppCard.vue`/`AppInput.vue`; `assets/main.css` (`@utility focus-ring`); ~68 Card + ~20 Input + 42 focus-ring sites
- **Fix:** build the two primitives + the utility; migrate call sites incrementally.
- **Accept:** the focus-ring magic shadow lives in one `@utility`; Card/Input inline copies materially reduced; `lint:tailwind`/`lint:canonical` clean; gates green.
- **Commit:** —
- **Notes:** large coordinated migration — main-thread, migrate in batches with a build between.

### FE-M3 · `useListCrud` factory · [x] DONE (see §Completed) · 🧵 main · dep: none · pairs-with: FE-M4
- **Ref:** FINDINGS_FE.md §4 FE-M3 · **Files:** new `composables/useListCrud.ts`; `useProfiles`/`usePersonas`/`useDataBank`/`useLorebooks`/`usePresets`/`usePromptTemplates`
- **Fix:** extract a list+CRUD (+ optional single-default reconcile) factory; migrate the hand-rolled composables; delete the `usePresets`≈`usePromptTemplates` copy-paste.
- **Accept:** those composables reduce to thin config; the `err instanceof Error ? …` boilerplate (15×) collapses; behavior unchanged; gates green.
- **Commit:** —

### FE-M4 · Standardize the error contract (stop swallowing) · [x] DONE (see §Completed) · 🤖 sub · dep: FE-M3
- **Ref:** FINDINGS_FE.md §4 FE-M4 · **Files:** `useProfiles.ts:52-118`; `usePersonas.ts`
- **Fix:** record failures on the shared `error` ref (optionally rethrow) as `useEntityCrud` does — no more `console.error`+return-null.
- **Accept:** a failed mutation sets `error`/surfaces a toast (never silent); gates green.
- **Commit:** —

### FE-M1 / FE-M2 · One state-cache strategy (kill provider split-brain) · [~] FE-M1 done (see §Completed); FE-M2 open · 🧵 main · dep: none
- **Ref:** FINDINGS_FE.md §4 FE-M1, FE-M2 · **Files:** `stores/settings.ts:19-62`; `useProvider.ts`; the per-instance-fetch composables
- **Fix:** pick one strategy — a small `useResource`/query cache keyed by endpoint, or promote shared lists to the store (like providers) with self-invalidating mutations.
- **Accept:** provider mutations no longer require manual `fetchProviders(true)` at each call site; no per-instance duplicate fetches for shared lists; gates green.
- **Commit:** —

### FE-M7 · Extract logic out of the over-large views · [x] DONE — both views' logic extracted; ProviderModelRow deferred (presentational) (see §Completed) · 🤖 sub (one view per commit)
- **Ref:** FINDINGS_FE.md §4 FE-M7 · **Files:** `ProviderView.vue:111-164,238-274`; `ChatView.vue:268-310`
- **Fix:** `useProviderModelFilter`/`useLocalModelManagement` + a `ProviderModelRow` subcomponent; move ChatView swipe/alternatives logic into `useChatMessages`.
- **Accept:** no repository-layer/business logic left in these views; gates green. (Do `ProviderView` and `ChatView` as separate commits.)
- **Commit:** —

### Low items (batch as 🤖 sub)
- **FE-L1** `[x]` DONE (see §Completed) — `utils/date.ts` (`formatDate` + i18n `timeAgo`); 10 sites routed through it, behavior preserved.
- **FE-L2** `[ ]` replace native `confirm()` with `useConfirmAction` (`ProviderView.vue:250,263,277`; `FragmentCreateView.vue:66`; `TemplateCreateView.vue:64`).
- **FE-L3** `[ ]` implement or hide the stub `console.log` handlers (`CharactersView.vue:149,172`; `TemplateView.vue:159`).
- **FE-L4** `[x]` DONE — removed `main.ts` prod `console.log`; the catch-block→`useAppToast` surfacing folds into FE-M4.
- **FE-L5** `[x]` DONE — `ModelFamilyView` unsupported-params pill → `error` token; MemoryView category maps left as documented-category-color (doc-wording nit deferred).
- **FE-L6** `[x]` DONE (see §Completed) — shared `src/types/params.ts` `ParamSchema`; all `any`s in ParamInput/ModelInferenceParams eliminated.
- **FE-L7** `[x]` DONE (see §Completed) — `utils/route.ts::routeParam` helper across 8 sites (1 create-mode site left, flagged).
- **FE-M10** `[x]` DONE (see §Completed) — 5 `@theme` tokens; 153 arbitrary micro-rem sizes converted across 52 files. *(Rem-based → not a scale-breaking bug; DRY only.)*
- **FE-L-latent** — folded into **FE-M5** (do not schedule separately).
- **FE-L8** — `[x]` resolved by **FE-C1** (`process.env.VITE_API_URL` hack removed; `import.meta.env` now injected by `vp test`).

---

## Completed

_(Move items here with `[x]`, the fixing commit hash, and a one-line note on what changed / what surprised you. Never delete.)_

- **[x] FE-M7** (commits `daa3433`, `d8d7ad1`) — extracted the business logic out of the two over-large views. **ProviderView:** `useProviderModelFilter` (debounced search + allow-list chips) + `useLocalModelManagement` (Ollama/LM Studio load/unload/delete/sync confirm+toast wrappers), both taking the view's single `useProvider` instance as deps (it isn't a singleton) — script 324→220. **ChatView:** moved the alternatives cache + getAlternativeCount/getCurrentAltIndex/handleSwipe verbatim into `useChatMessages` (they operate purely on its `messages` + fetch/activate) — script 311→267. Templates + behaviour unchanged; the extracted logic is now unit-testable. **Deferred (optional):** the `ProviderModelRow` subcomponent — purely presentational template extraction, lower value than the logic move; ProviderView's template bloat remains but the "repository-layer work in a view" concern is resolved. Gate: build, 60 tests, oxlint, tailwind.
- **[~] FE-M1** (commit `3939e5c`; the FE-M1 half of the FE-M1/M2 item) — the provider list is a Pinia store singleton, but `useProvider`'s create/save (via `useEntityCrud`) never touched it, so the shared list went stale unless each call site manually `fetchProviders(true)` (ProviderView + ProvidersTab both did). Moved the invalidation into `useProvider.createProvider/saveProvider` (refresh the store on success) and removed both manual call sites (ProviderView drops the now-unused `settingsStore`; ProvidersTab keeps `refresh` for its error-retry). **FE-M2 still open** — the broader "unify per-instance list caching (presets/templates/personas/profiles/databank)" half needs a strategy pick (a `useResource` query-cache vs promoting those lists to the store like providers). Gate: build, 60 tests, oxlint, tailwind.
- **[x] FE-H4** (commits `213bfbb`, `60d5b4f`, `577b5a6`) — shipped as **three `@utility` classes**, NOT the tracked `AppCard.vue`/`AppInput.vue` components (user call: style-only patterns with varied bindings → a utility is a drop-in class swap with zero binding churn, consistent with the focus-ring approach). `focus-ring` (46 sites: 42 `focus:`, 1 `focus-within:`, 3 bare-in-ternary), `input-field` (19 sites, composes focus-ring; `font-mono`/`pr-10` kept at call sites), `app-card` (10 exact-`p-4` sites; named `app-card` to dodge DaisyUI's `.card`). Each verified against the **built CSS** — byte-identical declarations incl. the composed `:focus` ring. Deliberately left: the different-value shadows (/0.1 glow, /0.12), 2 flex trigger-buttons, PresetView's `flex-1` input, SetupWizard's divergent `px-3`/`focus:ring-1` input, and all non-`p-4` card-ish surfaces (the finding's "~68" counted those loosely; the canonical p-4 card is 10). AGENTS/CLAUDE §6.3 Input/Card patterns updated to reference the utilities. Gate: build, 60 tests, oxlint, both tailwind lints.
- **[x] FE-M3 + FE-M4** (commits `049e825`, `330e8f1`) — added `useListCrud` (the list sibling of `useEntityCrud`) and migrated presets/templates (list-only), then profiles/dataBank/personas (list+CRUD) onto it — killed the usePresets≈usePromptTemplates copy-paste. **FE-M4:** the migrated mutations now record failures on the shared `error` ref instead of `console.error`+swallow (useProfiles/useDataBank never set `error` before — the real silent-failure bug); kept the null/false **return contract** the callers already branch on (ProfilesTab toasts on the result; PersonaTab keeps the form open + shows `error`), so **zero caller changes** — verified by a full `vue-tsc -b` across every consumer. Design note: the list factory records-and-returns rather than rethrowing like useEntityCrud, because these list callers switch on the result inline (vs a detail page's one-shot await). **Deliberately NOT migrated:** `useLorebooks` (outlier — detail `currentLorebook`, parallel fetch-for-chat merge, nested entry CRUD); `usePersonas.savePersona` stays bespoke (multipart avatar upload openapi-fetch can't do) but runs on the factory's items/error refs. Only signature change: `useProfiles.setDefault` Profile|null→boolean (truthiness-only). Not yet covered by a failed-mutation test — behavior mirrors the proven useEntityCrud path. Gate: build, 60 tests, oxlint, both tailwind lints.

- **[x] FE-L6 + FE-L7** (commit tagged `FE-L6`, `FE-L7`) — **FE-L6:** introduced a shared recursive `src/types/params.ts` `ParamSchema` (type/default/min/max/str_values + recursive `item_schema`/`properties`) and eliminated every `any` in `ParamInput.vue`/`ModelInferenceParams.vue`; `ModelFamilyView` dropped its local copy for the shared one. Typed cleanly (one narrow `default as number` cast in a numeric-only computed). **FE-L7:** new `utils/route.ts::routeParam(value): string` (+ test) replacing `route.params.x as string` across **8** sites (grep found more than the cited 2); deliberately left `CharacterCreateView:22` (`as string | undefined` — its `undefined` signals create-mode, which `routeParam` would change). Verified: build, 60 tests, coverage ≥ floor, lint/fmt green.
- **[x] FE-M10** (commit tagged `FE-M10`) — defined 5 named font-size tokens in `main.css` `@theme` (`--text-2xs` 0.6875rem, `--text-3xs` 0.625rem, `--text-4xs` 0.5625rem, `--text-5xs` 0.5rem, `--text-2sm` 0.8125rem) and replaced all **153** arbitrary `text-[…rem]` values across 52 files (66/57/27/2/1). Rem-based so rendering is byte-identical (behavior-preserving, not a bug fix); no line-height companions needed. Verified: `grep text-[…rem]` clean, `lint:tailwind` passes (the new tokens make the old arbitraries "unnecessary" — all converted), build + 59 tests + canonical + fmt green.
- **[~] FE-H2 — part (a) toasts done; (b) SetupWizard + (c) settings-headings deferred** (commit tagged `FE-H2`) — migrated **61 toast calls → vue-i18n keys, 0 hardcoded literals left** (57 cited + 4 backtick/ternary in `ProviderView` with interpolation → named `{model}` params). Added feature-namespaced keys to `en.json` ONLY (chat/setup/connections.provider·model·family·preset·template·fragment `.toast`) — de/es/fr/pt fall back to English (the FE-H3 gap; don't widen further without FE-H3). Wired `useI18n` into 8 files, reused `t` in 5; `useCreateChat` gets `t` at composable-body top (valid setup context). Left `SetupWizardView`'s non-toast strings + settings headings/date-labels for parts (b)/(c). Verified independently: build (vue-tsc → all keys resolve), 59 tests, coverage exit 0, lint/fmt clean, 0 remaining literals, en.json valid, 0 missing keys.
- **[x] FE-L4 + FE-L5** (commit tagged `FE-L4`, `FE-L5`) — **FE-L4:** removed the unconditional prod `console.log("The Bannered Mare initialized…")` from `main.ts` (the broader "route catch-block logs through `useAppToast`" folds into FE-M4). **FE-L5:** converted the "unsupported parameters" pill in `ModelFamilyView.vue` from raw `bg-red-500/10 text-red-400` to the semantic `bg-error/10 text-error` token (negative status, not a capability/category badge); the MemoryView category/scope maps are left as defensible category colors (widening the AGENTS.md exception wording is a deferred doc nit). Verified: build, 59 tests, oxlint + `lint:tailwind` + `lint:canonical` + fmt all clean.
- **[x] FE-L1** (commit tagged `FE-L1`) — created `src/utils/date.ts` (`formatDate` + `timeAgo`, pure, `t`-injected like `formatLog.ts`) + `date.test.ts` (6 tests), and routed 10 call sites through it. **Behavior preserved exactly:** 6/7 `formatDate` were identical (medium date + short time); `CharacterDetailView`'s outlier (long date-only `en-US`) kept via a parameterized call + thin local wrapper. `timeAgo` was 3 distinct behaviors — consolidated the **4 i18n** variants (`justNow`/`weeks` knobs; `BookmarksView` uniquely omits just-now + adds a weeks bucket) and **deliberately left** the non-i18n `CharacterListRow` (variant A, hardcoded compact English) untouched to avoid changing its output. Verified: 59 tests, coverage 6.61% lines ≥ floor, build/lint/fmt green.
- **[x] FE-M9** (commit tagged `FE-M9`) — +20 tests (33→53): extended `useCharacterForm.test.ts` (+13: gender→`custom_gender` incl. free-text→`others`+verbatim and blank-omit; `example_dialogues` regex round-trip incl. freeform preservation + `<START>` stripping; the lorebook entry-diff driving exactly one DELETE / one PUT / one POST) and new `useCursorList.test.ts` (+7: last-request-wins race via out-of-order resolution, `reset()` invalidation, `loadMore` gating, null-`fetchPage` no-op). Target coverage: `useCharacterForm.ts` **80.7%** lines, `useCursorList.ts` **91.2%**. Also fixed a latent pollution hazard — the old "species and age" test swaps `client.GET` with no restore, so the new suites capture the pristine client and restore in `before/afterEach`. **2 findings (documented, not fixed — follow-up candidates):** (a) dead self-assignment `useCharacterForm.ts:155` (`if (data.gender === "Non-binary") data.gender = "Non-binary";`); (b) a freeform dialogue edit+save restructures the stored format to `User: \nCharacter: <text>` (content preserved, not data loss). Verified independently: 53 tests, coverage 6.4% lines ≥ floor, build/lint/fmt green.
- **[x] FE-C2** (commit tagged `FE-C2`) — added 11 characterization tests for `readStream` + `sendMessage`/`regenerate` to `useChatMessages.test.ts` (22→33): partial-chunk reassembly (one frame split across 4 stream chunks), `[DONE]` short-circuit, malformed-JSON tolerance (warn + skip, later text still lands), `reasoning` accumulates separately, `start` id-swap (with/without `message_id`), `error` → placeholder dropped + `error.value` set, non-OK send, **abort mid-stream** (signal-wired mock + `flushPromises` → quiet resolve, no blank bubble), **chat-switch mid-stream** (post-switch token doesn't land — exercises the re-find-by-id `-1` guard), and `regenerate`. Coverage 4.75→**5.73%** lines. **Characterization notes (no bug):** `sendMessage` does NOT reject on stream `error`/non-OK/abort — it surfaces via `error.value` and resolves (for the toast layer); the chat-switch `reset` only fires under `autoLoad:true` (the prod default), so the tests use it. Verified independently: 33 tests, coverage ≥ floor, build/lint/fmt green.
- **[x] FE-H1** (commit tagged `FE-H1`) — **removed** the write-only "Stream Responses" / "Typing Indicator" toggles from `InterfaceTab.vue` (refs, the `onMounted` localStorage hydration, both handlers, the orphaned `onMounted` import, and the two template rows — three dividers collapsed to one). Chose removal over wiring: wiring "Stream Responses" means building a whole non-streaming (blocking) send path in `useChatMessages` (a feature, unverifiable without running the app) and "Typing Indicator" has no clear consumer — an advertised-but-broken control is worse than none. **Reversible** if you'd rather have it as a feature. Left the 4 now-orphaned `settings.interface.stream*/typing*` i18n keys (present in all 5 locales) for the FE-H2/H3 i18n sweep. Verified: build/lint/fmt green, 22 tests pass.
- **[x] FE-C3** (commit tagged `FE-C3`) — verified the backend persists the user message but streams only the *assistant* id in `start` (`chat_message/service.py:419-420,508-516`), so a FE-only fix must refetch. Added `reconcileSentUserMessage()`: after `readStream` completes in `sendMessage`, GET the 2 newest messages and swap the just-sent user bubble's client uuid for the persisted id **in place** (mutates `messages` directly — no cursor-list reset, so pagination/scroll are preserved); best-effort (a failed reconcile keeps the pre-fix behavior, never breaks a successful send). Regression test `useChatMessages.test.ts` drives send → reconcile → edit and asserts the edit PUTs `/messages/user-real` (would've been a phantom uuid pre-fix). Verified: 7 files / 22 tests, coverage up to **4.73%**, build/lint/fmt green.
- **[x] FE-H7** (commit tagged `FE-H7`) — added `@vitest/coverage-v8@4.1.9`, a `coverage` block in `vite.config.ts` (v8, `all: true`, product-code include, `text-summary`+`json-summary` reporters), a `test:coverage` script, and switched the CI "Test" step to `bun run test:coverage`. Floor set just under the measured baseline — lines 2.5 / stmts 2.5 / fns 1.3 / branches 1.6 (actual 2.66/2.59/1.4/1.69) — so CI catches regressions and ratchets up as Wave 2/3 tests land. **Surprise + fix:** enabling `--coverage` made `localStorage` resolve to Node's experimental native binding (undefined) instead of happy-dom's on `globalThis`, so `i18n.ts`'s module-load `localStorage.getItem` threw and failed all suites (intermittently — it depends on which global wins). Added `src/test/setup-globals.ts` (a setupFile ordered BEFORE `setup.ts`, since ES imports hoist) that binds `localStorage` to happy-dom's `window.localStorage` or an in-memory stub. Confirmed happy-dom's `document` is otherwise intact under coverage (mount tests pass). Verified: coverage stable 3/3 (2.66% ≥ floor), plain `vp test run` + build + lint + fmt all green; `coverage/` already gitignored.
- **[x] FE-H6** (commit tagged `FE-H6`) — added `src/mocks/server.ts` (`setupServer(...handlers)` reusing the exact handler array `browser.ts` feeds `setupWorker`) and wired `beforeAll(server.listen({onUnhandledRequest:"error"}))` / `afterEach(resetHandlers)` / `afterAll(close)` into `src/test/setup.ts`. Demonstration test `useProviders.test.ts` drives the real composable → store → **unpatched** typed client and asserts the `/api/providers` fixture loads through MSW (no `global.fetch`/`client` monkeypatch). **No extra deps or config needed** — msw 2.14.6 was already present; happy-dom resolves the relative `/api/...` path against its default origin and msw/node matches by pathname. Verified independently: `vp test run` = 6 files / 21 tests; build/lint/fmt green. Note: setup now imports the full handler+fixture graph on every test file's critical path (~0.45s) — fine, but known.
- **[x] FE-C1** (commit tagged `FE-C1`) — switched `"test"` `bun test`→`vp test run`; **removed the `"vitest": "npm:@voidzero-dev/vite-plus-test"` override** — it exposes no `vitest` bin and broke `vp test`, while `vite-plus` already depends on real `vitest@4.1.9`, which now resolves. Added `@vue/test-utils` + `happy-dom`; added a `test` block to `vite.config.ts` (`happy-dom` env + `src/test/setup.ts` registering i18n + the 3 global primitives so `mount()` mirrors `main.ts`); migrated the 4 tests off `bun:test`→`vitest` (dropped the bun-only `process.env` hack → also closes FE-L8); deleted the obsolete `src/bun-test-env.d.ts`; added an `AppToggle` **smoke test that mounts a real SFC**. Verified: `vp test run` = **5 files / 20 tests pass**; `bun run build` + `vp lint` + `vp fmt --check` green; CI runs `bun run test`→`vp test run` (`vp` from `node_modules/.bin`) so it's unbroken. **Surprise:** the blocker was not missing deps — it was the pre-existing `vitest` override clobbering the real bin.
