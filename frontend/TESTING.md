# Frontend tests

Run these from `frontend/`. No backend, database, network access to LLM providers,
or provider credentials are needed.

```sh
bun run test
bun run test -- src/composables/__tests__/useChatMessages
bun run test:coverage
bun run check
bun run lint:tailwind
bun run lint:canonical
bun run build
```

The coverage command writes `coverage/index.html`, `coverage/lcov.info`, and
`coverage/coverage-summary.json`. CI runs the same coverage gates and retains the
`frontend-coverage` artifact for seven days, including reports from failing suites.
Open the HTML report to find unexecuted branches before adding tests.

## Layers and boundaries

- Pure unit tests cover error normalization, filters, sorting, and data mapping.
- Composable/store tests cover lifecycle, cache sharing, mutation reconciliation,
  request races, retries, and persistence.
- API integration tests exercise the real typed client through MSW. They assert
  request bodies/query parameters and the resulting state, including rejected writes.
- Component tests mount real Vue components and exercise inputs, emitted values,
  teleports, dialog focus handling, recursive parameter editing, and sanitized prose.

Vitest runs through `vite-plus/test`, sharing Vite's Vue transform and aliases.
happy-dom supplies ordinary DOM behavior. The NarrativeText suite opts into jsdom
with `// @vitest-environment jsdom`: DOMPurify explicitly does not support happy-dom
as a trustworthy sanitization environment. Keep the real sanitizer in these tests.

These are unit/component tests, not browser end-to-end tests. CSS layout, actual
browser focus/scroll behavior, upload/download interactions, and complete routed
journeys still need a future Playwright suite. An MSW-backed test verifies the
frontend's API expectations; it does not prove the backend implements them.

## Adding a regression

1. Identify the observable failure: wrong row after navigation, lost draft after a
   rejected save, duplicate request, stale cache, leaked resource, or invalid UI value.
2. Add a test next to the affected module under `__tests__/`. Name the user-visible
   invariant, reproduce the failure, and verify both the result and necessary cleanup.
3. Use the smallest real boundary that catches the bug. Inject a fake operation into
   a generic factory; use MSW for a feature's client-to-HTTP contract; mount a component
   for interactions. Avoid replacing the entire client or composable under test.
4. Cover failure and retry when an operation can fail. Check that the previous data
   survives, the error is useful, and loading/saving flags settle.
5. Run the targeted test, then the coverage command and frontend quality gates.

`src/test/helpers.ts` supplies `mountComposable` and `deferred`. The first runs setup,
watchers and lifecycle hooks in a mounted host. The second lets tests resolve
requests in a chosen order; do not simulate races with arbitrary sleeps.

The global setup registers i18n and shared primitives, starts MSW, rejects unhandled
requests, resets per-test handlers, and automatically unmounts wrappers. Create a
fresh Pinia for each store test. Give MSW handlers fresh response objects: several
stores legitimately mutate cached rows, so sharing a mutable fixture between tests
can make results depend on execution order. Do not mutate the mock app's global DB.

Use fake timers for debounce, toast expiry, and confirmation timeouts, and restore
real timers afterward. Restore spies/stubbed globals, settle pending promises, and
stop manually-created effect scopes. For preferences initialized on first import,
reset the module cache before importing and set storage first; no production-only
reset hooks are required.

For teleports, query the actual document and dispatch events from the control that
receives focus. Events inside a teleported menu do not bubble through its component's
original DOM parent. Prefer roles, labels, visible text and public emits over internal
refs or exact generated markup. Use structural assertions rather than large snapshots.

## Coverage policy

Coverage includes all `.ts` and `.vue` product files, including unimported views.
Generated declarations, test helpers, mock fixtures, type-only files and the application
entry point are excluded. Keep that denominator intact.

Global floors are 31.5% lines/statements, 26.5% functions and 23.5% branches. They prevent
backsliding while the remaining view layer gets tested. Critical files have separate
minimums so adding UI tests cannot hide a regression in core behavior:

| Files                                                                                  | Lines | Statements | Functions | Branches |
| -------------------------------------------------------------------------------------- | ----: | ---------: | --------: | -------: |
| API client                                                                             |   95% |        95% |       95% |      90% |
| Each store                                                                             |   95% |        90% |       95% |      80% |
| Asset cache, character form, chat messages/creation, entity/list CRUD, page pagination |   95% |        90% |       90% |      80% |

Raise floors when meaningful coverage grows. Do not exclude difficult product files,
weaken assertions, or stub out the behavior being measured to meet a percentage.
