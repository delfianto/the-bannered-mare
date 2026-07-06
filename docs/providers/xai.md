# xAI Grok API — Deep Analysis

> **Scope:** Complete xAI Chat Completions API specification for The Bannered Mare's
> multi-provider adapter architecture. Covers authentication, request/response schemas,
> streaming, tool calling, reasoning models, and all current Grok model variants.


## Table of Contents

1. [API Overview](#1-api-overview)
2. [Authentication](#2-authentication)
3. [Endpoints](#3-endpoints)
4. [Request Schema](#4-request-schema)
5. [Message Format](#5-message-format)
6. [Response Schema](#6-response-schema)
7. [Streaming](#7-streaming)
8. [Tool Calling & Server-Side Tools](#8-tool-calling--server-side-tools)
9. [Reasoning Models](#9-reasoning-models)
10. [Model Catalog](#10-model-catalog)
11. [Discontinuities with OpenAI](#11-discontinuities-with-openai)
12. [Current The Bannered Mare Implementation](#12-current-the-bannered-mare-implementation)
13. [Adapter Recommendations](#13-adapter-recommendations)


## 1. API Overview

xAI provides an **OpenAI-compatible** Chat Completions API. You can use the OpenAI SDK
with a base URL override, meaning the bulk of the OpenAI adapter can be reused.

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["XAI_API_KEY"],
    base_url="https://api.x.ai/v1",
)
```

xAI also offers a newer **Responses API** (`/v1/responses`) positioned as the primary
interface going forward. However, Chat Completions remains fully supported and is the
correct target for The Bannered Mare's adapter pattern.


## 2. Authentication

| Field | Value |
|-------|-------|
| Header | `Authorization: Bearer <XAI_API_KEY>` |
| Key source | `https://console.x.ai/team/default/api-keys` |
| Env var convention | `XAI_API_KEY` |

Same Bearer token pattern as OpenAI — no special headers required.


## 3. Endpoints

**Base URL:** `https://api.x.ai/v1`

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/chat/completions` | Chat completions (OpenAI-compatible) |
| POST | `/v1/responses` | Responses API (newer, stateful) |
| GET | `/v1/responses/{response_id}` | Retrieve stored response |
| DELETE | `/v1/responses/{response_id}` | Delete stored response |
| GET | `/v1/chat/deferred-completion/{request_id}` | Poll async/deferred results |
| GET | `/v1/models` | List available models |


## 4. Request Schema

### POST `/v1/chat/completions`

| Parameter | Type | Required | Default | Range | Notes |
|-----------|------|----------|---------|-------|-------|
| `model` | string | **Yes** | — | — | Model ID |
| `messages` | array | **Yes** | — | — | Message objects |
| `temperature` | number | No | — | 0–2 | Sampling temperature |
| `top_p` | number | No | — | 0–1 | Nucleus sampling |
| `n` | integer | No | 1 | ≥ 1 | Number of choices |
| `stream` | boolean | No | false | — | Enable SSE streaming |
| `stream_options` | object | No | — | — | `{"include_usage": true}` for usage in final chunk |
| `stop` | array | No | — | Max 4 | Stop sequences. **Incompatible with reasoning models** |
| `max_completion_tokens` | integer | No | — | — | Output token limit (preferred) |
| `max_tokens` | integer | No | — | — | **Deprecated** — use `max_completion_tokens` |
| `presence_penalty` | number | No | — | -2.0–2.0 | **Incompatible with reasoning models** |
| `frequency_penalty` | number | No | — | -2.0–2.0 | **Incompatible with reasoning models** |
| `logit_bias` | object | No | null | -100–100 | Listed but **unsupported** |
| `logprobs` | boolean | No | false | — | Return log probabilities |
| `top_logprobs` | integer | No | — | 0–8 | Top logprobs per position |
| `response_format` | object | No | — | — | JSON mode / JSON schema |
| `seed` | integer | No | null | — | Best-effort deterministic |
| `tools` | array | No | null | Max 128 | Tool definitions |
| `tool_choice` | string/object | No | — | `"auto"`, `"required"`, `"none"`, or specific | Tool selection |
| `parallel_tool_calls` | boolean | No | — | — | Multiple simultaneous tool calls |
| `reasoning_effort` | string | No | — | `"low"`, `"high"` | **grok-3-mini only**; errors on other models |
| `user` | string | No | null | — | End-user ID |
| `deferred` | boolean | No | false | — | xAI-specific async mode |

### Parameters NOT Supported

- `top_k` — Not available
- `logit_bias` — Listed in schema but explicitly unsupported
- `search_parameters` — **Retired** Jan 2026; replaced by server-side tools


## 5. Message Format

Standard OpenAI message format:

```json
{
  "role": "system" | "developer" | "user" | "assistant",
  "content": "string"
}
```

- `system` and `developer` are aliases (both set system prompt)
- Must be the first message, maximum one
- Supports multimodal content arrays for images:

```json
{
  "role": "user",
  "content": [
    {"type": "image_url", "image_url": {"url": "...", "detail": "high"}},
    {"type": "text", "text": "Describe this image"}
  ]
}
```

Image detail levels: `"auto"` (default), `"low"`, `"high"`. Max 20 MiB. Formats: JPEG, PNG.


## 6. Response Schema

### Non-Streaming Response

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "grok-4-1-fast-reasoning",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Response text",
        "reasoning_content": "Internal reasoning trace (reasoning models only)",
        "refusal": null,
        "tool_calls": null
      },
      "finish_reason": "stop",
      "logprobs": null
    }
  ],
  "citations": [],
  "output_files": [],
  "system_fingerprint": "fp_...",
  "usage": {
    "prompt_tokens": 42,
    "completion_tokens": 128,
    "total_tokens": 170,
    "reasoning_tokens": 512,
    "cost_in_usd_ticks": 1234
  }
}
```

### xAI-Specific Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `choices[].message.reasoning_content` | string | Reasoning trace (plaintext for grok-3-mini, encrypted for grok-4 reasoning) |
| `citations` | array | Source URLs when server-side search tools are used |
| `output_files` | array | Files generated by code_interpreter |
| `usage.reasoning_tokens` | integer | Tokens consumed by reasoning |
| `usage.cost_in_usd_ticks` | integer | Cost where 10,000,000,000 ticks = 1 USD |

### Finish Reasons

| Value | Meaning |
|-------|---------|
| `"stop"` | Natural completion or stop sequence |
| `"length"` | Hit `max_completion_tokens` |
| `"end_turn"` | Model decided to end |
| `"tool_calls"` | Model invoked a tool |


## 7. Streaming

Standard OpenAI SSE format with `data:` prefix and `[DONE]` sentinel:

```
data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}],"usage":null}

data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}],"usage":null}

data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{...}}

data: [DONE]
```

### Key Streaming Differences

- **Tool calls are returned in a single chunk**, NOT streamed across multiple chunks
  (unlike OpenAI which spreads tool call arguments across deltas)
- Set `stream_options: {"include_usage": true}` to receive usage in the final chunk
- **Timeout warning:** Reasoning models can think for extended periods before producing
  output. Set client timeout to **3600+ seconds** for reasoning model streams.


## 8. Tool Calling & Server-Side Tools

### Client-Side Function Calling

Standard OpenAI function calling format:

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get current weather",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {"type": "string"}
          },
          "required": ["location"]
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

Max 128 tools per request.

### Server-Side Tools (xAI-Specific)

Execute on xAI servers — no client-side implementation needed:

```json
{
  "tools": [
    {"type": "web_search"},
    {"type": "x_search"},
    {"type": "code_interpreter"},
    {"type": "collections_search"}
  ]
}
```

| Tool | Description | Pricing |
|------|-------------|---------|
| `web_search` | Web search with optional domain filters (max 5 allowed/excluded) | $5 / 1,000 calls |
| `x_search` | Search X/Twitter posts, users, threads | $5 / 1,000 calls |
| `code_interpreter` | Python sandbox execution, returns files | $5 / 1,000 calls |
| `collections_search` | Search uploaded document collections | $5 / 1,000 calls |

Server-side and client-side tools can be mixed in the same request.

### Web Search Filters

```json
{
  "type": "web_search",
  "web_search": {
    "filters": {
      "allowed_domains": ["example.com"],
      "excluded_domains": []
    },
    "enable_image_understanding": true
  }
}
```

`allowed_domains` and `excluded_domains` are mutually exclusive. Max 5 domains each.


## 9. Reasoning Models

### Reasoning vs Non-Reasoning Variants

Grok 4 and later ship as paired variants:

| Variant | Reasoning | Penalties/Stop | Use Case |
|---------|-----------|----------------|----------|
| `*-reasoning` | Always active | **Not supported** | Complex analysis, planning |
| `*-non-reasoning` | Disabled | Supported | Creative writing, RP, chat |

### Constraints for Reasoning Models

These parameters **error** when sent to reasoning variants:
- `frequency_penalty`
- `presence_penalty`
- `stop`

### `reasoning_effort` Parameter

- **Only supported on `grok-3-mini`**
- Values: `"low"`, `"high"` (no `"medium"` — differs from OpenAI)
- Sending to grok-4 or grok-4.20 models causes an error

### Reasoning Content

- `grok-3-mini`: Plaintext reasoning in `choices[].message.reasoning_content`
- `grok-4` reasoning models: Encrypted reasoning (accessible via Responses API)
- `usage.reasoning_tokens`: Token count consumed by reasoning


## 10. Model Catalog

### Grok 4.20 Family (Latest, March 2026)

| Model ID | Context | Max Output | Input $/M | Output $/M | Cached $/M | Capabilities |
|----------|---------|------------|-----------|------------|------------|-------------|
| `grok-4.20-0309-reasoning` | 2,000,000 | — | $2.00 | $6.00 | $0.20 | functions, structured, reasoning, vision |
| `grok-4.20-0309-non-reasoning` | 2,000,000 | — | $2.00 | $6.00 | $0.20 | functions, structured, vision |
| `grok-4.20-multi-agent-0309` | 2,000,000 | — | $2.00 | $6.00 | $0.20 | functions, structured, reasoning, vision |

**Key specs:** 2M context window. Cheapest per-token of the Grok 4 family. Supports vision.
Multi-agent variant optimized for agentic workflows.

### Grok 4.10 Fast Family (February 2026)

| Model ID | Context | Max Output | Input $/M | Output $/M | Cached $/M | Capabilities |
|----------|---------|------------|-----------|------------|------------|-------------|
| `grok-4-1-fast-reasoning` | 2,000,000 | 30,000 | $0.20 | $0.50 | $0.05 | functions, structured, reasoning, vision |
| `grok-4-1-fast-non-reasoning` | 2,000,000 | 30,000 | $0.20 | $0.50 | $0.05 | functions, structured, vision |

**Key specs:** 2M context, 30K max output. Ultra-cheap ($0.20/$0.50 per MTok). Best value
for high-throughput RP. Supports vision.

### Grok 4.0 Family (Original, July 2025)

| Model ID | Context | Max Output | Input $/M | Output $/M | Cached $/M | Capabilities |
|----------|---------|------------|-----------|------------|------------|-------------|
| `grok-4-0709` | 256,000 | 256,000 | $3.00 | $15.00 | $0.75 | functions, structured, reasoning, vision |
| `grok-4-fast-reasoning` | 2,000,000 | 30,000 | $0.20 | $0.50 | $0.05 | functions, structured, reasoning, vision |
| `grok-4-fast-non-reasoning` | 2,000,000 | 30,000 | $0.20 | $0.50 | $0.05 | functions, structured, vision |

### Grok 3 Family (Legacy)

| Model ID | Context | Max Output | Input $/M | Output $/M | Capabilities |
|----------|---------|------------|-----------|------------|-------------|
| `grok-3` | 131,072 | 16,000 | $3.00 | $15.00 | functions, structured |
| `grok-3-mini` | 131,072 | 16,000 | $0.30 | $0.50 | functions, structured, reasoning (`reasoning_effort`) |

### Specialized Models

| Model ID | Context | Max Output | Input $/M | Output $/M | Capabilities |
|----------|---------|------------|-----------|------------|-------------|
| `grok-code-fast-1` | 256,000 | 10,000 | $0.20 | $1.50 | reasoning, structured, functions |
| `grok-2-vision-1212` | 32,000 | — | $2.00 | $10.00 | vision |

### Knowledge Cutoff

- **Grok 3 & 4 families:** November 2024
- **Grok Code Fast 1:** September 2025

### Rate Limit Tiers

Tiers based on cumulative spend since Jan 1, 2026 (never downgrade):

| Tier | Cumulative Spend |
|------|-----------------|
| Tier 0 | $0 (default) |
| Tier 1 | $50 |
| Tier 2 | $250 |
| Tier 3 | $1,000 |
| Tier 4 | $5,000 |

Top-tier limits for grok-4.20 and grok-4-1-fast: 10,000,000 TPM, 1,800 RPM.


## 11. Discontinuities with OpenAI

Despite being OpenAI-compatible, these differences matter for a provider adapter:

| Aspect | OpenAI | xAI |
|--------|--------|-----|
| Base URL | `api.openai.com/v1` | `api.x.ai/v1` |
| `top_k` | Not supported | Not supported |
| `logit_bias` | Supported | **Unsupported** (schema accepts, silently ignored) |
| `reasoning_effort` values | `"low"`, `"medium"`, `"high"` | `"low"`, `"high"` only |
| `reasoning_effort` scope | o-series models | **grok-3-mini only** (errors on grok-4+) |
| `reasoning_content` in response | Not in Chat Completions | Present in `choices[].message` |
| Tool calls in streaming | Spread across chunks | **Single chunk** |
| `citations` in response | Absent | Array (when search tools used) |
| `output_files` in response | Absent | Array (when code_interpreter used) |
| `cost_in_usd_ticks` in usage | Absent | xAI-specific cost tracking |
| `reasoning_tokens` in usage | Absent | Present for reasoning models |
| `deferred` parameter | N/A | xAI-specific async completion |
| Server-side tools | N/A | `web_search`, `x_search`, `code_interpreter`, `collections_search` |
| Penalties + reasoning | Compatible | **Error** when penalties/stop sent to reasoning models |
| `max_tokens` | Supported | **Deprecated** — must use `max_completion_tokens` |
| Prompt caching | Explicit | **Implicit** (automatic, no special parameter) |

### Critical Adapter Implications

1. **Parameter filtering by model variant:** Must strip `frequency_penalty`,
   `presence_penalty`, and `stop` when targeting `*-reasoning` model IDs.
2. **Timeout handling:** Reasoning models can spend minutes thinking before producing
   output. Default httpx timeout (60s) will fail. Use 3600s+.
3. **Extra response fields:** Parse `reasoning_content`, `citations`, `reasoning_tokens`,
   and `cost_in_usd_ticks` into the canonical `CompletionResponse`.
4. **Streaming tool calls:** Don't attempt to accumulate tool call arguments across
   chunks — they arrive complete in a single delta.


## 12. Current The Bannered Mare Implementation

### Fixture State

**Model families** (`src/fixtures/families/xai.py`):
- `xai/grok-4` — grok-4-0709 (256K context). Correct.
- `xai/grok-4.1` — References `grok-4.1-2025-11-17`. **Stale** — should be Grok 4.10 Fast.
- `xai/grok-4.1-fast` — References `grok-4.1-fast`. **Stale** — model IDs are now
  `grok-4-1-fast-reasoning` / `grok-4-1-fast-non-reasoning`.

**Missing families:**
- No Grok 4.20 family at all (March 2026 release)
- No distinction between reasoning and non-reasoning variants
- Vision capability marked `False` on all families (should be `True` for 4.10+/4.20)

**Model seeds** (`src/fixtures/models.py`):
- `grok-4-0709` — Correct ID
- `grok-4-fast-non-reasoning` — Correct ID
- `grok-4-1-fast-non-reasoning` — Correct ID

**Missing models:**
- No `grok-4.20-0309-non-reasoning` (best for RP: cheap, 2M context, no reasoning overhead)
- No `grok-4.20-0309-reasoning` variant
- No `grok-4-1-fast-reasoning` variant

### Provider Client

Current `ProviderClient` sends all requests through OpenAI protocol, which works for xAI.
However:
- No parameter filtering for reasoning model constraints
- No timeout override for reasoning models
- Does not parse `reasoning_content`, `citations`, or xAI-specific usage fields


## 13. Adapter Recommendations

### Reuse OpenAI Adapter

xAI is OpenAI-compatible — no dedicated adapter class needed. The `OpenAIAdapter` should
handle xAI with these provider-specific overrides:

### 1. Parameter Filtering by Model Variant

```python
_REASONING_INCOMPATIBLE = {"frequency_penalty", "presence_penalty", "stop"}

def filter_parameters(self, params: dict, model: str) -> dict:
    if model.endswith("-reasoning") or model == "grok-4-0709":
        return {k: v for k, v in params.items() if k not in _REASONING_INCOMPATIBLE}
    return params
```

### 2. Timeout Override

```python
def get_timeout(self, model: str) -> float:
    if "reasoning" in model or model == "grok-4-0709":
        return 3600.0  # reasoning models can think for minutes
    return 120.0
```

### 3. Extended Response Parsing

```python
@dataclass
class XAICompletionResponse(CompletionResponse):
    reasoning_content: str | None = None
    citations: list[str] = field(default_factory=list)
    reasoning_tokens: int = 0
    cost_usd_ticks: int = 0
```

### 4. `max_tokens` → `max_completion_tokens` Migration

The adapter should rename `max_tokens` to `max_completion_tokens` in the payload for xAI:

```python
def build_payload(self, request: CompletionRequest) -> dict:
    payload = super().build_payload(request)
    if "max_tokens" in payload:
        payload["max_completion_tokens"] = payload.pop("max_tokens")
    return payload
```

### Fixture Updates Needed

1. **Rename** `xai/grok-4.1` → actual model IDs, update context/output specs
2. **Add** `xai/grok-4.20` family with reasoning and non-reasoning variants
3. **Fix** `supports_vision: True` on all 4.10+/4.20 families
4. **Add** `max_completion_tokens` as the parameter name (not `max_tokens`)
5. **Add** `grok-4.20-0309-non-reasoning` model seed (best value for RP)
