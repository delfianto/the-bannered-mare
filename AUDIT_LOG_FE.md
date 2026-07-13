# Frontend Architectural Audit — The Bannered Mare

**Date:** 2026-07-14
**Scope:** `frontend/` — Vue 3.5 / TypeScript / **Tailwind v4 + DaisyUI 5** / Vite / bun SPA.
**Method:** Read-only audit across three independent dimensions — (1) component & composable architecture + client state, (2) API/data layer, TypeScript rigor & contract consumption, (3) design-system consistency, routing/structure, accessibility & build/tooling/test health. Findings confirmed independently by more than one dimension are marked **⊕** (higher confidence).

> **Nothing in this document has been changed yet.** It is a findings log for planning. Each finding carries a stable ID (`FE-n`), a severity, concrete `file:line` locations, the problem, its cost, and a sized recommendation.

## Stack correction (important)

The root `CLAUDE.md` describes the frontend as "**Nuxt UI v4**." In reality the app uses **DaisyUI 5 (CSS classes) + hand-rolled Tailwind v4 + a small set of shared Vue primitives** in `src/components/shared/`. Nuxt UI and its MCP design server are **not wired in**, and a `shadcn-vue` `components.json` is a stale leftover (see FE-19). This documentation drift is itself worth fixing so contributors and tooling know which design system is in play.

---

## Executive summary

The foundation is strong: a typed `openapi-fetch` client (`src/api/client.ts`), a documented **View → Component → Composable → Client** layering (AGENTS §4.2), a "types directly from the generated `schema.d.ts`, no parallel type system" decision (§4.3), and a well-built 12-theme DaisyUI system (`themes.css`, focus-visible ring, reduced-motion). The recurring theme — mirroring the backend — is that **these good abstractions are only half-adopted**: ~44 raw `fetch()` calls bypass the typed client, `any` clusters at feature seams, and interaction/UI patterns are copy-pasted instead of extracted.

Do first (small, high value or real bugs):
1. **FE-3** — remove the `as any` block hiding a real `lore_book_id` vs `lorebook_id` path bug.
2. **FE-2** — add focus management to the shared `Modal` primitive (fixes a11y app-wide).
3. **FE-14** — fix `text-error-foreground` (undefined token on every destructive confirm button).

---

## Tier 1 — High

### FE-1. ⊕ ~44 raw `fetch()` calls bypass the typed client, base URL, and reachability tracking
- **Severity:** High · **Size:** large
- **Location (representative):** `useChatMessages.ts:232,275,303,324,336`; `useModel.ts:40,59,77,94,111,128,139`; `usePromptTemplate.ts` (11 calls); `usePreset.ts:17,30,47,60`; `usePromptFragment.ts`; `useProvider.ts:54`; `useModelFamily.ts:44,61`; `useChatSessions.ts:103`; `useBookmarks.ts:30-32`; `PersonaTab.vue:99-171`; `CharactersView.vue:179,190,230`
- **Problem:** AGENTS §2.2/§4.2 designate `api/client.ts` as the only place that speaks HTTP (via `openapi-fetch`), with a single documented exception (multipart FormData). In practice most mutations and several reads use bare `fetch("/api/...")`. Consequences: (a) they skip `trackedFetch`, so a 502/503 won't flip `useServerStatus` and the `ServerStatusBanner` stays green while the app is broken; (b) they hardcode relative `/api/...` and ignore `VITE_API_URL` (which the typed client honors at `client.ts:22`), so a split-origin deploy silently breaks for every raw-fetch endpoint; (c) they return `await response.json()` typed as `any`, discarding the contract. `useProfiles.ts:38-98` proves the typed client handles PUT/POST/DELETE cleanly — this is drift, not necessity.
- **Why it matters:** The single biggest data-layer erosion — it fractures the contract guarantee, the reachability UX, and the env-config story into a "typed half" and an "untyped half," invisible until a non-localhost deploy or a backend outage.
- **Recommendation (large):** Migrate onto `client.GET/POST/PUT/PATCH/DELETE` with schema `*Create`/`*Update` body types and the `{ data, error }` branch. Leave SSE sends on raw `fetch` (body reader) but route them through a shared wrapper that still uses `VITE_API_URL` + `trackedFetch` (see FE-4).

### FE-2. Shared `Modal` / `SelectMenu` primitives lack a11y fundamentals
- **Severity:** High · **Size:** medium
- **Location:** `src/components/shared/Modal.vue:72-108` (base for ConfirmModal, ImportPresetModal, ModelCreateModal, LogDetailModal, ProfilePickerModal) and the close button at `:102-107`; `src/components/shared/SelectMenu.vue`
- **Problem:** `Modal.vue` correctly sets `role="dialog"`/`aria-modal` + Escape + body-scroll lock, but never moves focus into the dialog on open, doesn't trap Tab (focus stays on the page behind the backdrop), doesn't restore focus on close, has no `aria-labelledby` linking the title, and the icon-only close button has no `aria-label`. `SelectMenu` has correct `role="listbox"/"option"` but the trigger lacks `role="combobox"`/`aria-expanded`/`aria-controls`/`aria-activedescendant`. Only 2 `aria-labelledby`/`describedby` usages exist app-wide.
- **Why it matters:** Keyboard and screen-reader users can't use dialogs properly — focus escapes to the obscured page and the dialog announces no accessible name. Because these are the *base* primitives, the defect is systemic. (Positives to keep: `main.css` ships a `:focus-visible` ring + `prefers-reduced-motion` block; `<aside>`/`<nav>` landmarks used; images consistently carry `:alt`.)
- **Recommendation (medium):** In `Modal.vue` focus the panel/first focusable on open, trap Tab, restore focus on close, wire `aria-labelledby`; add `aria-label` to the close button. Add combobox ARIA to `SelectMenu`'s trigger.

### FE-3. `as any` in `useCharacterForm` masks a real, unresolved path-param bug
- **Severity:** High · **Size:** small/medium
- **Location:** `src/composables/useCharacterForm.ts:219-254` (also `:17`, `:222-290`)
- **Problem:** The lorebook-sync block casts every `client` call `as any`, with a literal left-in note: `// Wait! Is it lore_book_id or lorebook_id? Let's check openapi schema.` The path is written `{ lore_book_id: lorebookId }` inside a template keyed `"/api/lorebooks/{lorebook_id}"`; `as any` is exactly what lets that mismatch compile. `bookDetails`/`entries` are then read through further `as any`.
- **Why it matters:** This is precisely the drift the generated schema exists to catch — `as any` disables the one check that would confirm the request shape, so a wrong param name ships silently.
- **Recommendation (small/medium):** Remove the casts; let `vue-tsc` resolve the correct param name against `schema.d.ts`; type `entries` from the lorebook-detail schema. If the multi-step reconciliation is intrinsic, extract a typed `syncLorebookEntries()` helper (see FE-12).

### FE-4. Chat SSE streaming has no `AbortController`
- **Severity:** High (UX/correctness) · **Size:** medium
- **Location:** `src/composables/useChatMessages.ts:148-215` (`readStream`), `:232`/`:275` (streaming `fetch`), `:356-371` (chat-switch `watch`); no `signal:` anywhere in the codebase
- **Problem:** `sendMessage`/`regenerate` open an SSE stream and loop on `reader.read()` with no abort signal. There's no "stop generation," and the chat-switch `watch` resets `messages` but doesn't cancel the in-flight reader — which keeps resolving and writing tokens into `messages.value[assistantMsgIndex]`, an index computed against the *old* chat's array, after the user navigated away.
- **Why it matters:** Streaming without cancellation is a UX gap (no stop button) and a correctness hazard (orphaned writes, wasted backend generation/tokens). Compounds FE-1.
- **Recommendation (medium):** Thread an `AbortController` per generation; abort in the chat-switch watcher; expose a `stop()` action. Guard `readStream` writes by re-finding the message id rather than a cached index.

### FE-5. ⊕ `ChatDrawer.vue` is a 1086-line god component
- **Severity:** High · **Size:** large
- **Location:** `src/components/chat/ChatDrawer.vue` (whole file; four tab bodies at L468-1081, script L1-430)
- **Problem:** One SFC owns four unrelated feature surfaces (Character detail, Settings/loadouts/persona/memories/lorebooks, Session prompt-preview, LLM Logs), wires 5+ composables (`useCharacter`, `usePersonas`, `useDataBank`, `useLorebooks`, `useChatPromptPreview`, `useChatLlmLogs`, `useCompletionSignal`), owns 7 lazy-load watchers (L100,140,163,181,219,235,397), a per-lorebook entry cache, ~10 formatters (`formatTokens`/`formatLatency`/`formatCost`/`formatLogTime`/`formatJson`, L257-287), and rename/delete-with-confirm logic (L391-425).
- **Why it matters:** Every tab pays every other tab's mount/parse cost; the watcher web makes lazy-loading hard to follow and easy to regress; formatters are untestable in isolation; chronic merge-conflict magnet. Single biggest cohesion problem in the component layer.
- **Recommendation (large):** Split each tab into its own child (`ChatDrawerCharacterTab.vue`, `…SettingsTab.vue`, `…SessionTab.vue`, `…LogsTab.vue`), each owning its composable + `v-if`-gated lazy fetch. Keep `ChatDrawer` as the teleport/transition shell + tab switch. Move log formatters into `formatLog.ts`.

---

## Tier 2 — Medium

### FE-6. ⊕ CRUD/list composables are copy-pasted skeletons
- **Severity:** Medium · **Size:** medium
- **Location:** CRUD twins — `useProvider.ts`, `useModel.ts`, `useModelFamily.ts`, `usePreset.ts`, `usePromptTemplate.ts`, `usePromptFragment.ts` (shared `loading/saving/deleting/error` + `fetch*/save*/delete*` try/finally). List twins — `useModels.ts` (L23-111), `useModelFamilies.ts` (L21-92), `usePromptFragments.ts`, `useCharacters.ts` (identical `page/hasMore/total/totalPages/loadPage/search`). Cursor lists — `useChatMessages.ts`, `useChatSessions.ts`.
- **Problem:** ~6 near-identical single-entity CRUD composables + ~4 identical page-pagination blocks + cursor variants; `totalPages` computed, the `query: Record<string,unknown>` + `as {…}` cast, `onMounted(autoLoad)`, and error handling all duplicated verbatim.
- **Why it matters:** A convention change (error toasting, retry, abort) must be applied N times and drifts (some seed `hasMore=true`, some `false`; some fall back to `created_at`, some `updated_at`). Composable-layer analog of FE-5 — low cohesion via duplication.
- **Recommendation (medium):** Introduce `useEntityCrud<TDetail,TCreate,TUpdate>(basePath)`, `usePaginatedList<TItem,TFilters>(path, opts)`, and `useCursorList` factories; reduce each composable to thin typed config.

### FE-7. No shared error policy — structured errors flattened to `JSON.stringify(apiError)`
- **Severity:** Medium · **Size:** medium
- **Location:** ~34 sites of `throw new Error(\`… ${JSON.stringify(apiError)}\`)` (e.g. `useChatMessages.ts:44,119`; `useCharacters.ts:35`; `useChatSessions.ts:36,85,119`); `APIError` defined `client.ts:29-37` and imported nowhere
- **Problem:** The backend returns structured errors (`HTTPValidationError.detail` in the schema; the domain-exception hierarchy returns `{detail}` bodies). Composables collapse the whole object into a JSON string in `Error.message`, so toasts show `Failed to load chats: {"detail":"..."}`. The two SSE paths *do* extract `err.detail` correctly (`useChatMessages.ts:242,285`), proving the inconsistency. The purpose-built `APIError` (carrying `statusCode` + `details`) is dead.
- **Why it matters:** Error UX/observability degrade to opaque blobs; no way to branch on status (404 vs 409 vs 422); handling is ad-hoc per call, contradicting AGENTS §6.5.
- **Recommendation (medium):** Add one `extractApiError(error): APIError` helper in `client.ts` that reads `detail`/`status`; have composables throw/return it. Adopt or delete `APIError`.

### FE-8. ⊕ `any` at feature seams defeats the schema-first decision
- **Severity:** Medium · **Size:** small
- **Location:** `stores/settings.ts:16,48` (`ref<any[]>`, `(data as any[]).sort((a: any, b: any) => …)`) — consumed with `(p: any)` in `ModelsTab.vue:109-149`, `ModelForm.vue:29-50`, `ModelView.vue:77-146`, `ModelFamiliesTab.vue:68`; creator emit contracts `CharacterTab.vue`/`BehaviorTab.vue`/`WorldTab.vue:16-18` (`"update:field": [field: keyof CharacterData, value: any]`), forwarded as `(field: any, val: any)` in `CharacterCreateView.vue:268,276,284`; `useChatMessages.ts:320` (`Promise<any[]>` alternatives cache); `views/chat/ChatView.vue:276` (`Map<string, any[]>`); `useBookmarks.ts:14-15`; `AppSidebar.vue:34` (`session: any`); `ModelView.vue:94,145` (`as any`)
- **Problem:** `fetchProviders` throws away the typed `client.GET("/api/providers")` result with `data as any[]`; because the shared store is `any`, every downstream component re-annotates `any`. This store alone seeds a large share of the app's 110 `any` occurrences.
- **Why it matters:** A single untyped state atom nullifies the contract for the most schema-heavy feature area (models/families/providers); these `any`s are exactly where post-`api:gen` contract drift slips past `vue-tsc`.
- **Recommendation (small):** Type `settings.providers` as `components["schemas"]["ProviderResponse"][]`; drop the downstream casts; type the alternatives cache from the schema; make `update:field` generic over `CharacterData[K]` so field/value stay correlated.

### FE-9. Status colors bypass DaisyUI semantic tokens (two parallel color systems)
- **Severity:** Medium · **Size:** medium
- **Location:** `src/components/settings/LogsTab.vue:73-76,225-292,343-392`; `PresetView.vue:356`; `TemplateView.vue:479`; ~40 more `.vue` files. 196 raw-palette occurrences vs 56 semantic-token usages.
- **Problem:** Semantic status is expressed two incompatible ways — DaisyUI tokens (`bg-success`/`text-error`/`bg-warning`, 56 uses) vs hardcoded palette hues (`text-emerald-500`=success ×48, `text-amber-500`=warning ×41, `text-red-500`=error ×18, `bg-blue-500`=info ×13).
- **Why it matters:** The app ships 12 themes (6 palettes × light/dark) plus a user-editable Custom theme via `data-theme`; semantic tokens are tuned per theme in `themes.css`, the raw hues are fixed. A hardcoded `emerald-500` "success" pill clashes in the Crimson/Emerald palette and ignores the Custom theme entirely — defeating theming for status UI.
- **Recommendation (medium):** Map raw status hues to tokens (`emerald→success`, `red→error`, `amber→warning`, `blue→info`), starting with `LogsTab.vue`; consider an ESLint rule banning raw palette classes in templates.

### FE-10. ⊕ Missing shared primitives → interaction/UI pattern sprawl
- **Severity:** Medium · **Size:** small each
- **Location:**
  - **Avatar fallback ×10:** `views/chat/ChatView.vue:76-84`, `components/chat/ChatHeader.vue:37-43`, `ChatDrawer.vue:297-307`, plus `CharacterCard.vue`, `CharacterListRow.vue`, `ChatSessionList.vue`, `HomeCharacterCard.vue`, `ContinueTaleSection.vue`, `profiles/PersonaTab.vue`, `views/CharacterDetailView.vue`. The `avatar_thumbnail || avatar || ui-avatars.com/…&background=C9922E…` chain (hardcoded amber) is hand-copied, each choosing its own tier.
  - **Confirm-to-delete ×11:** `views/settings/ModelView.vue:33,218-231` (`confirmDelete` ref + `setTimeout(…, 3000)`) and the same pattern in `ChatDrawer.vue:416-425`, `MemoryView.vue`, `LorebooksView.vue`, `ModelFamilyView.vue`, `TemplateView.vue`, `PresetView.vue`, `FragmentView.vue`, `profiles/ProfileCard.vue`, `profiles/PersonaTab.vue`, `lorebooks/LoreEntryCard.vue` — inconsistent names (`confirmDelete`/`pendingDelete`/`pendingDeleteId`), several without timer cleanup.
  - **Overlay transition ×2:** `ChatDrawer.vue:52-158,289-293` vs `components/shared/Modal.vue` (same `visible`/`entered`/`closeTimer`/`DURATION` + double-`requestAnimationFrame` + body-scroll-lock + ESC; the drawer comment at L52 admits it "mirrors Modal.vue").
- **Why it matters:** Brand color/fallback provider frozen in 10 sites; repeated timer-leak risk and inconsistent confirm UX; overlay a11y/scroll-lock rules live in two places (compounds FE-2). Clearest "should be one shared thing" wins.
- **Recommendation (small):** `<CharacterAvatar :character :size>` (or `utils/avatar.ts`); `useConfirmAction(onConfirm, { timeout })` → `{ armed, trigger }` (or `<ConfirmButton>`); `useOverlayTransition({ duration })` consumed by both `Modal` and `ChatDrawer`.

### FE-11. Dead defensive pagination branches ×10 + two provider sources of truth
- **Severity:** Medium · **Size:** small/medium
- **Location:** `useChatMessages.ts:48-60`, `useCharacters.ts:39-53`, `useChatSessions.ts:40-55` (pattern across ~10 list composables); schema `PaginatedResponse_*_` at `schema.d.ts:3391-3450`. Provider duplication: `stores/settings.ts:16-56` (untyped store) vs `composables/useProviders.ts` (typed `ProviderResponse[]`); `ModelView.vue:48,94,145` picks the store version.
- **Problem:** Each list composable does `const items = Array.isArray(data) ? data : data.items` + a `meta ? … : …` fallback recomputing `hasMore`/`cursor` from `items.length`/`items.at(-1).created_at`. The schema proves `data` is *always* an object with *required* `items` + `meta`, so `Array.isArray(data)` is always `false` — the array branch and the whole `else` are unreachable (no type-checker flags it, since `Array.isArray` narrows legitimately). Separately, the provider list is fetched two ways that don't invalidate each other.
- **Why it matters:** ~10 copies of unreachable logic obscure the real contract and invite divergence; the dual provider cache means an edit in one path doesn't refresh the other, muddying the store-vs-composable boundary.
- **Recommendation (medium):** Delete the fallbacks; read `data.items`/`data.meta` directly (folds into the `usePaginatedList` factory from FE-6). Pick one provider source — promote to a typed store method reused everywhere, or drop the store copy and let `ModelView` use `useProviders` (the store then legitimately owns only `parameterDocs`).

### FE-12. Business logic stranded in views; `ChatHeader` is a prop-drilling middleman
- **Severity:** Medium · **Size:** medium
- **Location:** `views/CharacterCreateView.vue:61-118` (`handleSave` ensure-lorebook-then-create/update-per-entry with a 14-field default payload inlined at `:91-104`; `handleExport:131-140` does manual Blob/anchor DOM work); `components/chat/ChatHeader.vue:12-23` (10 props), `:25-33` (7 emits), `:93-112` (forwarding); source in `views/chat/ChatView.vue:366-384` with seven thin `handleChange*` wrappers at `:224-251`
- **Problem:** The view orchestrates the most intricate multi-step API work in the character feature (AGENTS §4.2 forbids raw business logic in views). `ChatHeader` declares 10 props/7 emits and forwards nearly all straight to `ChatDrawer`, carrying data (`models`, `profiles`, `currentPersonaId`) it never renders — a 3-layer View→Header→Drawer relay.
- **Why it matters:** The character sync logic is untestable/unreusable stranded in a routed page; any new per-chat setting must be threaded through three components.
- **Recommendation (medium):** Move the sync loop into `useCharacterForm` (or `useCharacterLorebook`) as `syncLorebook(characterId, entries)`; hoist entry defaults to `constants/`; extract `downloadJson()`. Have `ChatDrawer` source `models`/`profiles`/`personas` from composables directly and lift per-chat mutations into a `useChatSession(chatId)` composable both `ChatView` and the drawer consume — the header then needs only `character`/`sessionTitle` + a `back` emit.

### FE-13. No 404 catch-all route; orphaned tests not in any gate
- **Severity:** Medium · **Size:** small
- **Location:** `src/router/index.ts:3-100` (no `/:pathMatch(.*)*`); `src/components/layout/AppShell.vue:11-14` (bare `<RouterView>`); tests `src/**/__tests__/*.test.ts` (3 files, `import … from "bun:test"`); `package.json` (no `test` script; `overrides` point `vitest`→`@voidzero-dev/vite-plus-test`, imported by nothing); `tsconfig.json:23` (`"exclude": ["src/**/__tests__/**"]`)
- **Problem:** Any unknown URL matches nothing, so `<RouterView>` renders an empty pane with no message; no `Suspense`/error boundary around lazily-imported views, so a failed chunk load surfaces nothing. Separately, three `bun:test` files exist but no `test` script runs them, `tsconfig` excludes `__tests__` from type-checking, and the gate (`vue-tsc -b && vp build`) never runs them — so they silently rot (they can reference renamed modules unnoticed, see FE-19).
- **Why it matters:** Blank-screen dead ends on typos/deep links/post-refactor URL changes; "coverage" is three unenforced files.
- **Recommendation (small):** Add a catch-all route to a `NotFoundView` + a route-level error/loading wrapper; add `"test": "bun test"` and run it in the gate/CI; reconcile the `vitest` override with the `bun:test` reality.

---

## Tier 3 — Low (mostly quick wins)

### FE-14. `text-error-foreground` is an undefined token on every destructive confirm
- **Severity:** Medium (visible) · **Size:** trivial
- **Location:** `src/components/shared/ConfirmModal.vue:46`
- **Problem:** The destructive branch applies `text-error-foreground`, but no such token exists — `themes.css` defines `--color-error-content` (DaisyUI name). `error-foreground` is stale shadcn naming, so Tailwind generates no class and the label falls back to inherited color on the red `bg-error`.
- **Recommendation (small):** Change to `text-error-content`.

### FE-15. SSE events hand-typed inline instead of a discriminated union
- **Severity:** Low/Medium · **Size:** small
- **Location:** `useChatMessages.ts:176` (`let event: { type?: string; content?: string; message?: string }`), branched `:187-201`
- **Problem:** The stream contract (`type: "text"|"reasoning"|"error"` with mode-specific fields) is redeclared as an all-optional bag and dispatched via string checks; a typo in an event name fails silently (`continue`). SSE bodies legitimately aren't in the OpenAPI schema, but this isn't modeled as a first-class type either.
- **Recommendation (small):** Define a `StreamEvent` discriminated union in `src/types/chat.ts` and narrow on it; keep it manually synced with the backend `StreamEvent` (comment the source).

### FE-16. `useBookmarks` uses raw fetch with no `.ok` check and `any[]` state
- **Severity:** Low/Medium · **Size:** small
- **Location:** `useBookmarks.ts:14-15,29-37`
- **Problem:** Three parallel `fetch(...).then(r => r.json())` calls with no `response.ok` check, then `?.items ?? []`. A 4xx/5xx JSON error body resolves as "data," so failures render as an empty (not errored) page; `characters`/`sessions` are `any[]`. (Compact instance of FE-1 + FE-7.)
- **Recommendation (small):** Move to `client.GET`, branch on `error`, type refs from the schema.

### FE-17. Environment/config half-wired; dead avatar-URL helpers
- **Severity:** Low · **Size:** small
- **Location:** `vite-env.d.ts:3-6` (declares only `VITE_USE_MOCKS`, `VITE_DEBUG_REQUEST`); `VITE_API_URL` read at `client.ts:22,40,45` and `useServerStatus.ts:31`; no `.env*` files; `getAvatarUrl`/`getPersonaAvatarUrl` at `client.ts:39-47`
- **Problem:** `VITE_API_URL` — the knob that switches the app off the dev proxy onto a real backend origin — isn't in `ImportMetaEnv`, so its reads fall back to Vite's untyped index signature (`any`) instead of a checked `string`; there's no `.env.example` documenting it or `VITE_USE_MOCKS`. Combined with FE-1, the base-URL story is only half-implemented. The `getAvatarUrl`/`getPersonaAvatarUrl` helpers are dead (never imported; AGENTS says not to use them).
- **Recommendation (small):** Add `readonly VITE_API_URL: string` (+ `DEV`) to `ImportMetaEnv`; commit a `.env.example`; remove the dead helpers.

### FE-18. Theme-agnostic `white/` `black/` overlays for hover and borders
- **Severity:** Low · **Size:** small
- **Location:** 33 occurrences incl. `Modal.vue:82,90,103` (`bg-black/60`, `border-white/10`, `hover:bg-white/10`), `ConfirmModal.vue:35` (`hover:bg-white/5`); also AvatarUpload, CharacterCard, ChatDrawer, ToastContainer
- **Problem:** Hover/border affordances use fixed `white/N` / `black/N` alphas instead of theme tokens; on light themes a `hover:bg-white/10` over a light panel is essentially invisible — clearly tuned against the dark palette.
- **Recommendation (small):** Replace decorative overlays with token-based equivalents (`hover:bg-base-content/10`, `border-base-content/10`). Backdrop `bg-black/60` is fine.

### FE-19. Dead tracked config and a broken orphan script
- **Severity:** Low · **Size:** trivial
- **Location:** `frontend/components.json` (shadcn-vue config — `baseColor: zinc`, aliases `@/components/ui`, `@/lib/utils` that don't exist); `frontend/test-messages.js` (imports `./src/mocks/loader-optimized` + `./src/mocks/data/messages-optimized`, neither exists — actual files are `loader.ts`/`messages.ts`, so it can't run)
- **Problem:** Dead config misleads contributors/tooling about the design system in play; a broken "test" script implies coverage that isn't there.
- **Recommendation (small):** Delete both; refresh the stale "Nuxt UI auto-generated" comment block in `.gitignore`.

### FE-20. Overlapping lint stacks contradict the documented tooling
- **Severity:** Low · **Size:** small/medium
- **Location:** `frontend/eslint.config.js`; `package.json` devDeps (`eslint@10`, `typescript-eslint`, `eslint-plugin-vue`, `eslint-plugin-tailwindcss@4`) + scripts (`lint`, `lint:tailwind`, `lint:canonical`); `scripts/canonical-classes.mjs`; AGENTS §4.1 / README:23
- **Problem:** AGENTS/README state linting is "Oxlint / Oxfmt … no standalone devDeps," but a full ESLint stack ships with three overlapping enforcement paths: `vp lint` (Oxlint), `eslint src/` (`lint:tailwind`), and a bespoke `canonical-classes.mjs` (`lint:canonical`) — the last two both enforce canonical Tailwind classes. `eslint-plugin-tailwindcss@4` is pointed at a Tailwind v4 CSS-first config (`cssConfigPath: src/assets/main.css`), which it supports only partially.
- **Recommendation (small/medium):** Reconcile docs with reality — consolidate on Oxlint + the `.mjs` script (drop the ESLint stack) or document ESLint as the canonical Tailwind linter; verify the plugin parses the v4 CSS config.

### FE-21. Monolithic SFCs and un-extracted Card/Input patterns
- **Severity:** Low · **Size:** medium
- **Location:** `ChatDrawer.vue` (1086, see FE-5), `views/settings/ProviderView.vue` (769), `ModelView.vue` (626), `SetupWizardView.vue` (571), `TemplateView.vue` (535), `ChatView.vue` (529); the Card pattern (`rounded-xl border bg-base-200/50 …`) inlined ~62×, the Input pattern ~10×
- **Problem:** Several very large single files; the two most-repeated design-system patterns live as copy-pasted class strings rather than shared primitives (despite `components/shared/` being the established home) — which is how a stray `text-error-foreground` (FE-14) or off-palette hue (FE-9) slips in.
- **Recommendation (medium):** Extract `AppCard`/`AppInput` (or `@utility` shortcuts in `main.css`); split the largest SFCs incrementally alongside feature work.

---

## Big picture

- **A strong typed client exists but is only half-adopted** (FE-1). Consolidating the ~44 raw `fetch()` calls onto `openapi-fetch` so the contract, `VITE_API_URL`, and reachability tracking apply uniformly is the single most valuable fix — most other data-layer findings are downstream of this split.
- **The generated contract is repeatedly distrusted or cast away** — dead `Array.isArray(data)` branches (FE-11), `as any` on client calls (FE-3), `any[]` shared state (FE-8) — so the app pays for code generation without collecting the safety.
- **Error handling has no shared policy** (FE-7): `JSON.stringify` in ~34 places, a dead `APIError` class, throw-vs-swallow inconsistency, no `.ok` checks on raw fetches.
- **The chat streaming path is the highest-risk surface** (FE-4 + FE-15): raw-fetch SSE with no cancellation (leaks on chat switch, no stop button) and an ad-hoc inline event type — deserves a focused hardening pass.
- **The theming/a11y foundation is strong but not consistently honored** (FE-2, FE-9, FE-14, FE-18) and **tooling/test health is the weakest axis** (FE-13, FE-19, FE-20): tests exist but nothing runs or type-checks them, and the repo carries dead config plus a lint story that contradicts its own docs. No architectural rot — the work is consolidation.

## Suggested sequencing

1. **Real bugs / cheap high-value:** FE-3 (path bug), FE-14 (broken token), FE-13 (404 + wire tests), FE-19 (delete dead config).
2. **App-wide a11y via base primitives:** FE-2 (+ FE-10 overlay extraction).
3. **Data-layer consolidation (the big one):** FE-1 typed-client migration, landing the FE-6 factories + FE-11 pagination cleanup as you go, then FE-7 error helper and FE-8 typing.
4. **Streaming hardening:** FE-4 + FE-15.
5. **Design-system consistency:** FE-9 (semantic tokens), FE-18, FE-21 (AppCard/AppInput), FE-10 (avatar/confirm primitives).
6. **Structure:** FE-5 (ChatDrawer split) + FE-12 (views/header), FE-17, FE-20.

> **Note:** the root `CLAUDE.md` "Nuxt UI v4" description should be corrected to "Tailwind v4 + DaisyUI 5" as part of this work (see Stack correction above).
