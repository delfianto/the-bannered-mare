# The Bannered Mare — Frontend Findings (Adversarial Architecture, Cleanliness & Testability Review)

> **Method.** This report synthesizes three **independent, adversarial** deep-dives run in parallel by separate agents, each with a distinct lens and no knowledge of the others' output: (1) architecture & patterns, (2) code cleanliness & complexity, (3) test suite & testability. Each finding cites verified `file:line` evidence. The prior `AUDIT_*.md` files were deliberately **not** consulted so this is a fresh, unbiased read. Tags: **[Arch]**, **[Clean]**, **[Test]** mark the originating lens; findings confirmed by more than one lens are noted.
>
> **Scope.** `frontend/src` — Vue 3.5 / TS6 strict / Tailwind v4 + DaisyUI 5 / Vite+. ~25K LOC of app code (excl. the 7.8K generated `schema.d.ts` and ~6K mocks). 44 composables, 82 components, 22 views, 1 Pinia store.

---

## 1. Verdict

**The frontend is genuinely well-architected and mechanically clean, but it has near-zero test protection and a small number of confirmed user-facing functional bugs riding on its most complex, least-testable code.** The good is real and not padding: the declared **View → Component → Composable → API Client layering is actually enforced** (a grep for `fetch(`/`openapi`/`@/api` across `views/` and `components/` returns **zero** hits); `api/client.ts` is a true single chokepoint with the two raw-`fetch` escape hatches (SSE, multipart) contained inside it and normalized to `{data,error}`; the three list/CRUD factories carry real concurrency engineering (monotonic `requestSeq` last-request-wins guards); singletons are principled with **no accidental shared state**; type discipline is strong (~8 real `any` in 25K LOC); and mechanical hygiene is near-perfect (exactly **one** px-arbitrary value tree-wide, universal `AppIcon`, zero `TODO/FIXME` markers, zero play-by-play comments).

**But the quality bar breaks on the two axes that matter most for a "highest standard" claim.** First, **testing is a desert with a green-CI fig leaf**: 4 test files / 18 tests for ~39K LOC, and — verified empirically — the wired `bun test` runner *physically cannot test the UI layer at all* (no DOM, no `@vue/test-utils`, `.vue` imports resolve to a path string). So the entire ~24K-LOC component/view layer, the SSE streaming state machine, and the `{data,error}` error path have **0% coverage**, and CI is green anyway. Second, the untested complex code hides **real bugs**: editing a just-sent chat message fails silently because the optimistic message UUID is never reconciled to the backend id, and two user-facing settings toggles ("Stream Responses", "Typing Indicator") persist to `localStorage` but are read by nothing.

The remaining issues are **maintainability debt, not structural collapse**: i18n is broken three ways (hardcoded English toasts, an entirely un-internationalized 571-line onboarding view, and four locale catalogs missing ~200 keys each), and duplication is concentrated where no shared primitive exists to stop it (no `Card`/`Input` component → design-system patterns inlined 20–68×; `formatDate` redefined 7×; the newest CRUD composables re-hand-roll what `useEntityCrud` already abstracts). Net: **strong B+ engineering with a first-rate architecture undermined by an absent safety net and a handful of latent correctness bugs.**

### Scorecard

| Dimension | Grade | One-line justification |
|---|---|---|
| Architecture / layering | **A−** | Layering enforced; single HTTP chokepoint; principled singletons; real race guards. |
| API boundary & typing | **A−** | `client.ts` funnels all HTTP; generated schema used directly; ~8 `any` in 25K LOC. |
| State-management coherence | **B−** | Provider "split-brain" cache; providers cached globally, everything else per-instance; some settings trapped inline. |
| Correctness (functional) | **C+** | 2 confirmed user-facing bugs (edit-just-sent-message, write-only toggles) + latent regen-abort restore gap. |
| Code cleanliness (mechanical) | **A** | 1 px-arbitrary value, universal AppIcon, zero dead/TODO/AI-ism comments, strong types. |
| DRY / shared primitives | **C+** | No Card/Input primitive → 68/20 inline copies; focus-ring ×42; formatDate ×7; factory bypass ×5. |
| i18n | **C−** | 57/83 toasts hardcoded; SetupWizard 0-i18n; 4 locales ~200 keys short each. |
| **Testability (in principle)** | **B+** | Composables return plain refs+actions; one fetch seam; MSW fake backend exists. |
| **Test coverage (actual)** | **F** | 4 files / 18 tests; 0% of UI layer; runner can't mount components; SSE & error paths untested. |

---

## 2. Critical

### FE-C1 · Test runner physically cannot test the UI layer — 0% of ~24K LOC reachable · [Test]
**Evidence (empirically verified this session).** Under `bun test`: `document`, `window`, `localStorage`, `matchMedia` are all `undefined`; `package.json` devDeps contain **no** `@vue/test-utils`, `jsdom`, `happy-dom`, `@testing-library/*`, or coverage tool; importing `src/components/chat/MessageBubble.vue` "succeeds" but `typeof mod.default === "string"` (Bun's default file loader returns the **file path** — no SFC compilation, no `@vitejs/plugin-vue` in the pipeline). 72 of 104 `.vue` files use `useI18n`/`$t` and `main.ts` registers 3 global components, so mounting also needs an i18n + global-component harness.
**Impact.** The entire component + view layer — including the largest, riskiest views (`ProviderView` 774, `ModelView` 615, `SetupWizardView` 571, `ChatView` 528) — is untestable **as configured**. No component test can ever be written until the runner changes.
**Fix.** Switch `"test"` from `bun test` to **`vp test`** (the dormant `vitest` = `@voidzero-dev/vite-plus-test` alias already in `package.json`), which applies `vite.config.ts` (vue plugin, `@` alias, YAML, `VITE_*` define) and supports `test.environment: "happy-dom"` + a setup file. Add `@vue/test-utils` + `happy-dom`. Then `mount(Component, { global: { plugins: [i18n], components: {…} } })` becomes possible. **This one change unblocks the entire testing effort** (also resolves FE-M8, FE-M9).

### FE-C2 · The app's core feature (SSE streaming) has zero tests · [Test]
**Evidence.** `composables/useChatMessages.ts` (394 LOC). `readStream` (`:122-212`) is a hand-rolled SSE parser: `TextDecoder` + `buffer.split("\n\n")` framing (`:140-141`), `data:` prefix + `[DONE]` sentinel (`:144-146`), `JSON.parse` in try/catch (`:151-155`), discriminated `start`/`text`/`reasoning`/`error` events (`:158-190`), **re-find-by-id on every write** to survive a chat switch (`:162-174`), and placeholder cleanup on abort/mid-stream-error (`:199`, `:209`). `sendMessage` (`:257`) and `regenerate` (`:214`) layer optimistic inserts + `AbortController` lifecycle on top.
**Impact.** This stateful async parser is the single most bug-prone unit in the codebase and drives the primary user journey. Any regression (framing edge case, race on rapid chat-switch, leaked placeholder on abort) ships silently. FE-C3 and FE-L-latent below are exactly the kind of bug this absence lets through.
**Fix.** Testable **today under any runner** — `streamFetch` calls global `fetch`, so mock it to return `new Response(new ReadableStream({…}))` emitting `data: {…}\n\n` chunks. Assert: partial-chunk reassembly across reads; `[DONE]`; malformed-JSON tolerance; `error` event → thrown + placeholder removed; abort mid-stream → quiet return + no blank bubble; chat-switch mid-stream → tokens don't land in the new chat.

### FE-C3 · Editing a just-sent message fails silently — optimistic UUID never reconciled · [Arch] · **confirmed functional bug**
**Evidence.** `sendMessage` pushes an optimistic user bubble with a throwaway id — `useChatMessages.ts:262-270` `id: crypto.randomUUID()`. The stream `start` event adopts the backend id **for the assistant placeholder only** (`:158-166`); the user message's temp UUID is never swapped, and nothing refetches after send. `MessageBubble` exposes an **edit action on user messages** (`MessageBubble.vue:89-92`), wired in `ChatView.vue:440` → `editMessage`, which PUTs to `/messages/{message_id}` with the client UUID (`useChatMessages.ts:307`). `ChatView.handleEditMessage` (`:262`) doesn't catch, so it fails with no toast.
**Impact.** The common sequence "send a message, then fix a typo in it" **reliably fails silently** until a chat-switch/reload reconciles ids. (The arch agent rated this HIGH; under an adversarial "highest-standard" reading it is a guaranteed-failure on a core path, hence elevated here.)
**Fix.** On the stream `start` event, reconcile the trailing user-message id too (backend includes it), or refetch the tail after send; alternatively gate the edit action off until the message has a server id. **Add a regression test once FE-C2's harness exists.**

---

## 3. High

### FE-H1 · "Stream Responses" & "Typing Indicator" toggles are write-only theater · [Arch] · **confirmed functional bug**
`InterfaceTab.vue:70-93` hydrates these from `localStorage`, renders them as `AppToggle`s (`:262`, `:285`), and writes back — but **nothing reads `setting-stream-responses`/`setting-typing-indicator`** (grep finds only the writer + i18n labels). Streaming is hardcoded `?stream=true` (`useChatMessages.ts:278`, `:231`). Two user-facing controls that do nothing. **Fix:** wire the flag into `sendMessage`/`regenerate` (branch on it), or delete the toggles; if kept, lift into a `useChatSettings` singleton so the chat can read them.

### FE-H2 · Pervasive hardcoded English bypasses vue-i18n · [Clean]
Three-layered, and these are **not keys** — untranslatable in *any* locale:
- **57 of 83 toasts (69%) are string literals**, e.g. `useCreateChat.ts:37,50`, `ProvidersTab.vue:30`, `ModelFamilyView.vue:46,52,54,62,65`, `TemplateView.vue:109-154`, `ProviderView.vue:148,199,208`. (`toast.x("literal")` = 57 vs `toast.x(t(…))` = 26.)
- **`SetupWizardView.vue` (571 LOC) has ZERO i18n** — 0 `useI18n`, 0 `$t`; every onboarding string hardcoded (`:210,219,232,238`).
- **Settings-detail views mix `$t` with hardcoded headings/date labels** — `ProviderView.vue:369,497,745,759-760`, `ModelFamilyView.vue:151,288,302,384-385`; `FragmentView.vue`/`PresetView.vue` don't even import `useI18n`.

**Fix:** move all `toast.*` literals + view text to `en.json` keys; add an ESLint `vue-i18n/no-raw-text` (or a `toast.*` literal check) to CI so it can't regress; internationalize `SetupWizardView` wholesale.

### FE-H3 · Four non-English locales each missing ~200 keys (verified TODO) · [Clean]
`en.json` = 588 key-lines; `de/es/fr/pt.json` = 388 each (~200 missing per locale, ~800 total). Namespaces `profiles`/`lorebooks`/`presetImport`/`chat.profile`/`nav.profiles`/`nav.lorebooks` are **en-only**. Profiles, Lorebooks, SillyTavern preset import, and chat profile-apply silently render **English** under de/es/fr/pt. **Fix:** mirror the `en.json` structure into the four catalogs, preserving `{name}`/`{count}` tokens. (This is the documented outstanding TODO — confirmed and quantified.)

### FE-H4 · No shared `Card`/`Input` primitive; design-system patterns copy-pasted; focus-ring magic value ×42 · [Clean]
`components/shared/` has no `Card`, `BaseInput`, or `TextInput`, so the design system's own "Common patterns" are inlined: Card `rounded-xl border bg-base-200…` **×68 across 30 files**; Input `h-11 w-full rounded-lg border bg-base-300…` **×20**; and `focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]` repeated **verbatim ×42**. A ring tweak = 42 edits. **Fix:** extract `<AppCard>`/`<AppInput>` primitives; promote the focus ring to a Tailwind `@utility` (e.g. `focus-ring`) in `main.css` and delete the 42 copies.

### FE-H5 · No injectable API seam; 29 composables statically import the client singleton · [Test]
29 composables `import { client } from "@/api/client"` (module singleton, `client.ts:37`); `streamFetch`/`multipartFetch` are module functions. No DI. The two existing composable tests cope by monkeypatching `global.fetch` (`useCharacterForm.test.ts:58`) and reassigning `client.GET` (`:92`) **with no `afterEach` restore** → cross-test pollution. **Fix:** stand up `msw/node` (FE-H6) so composables hit the real handler contract via unpatched fetch; failing that, enforce `afterEach` restore discipline.

### FE-H6 · The 2,173-line MSW harness + 38 fixtures are never reused for tests · [Test]
`mocks/handlers.ts` = 2,173 LOC (40+ handlers) and `mocks/data/` has 38 fixtures, but `mocks/` contains only `browser.ts` (`setupWorker`, dev/service-worker only) — **no `server.ts` with `setupServer` from `msw/node`** (`grep msw/node` → none), though `msw@^2.14.6` is installed. The single largest testing asset in the repo is inaccessible to automated tests. **Fix:** add `mocks/server.ts` = `setupServer(...handlers)` + `beforeAll(listen)/afterEach(resetHandlers)/afterAll(close)` in a setup file; all 29 API-coupled composables then test against the real contract.

### FE-H7 · CI test gate is hollow (green ≠ safe) · [Test]
`.github/workflows/frontend-ci.yml` runs `bun run test` — 18 shallow tests in 449ms, no coverage threshold, UI layer unreachable (FE-C1). A green pipeline signals safety it does not provide; a broken stream parser, mis-mapped FormData field, or pagination race all pass CI. **Fix:** after FE-C1/C2, add coverage reporting with a floor (start low, ratchet up).

---

## 4. Medium

### FE-M1 · Provider global-state "split brain" — cached in the store, mutated outside it · [Arch]
Provider *list* lives in Pinia (`stores/settings.ts:19-62`, surfaced via `useProviders`), but single-provider *mutations* go through `useProvider()` → `useEntityCrud` which **never touches the store** (`useProvider.ts:15-22`). After create/edit the shared list is stale unless each call site manually refetches — today two remember (`ProviderView.vue:207`, `ProvidersTab.vue:32`). Fragile-by-convention: any future mutation site that forgets desyncs the Providers/Models/Family tabs. **Fix:** make the store own provider mutations (patch `providers` in place), or have `useProvider` invalidate the store on success.

### FE-M2 · Inconsistent caching strategy — providers cached globally, everything else per-instance · [Arch]
Only providers get a shared cached singleton. Presets, templates, personas, profiles, databank each auto-fetch **per component instance** on mount (`onMounted` inside each composable). N simultaneous consumers = N round-trips + N independently-mutated copies of the same list. **Fix:** pick one strategy — a small `useResource`/query-cache keyed by endpoint, or promote the shared lists to the store like providers.

### FE-M3 · `useEntityCrud`/`usePaginatedList` bypassed by the newer CRUD composables · [Arch]+[Clean] (both lenses)
Factories are adopted by 6+4 core composables but the profiles/lorebooks feature set hand-rolls the identical skeleton: `useProfiles.ts` (140), `useDataBank.ts` (127), `useLorebooks.ts` (260), `usePersonas.ts` (117); and `usePresets.ts` ≈ `usePromptTemplates.ts` **near-verbatim** (both skip `usePaginatedList`, hardcode `{limit:50}`). `err instanceof Error ? err : new Error("Unknown error")` appears **15×**; the "single-default invariant" reconcile is duplicated with subtle differences (`usePersonas.ts:38-47`, `useProfiles.ts:47,70,111`). **Fix:** extract a `useListCrud` factory and migrate presets/templates/personas/profiles/databank onto it.

### FE-M4 · Inconsistent error contract — some mutations record `error`, others swallow it · [Arch]+[Clean]
`useEntityCrud` records failures on a shared `error` ref; but `useProfiles` mutations catch, `console.error`, and **return `null`/`false` without setting `error.value`** (`useProfiles.ts:52-55,76-79,94-97,115-118`), and `usePersonas` is internally inconsistent. Silent mutation failures; violates the CLAUDE.md "don't swallow errors silently" rule. **Fix:** standardize on the `useEntityCrud` contract (record on `error`, optionally rethrow) across all CRUD composables.

### FE-M5 · No user-facing stop/cancel for in-flight streaming · [Arch]
`useChatMessages.stop()` exists with a proper `AbortController` (`:64-68`) but `ChatView` never destructures/wires it (`:40-54`); the only abort path is the chat-switch watch (`:361-375`). Users can't halt runaway generation without navigating away, and the abort machinery is only ever exercised on unmount. **Fix:** expose `stop` and render a stop button while `isGenerating`. **Note:** doing so will expose the latent FE-L-latent regen-abort restore gap — fix together.

### FE-M6 · `useCharacterForm` lorebook sync is sequential N+1 and non-atomic · [Arch]
After the multipart save, it fetches the character's lorebook then loops deleting/creating/updating entries one awaited round-trip at a time (`useCharacterForm.ts:244-276`). N+1 latency and non-transactional — a failure mid-loop leaves a half-synced lorebook with no rollback. **Fix:** a backend bulk-sync endpoint, or at minimum `Promise.all` the independent ops and surface partial-failure state.

### FE-M7 · Over-large views carry extractable logic · [Clean]
`ProviderView.vue` (774; script 324) mixes provider form + model-filter/debounce (`:111-164`) + local-model load/unload/sync (`:238-274`) + add-model modal + inline `formatDate`/`timeAgo`/`formatSize` — it does repository-layer work in a view. `ChatView.vue` (528; script 311) carries ~45 lines of swipe/alternatives business logic (`:268-310`) that belong in `useChatMessages`. Others (`ModelView` 615, `TemplateView` 526, `InterfaceTab` 483) are mostly template-heavy forms — lower priority. **Fix:** extract `useProviderModelFilter`/`useLocalModelManagement` + a `ProviderModelRow` subcomponent; move swipe logic into the composable.

### FE-M8 · Singleton composables share module state with no reset seam · [Test]
`useTheme.ts:5-30` holds module-level `isDark`/`colorScheme`/`initialized` with an `if (initialized) return` guard and **no exported reset**; same shape in `useToast.ts:11` and `useServerStatus.ts:13`. Once a test initializes one, state bleeds across tests. `useToast` uses `setTimeout` (`:29`) → needs fake timers. **Fix:** export a test-only `__reset()` (or reset in a factory); use fake timers for toast expiry. (Resolved in practice once FE-C1 lands a proper harness.)

### FE-M9 · The one composable test covers ~20% and skips the gnarly logic · [Test]
`useCharacterForm.test.ts` asserts default init + basic `buildFormData`/`mapResponseToForm`, but **skips** gender→`custom_gender` normalization (`useCharacterForm.ts:110-119`), the dialogue regex round-trip (`:164-185` — the trickiest code in the file), and the **entire lorebook entry-diff** in `saveCharacter` (`:211-276`) — it stubs `/api/lorebooks` empty so the diff loop never runs. The parts most likely to silently corrupt a character on save are untested. **Fix:** add gender/dialogue round-trip cases and a non-empty lorebook diff.

### FE-M10 · 153 arbitrary micro-rem font sizes, no named token · [Clean] · *(myth-buster: NOT a scale-breaking bug)*
`text-[0.625rem]` ×66, `text-[0.6875rem]` ×57, `text-[0.5625rem]` ×27 across 52 files; `main.css @theme` defines no custom text sizes. **Correction to the guideline's fear:** these are **rem**, so they *do* scale with the app-wide Text Size setting — this is a DRY/missing-token issue, not the px scale-breaking violation (the only true px-arbitrary hit is a single `backdrop-blur-[2px]`). **Fix:** define `--text-2xs`/`--text-3xs` in `@theme` and replace the arbitrary values.

---

## 5. Low

- **FE-L1 · `formatDate` ×7, `timeAgo` ×5, no `utils/date.ts`** · [Clean]. `formatDate` in `CharacterDetailView.vue:74`, `ModelFamilyView.vue:100`, `ModelView.vue:224`, `ProviderView.vue:214`, `TemplateView.vue:162`, `FragmentView.vue:84`, `PresetView.vue:119`; `timeAgo` in 5 more. Also non-locale-aware. **Fix:** one `utils/date.ts` (or vue-i18n `d()`).
- **FE-L2 · Native `confirm()` vs `useConfirmAction`** · [Arch]. `ProviderView.vue:250,263,277` + `FragmentCreateView.vue:66` + `TemplateCreateView.vue:64` use browser-native confirm while 10 other places use the app primitive. Inconsistent UX + blocks the main thread.
- **FE-L3 · Stub `console.log` handlers wired to live UI** · [Clean]. `CharactersView.vue:149` (bulk export no-op), `:172`, `TemplateView.vue:159` ("fragment picker modal needed") — visible buttons that do nothing; TODOs-in-disguise (there are zero real TODO markers, so these hide). **Fix:** implement or disable the controls.
- **FE-L4 · `main.ts:87` unconditional prod `console.log`** · [Clean]; plus ~50 `console.error` in catch blocks, several of which only log instead of surfacing via `useAppToast` (§6.5). **Fix:** drop the init log; standardize error surfacing.
- **FE-L5 · Borderline status hues outside the enumerated exceptions** · [Clean]. `ModelFamilyView.vue:373` `bg-red-500/10 text-red-400` for unsupported params is negative-status semantics → should be the `error` token (it is not a capability badge). `MemoryView.vue:54-58,155-159` category/scope maps fall outside the doc's narrowly-worded "relevance-ramp" exception. Otherwise status-token discipline is clean.
- **FE-L6 · Recursive param renderer typed `any`** · [Arch]. `ParamInput.vue:6` `schema: any` (+ `:158,:164`) and `ModelInferenceParams.vue:18` — the weakest type spot; understandable for dynamic JSON-schema but the 414-line recursive component has no type safety.
- **FE-L7 · Untyped route params, no guards** · [Arch]. `route.params.chatId as string` (`ChatView.vue:24`), `route.params.id as string` (`ProviderView.vue:169`). Acceptable for a local no-auth app; noted.
- **FE-L-latent · Regenerate optimistic-removal not restored on abort** · [Arch] (latent). `regenerate` optimistically drops the last assistant message (`useChatMessages.ts:219-222`); on `AbortError`, `readStream` returns without rethrow (`:201`) so the catch that would `loadMessages()` never runs — the removed reply isn't restored. Currently masked because `stop` isn't wired (FE-M5); **becomes a visible bug the moment a stop button is added.**
- **FE-L8 · `bun test` ≠ vitest env** · [Test]. `vitest` aliased in `overrides` only; no bin installed; `VITE_*` not injected, forcing `process.env.VITE_API_URL` hack at `useCharacterForm.test.ts:1`. Resolved by FE-C1's `vp test` move.

---

## 6. What's genuinely good (verified, not padding)

- **Layering is real, not aspirational.** Zero `fetch(`/`openapi`/`@/api` in `views/` or `components/` (grep-verified). View→Component→Composable→Client holds across the whole app.
- **The API boundary is a true chokepoint.** `client.ts` funnels every HTTP path — typed client, `streamFetch` (SSE), `multipartFetch` (FormData) — through reachability tracking; the raw-fetch exceptions are contained and normalized to `{data,error}` (never leak `Response`); `extractApiError` centralizes `{detail}` vs `HTTPValidationError[]` with status carried through.
- **Serious concurrency care.** `usePaginatedList`/`useCursorList` use a monotonic `requestSeq` so a slow earlier response can't clobber a newer one; `useChatMessages` re-finds the streaming target by id on every write and aborts on chat switch before reset. Thoughtful, not accidental.
- **Singletons are principled; no accidental shared state.** 9 module-level singletons, all cross-cutting, each `init()`-guarded; every data composable uses function-local refs (verified).
- **Type discipline.** Generated `schema.d.ts` used directly via `components["schemas"][…]`; `types/` only *aliases* generated types plus one legitimately hand-written `StreamEvent` (SSE isn't in OpenAPI). ~8 real `any` in 25K LOC.
- **Mechanical hygiene is near-perfect.** Exactly one px-arbitrary value tree-wide; universal `AppIcon` (0 bare `i-lucide` spans); `any` confined to mocks/tests + documented recursive-schema; zero play-by-play AI-ism comments; no commented-out code; zero `TODO/FIXME/HACK` markers.
- **Router hygiene.** Full per-route lazy `import()` code-splitting, `/:pathMatch(.*)*` 404, and a chunk-load-error one-shot hard-reload recovery with a sessionStorage loop-guard.
- **Testable-in-principle + a fake backend already exists.** Business logic lives in composables returning plain refs+actions; one fetch seam; a 2,173-line schema-faithful MSW backend is built — the hard part of integration testing is done, it just needs an `msw/node` entry point and the right runner. **The correct runner (`vp test`) is one line away.**

---

## 7. Prioritized remediation roadmap

**Wave 1 — Establish a safety net (unblocks everything else).**
1. **FE-C1** — switch `"test"` → `vp test`; add `@vue/test-utils` + `happy-dom` + a setup file. *(One change; makes the UI layer testable.)*
2. **FE-H6** — add `mocks/server.ts` (`msw/node setupServer`) reusing the existing handlers. *(Unlocks contract-true composable tests; resolves most of FE-H5.)*
3. **FE-H7** — add coverage reporting with a low floor, ratchet upward.

**Wave 2 — Fix the confirmed bugs, then lock them with tests.**
4. **FE-C3** — reconcile the optimistic user-message id (or gate edit until it has a server id).
5. **FE-H1** — wire or delete the Stream/Typing toggles.
6. **FE-C2** — characterization tests for `useChatMessages` SSE parsing (catches FE-C3-class + FE-L-latent regressions).
7. **FE-M5** + **FE-L-latent** — expose `stop()` with a UI button *and* fix the regen-abort restore together.

**Wave 3 — Extend coverage to the risk surface.** `extractApiError`/`multipartFetch` (FE-H5), `useCursorList` race guard, `useCharacterForm` gnarly paths (FE-M9), then first component smoke tests (`MessageBubble`, `ParamInput`) proving the mount harness.

**Wave 4 — Maintainability debt.** i18n cleanup (FE-H2/H3 + a `no-raw-text` lint gate), shared `AppCard`/`AppInput` + `focus-ring` utility (FE-H4), `useListCrud` factory + error-contract standardization (FE-M3/M4), `utils/date.ts` (FE-L1), state-cache strategy (FE-M1/M2), extract `ProviderView`/`ChatView` logic (FE-M7).

---

## 8. Appendix — Cross-check against the prior `AUDIT_*.md` (reviewed only *after* the fresh analysis above)

This codebase is **post-refactor**: `AUDIT_LOG_FE.md` (FE-1…21) and `AUDIT_LOG_v2.md` (V2-*, 26 items) document a large prior wave, all marked DONE with commit hashes. The fresh analysis above was produced **blind** to those files (the reviewing agents were barred from reading them). Comparing now yields three buckets — the first is the important one.

### 8.1 Fresh findings that show a "DONE" audit item is only *partially* fixed
- **FE-C3 vs `V2-A2` (marked DONE, commit `f324b23`).** V2-A2 ("streamed message never adopts backend id") fixed the **assistant** placeholder — `readStream`'s `start` arm swaps `currentId`→`event.message_id` (**verified** `useChatMessages.ts:158-166`). But the **user** message pushed at `:262-270` keeps its `crypto.randomUUID()`, is never reconciled (no refetch, no user-side id in the stream), so `editMessage` PUTs that client UUID (`:307`) and 404s before the optimistic update at `:313`. **The symmetric half of the same bug is still live** — editing the message you just *typed* fails until reload. Verified directly this session.
- **FE-C1/FE-C2 vs `V2-B6` / `FE-13` (marked DONE).** Those fixed test *gating* (tests type-checked + run in CI; chunk-load error boundary added) — genuinely done. But neither recognized that the wired `bun test` runner **cannot mount a component at all** (no DOM; `.vue` imports resolve to a path string) or that coverage is ~4 files for ~25K LOC. The audits asked "do tests run?" and stopped; the substance — "*can* the UI be tested, and is anything actually tested?" — was never raised. This is the single biggest blind spot in the prior audits.
- **FE-M3/FE-M4 vs `V2-B2` / `V2-D2` (marked DONE).** V2-B2 migrated the 6 CRUD twins onto `useEntityCrud`; V2-D2 made its writes record `error`. But the newer `useProfiles`/`usePersonas`/`useDataBank`/`useLorebooks` composables **re-hand-roll the skeleton and re-swallow errors** — drift re-accumulated after the audit closed. The abstraction is right; adoption regressed.
- **FE-M5 vs `FE-4` / `V2-D8` (marked DONE).** The `AbortController`+`stop()` mechanism was built and its empty-bubble edge fixed — but `stop()` is wired to **no UI**, so users still can't halt generation. Plumbing exists; the button was never added.

### 8.2 Audit fixes the fresh pass independently *confirms* genuine (validation, not re-flag)
- The **`requestSeq` last-request-wins race guard** the arch lens praised is exactly `V2-D1`'s fix — confirmed present and correct in `usePaginatedList`/`useCursorList`.
- The **chunk-load-error router recovery** in the "what's good" list is `V2-B6`'s addition — confirmed.
- **`extractApiError` carrying `{detail}`/`HTTPValidationError[]` + status** is `FE-7` + `V2-D6` — confirmed centralized.
- **Status-token discipline / no stale `-foreground` tokens** (`FE-14`, `V2-B4`) — the cleanliness lens confirmed near-perfect adherence.
- **Layering enforced / no raw fetch outside `client.ts`** (`FE-1`, `V2-B1`) — the fresh grep confirmed zero API calls in views/components; multipart contained in `client.ts`.

### 8.3 Fresh findings the audits never raised (genuinely new)
FE-H1 (write-only Stream/Typing toggles), FE-H2 (57/83 hardcoded-English toasts — the audits covered locale-key *gaps*, `FE`-side, but not literal strings bypassing i18n entirely), the **"runner physically can't mount the UI"** root cause (FE-C1), and the reframing of the test story as a **coverage desert** rather than a gating problem.
