# Local Model Server APIs -- Deep Analysis for Multi-Backend Architecture

> **Sources:** llama.cpp server README, OOBA text-generation-webui OpenAI API wiki + typing.py,
> vLLM OpenAI-compatible server docs, KoboldCpp API (expose.h + koboldcpp_api),
> TabbyAPI source (endpoints/, common/sampling.py)
>
> **Goal:** Define what The Bannered Mare must support to integrate with local inference backends,
> complementing the cloud provider analysis in OPENAI.md and ANTHROPIC.md.

---

## Table of Contents

1. [Overview -- Why Local Backends Matter](#1-overview----why-local-backends-matter)
2. [llama.cpp Server](#2-llamacpp-server)
3. [Text Generation WebUI (OOBA)](#3-text-generation-webui-ooba)
4. [vLLM](#4-vllm)
5. [KoboldCpp](#5-koboldcpp)
6. [TabbyAPI](#6-tabbyapi)
7. [Text Completion vs Chat Completion](#7-text-completion-vs-chat-completion)
8. [Compatibility Matrix](#8-compatibility-matrix)
9. [Extra Sampling Parameters (Not in OpenAI)](#9-extra-sampling-parameters-not-in-openai)
10. [Adapter Strategy](#10-adapter-strategy)
11. [Implementation Plan](#11-implementation-plan)

---

## 1. Overview -- Why Local Backends Matter

### 1.1 The Case for Self-Hosted Models

- **Zero API costs** -- inference runs on owned hardware; no per-token billing.
- **Full data privacy** -- prompts and completions never leave the machine.
- **Custom models** -- fine-tuned, merged, or quantized checkpoints that no cloud
  provider hosts.
- **No rate limits** -- throughput is bounded only by hardware, not by tier quotas.
- **The Bannered Mare explicitly targets local model integration** as a first-class path.
  The CLAUDE.md project instructions name Ollama and vLLM as example backends.

### 1.2 Two API Paradigms

Local servers expose one or both of:

| Paradigm | Endpoint pattern | Input shape | Who formats the prompt? |
|---|---|---|---|
| **Chat Completion** (OpenAI-compatible) | `POST /v1/chat/completions` | `messages: [{role, content}]` | Server applies chat template |
| **Text Completion** (legacy / native) | `POST /v1/completions` or `POST /api/v1/generate` | `prompt: "single string"` | **Client** must format instruct markup |

Most modern local servers now ship an OpenAI-compatible layer. Some (KoboldCpp,
llama.cpp) also retain a native text-completion API with richer parameter sets.

### 1.3 Servers Covered

| Server | Backend engine | Primary audience | API style |
|---|---|---|---|
| **llama.cpp server** | llama.cpp (GGUF) | General / developers | Native + OpenAI |
| **Text Gen WebUI (OOBA)** | transformers / ExLlamaV2 / llama.cpp | RP community, general | OpenAI + Anthropic + legacy |
| **vLLM** | vLLM (PagedAttention) | Production / high-throughput | OpenAI (most complete) |
| **KoboldCpp** | llama.cpp (GGUF) | SillyTavern / RP community | KoboldAI native + OpenAI |
| **TabbyAPI** | ExLlamaV2 / ExLlamaV3 | Quantized model enthusiasts | OpenAI + KoboldAI |

> Ollama is excluded here -- it has its own dedicated analysis document.

---

## 2. llama.cpp Server

### 2.1 Overview

- Lightweight C++ inference server shipped as `llama-server` (formerly `server`).
- Runs GGUF-format models directly with CPU, CUDA, Metal, Vulkan, and SYCL backends.
- Offers **both** a native REST API and an OpenAI-compatible API layer.
- Supports parallel decoding with multi-user slot management, continuous batching,
  speculative decoding, multimodal input, and function calling.
- Default port: **8080**.

### 2.2 OpenAI-Compatible API

#### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/chat/completions` | Chat completion (messages array) |
| `POST` | `/v1/completions` | Text completion (prompt string) |
| `POST` | `/v1/embeddings` | Embeddings (pooled, normalized) |
| `POST` | `/v1/responses` | OpenAI Responses API (converted to chat internally) |
| `POST` | `/v1/messages` | Anthropic Messages API compatibility |
| `GET`  | `/v1/models` | List loaded models |

#### Supported OpenAI Parameters

Standard OpenAI params work as expected: `model`, `messages`, `prompt`,
`temperature`, `top_p`, `max_tokens` / `max_completion_tokens`, `stream`,
`stream_options`, `stop`, `frequency_penalty`, `presence_penalty`, `seed`, `n`,
`logprobs`, `top_logprobs`, `logit_bias`, `response_format`, `tools`,
`tool_choice`.

#### Extra Parameters (passed alongside OpenAI params)

All native `/completion` parameters are also accepted on `/v1/chat/completions`
and `/v1/completions`. Key extras:

- `cache_prompt` (bool) -- reuse KV cache from previous request.
- `samplers` (array of strings) -- custom sampler chain ordering.
  Default: `["dry", "top_k", "typ_p", "top_p", "min_p", "xtc", "temperature"]`.
- `mirostat` (0/1/2), `mirostat_tau`, `mirostat_eta`.
- `min_p`, `typical_p`, `top_k` (not in standard OpenAI).
- `grammar`, `json_schema` -- GBNF grammar-constrained generation.
- `repeat_penalty`, `repeat_last_n` -- token repetition control.
- `dynatemp_range`, `dynatemp_exponent` -- dynamic temperature.
- `dry_multiplier`, `dry_base`, `dry_allowed_length`, `dry_penalty_last_n`,
  `dry_sequence_breakers` -- DRY repetition penalty.
- `xtc_probability`, `xtc_threshold` -- XTC sampler.
- `id_slot` -- assign request to a specific inference slot.
- `n_predict` -- alias for max_tokens in native API.
- `chat_template_kwargs` -- extra vars for Jinja template.
- `reasoning_format` -- parse reasoning (e.g. Deepseek-style `reasoning_content`).

#### Response Format

Matches OpenAI structure. Extra `timings` object included:

```json
{
  "choices": [{ "index": 0, "message": {...}, "finish_reason": "stop" }],
  "usage": { "prompt_tokens": 42, "completion_tokens": 35, "total_tokens": 77 },
  "timings": {
    "prompt_n": 1, "cache_n": 236,
    "prompt_ms": 30.9, "predicted_n": 35, "predicted_ms": 661.0,
    "predicted_per_second": 52.9
  }
}
```

### 2.3 Native API

These endpoints use a different request/response shape from OpenAI.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/completion` | Text completion (native format) |
| `POST` | `/infill` | Fill-in-the-middle for code |
| `POST` | `/tokenize` | Tokenize text to token IDs |
| `POST` | `/detokenize` | Decode token IDs to text |
| `POST` | `/apply-template` | Apply chat template without generating |
| `POST` | `/embedding` | Non-OAI embeddings (supports all poolings) |
| `POST` | `/reranking` | Document reranking |
| `GET`  | `/health` | Server health (also `/v1/health`) |
| `GET`  | `/slots` | Active slot info (enable with `--slots`) |
| `GET`  | `/props` | Server properties, model info |
| `GET`  | `/metrics` | Prometheus metrics (enable with `--metrics`) |
| `POST` | `/slots/{id}?action=save` | Save slot KV cache to file |
| `POST` | `/slots/{id}?action=restore` | Restore slot KV cache from file |
| `POST` | `/slots/{id}?action=erase` | Erase slot KV cache |
| `GET`  | `/lora-adapters` | List loaded LoRA adapters |
| `POST` | `/lora-adapters` | Hot-swap LoRA adapters with per-request scaling |

#### Native `/completion` Request

```json
{
  "prompt": "Building a website can be done in 10 simple steps:",
  "n_predict": 128,
  "temperature": 0.8,
  "top_k": 40,
  "top_p": 0.95,
  "min_p": 0.05,
  "stream": true,
  "cache_prompt": true,
  "grammar": "",
  "samplers": ["dry", "top_k", "typ_p", "top_p", "min_p", "xtc", "temperature"]
}
```

#### Native `/completion` Response

```json
{
  "content": "...",
  "stop": true,
  "stop_type": "eos",
  "stopping_word": "",
  "model": "model-alias",
  "generation_settings": { "n_ctx": 4096, "temperature": 0.8, "..." : "..." },
  "tokens_cached": 42,
  "tokens_evaluated": 10,
  "timings": { "predicted_per_second": 52.9 }
}
```

### 2.4 Key Differences from OpenAI

- **No authentication by default** -- local server, no API key needed (optional
  `--api-key` flag available).
- **Grammar-constrained generation** -- unique `grammar` (GBNF) and `json_schema`
  params for structured output.
- **Slot management** -- concurrent requests assigned to slots; `id_slot` for pinning.
- **`cache_prompt`** -- KV cache reuse across requests (significant speedup for
  multi-turn conversations with shared prefix).
- **DRY / XTC samplers** -- additional repetition penalty mechanisms not in OpenAI.
- **Dynamic temperature** -- `dynatemp_range`/`dynatemp_exponent`.
- **Per-request LoRA** -- hot-swap LoRA adapters with scaling per request.
- **Anthropic Messages API** -- also supports `/v1/messages` endpoint.

---

## 3. Text Generation WebUI (OOBA)

### 3.1 Overview

- Python-based UI and API server (oobabooga/text-generation-webui).
- Supports multiple inference backends: transformers, ExLlamaV2, ExLlamaV3, llama.cpp,
  AutoGPTQ, and more.
- Very popular in the RP community; used heavily with SillyTavern.
- API enabled with `--api` flag. Default port: **5000**.
- Provides OpenAI-compatible, Anthropic-compatible, and internal management endpoints.

### 3.2 OpenAI-Compatible API

#### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/chat/completions` | Chat completion |
| `POST` | `/v1/completions` | Text completion |
| `POST` | `/v1/embeddings` | Embeddings (via sentence-transformers) |
| `POST` | `/v1/images/generations` | Image generation |
| `POST` | `/v1/audio/*` | Audio endpoints |
| `GET`  | `/v1/models` | List models (currently loaded first) |
| `GET`  | `/v1/models/{id}` | Model info |

#### Standard OpenAI Parameters (ChatCompletionRequest)

```
messages, model, frequency_penalty, presence_penalty, temperature, top_p,
logit_bias, logprobs, top_logprobs, max_tokens, max_completion_tokens, n,
stop, stream, stream_options, tools, tool_choice, user
```

#### Extra Parameters -- Sampling (GenerationOptions mixin)

OOBA's real power is its extensive sampler set, all passable alongside OpenAI params:

| Parameter | Type | Description |
|---|---|---|
| `preset` | string | Load a preset YAML from `user_data/presets/` |
| `min_p` | float | Minimum probability threshold |
| `top_k` | int | Top-K sampling |
| `typical_p` | float | Typical sampling |
| `top_a` | float | Top-A sampling |
| `top_n_sigma` | float | Top-N sigma sampling |
| `tfs` | float | Tail free sampling |
| `xtc_threshold` | float | XTC sampler threshold |
| `xtc_probability` | float | XTC sampler probability |
| `epsilon_cutoff` | float | Epsilon cutoff |
| `eta_cutoff` | float | Eta cutoff |
| `smoothing_factor` | float | Smoothing factor |
| `smoothing_curve` | float | Smoothing curve |
| `dynatemp_low` | float | Dynamic temperature low bound |
| `dynatemp_high` | float | Dynamic temperature high bound |
| `dynatemp_exponent` | float | Dynamic temperature exponent |
| `repetition_penalty` | float | Repetition penalty (multiplicative) |
| `encoder_repetition_penalty` | float | Encoder repetition penalty |
| `no_repeat_ngram_size` | int | Block repeated N-grams |
| `repetition_penalty_range` | int | Window for repetition penalty |
| `penalty_alpha` | float | Contrastive search alpha |
| `guidance_scale` | float | CFG scale (classifier-free guidance) |
| `negative_prompt` | string | Negative prompt for CFG |
| `mirostat_mode` | int | Mirostat mode (0/1/2) |
| `mirostat_tau` | float | Mirostat target entropy |
| `mirostat_eta` | float | Mirostat learning rate |
| `dry_multiplier` | float | DRY penalty multiplier |
| `dry_base` | float | DRY penalty base |
| `dry_allowed_length` | int | DRY allowed repetition length |
| `dry_sequence_breakers` | string | DRY sequence breakers (JSON array) |
| `adaptive_target` | float | Adaptive sampling target |
| `adaptive_decay` | float | Adaptive sampling decay |
| `do_sample` | bool | Enable sampling (vs greedy) |
| `dynamic_temperature` | bool | Enable dynamic temperature |
| `temperature_last` | bool | Apply temperature last in sampler chain |
| `seed` | int | RNG seed (-1 = random) |
| `sampler_priority` | list/string | Custom sampler chain ordering |
| `grammar_string` | string | GBNF grammar constraint |
| `enable_thinking` | bool | Enable thinking/reasoning mode |
| `reasoning_effort` | string | Reasoning effort level |
| `ban_eos_token` | bool | Ban EOS token |
| `skip_special_tokens` | bool | Skip special tokens in output |
| `custom_token_bans` | string | Comma-separated banned token IDs |
| `truncation_length` | int | Override context truncation |
| `auto_max_new_tokens` | bool | Auto-calculate max new tokens |

#### Extra Parameters -- Chat Mode

| Parameter | Type | Description |
|---|---|---|
| `mode` | string | `"instruct"`, `"chat"`, or `"chat-instruct"` |
| `character` | string | Load character from `user_data/characters/` |
| `instruction_template` | string | Override instruct template |
| `instruction_template_str` | string | Raw Jinja2 template string |
| `bot_name` / `name2` | string | Character name |
| `user_name` / `name1` | string | User name |
| `context` | string | Character context/description |
| `greeting` | string | Character greeting |
| `user_bio` | string | User description/personality |
| `chat_template_str` | string | Jinja2 chat template |
| `chat_instruct_command` | string | Instruct-mode wrapper command |
| `continue_` | bool | Continue last bot message |

### 3.3 Internal/Management Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/internal/logits` | Get raw logits (optionally with samplers) |
| `GET`  | `/v1/internal/model/list` | List available models |
| `POST` | `/v1/internal/model/load` | Load model with args |
| `POST` | `/v1/internal/token/encode` | Tokenize text |
| `POST` | `/v1/internal/token/decode` | Detokenize tokens |
| `POST` | `/v1/internal/token-count` | Count tokens |

### 3.4 Key Differences from OpenAI

- **Character and instruct template built-in** -- the `character`, `mode`,
  `instruction_template` params allow server-side prompt formatting with
  character cards, eliminating client-side template logic.
- **Anthropic Messages API** -- also supports `/v1/messages` (Claude-compatible).
- **Largest sampler set** -- more sampling parameters than any other local backend.
- **`model` param is ignored** -- model switching happens via internal endpoints, not
  per-request. The `model` field in requests is cosmetic.
- **Grammar support** -- `grammar_string` for GBNF grammar constraints.
- **Optional API key** -- via `--api-key` flag.
- **Tool/function calling** -- supported via model Jinja2 templates.

---

## 4. vLLM

### 4.1 Overview

- High-performance inference engine using PagedAttention for efficient GPU memory
  management.
- Designed for production serving with continuous batching, tensor parallelism, and
  high throughput.
- Provides the **most complete** OpenAI-compatible API of all local servers.
- Supports guided generation (JSON schema, regex, grammar) natively.
- Default port: **8000**.

### 4.2 OpenAI-Compatible API

#### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/chat/completions` | Chat completion |
| `POST` | `/v1/completions` | Text completion |
| `POST` | `/v1/embeddings` | Embeddings |
| `GET`  | `/v1/models` | List models |
| `GET`  | `/health` | Health check |
| `GET`  | `/version` | Server version |

#### Supported OpenAI Parameters

Full OpenAI spec support:

```
model, messages, prompt, temperature, top_p, max_tokens, max_completion_tokens,
n, stream, stream_options, stop, frequency_penalty, presence_penalty, seed,
logprobs, top_logprobs, logit_bias, response_format, tools, tool_choice,
best_of, echo, suffix, user
```

#### Extra Parameters

| Parameter | Type | Description |
|---|---|---|
| `top_k` | int | Top-K sampling |
| `min_p` | float | Minimum probability threshold |
| `repetition_penalty` | float | Multiplicative repetition penalty |
| `length_penalty` | float | Length penalty for beam search |
| `early_stopping` | bool | Early stopping for beam search |
| `guided_json` | object/string | JSON schema for constrained generation |
| `guided_regex` | string | Regex pattern for constrained generation |
| `guided_grammar` | string | BNF grammar for constrained generation |
| `guided_choice` | list[string] | Constrain output to one of provided choices |
| `guided_decoding_backend` | string | Backend for guided generation |
| `ignore_eos` | bool | Ignore EOS token |
| `min_tokens` | int | Minimum tokens before allowing EOS |
| `skip_special_tokens` | bool | Skip special tokens in output |
| `spaces_between_special_tokens` | bool | Add spaces between special tokens |
| `include_stop_str_in_output` | bool | Include stop string in output |

### 4.3 Guided Generation (Structured Output)

vLLM's guided generation is its standout feature for structured output:

```json
{
  "model": "meta-llama/Llama-3-8B-Instruct",
  "messages": [{"role": "user", "content": "Generate a user profile"}],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "user_profile",
      "schema": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "age": {"type": "integer"}
        },
        "required": ["name", "age"]
      }
    }
  }
}
```

Alternative constrained generation via extra params:
- `guided_json` -- pass a JSON schema directly.
- `guided_regex` -- constrain output to match a regex.
- `guided_grammar` -- constrain output using BNF grammar.
- `guided_choice` -- constrain output to one of N strings.

### 4.4 Key Differences from OpenAI

- **Most OpenAI-compatible** -- closest to the real OpenAI API of all local servers.
- **Guided generation** -- `guided_json`, `guided_regex`, `guided_grammar` provide
  flexible structured output beyond OpenAI's `response_format`.
- **High throughput** -- continuous batching, PagedAttention, tensor parallelism.
- **No auth by default** -- add via `--api-key` flag.
- **No grammar (GBNF)** -- uses its own guided generation format instead.
- **Fewer exotic samplers** -- no mirostat, DRY, XTC; focuses on standard OpenAI
  params plus min_p and repetition_penalty.
- **`model` param matters** -- unlike OOBA, vLLM routes to loaded models.

---

## 5. KoboldCpp

### 5.1 Overview

- C++ inference server built on llama.cpp, maintained by Concedo.
- The most popular backend for SillyTavern RP users.
- Offers **both** a KoboldAI-native API and an OpenAI-compatible API.
- Supports GGUF models, multimodal input, speculative decoding, and smart context
  management.
- Default port: **5001**.

### 5.2 KoboldAI API (Native)

The native API is **text completion only** -- it takes a single prompt string, not a
messages array. Instruct formatting must be done client-side.

#### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/generate` | Text generation (synchronous) |
| `POST` | `/api/extra/generate/stream` | Streaming text generation (SSE) |
| `GET`  | `/api/v1/model` | Current model info |
| `GET`  | `/api/v1/config/max_length` | Max generation length |
| `GET`  | `/api/v1/config/max_context_length` | Max context length |
| `GET`  | `/api/v1/info/version` | KoboldAI version |
| `POST` | `/api/extra/tokencount` | Count tokens in text |
| `POST` | `/api/extra/abort` | Abort current generation |
| `GET`  | `/api/extra/generate/check` | Check generation status |

#### Generate Request

```json
{
  "prompt": "<formatted instruct prompt string>",
  "max_context_length": 4096,
  "max_length": 256,
  "temperature": 0.7,
  "top_k": 40,
  "top_p": 0.9,
  "top_a": 0.0,
  "min_p": 0.05,
  "typical_p": 1.0,
  "tfs": 1.0,
  "rep_pen": 1.1,
  "rep_pen_range": 320,
  "rep_pen_slope": 1.0,
  "presence_penalty": 0.0,
  "mirostat": 0,
  "mirostat_tau": 5.0,
  "mirostat_eta": 0.1,
  "sampler_order": [6, 0, 1, 3, 4, 2, 5],
  "seed": -1,
  "stop_sequence": ["\\nUser:", "\\n###"],
  "grammar": "",
  "dynatemp_range": 0.0,
  "dynatemp_exponent": 1.0,
  "smoothing_factor": 0.0,
  "smoothing_curve": 1.0,
  "xtc_threshold": 0.0,
  "xtc_probability": 0.0,
  "dry_multiplier": 0.0,
  "dry_base": 0.0,
  "dry_allowed_length": 0,
  "dry_penalty_last_n": 0,
  "dry_sequence_breakers": [],
  "nsigma": 0.0,
  "adaptive_target": -1.0,
  "adaptive_decay": 0.9,
  "logit_biases": [],
  "banned_tokens": [],
  "render_special": false,
  "allow_eos_token": true,
  "bypass_eos_token": false,
  "stream_sse": false
}
```

#### Generate Response

```json
{
  "results": [
    { "text": "...generated continuation..." }
  ]
}
```

#### Streaming Response (SSE)

Each SSE event:
```json
{ "token": "next_token_text" }
```

### 5.3 OpenAI-Compatible API

KoboldCpp also serves the standard OpenAI-compatible endpoints:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/chat/completions` | Chat completion |
| `POST` | `/v1/completions` | Text completion |
| `GET`  | `/v1/models` | List models |

These accept standard OpenAI parameters and produce standard OpenAI response shapes.
The extra KoboldCpp sampling parameters can also be passed.

### 5.4 Key Differences from OpenAI

- **Two API modes** -- KoboldAI native (text completion only) + OpenAI-compatible.
  SillyTavern primarily uses the KoboldAI native API.
- **Native API is TEXT COMPLETION only** -- single prompt string, not messages.
  Client must format instruct markup.
- **`sampler_order`** -- explicit ordering of sampling steps as integer array:
  `[0=top_k, 1=top_a, 2=top_p, 3=tfs, 4=typical, 5=temperature, 6=rep_pen]`.
- **Context shifting** -- automatic context window management (`use_contextshift`)
  that slides the context window without full reprocessing.
- **Smart context** -- `use_smartcontext` for intelligent context trimming.
- **`rep_pen`** -- uses `rep_pen` naming (multiplicative, different from OpenAI's
  `frequency_penalty`/`presence_penalty` which are additive logit biases).
- **No auth** -- local server, no API key.
- **Grammar support** -- GBNF grammar via `grammar` param.
- **Generation abort** -- `POST /api/extra/abort` to cancel in-progress generation.
- **Tool call support** -- available via `tool_call_fix` flag for bracket handling.

---

## 6. TabbyAPI

### 6.1 Overview

- FastAPI-based serving engine for ExLlamaV2 and ExLlamaV3 backends.
- The official API backend for ExLlamaV2/V3.
- Focus on high-quality quantized model serving (EXL2, EXL3, GPTQ, FP16).
- Supports OpenAI-compatible API, KoboldAI API, and extensive management endpoints.
- Concurrent inference with asyncio and continuous batching via paged attention.
- Default port: **5000**.

### 6.2 OpenAI-Compatible API

#### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/chat/completions` | Chat completion |
| `POST` | `/v1/completions` | Text completion |
| `POST` | `/v1/embeddings` | Embeddings |
| `GET`  | `/v1/models` | List models |

#### Supported OpenAI Parameters

```
model, messages, prompt, temperature, top_p, max_tokens, max_completion_tokens,
n, stream, stream_options, stop, frequency_penalty, presence_penalty, logprobs,
logit_bias, response_format, tools, functions
```

Also: `best_of`, `echo`, `suffix`, `user` (accepted for compatibility, not used).

#### Extra Sampling Parameters (BaseSamplerRequest)

TabbyAPI has one of the richest sampler sets, rivaling OOBA:

| Parameter | Type | Aliases | Description |
|---|---|---|---|
| `min_tokens` | int | `min_length` | Minimum tokens before EOS allowed |
| `top_k` | int | -- | Top-K sampling |
| `min_p` | float | -- | Minimum probability threshold |
| `top_a` | float | -- | Top-A sampling |
| `typical` | float | `typical_p` | Typical sampling |
| `tfs` | float | -- | Tail free sampling |
| `skew` | float | -- | Skew sampling |
| `xtc_probability` | float | -- | XTC sampler probability |
| `xtc_threshold` | float | -- | XTC sampler threshold |
| `smoothing_factor` | float | -- | Smoothing factor |
| `repetition_penalty` | float | `rep_pen` | Multiplicative repetition penalty |
| `penalty_range` | int | `rep_pen_range`, `repetition_penalty_range` | Penalty window |
| `repetition_decay` | int | -- | Repetition penalty decay |
| `mirostat_mode` | int | `mirostat` | Mirostat mode (0/1/2) |
| `mirostat_tau` | float | -- | Mirostat target entropy |
| `mirostat_eta` | float | -- | Mirostat learning rate |
| `dry_multiplier` | float | -- | DRY penalty multiplier |
| `dry_base` | float | -- | DRY penalty base |
| `dry_allowed_length` | int | -- | DRY allowed length |
| `dry_range` | int | `dry_penalty_last_n` | DRY window |
| `dry_sequence_breakers` | list | -- | DRY sequence breakers |
| `max_temp` | float | `dynatemp_high` | Dynamic temperature high bound |
| `min_temp` | float | `dynatemp_low` | Dynamic temperature low bound |
| `temp_exponent` | float | `dynatemp_exponent` | Dynamic temperature exponent |
| `cfg_scale` | float | `guidance_scale` | Classifier-free guidance scale |
| `negative_prompt` | string | -- | Negative prompt for CFG |
| `temperature_last` | bool | -- | Apply temperature last |
| `token_healing` | bool | -- | Enable token healing |
| `adaptive_target` | float | -- | Adaptive sampling target |
| `adaptive_decay` | float | -- | Adaptive sampling decay |
| `add_bos_token` | bool | -- | Add BOS token |
| `ban_eos_token` | bool | `ignore_eos` | Ban EOS token |
| `banned_strings` | list | -- | Banned output strings |
| `banned_tokens` | list | `custom_token_bans` | Banned token IDs |
| `allowed_tokens` | list | `allowed_token_ids` | Whitelist token IDs |
| `json_schema` | object | -- | JSON schema constraint |
| `regex_pattern` | string | -- | Regex pattern constraint |
| `grammar_string` | string | -- | GBNF/EBNF grammar constraint |
| `speculative_ngram` | bool | -- | Enable speculative N-gram decoding |

#### Chat Completion Extra Parameters

| Parameter | Type | Description |
|---|---|---|
| `prompt_template` | string | Override chat template |
| `add_generation_prompt` | bool | Append generation prompt (default true) |
| `template_vars` / `chat_template_kwargs` | dict | Extra Jinja2 template variables |
| `response_prefix` | string | Prefix for model response |

### 6.3 KoboldAI-Compatible API

TabbyAPI also serves a KoboldAI API for SillyTavern compatibility:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/generate` | Text generation |
| `POST` | `/api/extra/generate/stream` | Streaming generation (SSE) |
| `POST` | `/api/extra/abort` | Abort generation |
| `GET/POST` | `/api/extra/generate/check` | Check generation status |
| `GET`  | `/api/v1/model` | Current model info |
| `GET`  | `/api/v1/config/max_length` | Max generation length |
| `GET`  | `/api/v1/config/max_context_length` | Max context length |
| `GET`  | `/api/v1/info/version` | Impersonates KoboldCpp |
| `POST` | `/api/extra/tokencount` | Count tokens |

### 6.4 Management Endpoints (Admin)

TabbyAPI has extensive model/LoRA/template management:

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET`  | `/v1/model` | API key | Currently loaded model |
| `POST` | `/v1/model/load` | Admin key | Load model (SSE progress) |
| `POST` | `/v1/model/unload` | Admin key | Unload model |
| `GET`  | `/v1/model/draft/list` | API key | List draft models |
| `GET`  | `/v1/loras` | API key | List LoRAs |
| `GET`  | `/v1/lora` | API key | Active LoRAs |
| `POST` | `/v1/lora/load` | Admin key | Load LoRAs |
| `POST` | `/v1/lora/unload` | Admin key | Unload LoRAs |
| `POST` | `/v1/token/encode` | API key | Tokenize text or messages |
| `POST` | `/v1/token/decode` | API key | Detokenize tokens |
| `GET`  | `/v1/templates` | API key | List prompt templates |
| `POST` | `/v1/template/switch` | Admin key | Switch template |
| `POST` | `/v1/template/unload` | Admin key | Unload template |
| `GET`  | `/v1/sampling/overrides` | API key | List sampler overrides |
| `POST` | `/v1/sampling/override/switch` | Admin key | Apply override preset |
| `POST` | `/v1/sampling/override/unload` | Admin key | Unload overrides |
| `GET`  | `/v1/auth/permission` | API key | Check key permission level |
| `POST` | `/v1/download` | Admin key | Download model from HuggingFace |
| `GET`  | `/health` | Public | Health check |
| `GET`  | `/.well-known/serviceinfo` | Public | Service discovery |
| `GET`  | `/v1/model/embedding/list` | API key | List embedding models |
| `POST` | `/v1/model/embedding/load` | Admin key | Load embedding model |
| `POST` | `/v1/model/embedding/unload` | Admin key | Unload embedding model |
| `GET`  | `/props` | API key | Model properties (llama.cpp compat) |

### 6.5 Key Differences from OpenAI

- **ExLlamaV2/V3 backend** -- different from llama.cpp; optimized for EXL2/EXL3
  quantized models.
- **Two-tier authentication** -- `X-api-key` for read/generate, `X-admin-key` for
  model management. Also supports `Authorization: Bearer` header.
- **Three constrained generation modes** -- `json_schema`, `regex_pattern`, and
  `grammar_string` (GBNF/EBNF).
- **Sampler override presets** -- YAML files in `sampler_overrides/` that can force
  or additively modify sampling parameters server-wide.
- **Model hot-loading** -- load/unload models without restarting the server.
- **HuggingFace download** -- download models directly from HF via the API.
- **`model` param ignored per-request** -- like OOBA, model switching is via
  management endpoints, though TabbyAPI supports inline model loading.
- **Multi-LoRA** -- load multiple LoRAs with independent scaling.

---

## 7. Text Completion vs Chat Completion

### 7.1 Text Completion (Legacy but Important)

Text completion endpoints take a **single prompt string** rather than a structured
messages array. The server does NO formatting; the client must assemble the full
prompt including any instruct markup.

| Backend | Text Completion Endpoint | Input |
|---|---|---|
| llama.cpp | `POST /completion` or `POST /v1/completions` | `prompt: "string"` |
| OOBA | `POST /v1/completions` | `prompt: "string"` |
| vLLM | `POST /v1/completions` | `prompt: "string"` |
| KoboldCpp | `POST /api/v1/generate` | `prompt: "string"` |
| TabbyAPI | `POST /v1/completions` or `POST /api/v1/generate` | `prompt: "string"` |

### 7.2 When Text Completion Matters for RP

1. **Instruct mode formatting** -- some RP frontends (SillyTavern) prefer to format
   the complete prompt client-side using text completion, giving exact control over
   instruct markers, character cards, and prompt structure.
2. **Model-specific formatting** -- certain models perform better when the exact prompt
   format is controlled, especially older or fine-tuned models without proper chat
   templates.
3. **Prefix/continuation** -- text completion allows starting the assistant's response
   with specific text (e.g., character name + colon) which is harder with chat APIs.
4. **SillyTavern uses text completion** for most local backends by default, building
   the full prompt from character card + chat history + instruct template.

### 7.3 Chat Completion (Modern Standard)

Chat completion endpoints accept a `messages` array and let the server apply the
appropriate chat/instruct template for the loaded model.

| Backend | Chat Endpoint | Template source |
|---|---|---|
| llama.cpp | `POST /v1/chat/completions` | Model metadata or `--chat-template` |
| OOBA | `POST /v1/chat/completions` | Auto-detected or `instruction_template` param |
| vLLM | `POST /v1/chat/completions` | Model tokenizer config |
| KoboldCpp | `POST /v1/chat/completions` | Model metadata |
| TabbyAPI | `POST /v1/chat/completions` | Jinja2 template (HuggingFace-compatible) |

### 7.4 Recommendation for The Bannered Mare

1. **Phase 1:** Support OpenAI-compatible chat completion (`/v1/chat/completions`).
   This works with ALL modern backends using the same adapter logic.
2. **Phase 2:** Add text completion support (`/v1/completions`) for advanced instruct
   mode control. The instruct formatting layer (from PROMPTS.md analysis) handles
   the `messages -> prompt string` conversion.
3. **Phase 3:** Add native KoboldAI API support (`/api/v1/generate`) for direct
   SillyTavern-style backends if needed.

---

## 8. Compatibility Matrix

### 8.1 OpenAI Parameter Support

| Parameter | llama.cpp | OOBA | vLLM | KoboldCpp | TabbyAPI |
|---|---|---|---|---|---|
| `temperature` | Yes | Yes | Yes | Yes | Yes |
| `top_p` | Yes | Yes | Yes | Yes | Yes |
| `top_k` | Yes (extra) | Yes (extra) | Yes (extra) | Yes | Yes (extra) |
| `max_tokens` | Yes | Yes | Yes | Yes | Yes |
| `stream` | Yes | Yes | Yes | Yes | Yes |
| `stop` | Yes | Yes | Yes | Yes (stop_sequence) | Yes |
| `frequency_penalty` | Yes | Yes | Yes | Via presence_penalty | Yes |
| `presence_penalty` | Yes | Yes | Yes | Yes | Yes |
| `seed` | Yes | Yes | Yes | Yes | Yes (via sampler) |
| `n` | Yes (n_cmpl) | Yes (limited) | Yes | No | Yes (limited) |
| `logprobs` | Yes | Yes | Yes | No | Yes |
| `top_logprobs` | Yes | Yes | Yes | No | Yes |
| `logit_bias` | Yes | Yes | Yes | Yes (logit_biases) | Yes |
| `response_format` | Yes (json_schema) | Limited | Yes (guided) | No | Yes (json/json_schema) |
| `tools` | Yes (--jinja) | Yes | Yes | Limited | Yes |
| `tool_choice` | Yes | Yes | Yes | No | Limited |
| `stream_options` | Yes | Yes | Yes | No | Yes |

### 8.2 Extra Sampler Support

| Parameter | llama.cpp | OOBA | vLLM | KoboldCpp | TabbyAPI |
|---|---|---|---|---|---|
| `min_p` | Yes | Yes | Yes | Yes | Yes |
| `typical_p` | Yes | Yes | No | Yes | Yes |
| `top_a` | No | Yes | No | Yes | Yes |
| `tfs` | No | Yes | No | Yes | Yes |
| `mirostat` (mode/tau/eta) | Yes | Yes | No | Yes | Yes |
| `repetition_penalty` | Yes (repeat_penalty) | Yes | Yes | Yes (rep_pen) | Yes |
| `grammar` (GBNF/EBNF) | Yes | Yes | No (own format) | Yes | Yes |
| `json_schema` | Yes | No | Yes (guided_json) | No | Yes |
| `regex_pattern` | No | No | Yes (guided_regex) | No | Yes |
| `sampler_order` / `sampler_priority` | Yes (samplers) | Yes | No | Yes | No (uses overrides) |
| `dynatemp` | Yes | Yes | No | Yes | Yes |
| `DRY` | Yes | Yes | No | Yes | Yes |
| `XTC` | Yes | Yes | No | Yes | Yes |
| `smoothing_factor` | No | Yes | No | Yes | Yes |
| `cfg_scale` / `guidance_scale` | No | Yes | No | No | Yes |
| `negative_prompt` | No | Yes | No | Yes | Yes |

### 8.3 Management Features

| Feature | llama.cpp | OOBA | vLLM | KoboldCpp | TabbyAPI |
|---|---|---|---|---|---|
| Model list | `/v1/models` | `/v1/models` | `/v1/models` | `/api/v1/model` | `/v1/models` |
| Model load/unload | No (fixed) | Yes (internal API) | No (fixed) | No (fixed) | Yes (admin API) |
| LoRA management | Yes (hot-swap) | Limited | No | No | Yes (admin API) |
| Tokenize | `/tokenize` | `/v1/internal/token/encode` | No | `/api/extra/tokencount` | `/v1/token/encode` |
| Detokenize | `/detokenize` | `/v1/internal/token/decode` | No | No | `/v1/token/decode` |
| Health check | `/health` | No | `/health` | No | `/health` |
| Abort generation | No | No | No | `/api/extra/abort` | `/api/extra/abort` |
| Template management | `/apply-template` | Via params | No | No | Yes (admin API) |

---

## 9. Extra Sampling Parameters (Not in OpenAI)

These parameters exist across local backends but are absent from the standard OpenAI API.
They are critical for RP quality tuning.

### 9.1 Probability Threshold Samplers

| Parameter | What it does | Who supports it |
|---|---|---|
| **`min_p`** | Discard tokens below (min_p * max_prob). Very popular for RP; often replaces top_p. | All five backends |
| **`typical_p`** | Locally typical sampling -- selects tokens close to expected information content. | llama.cpp, OOBA, KoboldCpp, TabbyAPI |
| **`top_a`** | Top-A -- adaptive threshold based on highest probability. | OOBA, KoboldCpp, TabbyAPI |
| **`tfs`** | Tail Free Sampling -- removes low-probability tail based on second derivative. | OOBA, KoboldCpp, TabbyAPI |
| **`top_n_sigma`** | Top-N sigma sampling based on standard deviations. | OOBA |

### 9.2 Repetition Control

| Parameter | What it does | Who supports it |
|---|---|---|
| **`repetition_penalty`** / **`rep_pen`** | Multiplicative penalty on repeated tokens. Different from OpenAI's additive `frequency_penalty`. | All five backends |
| **`DRY`** (`dry_multiplier`, `dry_base`, etc.) | Don't Repeat Yourself -- exponential penalty based on repeating sequence length. | llama.cpp, OOBA, KoboldCpp, TabbyAPI |
| **`XTC`** (`xtc_probability`, `xtc_threshold`) | Exclude Top Choices -- probabilistically removes top tokens to increase diversity. | llama.cpp, OOBA, KoboldCpp, TabbyAPI |
| **`encoder_repetition_penalty`** | Penalty applied to encoder-level repetitions. | OOBA |
| **`no_repeat_ngram_size`** | Hard ban on repeated N-grams. | OOBA |

### 9.3 Dynamic and Adaptive Sampling

| Parameter | What it does | Who supports it |
|---|---|---|
| **`dynatemp_range`** / **`dynatemp_exponent`** | Dynamic temperature that adjusts based on token probability distribution. | llama.cpp, OOBA, KoboldCpp, TabbyAPI |
| **`mirostat`** (mode 1 and 2) | Targets a specific perplexity level, automatically adjusting sampling. | llama.cpp, OOBA, KoboldCpp, TabbyAPI |
| **`smoothing_factor`** / **`smoothing_curve`** | Quadratic smoothing of token probabilities. | OOBA, KoboldCpp, TabbyAPI |
| **`adaptive_target`** / **`adaptive_decay`** | Adaptive sampling toward target entropy. | OOBA, KoboldCpp, TabbyAPI |

### 9.4 Constrained Generation

| Parameter | What it does | Who supports it |
|---|---|---|
| **`grammar`** / **`grammar_string`** | GBNF grammar constraint for structured output. | llama.cpp, OOBA, KoboldCpp, TabbyAPI |
| **`json_schema`** | JSON schema constraint (compiled to grammar). | llama.cpp, vLLM, TabbyAPI |
| **`guided_regex`** / **`regex_pattern`** | Regex constraint on output. | vLLM, TabbyAPI |
| **`guided_choice`** | Constrain output to one of N choices. | vLLM |

### 9.5 Sampler Ordering

| Parameter | Format | Who supports it |
|---|---|---|
| **`samplers`** | Array of sampler name strings | llama.cpp |
| **`sampler_order`** | Array of integer IDs | KoboldCpp |
| **`sampler_priority`** | Array of sampler name strings or pipe-delimited string | OOBA |
| Sampler override presets | YAML files with force/additive options | TabbyAPI |

---

## 10. Adapter Strategy

### 10.1 Architecture Decision

Given the analysis above, the adapter architecture from OPENAI.md section 12 applies
directly to local backends:

```
ProviderGateway
    |
    +-- OpenAIAdapter (base)
    |       |
    |       +-- used for: vLLM, TabbyAPI, OOBA, llama.cpp (OAI mode)
    |
    +-- LocalOpenAIAdapter (subclass of OpenAIAdapter)
    |       |
    |       +-- Removes Authorization header
    |       +-- Passes extra sampling params via CompletionRequest.extra
    |       +-- Adds model discovery via backend-specific endpoints
    |
    +-- KoboldAIAdapter (separate adapter, if native API needed)
            |
            +-- Text completion only (prompt string, not messages)
            +-- Different request/response shape
            +-- Used only for KoboldCpp/TabbyAPI native API
```

### 10.2 OpenAI-Compatible Path (Recommended)

For all modern local backends, the OpenAI-compatible path works:

1. **Set `base_url`** to the local server address (e.g., `http://localhost:8080/v1`).
2. **Remove or dummy the API key** -- most local servers ignore it or accept any value.
3. **Pass standard params** through `CompletionRequest` fields directly.
4. **Pass extra params** via `CompletionRequest.extra` dict -- the adapter
   serializes them into the request body alongside standard params.
5. **Parse standard response** -- all backends return OpenAI-compatible response shapes.

```python
# From OPENAI.md section 12.3:
@dataclass
class CompletionRequest:
    messages: list[ChatMessage]
    model: str
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    stop: list[str] | None = None
    stream: bool = False
    # ... standard fields ...
    extra: dict[str, Any] | None = None  # <-- local backend params go here
```

Example `extra` for a local backend request:
```python
extra = {
    "min_p": 0.05,
    "repetition_penalty": 1.1,
    "mirostat": 2,
    "mirostat_tau": 5.0,
    "grammar": '...',
    "cache_prompt": True,
    "samplers": ["dry", "top_k", "typ_p", "top_p", "min_p", "temperature"],
}
```

### 10.3 Provider Type Mapping

```python
class ProviderType(str, Enum):
    # Cloud providers
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OPENROUTER = "openrouter"
    XAI = "xai"

    # Local providers
    OLLAMA = "ollama"
    LLAMACPP = "llamacpp"
    VLLM = "vllm"
    KOBOLDCPP = "koboldcpp"
    OOBA = "ooba"
    TABBYAPI = "tabbyapi"
    CUSTOM = "custom"          # Generic OpenAI-compatible

# In ProviderGateway:
_adapters = {
    ProviderType.LLAMACPP: LocalOpenAIAdapter,
    ProviderType.VLLM: LocalOpenAIAdapter,
    ProviderType.OOBA: LocalOpenAIAdapter,
    ProviderType.TABBYAPI: LocalOpenAIAdapter,
    ProviderType.KOBOLDCPP: LocalOpenAIAdapter,  # OAI mode
    ProviderType.CUSTOM: LocalOpenAIAdapter,
}
```

### 10.4 Key Adapter Behaviors

| Behavior | Cloud (OpenAI) | Local Backend |
|---|---|---|
| Auth header | `Bearer <api_key>` | None or dummy |
| Base URL | `https://api.openai.com/v1` | `http://localhost:<port>/v1` |
| `model` field | Routes to specific model | Often ignored (server has one model) |
| Extra params | Not sent | Merged into request body from `extra` |
| Response parsing | Standard OpenAI | Standard OpenAI (+ optional extra fields) |
| Error handling | HTTP 4xx/5xx with OpenAI error shape | Varies; best-effort parsing |

---

## 11. Implementation Plan

### Phase 1: OpenAI-Compatible Chat Completion

**Target:** Works with all five local backends out of the box.

- Implement `LocalOpenAIAdapter` as a subclass of `OpenAIAdapter`:
  - Override `build_headers()` to omit or dummy Authorization.
  - Override `build_payload()` to merge `CompletionRequest.extra` into the body.
  - Keep `parse_response()` and `parse_stream_chunk()` identical to OpenAI.
- Add `ProviderType` entries for each local backend.
- Register adapters in `ProviderGateway`.
- Test with: llama.cpp, OOBA, vLLM, KoboldCpp, TabbyAPI.

### Phase 2: Model Discovery

**Target:** Detect available models and capabilities from each backend.

- `GET /v1/models` -- standard across all backends.
- Backend-specific info endpoints:
  - llama.cpp: `GET /props`, `GET /health`.
  - OOBA: `GET /v1/internal/model/list`.
  - TabbyAPI: `GET /v1/model`, `GET /health`, `GET /.well-known/serviceinfo`.
  - KoboldCpp: `GET /api/v1/model`, `GET /api/v1/config/max_context_length`.

### Phase 3: Text Completion Support

**Target:** Enable direct prompt control for advanced instruct mode.

- Add `POST /v1/completions` support to `LocalOpenAIAdapter`.
- Build instruct formatting layer that converts `CompletionRequest.messages` to a
  single prompt string using model-specific templates.
- This is the bridge between The Bannered Mare's internal `ChatMessage` format and the
  text completion API.

### Phase 4: Extra Sampling Parameters

**Target:** Expose local-backend-specific sampling through the UI/API.

- Define a `LocalSamplingParams` schema with the common local-only params:
  `min_p`, `typical_p`, `top_a`, `tfs`, `mirostat`, `repetition_penalty`,
  `grammar`, `sampler_order`, `dynatemp_range`, `dry_*`, `xtc_*`.
- Map these into `CompletionRequest.extra` automatically.
- Validate param support per backend (use compatibility matrix from section 8).

### Phase 5: Native API Support (Optional)

**Target:** Direct KoboldAI API for SillyTavern power users.

- Implement `KoboldAIAdapter` with native request/response shapes.
- `POST /api/v1/generate` with prompt string.
- `POST /api/extra/generate/stream` for SSE streaming.
- Useful for: KoboldCpp native, TabbyAPI KoboldAI endpoints.

### Phase 6: Management Features (Optional)

**Target:** Model loading, LoRA management, tokenization.

- Tokenize/detokenize via backend-appropriate endpoints.
- Model load/unload for TabbyAPI and OOBA.
- LoRA hot-swap for llama.cpp and TabbyAPI.
- These are admin-level features, not part of the core inference path.
