---
name: new-msw-handler
description: Scaffold an MSW request handler and fixture that match a backend OpenAPI schema. Use when adding mock coverage for an endpoint, or when a regenerated schema changes a response shape — keeps src/mocks in sync with src/api/schema.d.ts so mock mode mirrors the real backend.
---

Add or update an MSW handler in `src/mocks/handlers.ts` whose request/response shape matches the generated schema. The mocks are hand-authored, so they are the easiest thing to let drift from the spec.

## Steps

1. **Find the contract:** locate the endpoint in `src/api/schema.d.ts`. Note the exact path, method, query/path params, and the response schema — including the pagination **envelope** (e.g. `{ logs, total, limit, skip }`) vs a bare array, and every field name / type / nullability.
2. **Match field-for-field:** build the fixture with the spec's exact field names (e.g. `latency_ms`, `created_at`, `prompt_tokens` — not invented aliases) and wrap it in the correct envelope. Mirror the seed-data style already in `src/mocks/data/`.
3. **Register the handler:** add `http.<method>("<path>", ...)` to `src/mocks/handlers.ts`, honoring query params (limit / skip / filters) and a small `delay()`.
4. **Verify in the browser:** MSW only runs in-browser. Start `VITE_USE_MOCKS=true vp dev --host`, exercise the feature, and confirm no blank / `undefined` columns — the symptom of a field-name mismatch.

## Gotcha

MSW handlers return plain JSON and are **not** type-checked against the schema — a typo in a field name compiles fine and only breaks at runtime against the real backend. Cross-check every field against `schema.d.ts`.
