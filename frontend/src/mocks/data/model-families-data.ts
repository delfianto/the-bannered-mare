import type { components } from "@/api/schema";

// Model families mirror the backend seed fixtures (backend/src/fixtures/families/*.py):
// exact family_identifier / name / provider_types plus the full parameter, unsupported,
// and extra_metadata schemas. Synthetic ids stay `fam-<identifier>` so they read clearly.
type ModelFamilyItem = components["schemas"]["ModelFamilyResponse"];

const NOW = new Date().toISOString();

export const allModelFamiliesMock: ModelFamilyItem[] = [
  {
    id: "fam-deepseek-deepseek-r1",
    name: "DeepSeek R1",
    family_identifier: "deepseek/deepseek-r1",
    description:
      "DeepSeek R1 reasoner. Thinking model — temperature/top_p and penalties are ignored by the API.",
    provider_types: ["openrouter", "opencode", "opencode_go"],
    unsupported_parameters: ["temperature", "top_p", "frequency_penalty", "presence_penalty"],
    parameters: {
      max_tokens: {
        type: "int",
        default: 8192,
        min_value: 1,
        max_value: 65536,
      },
    },
    extra_metadata: {
      lineage: "deepseek",
      context_window: 128000,
      supports_vision: false,
      supports_function_calling: true,
      models: ["deepseek/deepseek-r1"],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-deepseek-deepseek-v3",
    name: "DeepSeek V3",
    family_identifier: "deepseek/deepseek-v3",
    description: "DeepSeek V3.1 / V3.2 chat models. 128K context, standard sampling.",
    provider_types: ["openrouter", "opencode", "opencode_go"],
    unsupported_parameters: [],
    parameters: {
      max_tokens: {
        type: "int",
        default: 4096,
        min_value: 1,
        max_value: 65536,
      },
      temperature: {
        type: "float",
        default: 1.0,
        min_value: 0.0,
        max_value: 2.0,
      },
      top_p: {
        type: "float",
        default: 0.95,
        min_value: 0.0,
        max_value: 1.0,
      },
      frequency_penalty: {
        type: "float",
        default: 0.0,
        min_value: -2.0,
        max_value: 2.0,
      },
      presence_penalty: {
        type: "float",
        default: 0.0,
        min_value: -2.0,
        max_value: 2.0,
      },
    },
    extra_metadata: {
      lineage: "deepseek",
      context_window: 128000,
      supports_vision: false,
      supports_function_calling: true,
      models: ["deepseek/deepseek-chat-v3.1", "deepseek/deepseek-v3.2"],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-deepseek-deepseek-v4",
    name: "DeepSeek V4",
    family_identifier: "deepseek/deepseek-v4",
    description: "DeepSeek V4 chat models (Pro / Flash). 128K context, standard sampling.",
    provider_types: ["openrouter", "opencode", "opencode_go"],
    unsupported_parameters: [],
    parameters: {
      max_tokens: {
        type: "int",
        default: 4096,
        min_value: 1,
        max_value: 65536,
      },
      temperature: {
        type: "float",
        default: 1.0,
        min_value: 0.0,
        max_value: 2.0,
      },
      top_p: {
        type: "float",
        default: 0.95,
        min_value: 0.0,
        max_value: 1.0,
      },
      frequency_penalty: {
        type: "float",
        default: 0.0,
        min_value: -2.0,
        max_value: 2.0,
      },
      presence_penalty: {
        type: "float",
        default: 0.0,
        min_value: -2.0,
        max_value: 2.0,
      },
    },
    extra_metadata: {
      lineage: "deepseek",
      context_window: 128000,
      supports_vision: false,
      supports_function_calling: true,
      models: ["deepseek/deepseek-v4-pro", "deepseek/deepseek-v4-flash"],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-google-gemma-4",
    name: "Gemma 4",
    family_identifier: "google/gemma-4",
    description:
      "Google Gemma 4 open-weight family (E2B, E4B, 12B, 26B A4B MoE, 31B). Multimodal, up to 256K context, thinking mode. Runs locally (Ollama GGUF) or hosted (OpenRouter).",
    provider_types: ["ollama", "lmstudio", "openrouter"],
    unsupported_parameters: [],
    parameters: {
      temperature: {
        type: "float",
        default: 1.0,
        min_value: 0.0,
        max_value: 2.0,
      },
      top_p: {
        type: "float",
        default: 0.95,
        min_value: 0.0,
        max_value: 1.0,
      },
      top_k: {
        type: "int",
        default: 64,
        min_value: 1,
        max_value: 200,
      },
      min_p: {
        type: "float",
        default: 0.0,
        min_value: 0.0,
        max_value: 1.0,
      },
      thinking_level: {
        type: "enum",
        default: "minimal",
        str_values: ["minimal", "low", "medium", "high"],
      },
      num_ctx: {
        type: "int",
        default: 32768,
        min_value: 512,
        max_value: 262144,
      },
      max_tokens: {
        type: "int",
        default: 4096,
        min_value: 1,
        max_value: 16384,
      },
    },
    extra_metadata: {
      lineage: "gemma",
      developer: "google",
      context_window: 262144,
      supports_vision: true,
      supports_thinking: true,
      quantization: "Q4_K_M",
      models: [
        "gemma4:e2b",
        "gemma4:e4b",
        "gemma4:12b",
        "gemma4:26b",
        "gemma4:31b",
        "google/gemma-4-31b-it",
        "google/gemma-4-26b-a4b-it",
      ],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-zai-glm-5",
    name: "GLM 5",
    family_identifier: "zai/glm-5",
    description:
      "Zhipu/Z.ai GLM-5 / 5.1 / 5.2 (incl. Turbo). Forced thinking with reasoning_effort (GLM-5.1+), temperature capped at 1.0, up to ~262K context. Routed via OpenRouter.",
    provider_types: ["openrouter", "opencode", "opencode_go"],
    unsupported_parameters: [],
    parameters: {
      max_tokens: {
        type: "int",
        default: 4096,
        min_value: 1,
        max_value: 128000,
      },
      reasoning_effort: {
        type: "enum",
        default: "medium",
        str_values: ["low", "medium", "high"],
      },
      temperature: {
        type: "float",
        default: 1.0,
        min_value: 0.0,
        max_value: 1.0,
      },
      top_p: {
        type: "float",
        default: 0.95,
        min_value: 0.01,
        max_value: 1.0,
      },
      top_k: {
        type: "int",
        default: 40,
        min_value: 1,
        max_value: 100,
      },
      thinking: {
        type: "object",
        properties: {
          type: {
            type: "enum",
            str_values: ["enabled", "disabled"],
          },
        },
      },
    },
    extra_metadata: {
      lineage: "glm",
      developer: "zhipu",
      context_window: 262144,
      supports_vision: false,
      supports_function_calling: true,
      thinking_behavior: "forced when enabled (5 / 5.1 / 5.2 / Turbo)",
      models: ["z-ai/glm-5", "z-ai/glm-5.1", "z-ai/glm-5.2"],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-moonshot-kimi-k2",
    name: "Kimi K2",
    family_identifier: "moonshot/kimi-k2",
    description:
      "Moonshot Kimi K2.5 / K2.6 (OpenAI/Anthropic-compatible). 256K context, full sampling surface plus reasoning_effort. Routed via OpenRouter.",
    provider_types: ["openrouter", "opencode", "opencode_go"],
    unsupported_parameters: ["top_k"],
    parameters: {
      max_tokens: {
        type: "int",
        default: 8192,
        min_value: 1,
        max_value: 65536,
      },
      temperature: {
        type: "float",
        default: 0.6,
        min_value: 0.0,
        max_value: 1.0,
      },
      top_p: {
        type: "float",
        default: 0.95,
        min_value: 0.0,
        max_value: 1.0,
      },
      frequency_penalty: {
        type: "float",
        default: 0.0,
        min_value: -2.0,
        max_value: 2.0,
      },
      presence_penalty: {
        type: "float",
        default: 0.0,
        min_value: -2.0,
        max_value: 2.0,
      },
      reasoning_effort: {
        type: "enum",
        default: "medium",
        str_values: ["low", "medium", "high"],
      },
    },
    extra_metadata: {
      lineage: "kimi",
      developer: "moonshot",
      context_window: 262144,
      supports_vision: false,
      supports_function_calling: true,
      note: "thinking ~temp 1.0, instant ~temp 0.6; max_tokens >= 16000 for full reasoning",
      models: ["moonshotai/kimi-k2.5", "moonshotai/kimi-k2.6"],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-meta-llama-3",
    name: "Llama 3",
    family_identifier: "meta/llama-3",
    description:
      "Meta Llama 3 / 3.1 / 3.3 and the community RP finetunes & merges built on them (Sao10K Euryale & Stheno, NeverSleep Lumimaid, TheDrummer Anubis, Steelskull Nevoria, Nous Hermes 3, Lunaris). Classic Llama-3 finetunes are 8K context; 3.1/3.3 are 128K. Run locally (Ollama/vLLM) or hosted (OpenRouter).",
    provider_types: ["ollama", "lmstudio", "openrouter"],
    unsupported_parameters: [],
    parameters: {
      max_tokens: {
        type: "int",
        default: 4096,
        min_value: 1,
        max_value: 16384,
      },
      temperature: {
        type: "float",
        default: 1.0,
        min_value: 0.0,
        max_value: 2.0,
      },
      top_p: {
        type: "float",
        default: 0.95,
        min_value: 0.0,
        max_value: 1.0,
      },
      top_k: {
        type: "int",
        default: 50,
        min_value: 1,
        max_value: 200,
      },
      min_p: {
        type: "float",
        default: 0.05,
        min_value: 0.0,
        max_value: 1.0,
      },
      repetition_penalty: {
        type: "float",
        default: 1.05,
        min_value: 1.0,
        max_value: 2.0,
      },
      num_ctx: {
        type: "int",
        default: 8192,
        min_value: 512,
        max_value: 131072,
      },
    },
    extra_metadata: {
      lineage: "llama",
      developer: "meta + community",
      context_window: 131072,
      supports_vision: false,
      supports_function_calling: false,
      notable_finetunes: {
        "Sao10K Euryale":
          "L3 v2.1 (70B/8K), L3.1 v2.2 (70B/128K), L3.3 v2.3 (70B/128K) — RP/creative flagship",
        "Sao10K Hanami": "L3.1 70B (X1) — RP-tuned Euryale sibling",
        "Sao10K Stheno": "L3 v3.2 (8B/8K), L3.1 v3.4 (8B) — beloved small-model RP",
        "Sao10K Lunaris": "L3 8B merge (Stheno 3.2 + others) — reliable L3 RP",
        "Steelskull Nevoria": "L3.3 70B merge",
        "Nous Hermes 3": "L3.1 8B/70B/405B — steerable, strong instruction following",
      },
      models: [
        "sao10k/l3.3-euryale-70b",
        "sao10k/l3.1-70b-hanami-x1",
        "nousresearch/hermes-3-llama-3.1-70b",
        "sao10k/l3-lunaris-8b",
      ],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-mistral-mistral-small",
    name: "Mistral Small 24B",
    family_identifier: "mistral/mistral-small",
    description:
      "Mistral Small 24B (3.1 / 3.2, including the Magistral reasoning variant) base and its finetunes (e.g. TheDrummer's Skyfall, Cydonia). 128K context. Local (Ollama GGUF) or hosted (OpenRouter).",
    provider_types: ["ollama", "lmstudio", "openrouter"],
    unsupported_parameters: [],
    parameters: {
      temperature: {
        type: "float",
        default: 0.9,
        min_value: 0.0,
        max_value: 2.0,
      },
      top_p: {
        type: "float",
        default: 0.92,
        min_value: 0.0,
        max_value: 1.0,
      },
      top_k: {
        type: "int",
        default: 65,
        min_value: 1,
        max_value: 200,
      },
      min_p: {
        type: "float",
        default: 0.02,
        min_value: 0.0,
        max_value: 1.0,
      },
      repeat_penalty: {
        type: "float",
        default: 1.1,
        min_value: 1.0,
        max_value: 2.0,
      },
      num_ctx: {
        type: "int",
        default: 8192,
        min_value: 512,
        max_value: 131072,
      },
      max_tokens: {
        type: "int",
        default: 4096,
        min_value: 1,
        max_value: 16384,
      },
    },
    extra_metadata: {
      lineage: "mistral",
      base_family: "Mistral Small 24B (3.1 / 3.2, incl. Magistral)",
      base_models: [
        "mistralai/Mistral-Small-3.2-24B-Instruct-2507",
        "mistralai/Magistral-Small-2506",
        "mistralai/Mistral-Small-3.1-24B-Instruct-2503",
      ],
      context_window: 131072,
      supports_vision: false,
      supports_function_calling: false,
      quantization: "Q4_K_M",
      finetunes: {
        "thedrummer/skyfall-36b-v2": {
          author: "TheDrummer",
          base_model: "mistralai/Mistral-Small-3.2-24B-Instruct-2507",
          note: "upscaled to 36B",
        },
        "thedrummer/cydonia-24b-v4.1": {
          author: "TheDrummer",
          base_model: "mistralai/Mistral-Small-3.2-24B-Instruct-2507",
        },
      },
      models: ["thedrummer/skyfall-36b-v2", "thedrummer/cydonia-24b-v4.1"],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-mistral-mistral-nemo",
    name: "Mistral Nemo 12B",
    family_identifier: "mistral/mistral-nemo",
    description:
      "Mistral Nemo 12B base and its finetunes (e.g. TheDrummer's Rocinante). Text-only, ~128K context. Local (Ollama GGUF) or hosted (OpenRouter).",
    provider_types: ["ollama", "lmstudio", "openrouter"],
    unsupported_parameters: [],
    parameters: {
      temperature: {
        type: "float",
        default: 0.9,
        min_value: 0.0,
        max_value: 2.0,
      },
      top_p: {
        type: "float",
        default: 0.92,
        min_value: 0.0,
        max_value: 1.0,
      },
      top_k: {
        type: "int",
        default: 65,
        min_value: 1,
        max_value: 200,
      },
      min_p: {
        type: "float",
        default: 0.02,
        min_value: 0.0,
        max_value: 1.0,
      },
      repeat_penalty: {
        type: "float",
        default: 1.1,
        min_value: 1.0,
        max_value: 2.0,
      },
      num_ctx: {
        type: "int",
        default: 8192,
        min_value: 512,
        max_value: 131072,
      },
      max_tokens: {
        type: "int",
        default: 4096,
        min_value: 1,
        max_value: 16384,
      },
    },
    extra_metadata: {
      lineage: "mistral",
      base_family: "Mistral Nemo 12B",
      base_model: "mistralai/Mistral-Nemo-Base-2407",
      context_window: 131072,
      supports_vision: false,
      supports_function_calling: false,
      quantization: "Q4_K_M",
      finetunes: {
        "thedrummer/rocinante-12b": {
          author: "TheDrummer",
          base_model: "mistralai/Mistral-Nemo-Base-2407",
        },
        "thedrummer/unslopnemo-12b": {
          author: "TheDrummer",
          base_model: "mistralai/Mistral-Nemo-Base-2407",
        },
      },
      models: ["thedrummer/rocinante-12b", "thedrummer/unslopnemo-12b"],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-poolside-laguna",
    name: "Poolside Laguna",
    family_identifier: "poolside/laguna",
    description:
      "Poolside Laguna coding-agent models (M.1 flagship, XS.2 compact). fp8-quantized, tool calling + reasoning, 262K context, 32K max output. Narrow sampler (temperature only). Free on OpenRouter for now.",
    provider_types: ["openrouter"],
    unsupported_parameters: ["top_p", "top_k", "frequency_penalty", "presence_penalty", "stop"],
    parameters: {
      max_tokens: {
        type: "int",
        default: 4096,
        min_value: 1,
        max_value: 32768,
      },
      temperature: {
        type: "float",
        default: 1.0,
        min_value: 0.0,
        max_value: 2.0,
      },
    },
    extra_metadata: {
      lineage: "poolside",
      developer: "poolside",
      context_window: 262144,
      supports_vision: false,
      supports_function_calling: true,
      supports_reasoning: true,
      note: "coding-agent models (fp8); free on OpenRouter for now",
      models: ["poolside/laguna-m.1", "poolside/laguna-xs-2.1"],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-xiaomi-mimo-v2-5",
    name: "Xiaomi MiMo V2.5",
    family_identifier: "xiaomi/mimo-v2.5",
    description:
      "Xiaomi MiMo V2.5 and V2.5-Pro. 1M context, 131K max output, reasoning-capable. Pro is a 1.02T MoE (42B active). top_k/min_p/repetition_penalty are Pro-only. Routed via OpenRouter.",
    provider_types: ["openrouter", "opencode", "opencode_go"],
    unsupported_parameters: [],
    parameters: {
      max_tokens: {
        type: "int",
        default: 4096,
        min_value: 1,
        max_value: 131072,
      },
      temperature: {
        type: "float",
        default: 1.0,
        min_value: 0.0,
        max_value: 2.0,
      },
      top_p: {
        type: "float",
        default: 0.95,
        min_value: 0.0,
        max_value: 1.0,
      },
      top_k: {
        type: "int",
        default: 40,
        min_value: 1,
        max_value: 100,
      },
      min_p: {
        type: "float",
        default: 0.0,
        min_value: 0.0,
        max_value: 1.0,
      },
      frequency_penalty: {
        type: "float",
        default: 0.0,
        min_value: -2.0,
        max_value: 2.0,
      },
      presence_penalty: {
        type: "float",
        default: 0.0,
        min_value: -2.0,
        max_value: 2.0,
      },
      repetition_penalty: {
        type: "float",
        default: 1.0,
        min_value: 1.0,
        max_value: 2.0,
      },
    },
    extra_metadata: {
      lineage: "mimo",
      developer: "xiaomi",
      context_window: 1048576,
      supports_vision: false,
      supports_function_calling: true,
      supports_reasoning: true,
      note: "V2.5-Pro is a 1.02T MoE (42B active); top_k/min_p/repetition_penalty are Pro-only. Recommended temp 1.0 / top_p 0.95.",
      models: ["xiaomi/mimo-v2.5", "xiaomi/mimo-v2.5-pro"],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-openai-gpt-4o",
    name: "OpenAI GPT-4o",
    family_identifier: "openai/gpt-4o",
    description: "OpenAI GPT-4o family (incl. mini). 128K context, multimodal, classic sampling.",
    provider_types: ["openai", "openrouter", "opencode"],
    unsupported_parameters: [
      "max_tokens",
      "reasoning_effort",
      "summary",
      "verbosity",
      "top_k",
      "min_p",
      "top_a",
      "repetition_penalty",
    ],
    parameters: {
      max_completion_tokens: {
        type: "int",
        default: 4096,
        min_value: 1,
        max_value: 16384,
      },
      temperature: {
        type: "float",
        default: 1.0,
        min_value: 0.0,
        max_value: 2.0,
      },
      top_p: {
        type: "float",
        default: 1.0,
        min_value: 0.0,
        max_value: 1.0,
      },
      frequency_penalty: {
        type: "float",
        default: 0.0,
        min_value: -2.0,
        max_value: 2.0,
      },
      presence_penalty: {
        type: "float",
        default: 0.0,
        min_value: -2.0,
        max_value: 2.0,
      },
      stop: {
        type: "list",
        item_schema: {
          type: "string",
        },
      },
      stream: {
        type: "boolean",
        default: true,
      },
      response_format: {
        type: "json",
        default: null,
      },
    },
    extra_metadata: {
      lineage: "gpt",
      developer: "openai",
      context_window: 128000,
      supports_vision: true,
      supports_function_calling: true,
      models: ["gpt-4o", "gpt-4o-mini"],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-openai-gpt-5-chat",
    name: "OpenAI GPT-5 Chat",
    family_identifier: "openai/gpt-5-chat",
    description:
      "OpenAI GPT-5 chat models (5, 5.1, 5.2, 5.3) — non-reasoning, classic sampling. Up to 400K context.",
    provider_types: ["openai", "openrouter", "opencode"],
    unsupported_parameters: [
      "max_tokens",
      "reasoning_effort",
      "summary",
      "verbosity",
      "top_k",
      "min_p",
      "top_a",
      "repetition_penalty",
    ],
    parameters: {
      max_completion_tokens: {
        type: "int",
        default: 8192,
        min_value: 1,
        max_value: 128000,
      },
      temperature: {
        type: "float",
        default: 1.0,
        min_value: 0.0,
        max_value: 2.0,
      },
      top_p: {
        type: "float",
        default: 1.0,
        min_value: 0.0,
        max_value: 1.0,
      },
      frequency_penalty: {
        type: "float",
        default: 0.0,
        min_value: -2.0,
        max_value: 2.0,
      },
      presence_penalty: {
        type: "float",
        default: 0.0,
        min_value: -2.0,
        max_value: 2.0,
      },
      stop: {
        type: "list",
        item_schema: {
          type: "string",
        },
      },
      stream: {
        type: "boolean",
        default: true,
      },
      response_format: {
        type: "json",
        default: null,
      },
    },
    extra_metadata: {
      lineage: "gpt",
      developer: "openai",
      context_window: 400000,
      supports_vision: false,
      supports_function_calling: true,
      models: [
        "gpt-5-chat-latest",
        "gpt-5.1-chat-latest",
        "gpt-5.2-chat-latest",
        "gpt-5.3-chat-latest",
      ],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-openai-gpt-5-thinking",
    name: "OpenAI GPT-5 Thinking",
    family_identifier: "openai/gpt-5-thinking",
    description:
      "OpenAI GPT-5.x reasoning models (5.4, 5.5, incl. mini/nano/pro). Extended reasoning via reasoning_effort + verbosity; sampling parameters are removed. Up to ~1M context.",
    provider_types: ["openai", "openrouter", "opencode"],
    unsupported_parameters: [
      "max_tokens",
      "temperature",
      "top_p",
      "frequency_penalty",
      "presence_penalty",
      "logprobs",
      "top_logprobs",
      "logit_bias",
      "top_k",
      "min_p",
      "top_a",
      "repetition_penalty",
    ],
    parameters: {
      max_completion_tokens: {
        type: "int",
        default: 8192,
        min_value: 1,
        max_value: 128000,
      },
      reasoning_effort: {
        type: "enum",
        default: "medium",
        str_values: ["low", "medium", "high", "xhigh"],
      },
      verbosity: {
        type: "enum",
        default: "medium",
        str_values: ["low", "medium", "high"],
      },
      summary: {
        type: "enum",
        default: "auto",
        str_values: ["concise", "detailed", "auto"],
      },
      stop: {
        type: "list",
        item_schema: {
          type: "string",
        },
      },
      stream: {
        type: "boolean",
        default: true,
      },
      response_format: {
        type: "json",
        default: null,
      },
    },
    extra_metadata: {
      lineage: "gpt",
      developer: "openai",
      context_window: 1000000,
      supports_vision: true,
      supports_function_calling: true,
      note: "reasoning_effort xhigh is GPT-5.5+ only; 5.4 caps at high",
      models: ["gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-5.4-pro", "gpt-5.5", "gpt-5.5-pro"],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-anthropic-claude-haiku-4-5",
    name: "Claude 4.5 Haiku",
    family_identifier: "anthropic/claude-haiku-4.5",
    description: "Anthropic Claude 4.5 Haiku. Fast, low-cost tier for RP.",
    provider_types: ["anthropic", "openrouter", "opencode"],
    unsupported_parameters: [],
    parameters: {
      max_tokens: {
        type: "int",
        default: 4096,
        min_value: 1,
        max_value: 16384,
      },
      temperature: {
        type: "float",
        min_value: 0.0,
        max_value: 1.0,
      },
      top_p: {
        type: "float",
        min_value: 0.0,
        max_value: 1.0,
      },
      top_k: {
        type: "int",
        default: 40,
        min_value: 1,
      },
      stop_sequences: {
        type: "list",
        item_schema: {
          type: "string",
        },
      },
      stream: {
        type: "boolean",
        default: true,
      },
      system: {
        type: "string",
      },
      thinking: {
        type: "object",
        properties: {
          type: {
            type: "enum",
            str_values: ["enabled", "disabled"],
          },
          budget_tokens: {
            type: "int",
            min_value: 1024,
            max_value: 20000,
          },
        },
      },
    },
    extra_metadata: {
      lineage: "claude-haiku",
      context_window: 500000,
      supports_vision: true,
      supports_function_calling: true,
      models: ["claude-4.5-haiku"],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-anthropic-claude-sonnet-4-5",
    name: "Claude 4.5 Sonnet",
    family_identifier: "anthropic/claude-sonnet-4.5",
    description: "Anthropic Claude 4.5 Sonnet. Balanced speed/intelligence for RP.",
    provider_types: ["anthropic", "openrouter", "opencode"],
    unsupported_parameters: [],
    parameters: {
      max_tokens: {
        type: "int",
        default: 4096,
        min_value: 1,
        max_value: 16384,
      },
      temperature: {
        type: "float",
        min_value: 0.0,
        max_value: 1.0,
      },
      top_p: {
        type: "float",
        min_value: 0.0,
        max_value: 1.0,
      },
      top_k: {
        type: "int",
        default: 40,
        min_value: 1,
      },
      stop_sequences: {
        type: "list",
        item_schema: {
          type: "string",
        },
      },
      stream: {
        type: "boolean",
        default: true,
      },
      system: {
        type: "string",
      },
      thinking: {
        type: "object",
        properties: {
          type: {
            type: "enum",
            str_values: ["enabled", "disabled"],
          },
          budget_tokens: {
            type: "int",
            min_value: 1024,
            max_value: 20000,
          },
        },
      },
    },
    extra_metadata: {
      lineage: "claude-sonnet",
      context_window: 500000,
      supports_vision: true,
      supports_function_calling: true,
      models: ["claude-4.5-sonnet"],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-anthropic-claude-opus-4-8",
    name: "Claude 4.8 Opus",
    family_identifier: "anthropic/claude-opus-4.8",
    description:
      "Anthropic Claude 4.8 Opus. Most capable Opus tier; state-of-the-art long-horizon agentic work. Same surface as 4.7 — adaptive thinking only, no sampling parameters.",
    provider_types: ["anthropic", "openrouter", "opencode"],
    unsupported_parameters: ["temperature", "top_p", "top_k", "budget_tokens"],
    parameters: {
      max_tokens: {
        type: "int",
        default: 8192,
        min_value: 1,
        max_value: 128000,
      },
      effort: {
        type: "enum",
        default: "high",
        str_values: ["low", "medium", "high", "xhigh", "max"],
      },
      stop_sequences: {
        type: "list",
        item_schema: {
          type: "string",
        },
      },
      stream: {
        type: "boolean",
        default: true,
      },
      system: {
        type: "string",
      },
      thinking: {
        type: "object",
        properties: {
          type: {
            type: "enum",
            str_values: ["adaptive", "disabled"],
          },
        },
      },
      metadata: {
        type: "object",
      },
    },
    extra_metadata: {
      lineage: "claude-opus",
      context_window: 1000000,
      supports_vision: true,
      supports_function_calling: true,
      models: ["claude-4.8-opus"],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-google-gemini-2-5",
    name: "Gemini 2.5",
    family_identifier: "google/gemini-2.5",
    description:
      "Google Gemini 2.5 Pro / Flash / Flash-Lite. 1M context, full sampling surface (top_k + penalties) and a numeric thinking budget.",
    provider_types: ["google", "openrouter"],
    unsupported_parameters: [],
    parameters: {
      max_output_tokens: {
        type: "int",
        default: 8192,
        min_value: 1,
        max_value: 65536,
      },
      temperature: {
        type: "float",
        default: 1.0,
        min_value: 0.0,
        max_value: 2.0,
      },
      top_p: {
        type: "float",
        default: 0.95,
        min_value: 0.0,
        max_value: 1.0,
      },
      top_k: {
        type: "int",
        default: 40,
        min_value: 1,
      },
      stop_sequences: {
        type: "list",
        item_schema: {
          type: "string",
        },
      },
      frequency_penalty: {
        type: "float",
        default: 0.0,
        min_value: -2.0,
        max_value: 2.0,
      },
      presence_penalty: {
        type: "float",
        default: 0.0,
        min_value: -2.0,
        max_value: 2.0,
      },
      safety_settings: {
        type: "list",
        default: [
          {
            category: "HARM_CATEGORY_HARASSMENT",
            threshold: "BLOCK_NONE",
          },
          {
            category: "HARM_CATEGORY_HATE_SPEECH",
            threshold: "BLOCK_NONE",
          },
          {
            category: "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            threshold: "BLOCK_NONE",
          },
          {
            category: "HARM_CATEGORY_DANGEROUS_CONTENT",
            threshold: "BLOCK_NONE",
          },
        ],
        item_schema: {
          type: "object",
          properties: {
            category: {
              type: "enum",
              str_values: [
                "HARM_CATEGORY_HARASSMENT",
                "HARM_CATEGORY_HATE_SPEECH",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "HARM_CATEGORY_DANGEROUS_CONTENT",
                "HARM_CATEGORY_CIVIC_INTEGRITY",
              ],
            },
            threshold: {
              type: "enum",
              default: "BLOCK_NONE",
              str_values: [
                "OFF",
                "BLOCK_NONE",
                "BLOCK_ONLY_HIGH",
                "BLOCK_MEDIUM_AND_ABOVE",
                "BLOCK_LOW_AND_ABOVE",
              ],
            },
          },
        },
      },
      thinking_budget: {
        type: "int",
        default: -1,
        min_value: -1,
        max_value: 32768,
      },
    },
    extra_metadata: {
      lineage: "gemini",
      developer: "google",
      context_window: 1000000,
      supports_vision: true,
      supports_function_calling: true,
      models: ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite"],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-google-gemini-3-5",
    name: "Gemini 3.5",
    family_identifier: "google/gemini-3.5",
    description:
      "Google Gemini 3.5 Flash. 1M context. Removes temperature/top_p/top_k entirely; thinking_level (minimal/low/medium/high, default medium) + media_resolution.",
    provider_types: ["google", "openrouter", "opencode"],
    unsupported_parameters: [
      "temperature",
      "top_p",
      "top_k",
      "frequency_penalty",
      "presence_penalty",
      "thinking_budget",
    ],
    parameters: {
      max_output_tokens: {
        type: "int",
        default: 8192,
        min_value: 1,
        max_value: 65536,
      },
      stop_sequences: {
        type: "list",
        item_schema: {
          type: "string",
        },
      },
      safety_settings: {
        type: "list",
        default: [
          {
            category: "HARM_CATEGORY_HARASSMENT",
            threshold: "BLOCK_NONE",
          },
          {
            category: "HARM_CATEGORY_HATE_SPEECH",
            threshold: "BLOCK_NONE",
          },
          {
            category: "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            threshold: "BLOCK_NONE",
          },
          {
            category: "HARM_CATEGORY_DANGEROUS_CONTENT",
            threshold: "BLOCK_NONE",
          },
        ],
        item_schema: {
          type: "object",
          properties: {
            category: {
              type: "enum",
              str_values: [
                "HARM_CATEGORY_HARASSMENT",
                "HARM_CATEGORY_HATE_SPEECH",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "HARM_CATEGORY_DANGEROUS_CONTENT",
                "HARM_CATEGORY_CIVIC_INTEGRITY",
              ],
            },
            threshold: {
              type: "enum",
              default: "BLOCK_NONE",
              str_values: [
                "OFF",
                "BLOCK_NONE",
                "BLOCK_ONLY_HIGH",
                "BLOCK_MEDIUM_AND_ABOVE",
                "BLOCK_LOW_AND_ABOVE",
              ],
            },
          },
        },
      },
      thinking_level: {
        type: "enum",
        default: "medium",
        str_values: ["minimal", "low", "medium", "high"],
      },
      media_resolution: {
        type: "enum",
        default: "MEDIA_RESOLUTION_MEDIUM",
        str_values: [
          "MEDIA_RESOLUTION_LOW",
          "MEDIA_RESOLUTION_MEDIUM",
          "MEDIA_RESOLUTION_HIGH",
          "MEDIA_RESOLUTION_ULTRA_HIGH",
        ],
      },
    },
    extra_metadata: {
      lineage: "gemini",
      developer: "google",
      context_window: 1000000,
      supports_vision: true,
      supports_function_calling: true,
      models: ["gemini-3.5-flash"],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-google-gemini-3",
    name: "Gemini 3",
    family_identifier: "google/gemini-3",
    description:
      "Google Gemini 3.0 / 3.1 Pro / Flash / Flash-Lite. 1M context. thinking_level (low/medium/high) + media_resolution; top_k and penalties removed, temperature defaults to 1.0 (changing it is discouraged).",
    provider_types: ["google", "openrouter"],
    unsupported_parameters: ["top_k", "frequency_penalty", "presence_penalty", "thinking_budget"],
    parameters: {
      max_output_tokens: {
        type: "int",
        default: 8192,
        min_value: 1,
        max_value: 65536,
      },
      temperature: {
        type: "float",
        default: 1.0,
        min_value: 0.0,
        max_value: 2.0,
      },
      top_p: {
        type: "float",
        default: 0.95,
        min_value: 0.0,
        max_value: 1.0,
      },
      stop_sequences: {
        type: "list",
        item_schema: {
          type: "string",
        },
      },
      safety_settings: {
        type: "list",
        default: [
          {
            category: "HARM_CATEGORY_HARASSMENT",
            threshold: "BLOCK_NONE",
          },
          {
            category: "HARM_CATEGORY_HATE_SPEECH",
            threshold: "BLOCK_NONE",
          },
          {
            category: "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            threshold: "BLOCK_NONE",
          },
          {
            category: "HARM_CATEGORY_DANGEROUS_CONTENT",
            threshold: "BLOCK_NONE",
          },
        ],
        item_schema: {
          type: "object",
          properties: {
            category: {
              type: "enum",
              str_values: [
                "HARM_CATEGORY_HARASSMENT",
                "HARM_CATEGORY_HATE_SPEECH",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "HARM_CATEGORY_DANGEROUS_CONTENT",
                "HARM_CATEGORY_CIVIC_INTEGRITY",
              ],
            },
            threshold: {
              type: "enum",
              default: "BLOCK_NONE",
              str_values: [
                "OFF",
                "BLOCK_NONE",
                "BLOCK_ONLY_HIGH",
                "BLOCK_MEDIUM_AND_ABOVE",
                "BLOCK_LOW_AND_ABOVE",
              ],
            },
          },
        },
      },
      thinking_level: {
        type: "enum",
        default: "high",
        str_values: ["low", "medium", "high"],
      },
      media_resolution: {
        type: "enum",
        default: "MEDIA_RESOLUTION_MEDIUM",
        str_values: [
          "MEDIA_RESOLUTION_LOW",
          "MEDIA_RESOLUTION_MEDIUM",
          "MEDIA_RESOLUTION_HIGH",
          "MEDIA_RESOLUTION_ULTRA_HIGH",
        ],
      },
    },
    extra_metadata: {
      lineage: "gemini",
      developer: "google",
      context_window: 1000000,
      supports_vision: true,
      supports_function_calling: true,
      models: ["gemini-3-flash-preview", "gemini-3.1-pro-preview", "gemini-3.1-flash-lite"],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-xai-grok-4-5",
    name: "Grok 4.5",
    family_identifier: "xai/grok-4.5",
    description:
      "xAI Grok 4.5 — reasoning model for coding, agentic, and knowledge work. 500K context, up to 30K output, reasoning_effort (low/medium/high, default high), and native tool calling (web/X search, code execution). As a reasoning model it rejects stop and the frequency/presence penalties. Served via xAI, OpenRouter, or OpenCode Zen.",
    provider_types: ["xai", "openrouter", "opencode"],
    unsupported_parameters: [
      "stop",
      "frequency_penalty",
      "presence_penalty",
      "top_k",
      "min_p",
      "top_a",
      "repetition_penalty",
    ],
    parameters: {
      max_completion_tokens: {
        type: "int",
        default: 4096,
        min_value: 1,
        max_value: 30000,
      },
      temperature: {
        type: "float",
        default: 1.0,
        min_value: 0.0,
        max_value: 2.0,
      },
      top_p: {
        type: "float",
        default: 1.0,
        min_value: 0.0,
        max_value: 1.0,
      },
      stream: {
        type: "boolean",
        default: true,
      },
      reasoning_effort: {
        type: "enum",
        default: "high",
        str_values: ["low", "medium", "high"],
      },
    },
    extra_metadata: {
      lineage: "grok",
      developer: "xai",
      context_window: 500000,
      supports_vision: true,
      supports_function_calling: true,
      note: "reasoning-only (low/medium/high, default high); native web/X search + code execution",
      models: ["grok-4.5"],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-xai-grok-4-2",
    name: "Grok 4.2",
    family_identifier: "xai/grok-4.2",
    description:
      "xAI Grok 4.20 (named 4.2 here) — flagship + multi-agent variant. 2M context, always-on reasoning (no stop/penalties). The multi-agent variant scales parallel agents via reasoning_effort (low/medium = 4, high/xhigh = 16) and agent_count, with web_search/x_search. Served via xAI or OpenRouter.",
    provider_types: ["xai", "openrouter"],
    unsupported_parameters: [
      "stop",
      "frequency_penalty",
      "presence_penalty",
      "top_k",
      "min_p",
      "top_a",
      "repetition_penalty",
    ],
    parameters: {
      max_completion_tokens: {
        type: "int",
        default: 4096,
        min_value: 1,
        max_value: 2000000,
      },
      temperature: {
        type: "float",
        default: 1.0,
        min_value: 0.0,
        max_value: 2.0,
      },
      top_p: {
        type: "float",
        default: 1.0,
        min_value: 0.0,
        max_value: 1.0,
      },
      stream: {
        type: "boolean",
        default: true,
      },
      reasoning_effort: {
        type: "enum",
        default: "high",
        str_values: ["low", "medium", "high", "xhigh"],
      },
      agent_count: {
        type: "int",
        min_value: 1,
        max_value: 16,
      },
    },
    extra_metadata: {
      lineage: "grok",
      developer: "xai",
      context_window: 2000000,
      supports_vision: true,
      supports_function_calling: true,
      note: "official name Grok 4.20; up to 2M output",
      models: ["grok-4.20"],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-zai-glm-4",
    name: "GLM 4",
    family_identifier: "zai/glm-4",
    description:
      "Zhipu/Z.ai GLM-4.5 / 4.6 / 4.7 (incl. Air, Flash). Hybrid thinking, temperature capped at 1.0, 200K context. Routed via OpenRouter.",
    provider_types: ["openrouter", "opencode", "opencode_go"],
    unsupported_parameters: [],
    parameters: {
      max_tokens: {
        type: "int",
        default: 4096,
        min_value: 1,
        max_value: 128000,
      },
      temperature: {
        type: "float",
        default: 1.0,
        min_value: 0.0,
        max_value: 1.0,
      },
      top_p: {
        type: "float",
        default: 0.95,
        min_value: 0.01,
        max_value: 1.0,
      },
      top_k: {
        type: "int",
        default: 40,
        min_value: 1,
        max_value: 100,
      },
      thinking: {
        type: "object",
        properties: {
          type: {
            type: "enum",
            str_values: ["enabled", "disabled"],
          },
        },
      },
    },
    extra_metadata: {
      lineage: "glm",
      developer: "zhipu",
      context_window: 200000,
      supports_vision: false,
      supports_function_calling: true,
      thinking_behavior: "auto on 4.5/4.6, forced-when-enabled on 4.7",
      models: ["z-ai/glm-4.7", "z-ai/glm-4.7-flash", "z-ai/glm-4.5-air"],
    },
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "fam-minimax-minimax-m3",
    name: "MiniMax M3",
    family_identifier: "minimax/minimax-m3",
    description:
      "MiniMax M3. 1M context, up to 512K output. Toggleable thinking (adaptive/disabled); top_k and penalties removed. Routed via OpenRouter.",
    provider_types: ["openrouter", "opencode", "opencode_go"],
    unsupported_parameters: ["top_k", "frequency_penalty", "presence_penalty"],
    parameters: {
      max_tokens: {
        type: "int",
        default: 8192,
        min_value: 1,
        max_value: 512000,
      },
      temperature: {
        type: "float",
        default: 1.0,
        min_value: 0.01,
        max_value: 1.0,
      },
      top_p: {
        type: "float",
        default: 0.95,
        min_value: 0.01,
        max_value: 1.0,
      },
      thinking: {
        type: "object",
        properties: {
          type: {
            type: "enum",
            str_values: ["adaptive", "disabled"],
          },
        },
      },
    },
    extra_metadata: {
      lineage: "minimax",
      developer: "minimax",
      context_window: 1048576,
      supports_vision: false,
      supports_function_calling: true,
      models: ["minimax/minimax-m3"],
    },
    created_at: NOW,
    updated_at: NOW,
  },
];
