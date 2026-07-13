# CACHE_IMPL — Prompt-Cache Correctness Plan

**Status:** investigation complete (2026-07-13), implementation not started.
**Goal:** every provider route reuses the cached/stable prompt prefix (profile/loadout
system prompt, character card, persona, examples, and — once stable — chat history)
instead of reprocessing it every turn, and the audit trail can actually measure it.

This document is self-contained: all findings, evidence, and step-by-step fixes are
here so a fresh session can execute it without re-deriving anything.

---

## 1. How the prompt is assembled today

`ChatMessageService` → `MessageContextBuilder.assemble()` (`backend/src/chat_message/context.py:62`)
→ `PromptBuilder.build_api_messages()` (`backend/src/prompt_template/prompt_builder.py:46`).

Components are emitted in `prompt_templates.component_order` (a JSON column, per
template row). Live value for the Default Template:

```json
["system_prompt", "world_lore_before_character", "character_context",
 "world_lore_after_character", "scenario", "persona",
 "world_lore_before_examples", "example_dialogues",
 "rag_context", "chat_history", "post_history_instructions"]
```

Stability of each component per turn:

| Component | Role | Stable across turns? |
|---|---|---|
| `system_prompt` (profile/loadout) | system | ✅ unless template uses `{{time}}`/`{{date}}` (§2.5) |
| `world_lore_*` (activated lorebook entries) | system | ⚠️ changes when keyword activation changes |
| `character_context`, `scenario`, `persona` | system | ✅ static per chat |
| `example_dialogues` | user/assistant | ✅ static per character |
| `rag_context` | system | ❌ **changes every turn** (§2.1) |
| `chat_history` | user/assistant (+ depth injections) | ❌ window slides per message once over budget (§2.2) |
| `post_history_instructions` | system | ✅ static per character |

Adapter registry (`backend/src/provider/adapters/__init__.py`): `anthropic` →
`AnthropicAdapter`; `google` → `GeminiAdapter`; `ollama` → `OllamaAdapter`;
`openai`/`xai`/`opencode`/`opencode_go`/`custom` → `OpenAIAdapter`; `openrouter` →
`OpenRouterAdapter(OpenAIAdapter)`; `lmstudio` → `LMStudioAdapter(OpenAIAdapter)`.

## 2. Findings (ranked by cost)

### 2.1 RAG context severs the cacheable prefix every turn — the #1 cost

`rag_context` is a **system message rebuilt every turn** from a semantic query over
the last 2 messages (`context.py:54`, `prompt_builder.py:98,165-175`) and sits
**before `chat_history`**. Prefix caching (OpenAI automatic, DeepSeek/GLM/Kimi
auto-cache via OpenRouter/OpenCode, Gemini implicit, llama.cpp/LM Studio KV reuse)
matches byte-for-byte from token 0 and stops at the first difference — so the match
ends right before the history, and **the entire conversation history is reprocessed
at full input price every turn**. `RAG__ENABLED=true` in `backend/.env`, and
LM Studio is the most-used provider (32/56 audited calls), where prompt reprocessing
is the dominant time-to-first-token cost.

### 2.2 History trimming slides per message

`_build_chat_history` (`prompt_builder.py:235-268`) walks backwards accumulating
until `template.max_history_tokens or 4096`. Once a chat exceeds the budget, the
oldest included message changes **every turn** → the history prefix shifts → cache
miss from the first history message onward, permanently.

### 2.3 Anthropic adapter: one breakpoint, and dynamic content poisons it

`anthropic.py:56-75`: **all** system-role messages are concatenated into a single
`system` block carrying the only `cache_control: {"type": "ephemeral"}` breakpoint.
Consequences:

- `rag_context` (system role) lands inside the cached block → changes every turn →
  even the scaffolding cache is invalidated every turn when RAG is on.
- Depth injections and `post_history_instructions` (system role) are silently
  hoisted out of their intended in-history position into the system block —
  a placement bug independent of caching.
- No breakpoint on the history → even a perfectly stable history is never cached.
- Streaming: `parse_stream_line` (`anthropic.py:158-193`) ignores `message_start`,
  the **only** streaming event carrying `input_tokens` / `cache_read_input_tokens` /
  `cache_creation_input_tokens` → streamed Claude calls record no input/cache usage.

### 2.4 Claude via OpenRouter / OpenCode Zen: zero caching

Those routes use the OpenAI-shaped adapters, which never emit `cache_control`.
Anthropic models do **not** cache without explicit breakpoints, even through
aggregators. OpenRouter documents pass-through: put `cache_control` on text parts
inside OpenAI-style `content` arrays. (OpenAI/DeepSeek/Gemini models via aggregators
cache automatically — only Anthropic-family models need this.)

### 2.5 `{{time}}` / `{{date}}` macros bust everything from token 0

`TemplateService._build_variables` (`backend/src/core/utils/template.py:96-112`)
renders `{{time}}` as HH:MM. DB check: **Default Template (the `is_default`
fallback!), Advanced RP Template, and Assistant Template all contain
`{{time}}`/`{{date}}` in `system_template`**. Any chat on those re-renders its
system prompt every minute/day → full cache invalidation. (The currently active
chat uses "Realistic Frankenstein MAX", which is clean.)

### 2.6 Telemetry is blind — hit rates cannot be measured

1. **Redaction eats usage counts.** `_SENSITIVE_KEYS` includes the substring
   `"token"` (`backend/src/core/logging/logger_config.py:61-69`), which matches
   `input_tokens`, `cache_read_tokens`, etc. — `llm_audit_logs.response_payload.usage`
   is stored as `***REDACTED***`. Confirmed live.
2. **`llm_audit_logs` has no cache columns** — only `prompt_tokens` /
   `completion_tokens` / `total_tokens`. `cache_read/creation` exist transiently in
   `TokenUsage` and one log line (`service.py` `prompt_cache_hit`), then are lost.
3. **OpenAI adapter drops usage-only stream chunks.** `parse_stream_line`
   (`openai.py`) returns `None` when `choices` is empty **before** reading `usage` —
   but the final usage chunk (OpenAI with `stream_options.include_usage`, OpenRouter
   accounting chunk) has `"choices": []`. Evidence: 3 of 11 OpenRouter audit rows
   have `prompt_tokens = 0`.
4. **`stream_options: {"include_usage": true}` is never sent** — native-OpenAI
   streaming returns no usage at all.

### 2.7 What is already fine (do not touch)

- Scaffolding order is deterministic and static per chat; no timestamps in history.
- Anthropic native does opt into caching for the system block (plus beta header —
  header is obsolete-but-harmless).
- Non-streaming usage parsing (incl. cache fields) is correct for
  Anthropic/OpenAI/Gemini; Gemini reads `cachedContentTokenCount` (implicit caching
  needs no opt-in; explicit `cachedContents` is not worth the lifecycle for this app).
- Local llama.cpp/LM Studio KV prefix reuse is automatic server-side — it only needs
  the request prefix to be stable (fixed by §3.1–3.2).
- Depth injections move with the tail by design; impact is a few hundred tokens near
  the end — acceptable, leave as is.

---

## 3. Implementation plan

Phases are independent commits, ordered by value. Run the backend QA gate
(`ruff format . && ruff check . --fix && basedpyright && pytest`) per phase.

### Phase 1 — Move `rag_context` after `chat_history`

**Code** (`prompt_builder.py`): make post-history placement authoritative regardless
of stored template rows:

1. In `build_api_messages`, drop `"rag_context"` from the `components` dict lookup
   loop — i.e., ignore it wherever it appears in `component_order` — and instead
   `api_messages.extend(self._build_rag_context(rag_results))` immediately after the
   `chat_history` component is emitted (before `post_history` fragments), OR keep it
   data-driven and add a normalization: when iterating `component_order`, skip
   `rag_context` if it appears before `chat_history` and emit it right after
   `chat_history`. Prefer the hard-coded post-history emission — simpler, and RAG
   placement is not something a template should break caching with.
2. Change `_build_rag_context` to emit `role: "user"` (or keep system — but see
   Phase 3: post-history system messages must no longer be hoisted on Anthropic).
   Recommended content shape: `[Relevant memory]\n...` as a system-style note; role
   `system` is fine for OpenAI-compatible providers.

**Data migration** (optional cleanup, Alembic data migration): update existing
`prompt_templates.component_order` arrays to move `"rag_context"` after
`"chat_history"` so the stored order matches reality:

```sql
-- inside an alembic data migration
UPDATE prompt_templates
SET component_order = (
  SELECT jsonb_agg(elem ORDER BY
    CASE WHEN elem = '"rag_context"'::jsonb
         THEN idx_of_chat_history + 0.5 ELSE ord END)
  ...
);
-- simpler: rewrite the arrays in Python inside the migration; N rows is tiny.
```

(Write it in Python in the migration body: load rows, `lst.remove("rag_context")`,
`lst.insert(lst.index("chat_history") + 1, "rag_context")`, update.)

**Tests:** builder test asserting rag_context messages appear after the last history
message and before post_history fragments/instructions, for a template whose stored
order still has rag_context early.

### Phase 2 — Chunked (cache-friendly) history eviction

Replace the per-message sliding window in `_build_chat_history` with block eviction
so the window start stays fixed for ~K turns. Stateless + deterministic:

```python
EVICTION_BLOCK = 8  # messages dropped per eviction step

# current behavior: cut_min = smallest drop count so the suffix fits max_tokens
# new behavior:      cut     = ceil(cut_min / EVICTION_BLOCK) * EVICTION_BLOCK
```

Because `cut_min` is monotonically non-decreasing as the chat grows and old message
token counts never change, `cut` only moves once per `EVICTION_BLOCK` turns → the
history prefix is byte-stable between evictions. Rounding **up** always fits the
budget. Implementation sketch:

```python
counts = [tok(m) + 3 for m in messages]
total = sum(counts)
cut_min = 0
while cut_min < len(messages) and total > max_tokens:
    total -= counts[cut_min]
    cut_min += 1
cut = min(len(messages), math.ceil(cut_min / EVICTION_BLOCK) * EVICTION_BLOCK) if cut_min else 0
history = [{"role": m.role.value, "content": m.content} for m in messages[cut:]]
```

Keep the depth-injection splice unchanged. **Tests:** (a) under budget → identical
output to today; (b) once over budget, growing the history by 1..EVICTION_BLOCK-1
messages does not change the first included message; (c) rounding never exceeds
budget.

### Phase 3 — Anthropic adapter: correct block layout + history breakpoint

`anthropic.py build_payload`:

1. **Split, don't hoist:** only the *leading run* of system messages (everything
   before the first non-system message = the stable scaffolding) goes into the
   `system` block with `cache_control` on it. Any system-role message appearing
   *after* a user/assistant message (RAG post-history, `post_history_instructions`,
   depth injections) is converted in place to a user turn:
   `{"role": "user", "content": f"[System note]\n{text}"}` — Anthropic's messages
   array only allows user/assistant. This fixes both the cache poisoning and the
   silent reordering bug.
2. **History breakpoint:** convert the **last** message's content to block form and
   mark it: `{"role": r, "content": [{"type": "text", "text": t, "cache_control":
   {"type": "ephemeral"}}]}`. Two breakpoints total (system + last message) — well
   under Anthropic's limit of 4. On the next turn the previous turns are a cache
   read; combined with Phase 2 the window is stable between evictions.
3. **Streaming usage:** in `parse_stream_line`, handle `message_start`:

   ```python
   if event_type == "message_start":
       u = data.get("message", {}).get("usage", {})
       if u:
           return StreamChunk(usage=TokenUsage(
               input_tokens=u.get("input_tokens", 0),
               cache_read_tokens=u.get("cache_read_input_tokens", 0),
               cache_creation_tokens=u.get("cache_creation_input_tokens", 0),
           ))
   ```

4. **Merge, don't overwrite, stream usage.** `_stream_completion`
   (`backend/src/chat_message/service.py`) does `last_usage = chunk.usage` — the
   `message_delta` usage (output only) would clobber `message_start` (input+cache).
   Merge field-wise (take max/non-zero per field) either in the service or in a
   small `TokenUsage.merge()` on `base.py`. This also benefits OpenAI-compat
   providers that split usage across chunks.

**Tests:** payload builder tests (leading system run cached; post-history system
converted to user; last-message breakpoint present; ≤4 breakpoints), stream parsing
test for `message_start`, merge test.

### Phase 4 — Anthropic models via OpenRouter (and OpenCode Zen if it passes through)

In `OpenRouterAdapter.build_payload` (after `super().build_payload`), when the model
id is Anthropic-family (`model.startswith("anthropic/")` on OpenRouter), rewrite for
cache_control pass-through:

- first system message content → `[{"type": "text", "text": ..., "cache_control": {"type": "ephemeral"}}]`
- last message content → same block form with `cache_control`.

OpenRouter forwards these to Anthropic and reports savings via
`usage.prompt_tokens_details.cached_tokens` (already parsed). For OpenCode Zen
(`opencode` provider type, also OpenAI-shaped): check their docs/behavior for
`cache_control` pass-through on Claude routes; if supported, apply the same
transform keyed on the model identifier (inspect `model_registry`/`model_routing`
rows for the id scheme); if not, document it as a no-op route.

**Tests:** OpenRouter payload test for an `anthropic/*` id (blocks present) and a
non-Anthropic id (payload unchanged).

### Phase 5 — Telemetry: make cache hits measurable

1. **Fix redaction over-match** (`logger_config.py`): the substring rule `"token"`
   must not match usage counters. Replace with: redact if the key (lowercased)
   is in an exact set (`token`, `api_key`, `apikey`, `authorization`, `password`,
   `secret`, `x-api-key`) **or** ends with `_token`/`-token`; never redact keys
   ending in `_tokens`. Add tests: `input_tokens`/`cache_read_tokens` survive;
   `access_token`, `x-api-key`, `Authorization` are still masked.
2. **Usage-only stream chunks** (`openai.py parse_stream_line`): extract `usage`
   *before* the `if not choices: return None` guard; when choices is empty but
   usage present, return a usage-only `StreamChunk`.
3. **Request usage in streams**: in `OpenAIAdapter.build_payload`, when
   `stream=True` and the caller didn't set it, add
   `payload["stream_options"] = {"include_usage": True}`. OpenAI, OpenRouter,
   LM Studio (llama.cpp) accept it. If a strict OpenAI-compatible server rejects it,
   override in that adapter subclass to drop it (watch `custom` provider type).
4. **Persist cache usage**: Alembic migration adding
   `cache_read_tokens INTEGER NOT NULL DEFAULT 0` and
   `cache_creation_tokens INTEGER NOT NULL DEFAULT 0` to `llm_audit_logs`; thread
   the values from `TokenUsage` through `llm_audit.classify_and_audit` →
   `audit/writer.py` → model. **API contract:** if `LlmAuditLogResponse` gains the
   new fields, regenerate `openapi.json` (`scripts/openapi.sh`) and
   `frontend/src/api/schema.d.ts` (`bun run api:gen`), and update the MSW handler
   fixtures (`frontend/src/mocks/handlers.ts` `/admin/logs/llm`). Optionally show a
   "cached" chip in the chat drawer Logs tab.

Post-fix hit-rate query (also useful in the Logs UI later):

```sql
SELECT provider,
       count(*)                                   AS calls,
       sum(prompt_tokens)                         AS prompt,
       sum(cache_read_tokens)                     AS cached,
       round(100.0 * sum(cache_read_tokens) / nullif(sum(prompt_tokens), 0), 1)
                                                  AS hit_pct
FROM llm_audit_logs
WHERE status = 'success' AND created_at > now() - interval '7 days'
GROUP BY provider ORDER BY calls DESC;
```

### Phase 6 — Template hygiene: `{{time}}`/`{{date}}`

- Remove `{{time}}`/`{{date}}` from the **Default Template**'s `system_template`
  (data migration or UI edit; it is the `is_default` fallback for every chat without
  an explicit template). Same for Advanced RP / Assistant templates, or leave those
  to the user with a warning.
- Document in `docs/architecture/backend/prompt-system.md`: temporal macros in
  `system_template` defeat prompt caching; if wall-clock context is wanted, put it
  in a `post_history` fragment (after the cached prefix) instead.
- Optional guard: template validation warns when `system_template` matches
  `{{\s*(time|date)\s*}}`.

### Phase 7 (optional) — Lore activation churn

Keyword-activated lore sits early (by design, ST semantics) and busts the scaffolding
cache when the activated set changes. If it becomes measurable noise (Phase 5 will
show it), consider activation stickiness (entry stays active for N turns after last
match) to reduce churn. Not part of the initial pass.

---

## 4. Verification plan (end to end)

1. **Unit:** all tests listed per phase, plus existing suite (`uv run pytest`,
   764+ tests green as of 2026-07-13).
2. **LM Studio (llama.cpp):** send 2–3 consecutive turns in a real chat; the server
   log prints prompt-processing counts — with Phases 1–2 the reprocessed portion per
   turn should collapse to roughly (last user turn + RAG block + depth-injection
   tail) instead of the full prompt. Time-to-first-token drop should be obvious.
3. **OpenRouter / OpenCode (DeepSeek, GLM, Kimi):** after Phase 5, second turn shows
   `cache_read_tokens > 0` in `llm_audit_logs`; run the §Phase-5 SQL.
4. **Anthropic native (when used):** turn 1 `cache_creation_tokens > 0`, turn 2
   `cache_read_tokens ≈ prior prompt size`, and the `prompt_cache_hit` log line now
   fires for streaming too.
5. **Claude via OpenRouter:** `usage.prompt_tokens_details.cached_tokens > 0` on
   turn 2 (Phase 4).

## 5. Risks / notes

- **Cache write premium (Anthropic):** ephemeral cache writes cost 1.25×; with an
  RP chat's read:write ratio this is strictly favorable, but a chat abandoned after
  one turn pays a small premium. Acceptable.
- **Anthropic post-history system→user conversion** changes prompt semantics
  slightly (system notes become user-visible-style turns). This matches ST
  conventions and only affects Anthropic-family routes; example dialogues and
  scaffolding are untouched.
- **`EVICTION_BLOCK` trade-off:** larger = more stable prefix but coarser context
  loss at eviction. 8 messages ≈ 4 exchanges is a sane default; could be a template
  column later.
- **`stream_options` on strict OpenAI-compat servers:** watch the `custom` provider
  type; drop the param in an adapter override if a 400 appears.
- **Do not** reorder anything else in the scaffolding — its byte-stability is what
  everything upstream of `chat_history` relies on.

## 6. Evidence appendix (2026-07-13)

- Audit traffic: `lmstudio` 32 calls, `opencode_go` 13, `openrouter` 11; 3/11
  OpenRouter success rows have `prompt_tokens = 0` (usage-only chunk dropped, §2.6.3).
- `RAG__ENABLED=true` in `backend/.env`.
- `response_payload.usage.*` stored as `***REDACTED***` (redaction over-match, §2.6.1).
- Templates containing `{{time}}`/`{{date}}` in `system_template`: Default Template
  (`is_default = true`), Advanced RP Template, Assistant Template. Active chat
  `JLj2_bIyw7En` uses "Realistic Frankenstein MAX" (clean).
- Key files: `prompt_builder.py:46-121` (assembly), `:235-268` (history window),
  `:165-175` (RAG), `context.py:38-71` (lore/RAG inputs),
  `adapters/anthropic.py:56-75,158-193`, `adapters/openai.py` (`parse_stream_line`
  empty-choices guard), `adapters/openrouter.py`, `logger_config.py:61-101`
  (redaction), `audit/writer.py:91-92`, `chat_message/llm_audit.py:92-93`,
  `chat_message/service.py` (`_stream_completion` usage overwrite,
  `prompt_cache_hit` log).
