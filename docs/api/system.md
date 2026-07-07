---
title: System & Admin
---

# System & Admin

The operational surface: a health probe, read-only queries over the audit logs, and two
built-in endpoints. The log queries read the [observability
sink](/architecture/backend/data-model#observability) — the LLM-call, HTTP-request, and
error records written by middleware and the audit writer. Like the rest of the API these
are **unauthenticated**, so keep the service off untrusted networks (see
[Authentication](/api/#authentication)).

## Health & built-ins

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Application health/readiness. |
| `GET` | `/` | API root banner. |
| `GET` | `/demo` | A minimal built-in HTML chat page for manual testing. |

`GET /health` returns a small JSON status object — use it for liveness/readiness probes.
`GET /` is the root banner. `GET /demo` serves a self-contained HTML chat UI (not JSON)
that exercises the streaming completion loop end to end without the frontend — handy for
sanity-checking a fresh backend.

## Admin log queries

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/admin/logs/llm` | Query LLM completion-call logs. |
| `GET` | `/admin/logs/llm/stats` | Aggregated LLM usage statistics. |
| `GET` | `/admin/logs/http` | Query HTTP request logs. |
| `GET` | `/admin/logs/errors` | Query unhandled-error logs. |

::: warning Different pagination
The admin log endpoints predate the shared envelope and use **skip/limit offset
pagination** with a `{ logs, total, limit, skip }` wrapper — *not* the `{ items, meta }`
envelope the rest of the API uses. Both `limit` (default `100`) and `skip` (default `0`)
are query params.
:::

### LLM logs and stats

`GET /admin/logs/llm` returns an `LlmAuditLogPage` — one row per completion call, filterable
by `chat_id`, `provider`, `model`, and `status`. Each `LlmAuditLogResponse` records the
`provider` and `model`, token counts (`prompt_tokens`, `completion_tokens`, `total_tokens`),
`latency_ms`, `status`, optional `estimated_cost_usd` and `error_message`, and the raw
`request_payload` / `response_payload`. Because `chat_id` is a set-null reference, these
rows **survive the deletion of their chat**, so the audit trail stays complete.

```bash
curl "http://localhost:8000/admin/logs/llm?provider=anthropic&status=success&limit=50"
```

`GET /admin/logs/llm/stats` aggregates that data over an optional window (`start_date`,
`end_date`) into an `LlmStatsResponse` — a `stats` array of per-`provider`/`model`
`LlmUsageStat` (total calls, token totals, cost, `avg_latency_ms`, success/error counts,
and `success_rate`) plus the resolved `period`.

```bash
curl "http://localhost:8000/admin/logs/llm/stats?start_date=2026-07-01&end_date=2026-07-31"
```

### HTTP and error logs

`GET /admin/logs/http` returns an `HttpLogPage` of `HttpLogResponse` rows — `method`,
`path`, `status_code`, `latency_ms`, `client_ip`, `user_agent`, and the captured
`request_body` / `response_body` — filterable by `method`, `path`, `status_code`, and
`request_id`. `GET /admin/logs/errors` returns an `ErrorLogPage` of `ErrorLogResponse` rows
(`error_type`, `message`, `stack_trace`, and a `context` object), filterable by
`error_type`. Both feed the **Logs** tab in the app's settings.

```bash
curl "http://localhost:8000/admin/logs/http?status_code=500&limit=20"
curl "http://localhost:8000/admin/logs/errors?error_type=ProviderTimeoutError"
```
