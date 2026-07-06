# SillyTavern v1.17.0 — Tool Calling / Function Calling System

## Overview

SillyTavern implements a full-featured tool calling (function calling) system that allows LLMs to invoke registered tools, receive results, and continue generating with that context. The system is designed to work across multiple providers with provider-specific format translations handled transparently on the backend.

The generation loop is recursive: the model may request a tool, the `ToolManager` runs it, the
result is fed back, and generation repeats until the model returns a plain answer:

<Figure tag="Figure 1" title="The tool-call recursion cycle" id="fig-tool-loop">
<svg viewBox="0 0 660 470" role="img" aria-label="Tool calling recursion loop" style="font-family:var(--vp-font-family-base)">
  <defs>
    <marker id="tbm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-arrow)"/>
    </marker>
  </defs>
  <g text-anchor="middle">
    <rect x="200" y="16" width="260" height="46" rx="10" fill="var(--tbm-dgm-surface-3)" stroke="var(--tbm-dgm-border-strong)"/>
    <text x="330" y="44" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">Register tools (ToolManager)</text>
    <rect x="200" y="96" width="260" height="48" rx="10" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/>
    <text x="330" y="118" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">Generate with tools</text>
    <text x="330" y="134" font-size="10" fill="var(--tbm-dgm-ink-2)">data.tools · tool_choice = auto</text>
    <rect x="470" y="188" width="170" height="48" rx="10" fill="var(--tbm-dgm-data-soft)" stroke="var(--tbm-dgm-data)"/>
    <text x="555" y="210" font-size="12" font-weight="700" fill="var(--tbm-dgm-ink)">Final response</text>
    <text x="555" y="226" font-size="10" fill="var(--tbm-dgm-ink-2)">no tool_call — done</text>
    <rect x="170" y="278" width="320" height="46" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <text x="330" y="306" font-size="12" fill="var(--tbm-dgm-ink)">ToolManager runs action(params)</text>
    <rect x="170" y="352" width="320" height="46" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <text x="330" y="380" font-size="12" fill="var(--tbm-dgm-ink)">Append result (role: tool) to messages</text>
  </g>
  <polygon points="330,158 404,192 330,226 256,192" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-accent)"/>
  <text x="330" y="196" text-anchor="middle" font-size="11.5" font-weight="600" fill="var(--tbm-dgm-ink)">tool_call?</text>
  <g stroke="var(--tbm-dgm-arrow)" stroke-width="1.6" fill="none" marker-end="url(#tbm-ah)">
    <path d="M330 62 L330 94"/>
    <path d="M330 144 L330 156"/>
    <path d="M404 192 L468 192"/>
    <path d="M330 226 L330 276"/>
    <path d="M330 324 L330 350"/>
    <path d="M170 375 L96 375 L96 120 L198 120"/>
  </g>
  <g font-size="10.5" fill="var(--tbm-dgm-ink-2)">
    <text x="424" y="184">no</text>
    <text x="342" y="250">yes</text>
    <text x="84" y="248" text-anchor="middle" transform="rotate(-90 84 248)">generate again</text>
  </g>
</svg>
<template #caption>

**Recurse until there's nothing left to call.** `ToolManager.registerFunctionToolsOpenAI` sets
`tool_choice = 'auto'`; if the model emits a `tool_call`, the manager runs the matching
`action(params)`, appends the result as a `tool`-role message, and re-generates — looping until
a response arrives with no tool call.

</template>
</Figure>

**Key files:**

| File | Role |
|------|------|
| `public/scripts/tool-calling.js` (1,143 lines) | Core `ToolManager` class -- registration, invocation, parsing, UI |
| `public/script.js` | Generation loop -- orchestrates the tool call recursion cycle |
| `public/scripts/openai.js` | Chat completion prompt builder -- token budgeting, message reconstruction |
| `src/endpoints/backends/chat-completions.js` | Backend proxy -- translates tools for each provider API |
| `src/prompt-converters.js` | Message format conversion -- tool_calls/tool messages per provider |


## 1. Tool Registration

### 1.1 The ToolDefinition Class

Every tool is wrapped in a `ToolDefinition` instance with private fields:

```js
// public/scripts/tool-calling.js:114-183
class ToolDefinition {
    #name;          // Unique identifier, e.g. "GenerateImage"
    #displayName;   // Human-friendly name, e.g. "Generate Image"
    #description;   // LLM-facing description of what the tool does
    #parameters;    // JSON Schema (draft-04) for the tool's parameters
    #action;        // async function(params) => result
    #formatMessage; // optional: async function(params) => toast string
    #shouldRegister;// optional: async function() => boolean (dynamic opt-out)
    #stealth;       // boolean: if true, result is hidden from chat, no follow-up gen
}
```

### 1.2 The ToolRegistration Interface

Tools are registered via `ToolManager.registerFunctionTool()` which accepts a single object:

```js
// public/scripts/tool-calling.js:33-43 (typedef)
/**
 * @typedef {object} ToolRegistration
 * @property {string} name
 * @property {string} displayName
 * @property {string} description
 * @property {object} parameters         // JSON Schema
 * @property {function} action           // async (params) => any
 * @property {function} [formatMessage]  // async (params) => string
 * @property {function} [shouldRegister] // async () => boolean
 * @property {boolean} [stealth]         // default false
 */
```

Duplicate names trigger a console warning and overwrite the previous definition (line 274-276).

### 1.3 The Tool Registry

The registry is a simple static `Map<string, ToolDefinition>`:

```js
// public/scripts/tool-calling.js:246
static #tools = new Map();
```

Tools can be registered and unregistered at any time during the session lifecycle. The `registerFunctionToolsOpenAI` method (line 399-417) iterates all tools, calls `shouldRegister()` on each, and populates the generation request's `data.tools` array and sets `data.tool_choice = 'auto'`.

### 1.4 OpenAI-Format Tool Schema

The canonical wire format follows OpenAI's function calling convention:

```js
// public/scripts/tool-calling.js:189-200
toFunctionOpenAI() {
    return {
        type: 'function',
        function: {
            name: this.#name,
            description: this.#description,
            parameters: this.#parameters,   // JSON Schema object
        },
    };
}
```

This OpenAI format is the single internal representation. Provider-specific translations happen server-side.


## 2. Built-in Tools

### 2.1 Image Generation Tool ("GenerateImage")

The only built-in tool ships with the Stable Diffusion extension:

```js
// public/scripts/extensions/stable-diffusion/index.js:5414-5441
ToolManager.registerFunctionTool({
    name: 'GenerateImage',
    displayName: 'Generate Image',
    description: 'Generate an image from a given text prompt. '
        + 'Use when a user asks to generate an image, imagine a concept...',
    parameters: Object.freeze({
        $schema: 'http://json-schema.org/draft-04/schema#',
        type: 'object',
        properties: {
            prompt: {
                type: 'string',
                description: extension_settings.sd.prompts[generationMode.TOOL]
                    || promptTemplates[generationMode.TOOL],
            },
        },
        required: ['prompt'],
    }),
    action: async (args) => {
        const url = await generatePicture(initiators.tool, {}, args.prompt);
        return encodeURI(url);
    },
});
```

This tool is conditionally registered based on `extension_settings.sd.function_tool`. If disabled, `ToolManager.unregisterFunctionTool('GenerateImage')` is called (line 5411).

### 2.2 No Other Built-in Tools

SillyTavern ships with no other built-in function tools. All additional tools come from extensions or user-defined slash commands.


## 3. Provider Integration

### 3.1 Supported Providers (26 total)

The `isToolCallingSupported()` method (lines 607-668) defines which providers support tool calling:

**Always supported** (hardcoded list at lines 642-666):
OpenAI, Custom, MistralAI, Claude (Anthropic), OpenRouter, AI/ML API, Groq, Cohere, DeepSeek, MakerSuite (Google AI Studio), VertexAI, AI21, xAI, Pollinations, Moonshot, Fireworks, CometAPI, Chutes, ElectronHub, Azure OpenAI, ZAI, SiliconFlow, NanoGPT.

**Conditionally supported** (based on model capabilities, lines 623-639):
- Pollinations: checks `currentModel.tools`
- Fireworks: checks `currentModel.supports_tools`
- OpenRouter: checks `currentModel.supported_parameters?.includes('tools')`
- MistralAI: checks `currentModel.capabilities?.function_calling`
- AI/ML API: checks `currentModel.features?.includes('openai/chat-completion.function')`
- Chutes: checks `currentModel.supported_features?.includes('tools')`
- ElectronHub: checks `currentModel.metadata?.function_call`

### 3.2 Tool Calling Restrictions

Tool calls are blocked for certain generation types (line 680):

```js
const noToolCallTypes = ['impersonate', 'quiet', 'continue'];
```

Tool calls also require the `function_calling` UI toggle to be enabled and the prompt post-processing mode must allow tool messages. The allowed modes are `NONE`, `MERGE_TOOLS`, `SEMI_TOOLS`, and `STRICT_TOOLS` (lines 616-619).

### 3.3 Backend Translation per Provider

The frontend always sends tools in OpenAI format. The backend (`src/endpoints/backends/chat-completions.js`) translates for each provider:

#### Claude (Anthropic) — lines 263-285

```js
requestBody.tools = request.body.tools
    .filter(tool => tool.type === 'function')
    .map(tool => tool.function)
    .map(fn => ({
        name: fn.name,
        description: fn.description,
        input_schema: flattenSchema(fn.parameters, ...)
    }));
requestBody.tool_choice = { type: request.body.tool_choice }; // e.g. { type: 'auto' }
```

Claude uses `input_schema` instead of `parameters`, and wraps `tool_choice` in an object with a `type` field.

#### Google Gemini / Vertex AI — lines 513-536

```js
const functionDeclarations = [];
for (const tool of request.body.tools) {
    if (tool.type === 'function') {
        // Remove $schema key (Gemini doesn't accept it)
        delete tool.function.parameters.$schema;
        // Remove empty properties objects
        if (Object.keys(tool.function.parameters.properties).length === 0) {
            delete tool.function.parameters;
        }
        functionDeclarations.push(tool.function);
    }
}
tools.push({ function_declarations: functionDeclarations });
```

Gemini uses `function_declarations` inside a `tools` array. The `tool_choice` is translated to `functionCallingConfig` (lines 582-604):

| OpenAI `tool_choice` | Gemini `functionCallingConfig.mode` |
|---|---|
| `'none'` | `'NONE'` |
| `'required'` | `'ANY'` |
| `'auto'` | `'AUTO'` |
| `{ function: { name } }` | `{ mode: 'ANY', allowedFunctionNames: [name] }` |

#### MistralAI — lines 854-857

Tools are passed through directly in OpenAI format. MistralAI tool call IDs are sanitized with SHA-512 hashing truncated to 9 chars (prompt-converters.js line 711).

#### Cohere — lines 930-937

Tools are passed through in OpenAI format. The `$schema` key is stripped from parameters. In prompt conversion, Cohere requires special handling: if an assistant message has `tool_calls`, a text content primer is injected (prompt-converters.js lines 394-401):

```js
msg.content = `I'm going to call a tool for that: ${msg.tool_calls.map(tc => tc?.function?.name).join(', ')}`;
```

#### DeepSeek — lines 1036-1047

Tools are passed in OpenAI format. Empty `required` arrays are deleted (DeepSeek rejects them). A separate prompt converter function adds a dummy `reasoning_content: ''` field to messages with `tool_calls` (prompt-converters.js lines 1371-1383).

#### OpenAI / OpenRouter / Groq / AI21 / xAI / Custom / Others — lines 2357-2360

Most providers pass tools straight through in OpenAI format:

```js
bodyParams['tools'] = request.body.tools;
bodyParams['tool_choice'] = request.body.tool_choice;
```

### 3.4 Schema Flattening

The `flattenSchema()` function (`src/util.js:1424-1472`) resolves `$ref` / `$defs` references in JSON schemas and strips unsupported keys for Google APIs (`default`, `additionalProperties`, `exclusiveMinimum`, `propertyNames`). It also removes the `$schema` key from the top level.


## 4. Message Format Conversion for Tool Calls

### 4.1 Claude Message Conversion

`convertClaudeMessages()` in `src/prompt-converters.js:197` transforms OpenAI-format tool messages into Anthropic's content block format:

**Assistant tool_calls to Claude:**
```js
// Lines 235-242
message.content = message.tool_calls.map((tc) => ({
    type: 'tool_use',
    id: tc.id,
    name: tc.function.name,
    input: parse(tc.function.arguments),
}));
```

**Tool results to Claude:**
```js
// Lines 244-251
message.role = 'user';
message.content = [{
    type: 'tool_result',
    tool_use_id: message.tool_call_id,
    content: message.content,
}];
```

### 4.2 Google Gemini Message Conversion

`convertGooglePrompt()` in `src/prompt-converters.js:454-556` converts tool call messages into Gemini's `functionCall`/`functionResponse` parts:

**Assistant tool_calls to Gemini:**
```js
// Lines 545-556
parts.push({
    functionCall: {
        name: toolCall.function.name,
        args: tryParse(toolCall.function.arguments),
    },
    ...(toolCall.signature ? { thoughtSignature: toolCall.signature } : {}),
});
```

**Tool results to Gemini:**
```js
// Lines 537-544
parts.push({
    functionResponse: {
        name: toolNameMap[part.tool_call_id],
        response: { name: name, content: part.content },
    },
});
```

### 4.3 Prompt Post-Processing Modes and Tool Messages

The `mergeMessages()` function (`src/prompt-converters.js:823-946`) has a `tools` boolean parameter that controls whether tool-related fields survive post-processing:

- When `tools = false`: `tool_calls` and `tool_call_id` are deleted from all messages; `tool` role messages are converted to `user` role.
- When `tools = true`: tool messages are preserved as-is with proper roles.

The post-processing mode names indicate tool support:

| Mode | Tools Preserved |
|------|----------------|
| `NONE` (no post-processing) | Yes (messages pass through raw) |
| `MERGE` | No |
| `MERGE_TOOLS` | Yes |
| `SEMI` | No |
| `SEMI_TOOLS` | Yes |
| `STRICT` | No |
| `STRICT_TOOLS` | Yes |
| `SINGLE` | No |


## 5. Execution Flow

### 5.1 Tool Call Lifecycle

The complete flow from user message to tool result injection:

```
User sends message
    |
    v
Generate() called in public/script.js
    |
    v
canPerformToolCalls check (line 4412):
  - Not a dry run
  - isToolCallingSupported() (correct API, enabled, model supports it)
  - depth < RECURSE_LIMIT (5)
    |
    v
ToolManager.registerFunctionToolsOpenAI(generate_data) adds tools + tool_choice to request
    |
    v
Request sent to backend -> provider API
    |
    v
Response arrives (streaming or non-streaming)
    |
    v
ToolManager.parseToolCalls() aggregates tool call deltas during streaming
    |
    v
ToolManager.hasToolCalls(data) checks if response contains tool calls
    |
    v
ToolManager.invokeFunctionTools(data) executes each tool's action function
    |
    v
ToolManager.saveFunctionToolInvocations() saves to chat as system message
    |
    v
Generate() calls itself recursively with depth + 1
```

### 5.2 Streaming Path (public/script.js lines 5319-5347)

```js
const isStreamWithToolCalls = streamingProcessor
    && Array.isArray(streamingProcessor.toolCalls)
    && streamingProcessor.toolCalls.length;

if (canPerformToolCalls && isStreamFinished && isStreamWithToolCalls) {
    const hasToolCalls = ToolManager.hasToolCalls(streamingProcessor.toolCalls);
    // If LLM produced empty text + no reasoning, delete the placeholder message
    const shouldDeleteMessage = type !== 'swipe'
        && ['', '...'].includes(lastMessage?.mes)
        && !lastMessage?.extra?.reasoning
        && ['', '...'].includes(streamingProcessor?.result);
    hasToolCalls && shouldDeleteMessage && await deleteLastMessage();

    const invocationResult = await ToolManager.invokeFunctionTools(
        streamingProcessor.toolCalls,
        { reasoningText: streamingProcessor.reasoningHandler.reasoning }
    );

    // ... error handling ...

    depth = depth + 1;
    await ToolManager.saveFunctionToolInvocations(invocationResult.invocations);
    return Generate('normal', { ...opts, depth }, dryRun);  // RECURSIVE CALL
}
```

### 5.3 Non-Streaming Path (public/script.js lines 5452-5471)

```js
if (canPerformToolCalls) {
    const hasToolCalls = ToolManager.hasToolCalls(data);
    const shouldDeleteMessage = type !== 'swipe'
        && ['', '...'].includes(getMessage)
        && !reasoning;
    hasToolCalls && shouldDeleteMessage && await deleteLastMessage();
    const invocationResult = await ToolManager.invokeFunctionTools(data, { reasoningText: reasoning });

    if (hasToolCalls) {
        depth = depth + 1;
        await ToolManager.saveFunctionToolInvocations(invocationResult.invocations);
        return Generate('normal', { ...opts, depth }, dryRun);
    }
}
```

### 5.4 Tool Invocation (public/scripts/tool-calling.js lines 769-824)

For each tool call in the response:

1. Extract `id`, `name`, and `parameters` from the normalized tool call object.
2. Show a toast notification with the formatted message (`toastr.info`).
3. Call `ToolManager.invokeFunctionTool(name, parameters)`.
4. Clear the toast.
5. If the result is an `Error`, push to `result.errors`.
6. If the tool is `stealth`, push name to `result.stealthCalls` (no chat message, no follow-up).
7. Otherwise, create a `ToolInvocation` object with `id`, `displayName`, `name`, `parameters`, `result`, `signature`, and `reasoning`.


## 6. Multi-turn Tool Use (Agentic Loop)

### 6.1 Recursion Mechanism

The tool calling loop is implemented via recursive calls to `Generate()`, tracked by a `depth` counter:

```js
// public/scripts/tool-calling.js:254
static RECURSE_LIMIT = 5;

// public/script.js:4412
const canPerformToolCalls = !dryRun
    && ToolManager.canPerformToolCalls(type)
    && depth < ToolManager.RECURSE_LIMIT;
```

This means the LLM can chain up to 5 rounds of tool calls before the system forces it to produce a final text response (by not including tools in the 6th request).

### 6.2 How Previous Tool Calls are Injected

When building the prompt for the next generation, previous tool invocations stored in `chat[j].extra.tool_invocations` are reconstructed into proper OpenAI-format messages:

```js
// public/scripts/openai.js:1022-1033
const toolCallMessage = await Message.createAsync(
    chatMessage.role, undefined, 'toolCall-' + chatMessage.identifier
);
const toolResultMessages = await Promise.all(
    invocations.slice().reverse().map(
        (inv) => Message.createAsync('tool', inv.result || '[No content]', inv.id)
    )
);
await toolCallMessage.setToolCalls(invocations, includeSignature, includeToolReasoning);

if (chatCompletion.canAffordAll([toolCallMessage, ...toolResultMessages])) {
    for (const resultMessage of toolResultMessages) {
        chatCompletion.insertAtStart(resultMessage, 'chatHistory');
    }
    chatCompletion.insertAtStart(toolCallMessage, 'chatHistory');
}
```

The `setToolCalls` method (line 3340-3357) constructs proper `tool_calls` objects and counts their tokens:

```js
async setToolCalls(invocations, includeSignature, includeReasoning) {
    this.tool_calls = invocations.map(i => ({
        id: i.id,
        type: 'function',
        function: {
            arguments: i.parameters,
            name: i.name,
        },
        ...(includeSignature && i.signature ? { signature: i.signature } : {}),
    }));
    // Token counting includes the tool_calls JSON
    this.tokens = await tokenHandler.countAsync({
        role: this.role,
        tool_calls: JSON.stringify(this.tool_calls),
    });
}
```

### 6.3 Reasoning Forwarding in Tool Chains

For providers that support interleaved reasoning (currently only OpenRouter, line 257-259), reasoning text from intermediate tool call turns can be preserved and forwarded:

```js
// public/scripts/openai.js:250-254
export const tool_reasoning_modes = {
    DISABLED: 'disabled',
    SINCE_LAST_USER: 'since_last_user',
    ACTIVE_CHAIN: 'active_chain',
};
```

- `DISABLED`: no reasoning is included with tool call messages.
- `SINCE_LAST_USER`: reasoning from all tool calls since the last user message is included.
- `ACTIVE_CHAIN`: only reasoning from consecutive tool-call turns is included.

Reasoning signatures (encrypted thought tokens from Anthropic, Google, OpenAI) are also preserved when the originating API/model matches the current one (openai.js lines 596-612).

### 6.4 Stealth Tool Calls

When all invocations are stealth (e.g., background operations), the generation stops without producing a follow-up LLM response:

```js
// public/script.js:5332
const shouldStopGeneration = (!invocationResult.invocations.length && shouldDeleteMessage)
    || invocationResult.stealthCalls.length;
```


## 7. Parsing Tool Calls from Diverse Response Formats

### 7.1 The parseToolCalls Method

`ToolManager.parseToolCalls()` (lines 426-557) handles streaming responses from four distinct formats, assembling tool calls incrementally from deltas:

**OpenAI format** (lines 430-469):
Reads `parsed.choices[].delta.tool_calls[]`, indexing by `choice.index` and `toolCallDelta.index`.

**Cohere format** (lines 471-486):
Handles event types `message-start`, `tool-call-start`, `tool-call-delta`, `tool-call-end` via `parsed.delta.message`.

**Anthropic format** (lines 487-532):
Handles `content_block` events of type `tool_use`, plus `input_json_delta` events that stream the arguments incrementally. The `__input_json_delta` key accumulates partial JSON, which is parsed on `content_block_stop`.

**Google Gemini format** (lines 533-556):
Reads `parsed.candidates[].content.parts[].functionCall`, including `thoughtSignature` if present.

### 7.2 The applyToolCallDelta Method

A recursive merge function (lines 564-598) that concatenates string fields, recursively merges object fields, and directly assigns other types. This handles the streaming scenario where tool call data arrives across multiple SSE events.

### 7.3 Non-Streaming Response Normalization

`#getToolCallsFromData()` (lines 690-752) normalizes the final response into a uniform `[{id, function: {name, arguments}}]` format from:

- OpenAI: `data.choices[0].message.tool_calls`
- Claude: `data.content.filter(c => c.type === 'tool_use')` -- converted via `convertClaudeToolCall`
- Gemini: `data.responseContent.parts.filter(p => p.functionCall)` -- converted via `convertGoogleToolCall`
- Cohere: `data.message.tool_calls`
- Streaming accumulator: `data[0]` (array of arrays from streaming)

OpenRouter reasoning signatures are extracted from `choice.message.reasoning_details` and attached to the corresponding tool call (lines 726-732).


## 8. Structured Output via Forced Tool Calls

### 8.1 Claude Structured Output

For Anthropic Claude, structured output (JSON schema) is implemented as a forced tool call:

```js
// src/endpoints/backends/chat-completions.js:276-285
if (request.body.json_schema) {
    const jsonTool = {
        name: request.body.json_schema.name,
        description: request.body.json_schema.description || 'Well-formed JSON object',
        input_schema: request.body.json_schema.value,
    };
    requestBody.tools = [...(requestBody.tools || []), jsonTool];
    requestBody.tool_choice = { type: 'tool', name: request.body.json_schema.name };
}
```

This appends a tool with the JSON schema as `input_schema` and forces the LLM to call it via `tool_choice: { type: 'tool', name: ... }`.

### 8.2 Other Providers

Most other providers (OpenAI, DeepSeek, AI21, etc.) use native `response_format: { type: 'json_schema', json_schema: { ... } }` for structured output, not tool forcing.


## 9. Tool Call UI

### 9.1 Toast Notifications During Execution

When a tool is invoked, a persistent toast notification appears:

```js
// public/scripts/tool-calling.js:794
const toast = message && toastr.info(message, 'Tool Calling', { timeOut: 0 });
const toolResult = await ToolManager.invokeFunctionTool(name, parameters);
toastr.clear(toast);
```

The message content comes from `formatMessage()`, which defaults to `"Invoking tool: {displayName || name}"`.

### 9.2 Chat Message with Collapsible Details

After tool invocations complete, a system message is added to the chat:

```js
// public/scripts/tool-calling.js:844-861
static #formatToolInvocationMessage(invocations) {
    const detailsElement = document.createElement('details');
    const summaryElement = document.createElement('summary');
    const preElement = document.createElement('pre');
    const codeElement = document.createElement('code');
    codeElement.classList.add('language-json');
    // ...
    summaryElement.textContent = `Tool calls: ${this.#groupToolNames(toolNames)}`;
    // ...
    return detailsElement.outerHTML;
}
```

This renders as a collapsible `<details>` element with:
- **Summary**: "Tool calls: ToolName1, ToolName2 (3)" (grouped by count)
- **Body**: Full JSON dump of all invocations with parsed parameters and results

### 9.3 Message Block Hiding

During streaming, if the LLM produces no text content (only tool calls), the message block is hidden:

```js
// public/script.js:3528-3531
if (this.messageDom instanceof HTMLElement
    && Array.isArray(this.toolCalls) && this.toolCalls.length > 0) {
    const shouldHide = ['', '...'].includes(this.result) && !this.reasoningHandler.reasoning;
    this.messageDom.classList.toggle('displayNone', shouldHide);
}
```

If the LLM produced empty text alongside tool calls, the entire empty assistant message is deleted before saving (script.js line 5325).

### 9.4 Event System

Two events are emitted when tool calls complete:

```js
// public/scripts/tool-calling.js:885-887
await eventSource.emit(event_types.TOOL_CALLS_PERFORMED, invocations);
addOneMessage(message);
await eventSource.emit(event_types.TOOL_CALLS_RENDERED, invocations);
```

- `TOOL_CALLS_PERFORMED`: fired after invocations complete but before the message is added to the DOM.
- `TOOL_CALLS_RENDERED`: fired after the message is rendered in the chat.


## 10. Extension Tools API

### 10.1 Context API

Extensions can register tools via the SillyTavern context API:

```js
// public/scripts/st-context.js:179-183
registerFunctionTool: ToolManager.registerFunctionTool.bind(ToolManager),
unregisterFunctionTool: ToolManager.unregisterFunctionTool.bind(ToolManager),
isToolCallingSupported: ToolManager.isToolCallingSupported.bind(ToolManager),
canPerformToolCalls: ToolManager.canPerformToolCalls.bind(ToolManager),
ToolManager,
```

Extensions call `getContext().registerFunctionTool({ name, description, parameters, action, ... })` to add tools.

### 10.2 Slash Command Registration

Users can register tools at runtime via slash commands without writing JavaScript:

```
/tools-register name=Echo
    description="Echoes a message"
    parameters={{var::echoSchema}}
    formatMessage={: Echoing... :}
    {: /echo {{var::arg.message}} :}
```

The slash command system provides four tool management commands:

| Command | Purpose |
|---------|---------|
| `/tools-register` | Register a tool with a closure as the action |
| `/tools-unregister` | Remove a tool by name |
| `/tools-list` | List all registered tools in OpenAI function format |
| `/tools-invoke` | Manually invoke a tool by name with JSON parameters |

The `/tools-register` command converts closures to async functions and assigns incoming parameters as scoped variables with the `arg.` prefix (lines 1061-1073):

```js
function closureToFunction(action, convertResult) {
    return async (args) => {
        const localClosure = action.getCopy();
        const scope = localClosure.scope;
        if (typeof args === 'object' && args !== null) {
            assignNestedVariables(scope, args, 'arg');
        }
        const result = await localClosure.execute();
        return convertResult(result.pipe);
    };
}
```

The `assignNestedVariables` helper (lines 61-73) recursively flattens nested parameters into dot-notation scope variables (e.g., `arg.address.city`).


## 11. Error Handling

### 11.1 Tool Invocation Errors

When a tool's action throws, the error is caught and returned as a string:

```js
// public/scripts/tool-calling.js:324-343
static async invokeFunctionTool(name, parameters) {
    try {
        if (!this.#tools.has(name)) {
            throw new Error(`No tool with the name "${name}" has been registered.`);
        }
        const result = await tool.invoke(invokeParameters);
        return typeof result === 'string' ? result : JSON.stringify(result);
    } catch (error) {
        if (error instanceof Error) {
            error.cause = name;
            return error.toString();
        }
        return new Error('Unknown error occurred while invoking the tool.', { cause: name }).toString();
    }
}
```

### 11.2 Error Aggregation

`invokeFunctionTools()` collects errors into the `result.errors` array. If errors occur, they are shown via a toast with a clickable popup:

```js
// public/scripts/tool-calling.js:896-901
static showToolCallError(errors) {
    toastr.error(
        'An error occurred while invoking function tools. Click here for more details.',
        'Tool Calling',
        {
            onclick: () => Popup.show.text(
                'Tool Calling Errors',
                DOMPurify.sanitize(errors.map(e => `${e.cause}: ${e.message}`).join('<br>'))
            ),
            timeOut: 5000,
        }
    );
}
```

### 11.3 Generation Stops on Total Failure

If all tool calls fail (no successful invocations) and the LLM produced empty text, generation stops:

```js
// public/script.js:5332
const shouldStopGeneration = (!invocationResult.invocations.length && shouldDeleteMessage)
    || invocationResult.stealthCalls.length;
```

This prevents an infinite loop of failed tool calls.

### 11.4 JSON Parse Failures in Streaming

When Anthropic's `input_json_delta` accumulator fails to parse, it logs a warning and continues:

```js
// public/scripts/tool-calling.js:524-529
try {
    const jsonDelta = { input: JSON.parse(jsonDeltaString) };
    delete targetToolCall[this.#INPUT_DELTA_KEY];
    ToolManager.#applyToolCallDelta(targetToolCall, jsonDelta);
} catch (error) {
    console.warn('[ToolManager] Failed to apply input JSON delta:', error);
}
```


## 12. Token Management

### 12.1 Pre-allocation of Tool Budget

Before building the chat prompt, tool schemas are serialized and their token count is reserved from the context budget:

```js
// public/scripts/openai.js:1280-1287
if (ToolManager.canPerformToolCalls(type)) {
    const toolData = {};
    await ToolManager.registerFunctionToolsOpenAI(toolData);
    const toolMessage = [{ role: 'user', content: JSON.stringify(toolData) }];
    const toolTokens = await tokenHandler.countAsync(toolMessage);
    chatCompletion.reserveBudget(toolTokens);
}
```

This ensures tool definitions do not cause the prompt to exceed the context window. The budget is reserved before chat history messages are added, so tool overhead always has priority.

### 12.2 Tool Call Message Token Counting

When previous tool invocations are reconstructed into chat messages, each message's tokens are counted and checked against the remaining budget:

```js
// public/scripts/openai.js:1025
if (chatCompletion.canAffordAll([toolCallMessage, ...toolResultMessages])) {
    // Insert tool messages
} else {
    break; // Stop adding older messages
}
```

The `Message.setToolCalls()` method counts tokens for the `tool_calls` JSON representation:

```js
// public/scripts/openai.js:3352-3356
this.tokens = await tokenHandler.countAsync({
    role: this.role,
    tool_calls: JSON.stringify(this.tool_calls),
    ...(this.reasoning ? { reasoning: this.reasoning } : {}),
});
```

### 12.3 Budget Priority

The token budget is consumed in this order:
1. System prompts and injections (highest priority)
2. **Tool schema definitions** (reserved early)
3. Chat history messages including tool call/result pairs (newest first)
4. Dialogue examples (lowest priority, may be dropped)


## 13. Provider-Specific Signature and Reasoning Handling

### 13.1 OpenRouter Signatures

OpenRouter uses `reasoning_details` for encrypted thought signatures. The prompt converter (`src/prompt-converters.js:1391-1445`) converts internal `signature` fields on messages and tool calls into this format:

```js
// Lines 1433-1439
if (Array.isArray(message.tool_calls)) {
    message.tool_calls.forEach((toolCall) => {
        if (typeof toolCall.signature === 'string') {
            addDetail(toolCall.signature, toolCall.id);
            delete toolCall.signature;
        }
    });
}
// Output: message.reasoning_details = [{ type: 'reasoning.encrypted', data: ..., format: ... }]
```

Formats are model-specific: `google-gemini-v1`, `anthropic-claude-v1`, `openai-responses-v1`, `xai-responses-v1`.

### 13.2 Google Gemini Thought Signatures

Gemini tool calls can include `thoughtSignature` fields which are preserved through the conversion pipeline (prompt-converters.js line 552) and parsed back from streaming responses (tool-calling.js lines 548-549).

### 13.3 DeepSeek Reasoning Dummy

DeepSeek's reasoning models require a `reasoning_content` field on assistant messages with tool calls, even if empty:

```js
// src/prompt-converters.js:1371-1383
export function addReasoningContentToToolCalls(messages) {
    for (const message of messages) {
        if (!Array.isArray(message.tool_calls) || 'reasoning_content' in message) {
            continue;
        }
        message.reasoning_content = '';
    }
}
```


## 14. Architecture Summary

```
                   FRONTEND (Browser)                              BACKEND (Node.js)
               ========================                        =======================

 [Extension / Slash Cmd]                                       [Provider APIs]
        |                                                           ^
        v                                                           |
 ToolManager.registerFunctionTool()                          Provider-specific
        |                                                    body construction:
        v                                                    - Claude: input_schema
 ToolManager.registerFunctionToolsOpenAI()                   - Gemini: function_declarations
   -> data.tools = [{type:'function', function:{...}}]       - Mistral: sanitized IDs
   -> data.tool_choice = 'auto'                              - Cohere: text primer
        |                                                    - DeepSeek: empty required fix
        v                                                           ^
 sendOpenAIRequest() ----POST /api/backends/chat-completions/generate--->
        |                                                           |
        v                                                           |
 ToolManager.parseToolCalls()  <---SSE stream / JSON response-------+
   (handles OpenAI/Claude/Gemini/Cohere delta formats)
        |
        v
 ToolManager.invokeFunctionTools()
   -> calls each tool's action()
   -> collects results + errors + stealth calls
        |
        v
 ToolManager.saveFunctionToolInvocations()
   -> adds system message to chat[] with <details> HTML
   -> emits TOOL_CALLS_PERFORMED + TOOL_CALLS_RENDERED
        |
        v
 Generate('normal', { depth: depth + 1 })    // recursive call
   -> previous tool calls reconstructed as assistant tool_call messages + tool result messages
   -> budget-checked and inserted into prompt
   -> cycle continues until RECURSE_LIMIT (5) or LLM stops calling tools
```


## 15. Key Metrics

| Metric | Value |
|--------|-------|
| Total lines in tool-calling.js | 1,143 |
| Maximum recursion depth | 5 (`RECURSE_LIMIT`) |
| Providers with tool support | 26 (23 hardcoded + per-model checks on 7) |
| Built-in tools | 1 (GenerateImage, from SD extension) |
| Slash commands for tool management | 4 (register, unregister, list, invoke) |
| Response format parsers | 4 (OpenAI, Claude, Gemini, Cohere) |
| Event types emitted | 2 (TOOL_CALLS_PERFORMED, TOOL_CALLS_RENDERED) |
| Structured output as forced tool | Claude only |
| Stealth tool support | Yes (no chat message, no follow-up) |
| Tool reasoning forwarding | OpenRouter only (3 modes) |
