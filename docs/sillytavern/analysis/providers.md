# SillyTavern v1.17.0 — LLM Provider Integration System

## Overview

SillyTavern's LLM provider system is a Node.js/Express server-side proxy that sits
between the browser frontend and dozens of upstream LLM APIs. The frontend sends a
single unified request payload to the ST backend; the backend routes, transforms, and
forwards that request to the chosen provider, then normalises the response back into a
common OpenAI-like shape before returning it.

**Key architectural properties:**

- No provider abstraction layer -- each provider is handled by either a dedicated
  handler function or an inline `if/else` branch inside a shared "OpenAI-compatible"
  code path.
- Two completely separate backend subsystems: **Chat Completions** (structured
  message-based) and **Text Completions** (raw prompt string).
- All auth, routing, prompt conversion, and response normalisation live in a single
  ~2 700-line file (`src/endpoints/backends/chat-completions.js`).


## 1. Provider Registry

### 1.1 Chat Completion Sources (CHAT_COMPLETION_SOURCES)

Defined in `src/constants.js:187-212`. Every value is a lowercase string identifier
sent by the frontend in `request.body.chat_completion_source`.

| Constant       | String Value    | Dedicated Handler Function          |
|----------------|-----------------|-------------------------------------|
| OPENAI         | `openai`        | shared OAI-compat path              |
| CLAUDE         | `claude`        | `sendClaudeRequest`                 |
| OPENROUTER     | `openrouter`    | shared OAI-compat path              |
| AI21           | `ai21`          | `sendAI21Request`                   |
| MAKERSUITE     | `makersuite`    | `sendMakerSuiteRequest`             |
| VERTEXAI       | `vertexai`      | `sendMakerSuiteRequest` (shared)    |
| MISTRALAI      | `mistralai`     | `sendMistralAIRequest`              |
| CUSTOM         | `custom`        | shared OAI-compat path              |
| COHERE         | `cohere`        | `sendCohereRequest`                 |
| PERPLEXITY     | `perplexity`    | shared OAI-compat path              |
| GROQ           | `groq`          | shared OAI-compat path              |
| CHUTES         | `chutes`        | `sendChutesRequest`                 |
| ELECTRONHUB    | `electronhub`   | `sendElectronHubRequest`            |
| NANOGPT        | `nanogpt`       | shared OAI-compat path              |
| DEEPSEEK       | `deepseek`      | `sendDeepSeekRequest`               |
| AIMLAPI        | `aimlapi`       | `sendAimlapiRequest`                |
| XAI            | `xai`           | `sendXaiRequest`                    |
| POLLINATIONS   | `pollinations`  | shared OAI-compat path              |
| MOONSHOT       | `moonshot`      | shared OAI-compat path              |
| FIREWORKS      | `fireworks`     | shared OAI-compat path              |
| COMETAPI       | `cometapi`      | shared OAI-compat (DISABLED)        |
| AZURE_OPENAI   | `azure_openai`  | `sendAzureOpenAIRequest`            |
| ZAI            | `zai`           | shared OAI-compat path              |
| SILICONFLOW    | `siliconflow`   | shared OAI-compat path              |

**Total: 23 chat-completion providers.**

### 1.2 Text Completion / Text Generation Types (TEXTGEN_TYPES)

Defined in `src/constants.js:220-236`. These represent self-hosted or text-oriented
backends accessed through a separate router.

| Constant       | String Value     |
|----------------|------------------|
| OOBA           | `ooba`           |
| MANCER         | `mancer`         |
| VLLM           | `vllm`           |
| APHRODITE      | `aphrodite`      |
| TABBY          | `tabby`          |
| KOBOLDCPP      | `koboldcpp`      |
| TOGETHERAI     | `togetherai`     |
| LLAMACPP       | `llamacpp`       |
| OLLAMA         | `ollama`         |
| INFERMATICAI   | `infermaticai`   |
| DREAMGEN       | `dreamgen`       |
| OPENROUTER     | `openrouter`     |
| FEATHERLESS    | `featherless`    |
| HUGGINGFACE    | `huggingface`    |
| GENERIC        | `generic`        |

**Total: 15 text-generation providers.**

Additionally, ST has dedicated endpoint files for:
- **KoboldAI** (legacy API) -- `src/endpoints/backends/kobold.js`
- **NovelAI** -- `src/endpoints/novelai.js`
- **AI Horde** -- `src/endpoints/horde.js`

**Grand total: ~40+ distinct provider integrations across both subsystems.**


## 2. Backend Request Handlers

File: `src/endpoints/backends/chat-completions.js` (2 683 lines).

### 2.1 Routing Pattern

The `POST /generate` endpoint uses a **two-tier dispatch**:

**Tier 1 -- Switch statement (lines 2033-2046):**

Providers with custom request formats are dispatched to dedicated `async` handler
functions:

```js
switch (request.body.chat_completion_source) {
    case CHAT_COMPLETION_SOURCES.CLAUDE:      return await sendClaudeRequest(request, response);
    case CHAT_COMPLETION_SOURCES.AI21:        return await sendAI21Request(request, response);
    case CHAT_COMPLETION_SOURCES.MAKERSUITE:  return await sendMakerSuiteRequest(request, response);
    case CHAT_COMPLETION_SOURCES.VERTEXAI:    return await sendMakerSuiteRequest(request, response);
    case CHAT_COMPLETION_SOURCES.MISTRALAI:   return await sendMistralAIRequest(request, response);
    case CHAT_COMPLETION_SOURCES.COHERE:      return await sendCohereRequest(request, response);
    case CHAT_COMPLETION_SOURCES.DEEPSEEK:    return await sendDeepSeekRequest(request, response);
    case CHAT_COMPLETION_SOURCES.AIMLAPI:     return await sendAimlapiRequest(request, response);
    case CHAT_COMPLETION_SOURCES.XAI:         return await sendXaiRequest(request, response);
    case CHAT_COMPLETION_SOURCES.CHUTES:      return await sendChutesRequest(request, response);
    case CHAT_COMPLETION_SOURCES.ELECTRONHUB: return await sendElectronHubRequest(request, response);
    case CHAT_COMPLETION_SOURCES.AZURE_OPENAI:return await sendAzureOpenAIRequest(request, response);
}
```

12 providers route to dedicated functions.

**Tier 2 -- If/else chain (lines 2054-2321):**

The remaining 11 providers fall through to a massive if/else chain that configures
`apiUrl`, `apiKey`, `headers`, and `bodyParams` variables, then merges them into a
single OpenAI-compatible request body sent to `/chat/completions` (or `/completions`
for text models).

This two-tier pattern means there are effectively two provider archetypes:
1. **Custom-format providers** (Claude, Gemini, Cohere, etc.) that need bespoke
   request bodies.
2. **OpenAI-compatible providers** (OpenRouter, Groq, Perplexity, etc.) that share a
   common request builder with provider-specific parameter overrides.

### 2.2 Dedicated Handler Functions

Each dedicated handler follows the same structural pattern:

1. Resolve API URL (direct or reverse proxy)
2. Retrieve API key from secret store
3. Validate key presence
4. Create AbortController tied to socket close
5. Convert prompt messages into provider-specific format
6. Build request body with provider-specific parameters
7. Send HTTP POST with `node-fetch`
8. If streaming: `forwardFetchResponse(generateResponse, response)` (pipe SSE)
9. If non-streaming: parse JSON, wrap into OAI format, send response
10. Catch errors and return 500


## 3. Prompt Converters

File: `src/prompt-converters.js` (1 445 lines).

SillyTavern's internal prompt format is **ChatML** -- an array of objects with
`{ role, content, name?, tool_calls?, tool_call_id? }`. Converters transform this into
each provider's native format.

### 3.1 Converter Functions

| Function                      | Target Format             | Key Transformations                                                          |
|-------------------------------|---------------------------|-----------------------------------------------------------------------------|
| `convertClaudeMessages()`     | Anthropic Messages API    | Extracts system prompt to top-level array, converts images to base64 source, merges consecutive same-role messages, handles tool_use/tool_result, adds prefill |
| `convertClaudePrompt()`       | Legacy Claude text format | Deprecated. Flattens to `\n\nHuman:`/`\n\nAssistant:` text string           |
| `convertGooglePrompt()`       | Gemini `contents` format  | Renames assistant->model, converts images to inlineData, handles functionCall/functionResponse, manages thought signatures |
| `convertCohereMessages()`     | Cohere V2 chat format     | Prepends names to content, handles tool call deduplication                   |
| `convertMistralMessages()`    | Mistral chat format       | Sanitises tool IDs via SHA-512 hash (9-char), handles prefix mode, fixes tool message ordering |
| `convertAI21Messages()`       | AI21 chat format          | Extracts system prompt, merges alternating turns, prepends names             |
| `convertXAIMessages()`        | xAI chat format           | Prepends character/user names to assistant/system messages                   |
| `convertTextCompletionPrompt()` | Plain text string       | Flattens to `Role: content\n` format, appends `assistant:` postfix          |

### 3.2 Post-Processing Types (PROMPT_PROCESSING_TYPE)

Applied via `postProcessPrompt()` to handle providers that require strict
user/assistant alternation:

| Type          | Behaviour                                                        |
|---------------|------------------------------------------------------------------|
| `merge`       | Squash consecutive same-role messages, flatten multimodal tokens  |
| `merge_tools` | Same as merge, but preserves tool call messages                  |
| `semi`        | Merge + force mid-prompt system messages to user role            |
| `semi_tools`  | Semi + preserve tool calls                                       |
| `strict`      | Semi + inject user placeholder messages for alternation          |
| `strict_tools`| Strict + preserve tool calls                                     |
| `single`      | Force every message to user role (single-turn)                   |

Used by: DeepSeek (`semi_tools`), Perplexity (`strict`), plus any provider configured
via `custom_prompt_post_processing`.

### 3.3 Caching Helpers

Several functions apply prompt caching annotations to messages:

- `cachingAtDepthForClaude()` -- Adds `cache_control: { type: 'ephemeral', ttl }` to
  Claude messages at a configurable depth from the end.
- `cachingAtDepthForOpenRouterClaude()` -- Same logic, adapted for OpenRouter's
  message format (handles string vs array content).
- `cachingSystemPromptForOpenRouter()` -- Adds cache_control to the first system
  message.
- `calculateClaudeBudgetTokens()` -- Maps reasoning effort levels to thinking budget
  tokens (numeric for traditional, string for adaptive on Opus 4.6+).
- `calculateGoogleBudgetTokens()` -- Maps effort levels to Gemini thinking budgets,
  with distinct functions for Flash, Flash Lite, Pro, Gemini 3 Flash, and Gemini 3 Pro.


## 4. Authentication

### 4.1 Secret Management System

File: `src/endpoints/secrets.js` (642 lines).

Secrets are stored as JSON files per-user on disk. The `SecretManager` class provides:

- **Multi-secret per key**: Each secret key can hold an array of `SecretValue` objects.
  Only one is `active` at a time.
- **Rotation**: `rotateSecret(key, id)` activates a specific secret by ID.
- **Masking**: `getMaskedValue()` masks all but the last 3 characters for UI display.
- **Atomic writes**: Uses `write-file-atomic` to prevent corruption.

All 40+ secret keys are defined in `SECRET_KEYS` (lines 8-78):

```js
export const SECRET_KEYS = {
    OPENAI: 'api_key_openai',
    CLAUDE: 'api_key_claude',
    OPENROUTER: 'api_key_openrouter',
    MAKERSUITE: 'api_key_makersuite',
    VERTEXAI: 'api_key_vertexai',
    VERTEXAI_SERVICE_ACCOUNT: 'vertexai_service_account_json',
    MISTRALAI: 'api_key_mistralai',
    COHERE: 'api_key_cohere',
    DEEPSEEK: 'api_key_deepseek',
    XAI: 'api_key_xai',
    GROQ: 'api_key_groq',
    AI21: 'api_key_ai21',
    AZURE_OPENAI: 'api_key_azure_openai',
    // ... 30+ more keys for various providers and services
};
```

### 4.2 Authentication Patterns by Provider

| Pattern                        | Providers                                                              |
|--------------------------------|------------------------------------------------------------------------|
| `Authorization: Bearer <key>`  | OpenAI, OpenRouter, MistralAI, Cohere, Groq, Perplexity, DeepSeek, xAI, AI/ML API, Chutes, ElectronHub, NanoGPT, Pollinations, Moonshot, Fireworks, SiliconFlow, all TEXTGEN_TYPES |
| `x-api-key: <key>`            | Claude (Anthropic native header)                                       |
| `api-key: <key>`              | Azure OpenAI (custom Azure header)                                     |
| `?key=<apiKey>` (query param) | Google AI Studio / MakerSuite                                          |
| `?key=<apiKey>` (express mode)| Vertex AI Express mode                                                 |
| `Authorization: Bearer <jwt>` | Vertex AI Full mode (JWT from service account -> OAuth2 access token)  |
| `X-API-KEY: <key>`            | Mancer, Aphrodite, Tabby (text gen backends)                           |
| No auth required               | Pollinations (optional key), KoboldCpp (local), LlamaCpp (local), Ollama (local) |

### 4.3 Reverse Proxy Support

Nearly every cloud provider supports a reverse proxy override. The pattern is
consistent across handlers:

```js
const apiUrl = new URL(request.body.reverse_proxy || API_DEFAULT).toString();
const apiKey = request.body.reverse_proxy
    ? request.body.proxy_password
    : readSecret(request.user.directories, SECRET_KEYS.PROVIDER);
```

This allows users to route through third-party proxy services that aggregate or relay
API access.

### 4.4 Vertex AI Authentication (Complex)

File: `src/endpoints/google.js:41-82`.

Vertex AI supports three authentication modes:

1. **Express** -- Simple API key (`api_key_vertexai`), passed as query parameter.
2. **Full** -- Service account JSON stored as a secret; ST generates a JWT
   (`generateJWTToken()`), exchanges it for an OAuth2 access token
   (`getAccessToken()`), then uses `Authorization: Bearer <token>`.
3. **Proxy** -- Uses `reverse_proxy` URL with `proxy_password` as Bearer token.


## 5. Parameter Management

### 5.1 Parameter Allowlists

File: `src/constants.js`.

Several providers use allowlists to filter request parameters to only those the API
accepts:

| Constant            | Provider     | Key Count | Notable Unique Params                         |
|---------------------|-------------|-----------|-----------------------------------------------|
| `OLLAMA_KEYS`       | Ollama      | 16        | `num_predict`, `num_ctx`, `num_batch`, `tfs_z`, `typical_p`, `repeat_last_n` |
| `OPENAI_KEYS`       | OpenAI (text) | 13     | `best_of`, `echo`, `logit_bias`               |
| `TOGETHERAI_KEYS`   | TogetherAI  | 12        | `repetition_penalty`                          |
| `INFERMATICAI_KEYS` | InfermaticAI| 19        | `ignore_eos`, `best_of`, `min_tokens`         |
| `VLLM_KEYS`         | vLLM        | 28        | `guided_json`, `guided_regex`, `guided_grammar`, `truncate_prompt_tokens` |
| `FEATHERLESS_KEYS`  | Featherless | 28        | Same as vLLM (identical set)                  |
| `OPENROUTER_KEYS`   | OpenRouter  | 17        | `provider`, `include_reasoning`, `top_a`, `repetition_penalty` |
| `AZURE_OPENAI_KEYS` | Azure OpenAI| 13        | `max_completion_tokens`, `reasoning_effort`, `tools`, `tool_choice` |

The filtering is applied via lodash `_.pickBy()` in the text completions handler:

```js
// text-completions.js:337
request.body = _.pickBy(request.body, (_, key) => TOGETHERAI_KEYS.includes(key));
```

### 5.2 Common Parameters Across Chat Providers

Most chat completion providers receive this common parameter set:

```
model, messages, temperature, max_tokens, top_p, stream,
presence_penalty, frequency_penalty, stop, seed
```

Provider-specific additions:
- **Claude**: `top_k`, `thinking`, `output_config`, `system` (array), `tool_choice`
- **Gemini**: `topK`, `candidateCount`, `safetySettings`, `thinkingConfig`,
  `responseModalities`, `systemInstruction`
- **OpenRouter**: `transforms`, `plugins`, `reasoning`, `min_p`, `top_a`,
  `repetition_penalty`, `provider`, `route`, `safety_settings`, `verbosity`
- **DeepSeek**: `logprobs`, `top_logprobs`
- **Cohere**: `k` (top_k), `p` (top_p), `safety_mode`, `documents`
- **Azure OpenAI**: `reasoning_effort`, `max_completion_tokens`


## 6. Response Normalisation

### 6.1 The OAI Wrapper Pattern

Non-OpenAI providers have their responses wrapped into an OpenAI-compatible structure
before being returned to the frontend. The pattern is:

```js
// Claude (line 389)
const reply = {
    choices: [{ message: { content: responseText } }],
    content: generateResponseJson.content  // original Anthropic content array preserved
};

// Gemini (line 726)
const reply = {
    choices: [{ message: { content: responseText } }],
    responseContent  // original Gemini parts array preserved
};
```

Providers that already return OAI-format responses (OpenRouter, Groq, Fireworks,
NanoGPT, Perplexity, etc.) are forwarded directly without transformation.

### 6.2 Streaming Normalisation

All streaming responses use `forwardFetchResponse()` from `src/util.js`, which pipes
the upstream SSE stream directly to the Express response. The only exception is
**Ollama** in text completion mode, which receives a JSON stream and rewraps each
chunk into SSE `data: {...}\n\n` format via `parseOllamaStream()`.

### 6.3 Special Response Handling

- **Gemini**: Filters out `thought` parts from response content. Extracts text via
  `responseContent.parts.filter(p => !p.thought).map(p => p.text).join('\n\n')`.
- **Gemini blocked prompts**: Checks `promptFeedback.blockReason` and includes it in
  the error message.
- **AI21 / MistralAI**: Already OAI-format; forwarded as-is.
- **Cohere V2**: Returns its own format; forwarded directly (client handles parsing).


## 7. Error Handling

### 7.1 Common Error Handling Pattern

Every handler follows this template:

```js
try {
    const generateResponse = await fetch(url, config);
    if (request.body.stream) {
        forwardFetchResponse(generateResponse, response);
    } else {
        if (!generateResponse.ok) {
            const errorText = await generateResponse.text();
            console.warn(`Provider API returned error: ${status} ${statusText} ${errorText}`);
            const errorJson = tryParse(errorText) ?? { error: true };
            return response.status(500).send(errorJson);
        }
        // ... success path
    }
} catch (error) {
    console.error('Error communicating with Provider:', error);
    if (!response.headersSent) {
        response.send({ error: true });
    } else {
        response.end();
    }
}
```

### 7.2 Rate Limiting Detection

Specific to the shared OAI-compat path (line 2427):

```js
const quota_error = fetchResponse.status === 429
    && errorData?.error?.type === 'insufficient_quota';
response.send({ error: { message }, quota_error: quota_error });
```

This flag is checked by the frontend to display quota-specific UI messages.

### 7.3 Connection Error Handling

The shared path also handles `ECONNREFUSED` specifically (line 2440):

```js
const message = error.code === 'ECONNREFUSED'
    ? `Connection refused: ${error.message}`
    : error.message || 'Unknown error occurred';
response.status(502).send({ error: { message, ...error } });
```

### 7.4 Request Abortion

Every handler creates an `AbortController` tied to the socket close event:

```js
const controller = new AbortController();
request.socket.removeAllListeners('close');
request.socket.on('close', function () {
    controller.abort();
});
```

This ensures upstream API requests are cancelled when the user navigates away or
the connection drops. KoboldCpp additionally sends an explicit abort request to
`/api/extra/abort`.

### 7.5 Header-Sent Safety

All handlers check `response.headersSent` before attempting to send error responses,
preventing the "headers already sent" crash that would occur if streaming had already
started.


## 8. Provider-Specific Features

### 8.1 Claude (Anthropic)

Handler: `sendClaudeRequest()` (lines 209-398).

- **Extended thinking**: Enabled for `claude-3-7`, `claude-opus-4`, `claude-sonnet-4`,
  `claude-haiku-4-5`, `claude-opus-4-5`, `claude-opus-4-6`, `claude-sonnet-4-6`.
  Uses `thinking.type = 'enabled'` with `budget_tokens`, or `thinking.type = 'adaptive'`
  with `output_config.effort` for Opus 4.6+.
- **Adaptive thinking**: Opus 4.6 / Sonnet 4.6 models use effort levels (low/medium/
  high/max) instead of numeric budget tokens.
- **Verbosity control**: Opus 4.5+ supports `output_config.effort` for response
  verbosity (separate from thinking).
- **System prompt caching**: Adds `cache_control: { type: 'ephemeral', ttl }` to the
  last system prompt block and the last tool definition.
- **Depth-based caching**: Configurable via `claude.cachingAtDepth`.
- **Beta headers**: Dynamically assembled array includes `output-128k-2025-02-19`,
  `context-1m-2025-08-07`, `tools-2024-05-16`, `prompt-caching-2024-07-31`,
  `extended-cache-ttl-2025-04-11`, `effort-2025-11-24`.
- **Web search**: Supported on Claude 3.5+ models via `web_search_20250305` tool.
- **Tool use**: Converts OpenAI tool format to Claude's `input_schema` format with
  schema flattening.
- **Structured output**: Implemented as a forced tool call.
- **Limited sampling models**: Opus 4.1+/Sonnet 4.5+ restrict temperature and top_p
  to be mutually exclusive.
- **No-prefill models**: Opus 4.6/Sonnet 4.6 convert trailing assistant messages to
  user role.
- **Image handling**: Images in assistant messages are moved to the next user message
  (Claude API requirement).

### 8.2 Google (Gemini / Vertex AI)

Handler: `sendMakerSuiteRequest()` (lines 405-735). Shared between MakerSuite and
Vertex AI.

- **Safety settings**: All categories set to `OFF` via `GEMINI_SAFETY` (5 categories)
  plus additional `VERTEX_SAFETY` (5 more image-specific categories) for Vertex AI.
- **Thinking configuration**: Gemini 2.5 Flash/Pro and Gemini 3 models support
  `thinkingConfig` with either numeric `thinkingBudget` or string `thinkingLevel`
  depending on model generation.
- **Image generation**: Certain Flash models support `responseModalities: ['text', 'image']`
  with configurable aspect ratio and image size.
- **Tool use / function calling**: Translates OpenAI `tool_choice` to Gemini's
  `functionCallingConfig` (NONE/ANY/AUTO modes).
- **Web search**: Adds `google_search: {}` tool (incompatible with function calling).
- **Thought signatures**: Manages encrypted thought signatures for Gemini 3 models,
  including `skip_thought_signature_validator` bypass magic.
- **Media resolution**: Gemini 3 supports `mediaResolution` config for inline data.
- **Vertex AI URL construction**: Complex URL building with region-specific hostnames,
  project IDs, and both `streamGenerateContent` and `generateContent` endpoints.

### 8.3 OpenRouter

Handled in the shared OAI-compat path (lines 2074-2157).

- **Transforms**: `middle-out` context compression (on/off/auto).
- **Plugins**: Web search plugin (`{ id: 'web' }`).
- **Reasoning**: `reasoning.exclude` flag, `reasoning.effort` level.
- **Provider routing**: `provider.order` array, `provider.allow_fallbacks`,
  `provider.quantizations` array.
- **Fallback routing**: `route: 'fallback'`.
- **Claude caching via OpenRouter**: System prompt caching and depth-based caching
  for Claude models accessed through OpenRouter.
- **Gemini safety settings**: Applied when model matches `google/gemini`.
- **Media embedding**: Audio (as `input_audio`) and video (as `video_url`) content
  conversion.
- **Reasoning signatures**: Converts stored signatures to OpenRouter's
  `reasoning_details` format with provider-specific format identifiers
  (`google-gemini-v1`, `anthropic-claude-v1`, `openai-responses-v1`,
  `xai-responses-v1`).
- **Cacheable model detection**: `isOpenRouterModelCacheable()` queries the
  OpenRouter `/models` API to check if `pricing.input_cache_write` is available.
- **Custom headers**: `HTTP-Referer: https://sillytavern.app`,
  `X-Title: SillyTavern`.

### 8.4 DeepSeek

Handler: `sendDeepSeekRequest()` (lines 1013-1116).

- **Reasoner models**: Detects `-reasoner` suffix to add `reasoning_content` fields
  to tool calls via `addReasoningContentToToolCalls()`.
- **Prompt processing**: Uses `SEMI_TOOLS` post-processing for strict alternation.
- **Empty required arrays**: Strips empty `required: []` from tool parameters
  (DeepSeek API rejects them).

### 8.5 xAI (Grok)

Handler: `sendXaiRequest()` (lines 1123-1222).

- **Reasoning effort**: Binary mapping -- `high` stays `high`, everything else maps
  to `low`.
- **JSON schema**: Full `json_schema` response format support.
- **Multimodal detection**: Uses `/language-models` endpoint instead of `/models` for
  modality information, with a hardcoded override for `grok-4-0709`.

### 8.6 Azure OpenAI

Handler: `sendAzureOpenAIRequest()` (lines 1547-1634).

- **Parameter allowlist**: Uses `AZURE_OPENAI_KEYS` for strict parameter filtering.
- **Auth header**: Uses `api-key` header (not `Authorization: Bearer`).
- **URL construction**: `{base_url}/openai/deployments/{deployment}/chat/completions?api-version={version}`.
- **Reasoning effort**: Applies `OPENAI_REASONING_EFFORT_MODELS` check and
  `OPENAI_REASONING_EFFORT_MAP` translation.
- **Status check**: Performs a two-step probe -- GET `/models` for basic connectivity,
  then POST a minimal chat completion to detect the underlying model ID.

### 8.7 Moonshot

Handled in the shared OAI-compat path (lines 2273-2284).

- **Thinking mode**: `thinking.type: 'enabled'/'disabled'` based on
  `include_reasoning` flag.
- **Assistant prefill**: `addAssistantPrefix()` with `partial` property when not using
  JSON schema.

### 8.8 Z.AI

Handled in the shared OAI-compat path (lines 2293-2307).

- **Dual endpoints**: `API_ZAI_COMMON` for general use, `API_ZAI_CODING` for coding
  tasks.
- **Accept-Language header**: Explicitly sets `en-US,en`.
- **Thinking mode**: Same pattern as Moonshot.

### 8.9 NanoGPT

Handled in the shared OAI-compat path (lines 2228-2256).

- **Web search**: Appends `:online` suffix to model name.
- **Reasoning effort mapping**: Custom `NANOGPT_REASONING_EFFORT_MAP` shifts all
  levels down one notch (e.g., `max` -> `high`, `high` -> `medium`).
- **Claude caching via NanoGPT**: Passes `cache_control.enabled` and `ttl` when
  model matches a Claude pattern.

### 8.10 Pollinations

Handled in the shared OAI-compat path (lines 2257-2272).

- **Random seed**: Generates a random seed if none provided
  (`Math.floor(Math.random() * 99999999)`).
- **Model listing**: Unique API that returns a flat array (not `{ data: [] }`),
  requiring rewrapping.

### 8.11 Custom Provider

Handled in the shared OAI-compat path (lines 2162-2179).

- **YAML-based customisation**: `custom_include_headers` and `custom_include_body`
  (merged via `mergeObjectWithYaml()`), `custom_exclude_body` (filtered via
  `excludeKeysByYaml()`).
- **No auth requirement**: Key is optional.


## 9. Text Completion Backends

File: `src/endpoints/backends/text-completions.js` (646 lines).

### 9.1 Architecture

Completely separate from the chat completions subsystem. Uses user-provided
`api_server` URLs (self-hosted endpoints) rather than hardcoded API base URLs.

### 9.2 Endpoint Routing

The `POST /generate` handler uses a switch statement to determine the URL path:

```
GENERIC, OOBA, VLLM, APHRODITE, TABBY, KOBOLDCPP,
    TOGETHERAI, INFERMATICAI, HUGGINGFACE     -> /v1/completions
DREAMGEN                                      -> /api/openai/v1/completions
MANCER                                        -> /oai/v1/completions
LLAMACPP                                      -> /completion
OLLAMA                                        -> /api/generate
OPENROUTER                                    -> /v1/chat/completions
```

### 9.3 Parameter Filtering

Each provider gets its parameters filtered through its allowlist:

```js
if (apiType === TEXTGEN_TYPES.TOGETHERAI) {
    request.body = _.pickBy(request.body, (_, key) => TOGETHERAI_KEYS.includes(key));
}
```

### 9.4 Ollama Special Handling

Ollama uses a non-OpenAI format (`/api/generate`) with parameters nested under
`options`:

```js
args.body = JSON.stringify({
    model: request.body.model,
    prompt: request.body.prompt,
    stream: request.body.stream ?? false,
    keep_alive: keepAlive,
    raw: true,
    options: _.pickBy(request.body, (_, key) => OLLAMA_KEYS.includes(key)),
});
```

Streaming responses are parsed from Ollama's newline-delimited JSON into SSE format
via `parseOllamaStream()`.

### 9.5 Additional Sub-Routers

- `/ollama/download` -- Pull/download Ollama models.
- `/ollama/caption-image` -- Image captioning via Ollama.
- `/llamacpp/props` -- Query llama.cpp server properties.
- `/llamacpp/slots` -- Manage KV cache slots (info/save/restore/erase).
- `/tabby/download` -- Download models via TabbyAPI (requires admin permission).

### 9.6 KoboldAI Legacy Backend

File: `src/endpoints/backends/kobold.js`.

Uses the original KoboldAI generation API with parameters like `rep_pen`,
`rep_pen_range`, `sampler_order`, `mirostat`, `grammar`, etc. Supports streaming via
`/extra/generate/stream` and explicit abort via `/extra/abort`. Includes a retry loop
with up to 50 attempts for queue-based generation.


## 10. Model Management

### 10.1 Model Discovery per Provider

The `POST /status` endpoint in chat-completions.js handles model listing. Each
provider has its own discovery path:

| Provider       | Endpoint                          | Response Normalisation                        |
|----------------|-----------------------------------|-----------------------------------------------|
| OpenAI         | `{url}/models`                    | Standard `{ data: [{ id }] }`                |
| OpenRouter     | `openrouter.ai/api/v1/models`     | Enriched with pricing and context_length info |
| MakerSuite     | `{url}/{version}/models?key=`     | Filters by `supportedGenerationMethods.includes('generateContent')`, strips `models/` prefix |
| Vertex AI      | Complex URL per auth mode         | Same as MakerSuite post-auth                  |
| Azure OpenAI   | GET `/openai/models` + POST probe | Returns detected model ID from a minimal completion request |
| Cohere         | `api.cohere.ai/v1/models`         | Rewraps `models[]` to `data[].id = model.name` |
| Pollinations   | `gen.pollinations.ai/text`        | Rewraps flat array: `{ id: model.name }`      |
| Chutes         | `llm.chutes.ai/v1/models`         | Remaps `pricing.prompt/completion` to `input/output` |
| NanoGPT        | `nano-gpt.com/api/v1/models?detailed=true` | Standard format                   |
| SiliconFlow    | `/models?type=text&sub_type=chat` | Standard format (with query filter)           |
| Most others    | `{url}/models`                    | Standard `{ data: [{ id }] }`                |

### 10.2 Text Completion Model Discovery

Uses a similar switch-based URL construction per `TEXTGEN_TYPE`:

```
OOBA, VLLM, etc.  -> /v1/models
DREAMGEN           -> /api/openai/v1/models
MANCER             -> /oai/v1/models
TABBY              -> /v1/model/list
TOGETHERAI         -> /api/models?&info
OLLAMA             -> /api/tags
HUGGINGFACE        -> /info
```

Ooba additionally queries `/v1/internal/model/info` for the loaded model name.
TabbyAPI queries `/v1/model` for the currently loaded model.

### 10.3 Multimodal Model Detection

A separate sub-router `/multimodal-models/` provides per-provider vision model
detection:

| Provider     | Method                                                          |
|--------------|-----------------------------------------------------------------|
| Pollinations | Filter by `input_modalities.includes('image')`                  |
| AI/ML API    | Filter by `features.includes('openai/chat-completion.vision')` |
| NanoGPT      | Filter by `capabilities.vision`                                 |
| ElectronHub  | Filter by `metadata.vision`                                     |
| Chutes       | Filter by `input_modalities.includes('image')`                  |
| MistralAI    | Filter by `capabilities.vision`                                 |
| xAI          | Uses `/language-models` endpoint + hardcoded exception          |
| Moonshot     | Filter by `supports_image_in`                                   |
| OpenRouter   | Filter by `architecture.input_modalities.includes('image')`     |


## 11. Additional Headers System

File: `src/additional-headers.js` (250 lines).

Text generation backends use a dispatcher map to inject auth headers per provider type:

```js
const headerGetters = {
    [TEXTGEN_TYPES.MANCER]: getMancerHeaders,      // X-API-KEY + Bearer
    [TEXTGEN_TYPES.VLLM]: getVllmHeaders,          // Bearer
    [TEXTGEN_TYPES.APHRODITE]: getAphroditeHeaders, // X-API-KEY + Bearer
    [TEXTGEN_TYPES.TABBY]: getTabbyHeaders,         // x-api-key + Bearer
    [TEXTGEN_TYPES.TOGETHERAI]: getTogetherAIHeaders, // Bearer
    [TEXTGEN_TYPES.OOBA]: getOobaHeaders,           // Bearer
    // ... 8 more
};
```

Additionally, `requestOverrides` from config allows host-based header injection:
```js
const overrideHeaders = requestOverrides?.find(e => e.hosts?.includes(urlHost))?.headers;
```


## 12. Quantitative Summary

| Metric                                   | Count  |
|------------------------------------------|--------|
| Chat completion provider sources         | 23     |
| Text generation provider types           | 15     |
| Additional dedicated backends            | 3 (KoboldAI, NovelAI, AI Horde) |
| Dedicated handler functions              | 12     |
| Prompt converter functions               | 8      |
| Secret key definitions                   | 40+    |
| Parameter allowlist arrays               | 8      |
| Lines in chat-completions.js             | 2 683  |
| Lines in text-completions.js             | 646    |
| Lines in prompt-converters.js            | 1 445  |
| Lines in constants.js                    | 558    |
| Lines in additional-headers.js           | 250    |
| Lines in secrets.js                      | 642    |
| Total lines across core LLM files       | ~6 224 |


## 13. Key File Reference

| File Path                                              | Purpose                          |
|--------------------------------------------------------|----------------------------------|
| `src/constants.js`                                     | Provider enums, parameter allowlists, safety settings |
| `src/endpoints/backends/chat-completions.js`           | All chat completion routing, handlers, model listing |
| `src/endpoints/backends/text-completions.js`           | Text completion routing, Ollama/LlamaCpp/Tabby sub-routers |
| `src/endpoints/backends/kobold.js`                     | Legacy KoboldAI backend          |
| `src/prompt-converters.js`                             | All prompt format conversions and caching helpers |
| `src/endpoints/secrets.js`                             | Secret storage, rotation, masking |
| `src/additional-headers.js`                            | Auth header injection for text gen backends |
| `src/endpoints/google.js`                              | Vertex AI auth (JWT/OAuth2), Google API config |
| `src/endpoints/openrouter.js`                          | OpenRouter model discovery, multimodal, image gen |
| `src/endpoints/novelai.js`                             | NovelAI text gen + image gen     |
| `src/endpoints/horde.js`                               | AI Horde distributed inference   |
