# Browser workflows

These tests run the production frontend in real desktop and mobile Chromium.
Each test gets a fresh browser context and test-owned API state. No backend,
database, external model provider, credentials, or developer data are used.

From `frontend/`:

```sh
bun install --frozen-lockfile
bunx playwright install chromium           # once; on Linux CI use --with-deps
bun run test:e2e                           # builds, starts preview, runs both projects
bun run test:e2e:ui                        # builds and opens Playwright UI
bun run test:e2e:run --project=chromium     # run an existing build
bunx playwright show-report                # most recent HTML report
```

Playwright starts `just fe-e2e-serve` from the repository root. Port **4187** is
reserved for this suite; an occupied port fails the run instead of silently testing
a developer's running server. Playwright owns server startup/teardown. `bun run check`
also type-checks the browser fixtures, tests and configuration.

CI builds once, installs Chromium with its OS dependencies, and runs both projects.
It uploads `playwright-report/` and `test-results/` for seven days. Failed tests retain
screenshots, video and traces. CI allows one diagnostic retry but still fails on
flaky tests. Debug a trace with:

```sh
bunx playwright show-trace test-results/<test-directory>/trace.zip
```

## Boundaries and extension

Import `test` and `expect` from `./fixtures`. Its automatic fixture installs network
interception before navigation and fails on unknown API endpoints or uncaught page
errors. API calls never fall through to a live backend. Third-party fonts are omitted
and portraits are served locally; service workers are blocked so dev MSW cannot hide
requests from Playwright. The fixture clones existing typed seed fixtures, records
writes and keeps mutations across reloads within each test. Persistence here belongs
to the fake API, not a database.

Keep user-facing assertions in the spec and add explicit endpoints in `fixtures.ts`
as workflows grow. Prefer roles, visible labels and placeholders; inspect recorded
writes when payload correctness matters. Wait for visible results, responses or
persisted preferences instead of fixed sleeps. Keep Vitest tests under `src/` and
Playwright specs under `e2e/` so the runners do not collect one another's tests.

Current workflows cover:

- Character portrait upload, JSON export, save/reload and failed-edit retry.
- Profile dialog focus trapping, Escape/focus restoration and failed-save recovery.
- Selecting a profile to start a tale, SSE-framed replies and reload.
- Generation failure/retry and conversation isolation when switching sessions.
- Keyboard menu navigation and persisted text size, plus narrow-screen settings.

## Continue here

1. Add provider/model creation and the complete setup wizard journey.
2. Add a controllable streaming HTTP fixture server for delayed chunks, Stop,
   mid-stream disconnects and switching sessions during an active generation. The
   current `route.fulfill` response contains SSE frames delivered in one body;
   it does not prove incremental rendering or cancellation over a live socket.
3. Add drag/drop imports, lorebook/memory CRUD and more responsive/layout assertions.
4. Add Firefox/WebKit projects and a scheduled CI matrix, then accessibility checks
   and a small set of stable visual baselines using local fonts.
5. Create a separate full-stack smoke job with FastAPI, a disposable migrated/seeded
   PostgreSQL database and a fake LLM service. Never reset a developer's database.

Browser results supplement the existing 85% Vitest coverage gates; they do not
contribute to or replace those percentages.
