# OpenRouter API — Deep Analysis for Multi-Provider Architecture

> **Source:** OpenRouter API documentation (openrouter.ai/docs), observed API behavior
> **Base URL:** `https://openrouter.ai/api/v1`
> **Goal:** Define exactly how the OpenRouter API works, how it differs from vanilla OpenAI,
> what the `OpenRouterAdapter` must handle, and how it maps to the shared
> `CompletionRequest`/`CompletionResponse` types defined in `analysis/OPENAI.md`.


## Table of Contents

1. [API Overview](#1-api-overview)
2. [Authentication & Extra Headers](#2-authentication)
3. [Request Schema — OpenAI + Extensions](#3-request-schema)
4. [Response Schema — OpenAI + Extensions](#4-response-schema)
5. [Streaming](#5-streaming)
6. [Models Endpoint](#6-models-endpoint)
7. [Key Value Proposition for The Bannered Mare](#7-value-proposition)
8. [Key Differences from OpenAI — Summary Table](#8-differences-from-openai)
9. [OpenRouterAdapter Implementation Spec](#9-adapter-spec)
10. [Mapping: Shared Types ↔ OpenRouter API](#10-type-mapping)
11. [Implementation Plan](#11-implementation-plan)


## 1. API Overview

OpenRouter is an **OpenAI-compatible API proxy** that routes requests to 200+ models from
dozens of providers (OpenAI, Anthropic, Google, Meta, Mistral, Cohere, etc.) through a
**single unified endpoint**.

| Property | Value |
|---|---|
| **Base URL** | `https://openrouter.ai/api/v1` |
| **Chat endpoint** | `POST /chat/completions` |
| **Models endpoint** | `GET /models` |
| **Auth** | `Authorization: Bearer <OPENROUTER_API_KEY>` |
| **Compatibility** | OpenAI Chat Completions API (drop-in replacement) |
| **Protocol** | HTTPS, JSON request/response, SSE for streaming |

### 1.1 How It Works

```
Client (The Bannered Mare)
    │
    │  POST /api/v1/chat/completions
    │  Authorization: Bearer or-...
    │  model: "anthropic/claude-sonnet-4"
    │
    ▼
┌──────────────┐
│  OpenRouter   │  ← Translates to provider-native format
│  Proxy Layer  │  ← Handles auth with downstream provider
│               │  ← Manages rate limits, retries, fallbacks
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Anthropic API│  ← Receives native Anthropic API call
│ (or OpenAI,  │
│  Google, etc)│
└──────────────┘
```

### 1.2 Why This Matters for The Bannered Mare

OpenRouter is the **lowest-friction path** to multi-model support. Because it speaks the
OpenAI protocol, the existing OpenAI adapter handles 90% of the work. The OpenRouterAdapter
is a **thin subclass** — not a separate implementation.


## 2. Authentication & Extra Headers

### 2.1 Required Header

```
Authorization: Bearer or-v1-abc123...
```

OpenRouter API keys are prefixed with `or-` (though older keys may use `sk-or-`).
Authentication works identically to OpenAI — a Bearer token in the Authorization header.

### 2.2 Optional Headers (Recommended)

| Header | Type | Description |
|---|---|---|
| `HTTP-Referer` | string (URL) | Your site URL. Used for ranking on openrouter.ai leaderboard. |
| `X-Title` | string | Your app name. Displayed on openrouter.ai rankings and activity. |

Example:

```
Authorization: Bearer or-v1-abc123...
HTTP-Referer: https://the-bannered-mare.app
X-Title: The Bannered Mare
Content-Type: application/json
```

### 2.3 Why These Headers Matter

- `HTTP-Referer` and `X-Title` are **not required** for API access but:
  - They associate usage with your application on the OpenRouter dashboard
  - They contribute to the public model activity leaderboard
  - They help OpenRouter understand usage patterns
- For The Bannered Mare, these should be **configurable** in the provider settings,
  defaulting to a sensible application name

### 2.4 For The Bannered Mare

The Provider model already stores `api_key_env_var` for credential lookup. The extra headers
(`HTTP-Referer`, `X-Title`) should be stored as part of the provider configuration or
drawn from application settings. The `OpenRouterAdapter.build_headers()` override handles
injecting them.


## 3. Request Schema — OpenAI + Extensions

OpenRouter accepts the **full OpenAI Chat Completions request schema** and passes all standard
parameters through to the downstream provider. On top of this, it adds several
OpenRouter-specific fields.

### 3.1 Standard OpenAI Parameters (Pass-Through)

All parameters documented in `analysis/OPENAI.md` Section 3 are supported:

| Parameter | Supported | Notes |
|---|---|---|
| `model` | Yes | Uses OpenRouter model IDs (e.g., `anthropic/claude-sonnet-4`) |
| `messages` | Yes | Standard OpenAI message format |
| `temperature` | Yes | Passed through to underlying provider |
| `top_p` | Yes | Passed through |
| `max_tokens` | Yes | Passed through |
| `max_completion_tokens` | Yes | Passed through for supported models |
| `frequency_penalty` | Yes | Passed through |
| `presence_penalty` | Yes | Passed through |
| `stop` | Yes | Passed through |
| `stream` | Yes | Passed through |
| `stream_options` | Yes | Passed through |
| `n` | Yes | Passed through (provider must support it) |
| `seed` | Yes | Passed through (provider must support it) |
| `response_format` | Yes | Passed through |
| `tools` | Yes | Passed through |
| `tool_choice` | Yes | Passed through |
| `logprobs` | Yes | Passed through (provider must support it) |
| `top_logprobs` | Yes | Passed through |
| `logit_bias` | Yes | Passed through (provider must support it) |
| `reasoning_effort` | Yes | Passed through for reasoning models |

### 3.2 OpenRouter-Specific Extensions

These fields are **added by OpenRouter** and not part of the standard OpenAI spec.

#### 3.2.1 `transforms` — Prompt Transformation

```json
{
  "transforms": ["middle-out"]
}
```

| Value | Description |
|---|---|
| `"middle-out"` | Compresses long prompts that exceed the model's context window by removing middle content while preserving the beginning and end. Avoids context-length errors. |

- Type: `string[]`
- Default: `[]` (no transforms)
- Currently, `"middle-out"` is the only supported transform

#### 3.2.2 `models` — Fallback Model Routing

```json
{
  "model": "anthropic/claude-sonnet-4",
  "models": [
    "anthropic/claude-sonnet-4",
    "openai/gpt-4o",
    "google/gemini-2.0-flash-001"
  ],
  "route": "fallback"
}
```

| Field | Type | Description |
|---|---|---|
| `models` | `string[]` | Ordered list of model IDs to try |
| `route` | `string` | Routing strategy. Currently only `"fallback"` is supported. |

**Behavior:**
- If the primary `model` is unavailable (down, rate-limited, erroring), OpenRouter
  automatically tries the next model in the `models` array
- The `route: "fallback"` strategy tries models in order until one succeeds
- The response `model` field reflects which model actually served the request
- This is transparent to the caller — the response format is identical

**Relevance to The Bannered Mare:** This is extremely valuable for reliability. A roleplay
session should not break because one provider has an outage. The UI could let users
configure a fallback chain.

#### 3.2.3 `provider` — Provider Preferences

```json
{
  "provider": {
    "order": ["Anthropic", "Azure"],
    "require": ["moderation"],
    "allow_fallbacks": true,
    "data_collection": "deny",
    "quantizations": ["fp16", "bf16"],
    "sort": "price",
    "ignore": ["Fireworks"]
  }
}
```

| Field | Type | Description |
|---|---|---|
| `provider.order` | `string[]` | Preferred provider order. OpenRouter tries these first. |
| `provider.require` | `string[]` | Required provider features (e.g., `"moderation"`, `"no-logging"`). |
| `provider.allow_fallbacks` | `boolean` | Whether to fall back to other providers if preferred ones fail. Default `true`. |
| `provider.data_collection` | `string` | `"allow"` or `"deny"` — controls whether providers may train on your data. |
| `provider.quantizations` | `string[]` | Preferred quantization levels: `"fp32"`, `"fp16"`, `"bf16"`, `"int8"`, `"int4"`. |
| `provider.sort` | `string` | Sort providers by: `"price"`, `"throughput"`, `"latency"`. |
| `provider.ignore` | `string[]` | Provider names to never route to. |

**Relevance to The Bannered Mare:** Provider preferences give users fine-grained control:
- RP users who care about quality might prefer `"sort": "throughput"` or specific providers
- Privacy-conscious users can set `"data_collection": "deny"`
- Users can avoid specific providers they've had bad experiences with
- Quantization preferences matter for model quality (fp16 > int4)

#### 3.2.4 Provider-Specific Parameters

Parameters not recognized by OpenRouter are passed through to the downstream provider.
This means Anthropic-specific params (like `top_k`) or provider-specific sampling
parameters work transparently:

```json
{
  "model": "anthropic/claude-sonnet-4",
  "messages": [...],
  "temperature": 0.8,
  "top_k": 40
}
```

The `top_k` parameter is not part of the OpenAI spec but Anthropic supports it, so
OpenRouter passes it through.

### 3.3 Model ID Format

OpenRouter uses a `provider/model` naming convention:

```
anthropic/claude-sonnet-4
openai/gpt-4o
google/gemini-2.0-flash-001
meta-llama/llama-3.1-405b-instruct
mistralai/mistral-large
deepseek/deepseek-r1
```

Some models have multiple providers. The model ID refers to the **model**, not the
provider serving it. Use the `provider` preferences to control which provider serves
a given model.

Suffixes may indicate variants:
- `:free` — free tier (rate-limited, lower priority)
- `:extended` — extended context length version

### 3.4 Complete Request Example

```json
{
  "model": "anthropic/claude-sonnet-4",
  "messages": [
    {"role": "system", "content": "You are a fantasy RPG narrator."},
    {"role": "user", "content": "I enter the dark cave."}
  ],
  "temperature": 0.85,
  "max_tokens": 1024,
  "top_p": 0.95,
  "frequency_penalty": 0.1,
  "stream": true,
  "models": [
    "anthropic/claude-sonnet-4",
    "openai/gpt-4o",
    "google/gemini-2.0-flash-001"
  ],
  "route": "fallback",
  "provider": {
    "sort": "throughput",
    "data_collection": "deny",
    "allow_fallbacks": true
  },
  "transforms": ["middle-out"]
}
```


## 4. Response Schema — OpenAI + Extensions

### 4.1 Non-Streaming Response

The response schema is **identical to OpenAI** with minor additions:

```json
{
  "id": "gen-1234567890abcdef",
  "object": "chat.completion",
  "created": 1700000000,
  "model": "anthropic/claude-sonnet-4",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "The cave entrance looms before you..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 42,
    "completion_tokens": 156,
    "total_tokens": 198
  }
}
```

### 4.2 Differences from OpenAI Response

| Field | OpenAI | OpenRouter | Impact |
|---|---|---|---|
| `id` | `chatcmpl-...` prefix | `gen-...` prefix | ID parsing must not assume prefix |
| `model` | Always the requested model | May differ if fallback was used | Must check actual model used |
| `system_fingerprint` | Present | Usually absent | Don't depend on it |
| `usage` | Standard token counts | Standard counts + optional cost extensions | Parse cost data when available |

### 4.3 Usage Object Extensions

OpenRouter may include additional cost/pricing information in the usage object or
as a separate field, depending on the model and provider. The standard `prompt_tokens`,
`completion_tokens`, and `total_tokens` fields are always present.

Some responses may include a `cost` field (as a float, in USD) at the top level of the
response, representing the total cost of the request. This is not part of the OpenAI
spec but is useful for tracking spend.

### 4.4 Error Responses

OpenRouter uses standard HTTP error codes with an OpenAI-compatible error body:

```json
{
  "error": {
    "message": "This model is currently overloaded. Try again later.",
    "type": "provider_error",
    "code": 503
  }
}
```

| Status | Meaning |
|---|---|
| 400 | Bad request (invalid params, missing model) |
| 401 | Invalid or missing API key |
| 402 | Insufficient credits |
| 403 | Content moderation triggered |
| 408 | Request timeout |
| 429 | Rate limited |
| 502 | Upstream provider error |
| 503 | Model overloaded or unavailable |

**Key difference:** The `402 Payment Required` status is OpenRouter-specific (credit
balance exhausted). The Bannered Mare should map this to a user-friendly "insufficient credits"
message.


## 5. Streaming

### 5.1 Format

Streaming is **identical to OpenAI SSE format**:

```
data: {"id":"gen-abc123","object":"chat.completion.chunk","created":1700000000,"model":"anthropic/claude-sonnet-4","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}

data: {"id":"gen-abc123","object":"chat.completion.chunk","created":1700000000,"model":"anthropic/claude-sonnet-4","choices":[{"index":0,"delta":{"content":"The"},"finish_reason":null}]}

data: {"id":"gen-abc123","object":"chat.completion.chunk","created":1700000000,"model":"anthropic/claude-sonnet-4","choices":[{"index":0,"delta":{"content":" cave"},"finish_reason":null}]}

data: [DONE]
```

### 5.2 Lifecycle

The streaming lifecycle is identical to OpenAI (see `OPENAI.md` Section 6.4):

```
Chunk 1: delta = {role: "assistant", content: ""}     ← role announcement
Chunk 2: delta = {content: "The"}                      ← content token
Chunk 3: delta = {content: " cave"}                    ← content token
...
Chunk N: delta = {}, finish_reason = "stop"            ← termination
data: [DONE]                                           ← stream end signal
```

### 5.3 Stream Options

The `stream_options: { include_usage: true }` parameter is supported, following
the same behavior as OpenAI — an additional chunk with `usage` data is emitted after
the final content chunk.

### 5.4 Implications for The Bannered Mare

Because streaming is identical to OpenAI, the existing `OpenAIAdapter.parse_stream_chunk()`
method works **without modification**. The `OpenRouterAdapter` does not need to override
any streaming logic. The only difference is that chunk `id` fields use the `gen-` prefix
and `model` may reflect a fallback model.


## 6. Models Endpoint

### 6.1 List All Models

```
GET https://openrouter.ai/api/v1/models
```

**No authentication required** for the models list endpoint.

### 6.2 Response Schema

```json
{
  "data": [
    {
      "id": "anthropic/claude-sonnet-4",
      "name": "Anthropic: Claude Sonnet 4",
      "created": 1700000000,
      "description": "Claude Sonnet 4 is Anthropic's...",
      "context_length": 200000,
      "architecture": {
        "tokenizer": "Claude",
        "instruct_type": "claude",
        "modality": "text+image->text"
      },
      "pricing": {
        "prompt": "0.000003",
        "completion": "0.000015",
        "image": "0.0048",
        "request": "0"
      },
      "top_provider": {
        "context_length": 200000,
        "max_completion_tokens": 8192,
        "is_moderated": false
      },
      "per_request_limits": null
    }
  ]
}
```

### 6.3 Model Object Fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Model identifier (`provider/model-name`) |
| `name` | string | Human-readable display name |
| `created` | integer | Unix timestamp of when model was added |
| `description` | string | Markdown description of the model |
| `context_length` | integer | Maximum context window in tokens |
| `architecture.tokenizer` | string | Tokenizer type (e.g., `"Claude"`, `"GPT"`, `"Llama"`) |
| `architecture.instruct_type` | string | Instruction format the model expects |
| `architecture.modality` | string | I/O modality (e.g., `"text->text"`, `"text+image->text"`) |
| `pricing.prompt` | string | Cost per token for input (USD, as decimal string) |
| `pricing.completion` | string | Cost per token for output (USD, as decimal string) |
| `pricing.image` | string | Cost per image input (USD, as decimal string) |
| `pricing.request` | string | Fixed cost per request (USD, as decimal string) |
| `top_provider.context_length` | integer | Context length from the best available provider |
| `top_provider.max_completion_tokens` | integer | Max output tokens from the best provider |
| `top_provider.is_moderated` | boolean | Whether the top provider applies content moderation |
| `per_request_limits` | object \| null | Rate limits specific to this model |

### 6.4 Filtering and Querying

The models endpoint supports query parameters for filtering:

| Parameter | Type | Description |
|---|---|---|
| `supported_parameters` | string | Filter by supported parameter (e.g., `tools`, `temperature`) |

### 6.5 Relevance to The Bannered Mare

The models endpoint is **extremely valuable** for The Bannered Mare:

1. **Auto-discovery:** Instead of manually seeding model records in the database,
   The Bannered Mare can query OpenRouter for available models and present them to users
2. **Pricing display:** The pricing data lets users see cost per token before selecting
   a model — important for users managing their OpenRouter credits
3. **Context length:** Knowing the context window helps the PromptBuilder decide how
   much conversation history to include
4. **Capability detection:** The `architecture.modality` field indicates whether a model
   supports image input, and `supported_parameters` reveals which generation params work
5. **Max output tokens:** `top_provider.max_completion_tokens` informs the default and
   maximum value for the `max_tokens` parameter

This endpoint should be exposed as a service method that the frontend can call to
populate model selection dropdowns.


## 7. Key Value Proposition for The Bannered Mare

### 7.1 Single API Key, All Providers

Without OpenRouter:
```
User needs:
  - OpenAI API key     → for GPT-4o
  - Anthropic API key  → for Claude
  - Google API key     → for Gemini
  - Mistral API key    → for Mistral Large
  - etc.
```

With OpenRouter:
```
User needs:
  - OpenRouter API key → for ALL of the above
```

For self-hosted The Bannered Mare users, this dramatically simplifies setup. One key,
one provider configuration, access to everything.

### 7.2 Automatic Fallbacks

If `anthropic/claude-sonnet-4` is experiencing an outage, the `models` array with
`route: "fallback"` automatically tries the next model. This keeps roleplay sessions
running even when individual providers have issues.

### 7.3 Cost Comparison

The models endpoint provides pricing for every model, enabling a future "cost advisor"
feature in The Bannered Mare that helps users pick the best model for their budget.

### 7.4 Provider Competition

Multiple providers may serve the same model (e.g., `meta-llama/llama-3.1-70b-instruct`
is available through many hosts). OpenRouter routes to the best available provider,
and users can use the `provider` preferences to optimize for price, speed, or latency.

### 7.5 No Translation Overhead for The Bannered Mare

Because OpenRouter speaks the OpenAI protocol, The Bannered Mare gets access to Anthropic,
Google, Meta, and dozens of other models **without implementing their native APIs**.
The `OpenRouterAdapter` is a thin wrapper — the heavy lifting is already done by
`OpenAIAdapter`.


## 8. Key Differences from OpenAI — Summary Table

| Aspect | OpenAI | OpenRouter | Adapter Impact |
|---|---|---|---|
| **Base URL** | `https://api.openai.com/v1` | `https://openrouter.ai/api/v1` | Override `base_url` |
| **Key prefix** | `sk-...` | `or-...` (or `sk-or-...`) | No code change (just config) |
| **Extra headers** | None | `HTTP-Referer`, `X-Title` | Override `build_headers()` |
| **Model IDs** | `gpt-4o`, `o3` | `openai/gpt-4o`, `anthropic/claude-sonnet-4` | No code change (passed through) |
| **Response ID** | `chatcmpl-...` | `gen-...` | No code change (ID is opaque string) |
| **`models` array** | N/A | Fallback model list | Pass via `extra` dict |
| **`route`** | N/A | Fallback strategy | Pass via `extra` dict |
| **`transforms`** | N/A | Prompt transformation | Pass via `extra` dict |
| **`provider`** | N/A | Provider preferences | Pass via `extra` dict |
| **402 error** | N/A | Insufficient credits | Add error mapping |
| **Models endpoint** | `GET /v1/models` (sparse) | `GET /v1/models` (rich: pricing, context, arch) | Add `list_models()` method |
| **Streaming** | SSE `data:` lines | Identical | No override needed |
| **Payload** | OpenAI-native | OpenAI pass-through + extras | Minimal override |

**Bottom line:** 3 things to override: `base_url`, `build_headers()`, and error mapping.
Everything else is inherited from `OpenAIAdapter`.


## 9. OpenRouterAdapter Implementation Spec

### 9.1 File Location

```
src/provider/
  adapters/
    openrouter.py        ← OpenRouterAdapter (this file)
    openai.py            ← OpenAIAdapter (parent class)
    base.py              ← ProviderAdapter ABC
```

### 9.2 Class Design

```python
class OpenRouterAdapter(OpenAIAdapter):
    """
    Adapter for OpenRouter's OpenAI-compatible API.

    Inherits all behavior from OpenAIAdapter and overrides only:
    - build_headers(): adds HTTP-Referer and X-Title
    - build_payload(): injects OpenRouter-specific fields from extra dict
    - list_models(): queries the models endpoint
    - Error mapping for 402 (insufficient credits)
    """

    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
```

### 9.3 `build_headers()` Override

```python
def build_headers(self) -> dict[str, str]:
    headers = super().build_headers()

    referer = self._get_config("http_referer")
    if referer:
        headers["HTTP-Referer"] = referer

    title = self._get_config("x_title")
    if title:
        headers["X-Title"] = title

    return headers
```

The `_get_config()` method reads from the provider's configuration (stored in the
Provider model's settings/metadata column). Fallback defaults:
- `http_referer`: Application URL from app settings, or omitted
- `x_title`: `"The Bannered Mare"` or the configured application name

### 9.4 `build_payload()` Override

```python
def build_payload(self, request: CompletionRequest) -> dict[str, Any]:
    payload = super().build_payload(request)

    if request.extra:
        # OpenRouter-specific fields are passed via CompletionRequest.extra
        openrouter_fields = ("models", "route", "transforms", "provider")
        for field in openrouter_fields:
            if field in request.extra:
                payload[field] = request.extra[field]

    return payload
```

Note: The parent `OpenAIAdapter.build_payload()` already applies `request.extra` via
`payload.update(request.extra)`. However, explicitly handling OpenRouter fields here
makes the intent clear and allows validation/transformation of these fields if needed
in the future. If the parent's `extra` handling is sufficient, this override can be
omitted entirely — the OpenRouter-specific params will pass through automatically.

### 9.5 `list_models()` Method

This is a **new method** not present on the base `ProviderAdapter` or `OpenAIAdapter`,
since model listing is particularly valuable for OpenRouter.

```python
async def list_models(self) -> list[OpenRouterModel]:
    """Fetch available models from OpenRouter.

    Returns:
        List of model objects with pricing, context length, and capabilities.
    """
    url = f"{self.base_url}/models"
    response = await self._client.get(url, headers=self.build_headers())
    response.raise_for_status()
    data = response.json()

    return [
        OpenRouterModel(
            id=m["id"],
            name=m.get("name", m["id"]),
            context_length=m.get("context_length", 0),
            max_completion_tokens=m.get("top_provider", {}).get(
                "max_completion_tokens"
            ),
            pricing_prompt=m.get("pricing", {}).get("prompt"),
            pricing_completion=m.get("pricing", {}).get("completion"),
            modality=m.get("architecture", {}).get("modality", "text->text"),
            description=m.get("description"),
        )
        for m in data.get("data", [])
    ]
```

### 9.6 `OpenRouterModel` Dataclass

```python
@dataclass
class OpenRouterModel:
    """Parsed model info from the OpenRouter models endpoint."""
    id: str
    name: str
    context_length: int
    max_completion_tokens: int | None
    pricing_prompt: str | None       # USD per token as decimal string
    pricing_completion: str | None   # USD per token as decimal string
    modality: str                    # e.g., "text->text", "text+image->text"
    description: str | None = None
```

### 9.7 Error Mapping Override

```python
def _map_error(self, status_code: int, body: dict[str, Any]) -> Exception:
    if status_code == 402:
        return InsufficientCreditsError(
            "OpenRouter credits exhausted. Add credits at openrouter.ai"
        )
    return super()._map_error(status_code, body)
```

### 9.8 What Is NOT Overridden

The following methods are **inherited as-is** from `OpenAIAdapter`:

| Method | Why No Override Needed |
|---|---|
| `complete()` | HTTP call logic is identical |
| `complete_stream()` | SSE parsing is identical |
| `build_url()` | Uses `self.base_url` which is already set to OpenRouter URL |
| `parse_response()` | Response shape is identical to OpenAI |
| `parse_stream_chunk()` | Chunk shape is identical to OpenAI |
| `_format_messages()` | Message format is identical |

This is the primary advantage of OpenRouter: ~90% code reuse with `OpenAIAdapter`.


## 10. Mapping: Shared Types ↔ OpenRouter API

### 10.1 CompletionRequest → OpenRouter Payload

| CompletionRequest Field | OpenRouter Payload Field | Transformation |
|---|---|---|
| `model` | `model` | Direct (use OpenRouter model ID format) |
| `messages` | `messages` | Direct (inherited from OpenAIAdapter) |
| `temperature` | `temperature` | Direct |
| `top_p` | `top_p` | Direct |
| `max_tokens` | `max_tokens` or `max_completion_tokens` | Inherited logic from OpenAIAdapter |
| `stop` | `stop` | Direct |
| `stream` | `stream` | Direct |
| `stream_include_usage` | `stream_options.include_usage` | Inherited |
| `n` | `n` | Direct |
| `frequency_penalty` | `frequency_penalty` | Direct |
| `presence_penalty` | `presence_penalty` | Direct |
| `reasoning_effort` | `reasoning_effort` | Direct |
| `response_format` | `response_format` | Inherited |
| `seed` | `seed` | Direct |
| `tools` | `tools` | Inherited |
| `tool_choice` | `tool_choice` | Inherited |
| `logit_bias` | `logit_bias` | Direct |
| `logprobs` | `logprobs` | Direct |
| `extra["models"]` | `models` | OpenRouter fallback list |
| `extra["route"]` | `route` | OpenRouter routing strategy |
| `extra["transforms"]` | `transforms` | OpenRouter prompt transforms |
| `extra["provider"]` | `provider` | OpenRouter provider preferences |

### 10.2 OpenRouter Response → CompletionResponse

| OpenRouter Response Field | CompletionResponse Field | Transformation |
|---|---|---|
| `id` (`gen-...`) | `id` | Direct (opaque string) |
| `choices[0].message.content` | `content` | Direct |
| `choices[0].finish_reason` | `finish_reason` | `FinishReason` enum mapping |
| `usage.prompt_tokens` | `usage.prompt_tokens` | Direct |
| `usage.completion_tokens` | `usage.completion_tokens` | Direct |
| `usage.total_tokens` | `usage.total_tokens` | Direct |
| `choices[0].message.tool_calls` | `tool_calls` | Inherited parsing |
| `model` | `model` | Direct (may differ from request if fallback used) |
| Full response dict | `raw` | Stored for debugging |

### 10.3 OpenRouter Streaming → CompletionChunk

Identical to OpenAI mapping (see `OPENAI.md` Section 6). No transformation differences.

| OpenRouter Chunk Field | CompletionChunk Field | Notes |
|---|---|---|
| `id` | `id` | `gen-` prefix, same across chunks |
| `choices[0].delta.content` | `delta_content` | Direct |
| `choices[0].delta.role` | `delta_role` | Direct |
| `choices[0].finish_reason` | `finish_reason` | Direct |
| `usage` | `usage` | Only on final chunk with `include_usage` |

### 10.4 Provider-Specific Extra Fields

The `CompletionRequest.extra` dict serves as the pass-through mechanism for
OpenRouter-specific parameters. This is already designed into the shared types:

```python
@dataclass
class CompletionRequest:
    ...
    extra: dict[str, Any] | None = None  # Provider-specific overrides
```

For OpenRouter, the `extra` dict carries:

```python
extra = {
    "models": ["anthropic/claude-sonnet-4", "openai/gpt-4o"],
    "route": "fallback",
    "transforms": ["middle-out"],
    "provider": {
        "sort": "throughput",
        "data_collection": "deny",
        "allow_fallbacks": True,
    },
}
```


## 11. Implementation Plan

### Phase 2, Step 7 (from OPENAI.md Section 15)

The OpenRouter adapter is part of **Phase 2: OpenAI-Compatible Providers**. It depends
on Phase 1 (shared types + OpenAI adapter) being complete.

### Step 7.1: Create the Adapter

```
File: src/provider/adapters/openrouter.py
```

1. Define `OpenRouterAdapter(OpenAIAdapter)` with:
   - Class constant: `DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"`
   - Override: `build_headers()` — inject `HTTP-Referer`, `X-Title`
   - Override: `_map_error()` — handle 402 status
   - New method: `list_models()` — query `/models` endpoint
2. Define `OpenRouterModel` dataclass for parsed model data
3. Register in `ProviderGateway._adapters`:
   ```python
   ProviderType.OPENROUTER: OpenRouterAdapter
   ```

### Step 7.2: Provider Configuration

Ensure the Provider model can store OpenRouter-specific settings:

| Setting | Storage | Example |
|---|---|---|
| API key | `api_key_env_var` (existing) | `"OPENROUTER_API_KEY"` |
| Base URL | `base_url` (existing) | `"https://openrouter.ai/api/v1"` |
| HTTP-Referer | Provider metadata/settings JSON | `"https://the-bannered-mare.app"` |
| X-Title | Provider metadata/settings JSON | `"The Bannered Mare"` |

No schema changes needed if the Provider model already has a JSON settings column.

### Step 7.3: OpenRouter-Specific Error Type

```
File: src/core/exceptions.py
```

Add:
```python
class InsufficientCreditsError(ProviderError):
    """Raised when the API key has insufficient credits (HTTP 402)."""
    pass
```

Map in router layer to HTTP 402 or 503 depending on UX preference.

### Step 7.4: Model Discovery Service (Optional, High Value)

```
File: src/provider/service.py (or src/model_discovery/service.py)
```

A service method that:
1. Detects that the provider is OpenRouter
2. Calls `adapter.list_models()`
3. Returns parsed model list with pricing and capabilities
4. Optionally caches results (models don't change frequently)

This enables a frontend "Browse Models" feature specific to OpenRouter providers.

### Step 7.5: Tests

```
File: tests/provider/adapters/test_openrouter.py
```

| Test | What It Verifies |
|---|---|
| `test_build_headers_includes_extra` | `HTTP-Referer` and `X-Title` present in headers |
| `test_build_headers_without_config` | Headers still valid when referer/title not configured |
| `test_build_payload_with_fallbacks` | `models`, `route` injected into payload |
| `test_build_payload_with_provider_prefs` | `provider` preferences injected |
| `test_build_payload_standard_only` | No OpenRouter fields when `extra` is empty |
| `test_parse_response_gen_prefix` | Handles `gen-` ID prefix correctly |
| `test_parse_response_fallback_model` | Response model may differ from request model |
| `test_error_mapping_402` | 402 mapped to `InsufficientCreditsError` |
| `test_list_models` | Models endpoint returns parsed `OpenRouterModel` list |
| `test_streaming_identical` | Streaming works with inherited parsing |

### Step 7.6: Verification

```bash
# 1. Lint and format
ruff format src/provider/adapters/openrouter.py
ruff check src/provider/adapters/openrouter.py --fix

# 2. Type check
basedpyright

# 3. Tests
pytest tests/provider/adapters/test_openrouter.py -v

# 4. Regenerate OpenAPI spec (if router changes exposed)
python src/core/utils/openapi.py
```

### Estimated Effort

| Component | Lines of Code | Time |
|---|---|---|
| `OpenRouterAdapter` class | ~80-100 | 30 min |
| `OpenRouterModel` dataclass | ~15 | 5 min |
| `InsufficientCreditsError` | ~5 | 2 min |
| Gateway registration | ~2 | 1 min |
| Tests | ~120-150 | 45 min |
| **Total** | **~220-270** | **~1.5 hours** |

This is the lightest adapter in the entire multi-provider system, which is exactly the
point — OpenRouter's OpenAI compatibility means minimal engineering effort for maximum
model coverage.


## Appendix A: OpenRouter Model ID Examples

For reference when testing, these are representative model IDs:

| Model ID | Provider | Notes |
|---|---|---|
| `openai/gpt-4o` | OpenAI | GPT-4o via OpenRouter |
| `openai/gpt-4o-mini` | OpenAI | Cheaper GPT-4o variant |
| `openai/o3` | OpenAI | Reasoning model |
| `anthropic/claude-sonnet-4` | Anthropic | Claude Sonnet 4 |
| `anthropic/claude-haiku-3.5` | Anthropic | Fast, cheap Claude |
| `google/gemini-2.0-flash-001` | Google | Gemini Flash |
| `google/gemini-2.5-pro-preview` | Google | Gemini Pro |
| `meta-llama/llama-3.1-405b-instruct` | Meta (hosted) | Largest open Llama |
| `mistralai/mistral-large` | Mistral | Mistral's flagship |
| `deepseek/deepseek-r1` | DeepSeek | Reasoning model |
| `qwen/qwen-2.5-72b-instruct` | Alibaba | Qwen 2.5 |
| `meta-llama/llama-3.1-8b-instruct:free` | Meta (hosted) | Free tier variant |


## Appendix B: Quick Decision Matrix

"Should I use OpenRouter or a direct provider adapter?"

| Scenario | Recommendation | Why |
|---|---|---|
| User has only one provider (e.g., OpenAI) | Direct adapter | Lower latency, no middleman |
| User wants access to many models | OpenRouter | One key, all models |
| User needs guaranteed lowest latency | Direct adapter | No proxy hop |
| User wants automatic fallbacks | OpenRouter | Built-in `models` + `route` |
| User wants to compare costs | OpenRouter | Models endpoint has pricing |
| User is self-hosting (Ollama) | Direct adapter (Ollama) | Local, no proxy needed |
| User wants maximum privacy | Direct adapter | Data doesn't traverse OpenRouter |
| User wants both cloud + local models | Both | OpenRouter for cloud, Ollama for local |

For The Bannered Mare's typical use case (RP sessions with various cloud models), OpenRouter
is often the best default recommendation for new users.
