# Tool Calling / Function Calling -- ST v1.17.0 vs Candlekeep Core

## Overview

This document compares tool calling (function calling) support between SillyTavern v1.17.0 and Candlekeep Core. SillyTavern has a mature, full-featured tool calling system. Candlekeep Core has partial parameter-level plumbing but no tool calling implementation.

---

## 1. Capability Matrix

| Capability | SillyTavern v1.17.0 | Candlekeep Core |
|---|---|---|
| Tool definition registration | Yes (`ToolManager` class, `ToolDefinition` objects) | No |
| Tool schema format | OpenAI function calling JSON Schema | N/A |
| Sending `tools` in API request | Yes (frontend builds, backend passes through) | Allowlisted in OpenAI adapter; not constructed anywhere |
| Sending `tool_choice` in API request | Yes (`auto`, `none`, `required`, forced name) | Allowlisted in OpenAI adapter; never set |
| `parallel_tool_calls` parameter | Yes (passed to supporting providers) | Allowlisted in OpenAI adapter; never set |
| Provider-specific tool format translation | Yes (6+ provider formats) | No |
| Parsing tool calls from responses | Yes (4 streaming formats, 5 non-streaming formats) | No |
| Tool invocation / execution | Yes (async action functions) | No |
| Multi-turn agentic loop | Yes (recursive `Generate()`, depth limit 5) | No |
| Tool result injection into prompt | Yes (reconstructed as assistant/tool messages) | No |
| Token budgeting for tool schemas | Yes (pre-allocated from context window) | No |
| Structured output via forced tool | Yes (Claude: JSON schema as forced tool call) | No |
| Extension/plugin tool registration API | Yes (context API + slash commands) | No |
| Tool call UI (toast, collapsible details) | Yes | N/A (no frontend) |

---

## 2. What SillyTavern Has

SillyTavern's tool calling system spans five files and roughly 1,500 lines of code across frontend and backend. The key components:

### 2.1 Tool Registration and Definition

Tools are registered via `ToolManager.registerFunctionTool()` with a standard interface: `name`, `description`, `parameters` (JSON Schema), `action` (async function), and optional `formatMessage`, `shouldRegister`, and `stealth` fields. A static `Map<string, ToolDefinition>` holds all registered tools. Extensions and slash commands can register/unregister tools at runtime.

One built-in tool ships: `GenerateImage` from the Stable Diffusion extension.

### 2.2 Provider Translation Layer

The frontend always constructs tools in OpenAI format. The Node.js backend translates per provider:

| Provider | Translation |
|---|---|
| OpenAI / OpenRouter / Groq / xAI / AI21 | Pass-through (`tools`, `tool_choice`) |
| Anthropic Claude | `parameters` -> `input_schema`; `tool_choice` -> `{ type: "auto" }` |
| Google Gemini | `tools` -> `function_declarations`; `tool_choice` -> `functionCallingConfig` with mode mapping |
| MistralAI | Pass-through; tool call IDs sanitized with SHA-512 hash |
| Cohere | Pass-through; `$schema` stripped; text primer injected on assistant tool_calls |
| DeepSeek | Pass-through; empty `required` arrays deleted; dummy `reasoning_content` added |

26 providers are flagged as tool-calling-capable, with 7 doing per-model capability checks at runtime.

### 2.3 Response Parsing

`ToolManager.parseToolCalls()` handles four distinct streaming formats (OpenAI delta, Cohere events, Anthropic content blocks, Gemini functionCall parts). Non-streaming responses are normalized from five provider formats into a uniform `[{id, function: {name, arguments}}]` shape.

### 2.4 Execution Loop

After parsing tool calls from a response, ST:

1. Invokes each tool's `action()` function.
2. Saves invocations as a system message in chat.
3. Recursively calls `Generate()` with `depth + 1`.
4. On the next generation, reconstructs previous tool call/result pairs as proper OpenAI-format messages in the prompt.
5. Repeats until depth reaches `RECURSE_LIMIT` (5) or the LLM stops calling tools.

### 2.5 Token Management

Tool schema definitions are serialized and their token count is reserved from the context budget before chat history is added. This guarantees tool overhead never causes context overflow.

---

## 3. What Candlekeep Core Has

### 3.1 Parameter Allowlists

The OpenAI adapter (`src/provider/adapters/openai.py`) includes three tool-related parameters in its allowlist:

```python
_OPENAI_PARAMS = {
    # ... sampling parameters ...
    "tools",
    "tool_choice",
    "parallel_tool_calls",
    # ...
}
```

The `build_payload` method iterates over the merged parameter dict and forwards any key found in `_OPENAI_PARAMS` to the provider request body. This means if a caller passes `tools` or `tool_choice` through the parameter chain (ModelFamily defaults -> Model overrides -> Preset overrides), those values reach the OpenAI API. The same applies to any OpenAI-compatible provider using the `OpenAIAdapter` (xAI, OpenRouter, Ollama, Custom).

### 3.2 Anthropic Finish Reason Mapping

The Anthropic adapter (`src/provider/adapters/anthropic.py`) maps Anthropic's `tool_use` stop reason to the canonical `tool_calls` finish reason:

```python
_STOP_REASON_MAP: dict[str, str] = {
    "end_turn": "stop",
    "max_tokens": "length",
    "stop_sequence": "stop",
    "tool_use": "tool_calls",
}
```

This mapping exists in the response parser, meaning Candlekeep will correctly report when Anthropic signals a tool-use stop. However, nothing in the system currently acts on this finish reason.

### 3.3 Gemini Malformed Function Call Handling

The Gemini adapter (`src/provider/adapters/gemini.py`) maps `MALFORMED_FUNCTION_CALL` to `stop` in its finish reason map. This is defensive handling only; no tool payloads are ever sent to Gemini.

### 3.4 Model Family Metadata

Model family fixtures track `supports_function_calling` as a boolean in `extra_metadata`:

| Provider | Families with `supports_function_calling: True` |
|---|---|
| Anthropic | 4 (Claude 4.5 Standard, 4.5 Opus, 4.6 Sonnet, 4.6 Opus) |
| OpenAI | 2 (GPT-4o, GPT-4.1) |
| Google | 2 (Gemini 2.5 Flash, Gemini 2.5 Pro) |
| xAI | 4 (Grok 3, Grok 3 Mini, Grok 4, Grok 4 Mini) |
| OpenRouter | 1 (Meta Llama 4 Maverick) |

This metadata is stored in the database and queryable, but is not referenced by any adapter or gateway logic. No code path checks this flag before deciding whether to include tools in a request.

### 3.5 What the Adapters Do Not Do

- **Anthropic adapter**: Does not extract `tools` or `tool_choice` from the parameter dict. Does not translate OpenAI tool schemas into Anthropic's `input_schema` format. Does not handle `tool_use` content blocks in responses.
- **Gemini adapter**: Does not extract tool parameters. Does not translate to `function_declarations` or `functionCallingConfig`. Does not parse `functionCall` parts from responses.
- **All adapters**: `CompletionResponse` and `StreamChunk` have no fields for tool call data. Response parsers extract only text content, reasoning, finish reason, and usage.

---

## 4. Gap Analysis

### 4.1 Request-Side Gaps

| Gap | Severity | Notes |
|---|---|---|
| No tool schema construction | Blocking | Nothing builds `[{type: "function", function: {name, description, parameters}}]` |
| No tool_choice logic | Blocking | No code sets `tool_choice` to `auto` / `required` / specific tool |
| OpenAI pass-through only | Partial | OpenAI adapter would forward `tools`/`tool_choice` if present in params, but Anthropic and Gemini adapters silently drop them |
| No Anthropic tool format translation | Blocking | Anthropic requires `input_schema` instead of `parameters`, and `tool_choice` wrapped in `{type: ...}` |
| No Gemini tool format translation | Blocking | Gemini requires `function_declarations` and `functionCallingConfig` |

### 4.2 Response-Side Gaps

| Gap | Severity | Notes |
|---|---|---|
| `CompletionResponse` has no `tool_calls` field | Blocking | Dataclass only carries `content`, `finish_reason`, `usage`, `reasoning`, `raw` |
| `StreamChunk` has no `tool_calls` field | Blocking | Only `content`, `reasoning`, `finish_reason`, `usage` |
| No tool call parsing in any response parser | Blocking | OpenAI `choices[].message.tool_calls`, Anthropic `tool_use` blocks, Gemini `functionCall` parts -- all ignored |
| No streaming tool call delta assembly | Blocking | ST implements incremental assembly across 4 formats; Candlekeep has no equivalent |
| `tool_use` finish reason mapped but unused | Informational | Anthropic adapter correctly maps it; nothing consumes it |

### 4.3 Execution-Side Gaps

| Gap | Severity | Notes |
|---|---|---|
| No tool registry | Blocking | No equivalent of `ToolManager` or tool definition storage |
| No tool invocation | Blocking | No mechanism to execute a function when the LLM requests one |
| No agentic loop | Blocking | No recursive generation with tool results injected back |
| No tool result message format | Blocking | No construction of `{role: "tool", content: ..., tool_call_id: ...}` messages |
| No token budget for tools | Significant | No pre-allocation of context window space for tool schemas |

---

## 5. Existing Infrastructure That Helps

Despite the gaps, several Candlekeep design decisions reduce the effort required to add tool calling:

1. **Adapter pattern with per-provider `build_payload`**: Each adapter already selectively extracts parameters. Adding tool translation to `AnthropicAdapter.build_payload` and `GeminiAdapter.build_payload` follows the established pattern.

2. **`_OPENAI_PARAMS` allowlist**: The OpenAI adapter already accepts `tools`, `tool_choice`, and `parallel_tool_calls`. For OpenAI-compatible providers, tool payloads would pass through with zero adapter changes.

3. **`CompletionResponse.raw` dict**: The raw provider response is preserved. Even without structured `tool_calls` parsing, a caller can inspect `raw` to extract tool calls manually. This is a viable short-term escape hatch.

4. **`extra_metadata.supports_function_calling` flag**: Model families already declare tool support. This can serve as the runtime gate (equivalent to ST's `isToolCallingSupported()`).

5. **Finish reason mapping**: The Anthropic adapter already translates `tool_use` -> `tool_calls`. Adding the equivalent to OpenAI (`tool_calls` pass-through) and Gemini (`MALFORMED_FUNCTION_CALL` already handled, need `FUNCTION_CALL` mapping) is minimal work.

6. **Stateless adapter design**: Adapters are pure data transformers with no HTTP logic. Adding tool payload construction is a contained change per adapter, with no gateway modifications required for the request side.

---

## 6. Architectural Differences

| Aspect | SillyTavern | Candlekeep Core |
|---|---|---|
| Tool registration | Frontend `ToolManager` class with static registry | N/A (would be a backend service/registry) |
| Tool invocation | Browser-side async functions | Would be server-side (Python async) |
| Multi-provider translation | Backend proxy translates per provider | Adapter pattern translates per provider (same concept, different layer) |
| Token budgeting | Frontend token counter reserves budget | Would need integration with prompt assembly |
| Agentic loop | Recursive `Generate()` with depth counter | Would be a loop in the generation service |
| Extension tools | JS context API + slash commands | Would be a plugin/extension system (not yet designed) |
| UI feedback | Toast notifications, collapsible HTML | N/A (headless backend; frontend responsibility) |
| Structured output via tools | Claude forced tool call fallback | Not needed (Anthropic SDK handles natively when needed) |

The fundamental difference: SillyTavern's tool system is split across frontend (registration, invocation, UI) and backend (provider translation). Candlekeep Core, as a headless backend, would own the entire pipeline server-side -- registration, translation, invocation, and loop orchestration.

---

## 7. Summary

SillyTavern v1.17.0 has a complete tool calling pipeline: registration, provider-specific request translation, multi-format response parsing, execution, and a recursive agentic loop with token budgeting. It supports 26 providers and handles 4 distinct streaming formats.

Candlekeep Core has parameter-level plumbing (OpenAI adapter allowlists `tools`/`tool_choice`/`parallel_tool_calls`, Anthropic adapter maps the `tool_use` stop reason, model families flag `supports_function_calling` in metadata) but no functional tool calling system. The adapter architecture is well-suited for adding provider-specific tool translation, and the `CompletionResponse.raw` field provides an interim escape hatch for reading tool calls from raw provider responses.

---

## Source References

**SillyTavern v1.17.0:**
- `public/scripts/tool-calling.js` -- ToolManager, registration, invocation, parsing (1,143 lines)
- `public/script.js` -- Generation loop, recursive tool call cycle
- `public/scripts/openai.js` -- Prompt builder, token budgeting, tool call message reconstruction
- `src/endpoints/backends/chat-completions.js` -- Provider-specific tool payload translation
- `src/prompt-converters.js` -- Message format conversion for tool roles

**Candlekeep Core:**
- `src/provider/adapters/openai.py` -- `_OPENAI_PARAMS` allowlist (lines 14-34)
- `src/provider/adapters/anthropic.py` -- `_STOP_REASON_MAP` with `tool_use` (line 13-18)
- `src/provider/adapters/gemini.py` -- `_FINISH_REASON_MAP` with `MALFORMED_FUNCTION_CALL` (line 14-24)
- `src/provider/adapters/base.py` -- `CompletionResponse` and `StreamChunk` dataclasses (lines 9-38)
- `src/provider/gateway.py` -- `ProviderGateway` with `_get_effective_parameters` merge chain
- `src/fixtures/families/*.py` -- `supports_function_calling` metadata flags
