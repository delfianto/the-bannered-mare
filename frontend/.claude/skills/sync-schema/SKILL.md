---
name: sync-schema
description: Regenerate the API types from the backend OpenAPI spec and report drift. Use when the backend contract may have changed, or before relying on API types — runs api:gen, diffs src/api/schema.d.ts, type-checks, and flags frontend usage that no longer matches the spec.
---

Regenerate `src/api/schema.d.ts` from `../candlekeep-core/openapi.json` and surface any drift between the frontend and the current backend contract.

## Steps

1. **Regenerate:** `bun run api:gen` (runs `openapi-typescript`). Never hand-edit `schema.d.ts`.
2. **Diff:** `git diff --stat src/api/schema.d.ts`, then inspect added/removed schemas and paths and changed field names/types. Call out new endpoints and any removed/renamed fields.
3. **Type-check:** `bun run typecheck` (vue-tsc). Errors here mark frontend code that referenced something the spec changed — fix those call sites.
4. **Hunt silent drift:** `vue-tsc` only catches code coupled to the schema. Grep for raw `fetch(` + hand-rolled response `interface`s that bypass the typed `client` (e.g. `grep -rnE '[^.]fetch\(' src`). Those won't error but may mismatch the spec — compare each against the regenerated schema and switch them to the typed `client` + `components["schemas"][...]`.
5. **Keep mocks in sync:** for any changed endpoint, update the matching MSW handler in `src/mocks/handlers.ts` and fixtures so mock mode stays spec-true (see `/new-msw-handler`).

## Output

Report: new/removed endpoints, changed field names/types, type errors fixed, and any raw-`fetch` call sites that diverge from the spec. If a UI feature consumes a changed endpoint, verify it in `VITE_USE_MOCKS=true vp dev`.
