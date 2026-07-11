import type { components } from "@/api/schema";

type ModelItem = components["schemas"]["ModelResponse"];
type ModelRoute = components["schemas"]["ModelRouteResponse"];

const NOW = new Date().toISOString();

function makeRoute(
  registryId: string,
  providerId: string,
  identifier: string,
  suffix?: string,
): ModelRoute {
  return {
    id: `${registryId.replace(/^mdl-/, "rt-")}${suffix ? `-${suffix}` : ""}`,
    model_registry_id: registryId,
    provider_id: providerId,
    model_identifier: identifier,
    enabled: true,
    created_at: NOW,
    updated_at: NOW,
  };
}

// Most registries expose a single provider route; `original_identifier` is the
// provider-independent native name the backend would derive from that route.
function single(
  id: string,
  displayName: string,
  originalIdentifier: string,
  modelFamilyId: string,
  providerId: string,
  modelIdentifier: string,
  parameters: Record<string, unknown>,
): ModelItem {
  const route = makeRoute(id, providerId, modelIdentifier);
  return {
    id,
    slug: originalIdentifier,
    display_name: displayName,
    original_identifier: originalIdentifier,
    model_family_id: modelFamilyId,
    parameters,
    enabled: true,
    active_route_id: route.id,
    routes: [route],
    created_at: NOW,
    updated_at: NOW,
    provider_enabled: true,
  };
}

// A canonical model with more than one provider route. The active route decides
// which provider the model runs through; the rest are ready fallbacks.
const deepseekV4Pro: ModelItem = (() => {
  const id = "mdl-deepseek-v4-pro";
  const openRouterRoute = makeRoute(
    id,
    "prov-openrouter",
    "deepseek/deepseek-v4-pro",
    "openrouter",
  );
  const openCodeGoRoute = makeRoute(id, "prov-opencode-go", "deepseek-v4-pro", "opencode-go");
  return {
    id,
    slug: "deepseek-v4-pro",
    display_name: "DeepSeek V4 Pro",
    original_identifier: "deepseek-v4-pro",
    model_family_id: "fam-openrouter-deepseek",
    parameters: {
      temperature: 0.7,
      max_tokens: 8192,
    },
    enabled: true,
    // OpenRouter is the active route; OpenCode Go is the fallback.
    active_route_id: openRouterRoute.id,
    routes: [openRouterRoute, openCodeGoRoute],
    created_at: NOW,
    updated_at: NOW,
    provider_enabled: true,
  };
})();

export const allModelsMock: ModelItem[] = [
  // =====================
  // OpenAI (6 models)
  // =====================
  single("mdl-openai-gpt4o", "GPT-4o", "gpt-4o", "fam-openai-gpt4o", "prov-openai", "gpt-4o", {
    max_completion_tokens: 4096,
    temperature: 0.85,
    top_p: 0.9,
    frequency_penalty: 0.3,
    presence_penalty: 0.2,
  }),
  single(
    "mdl-openai-gpt4o-mini",
    "GPT-4o Mini",
    "gpt-4o-mini",
    "fam-openai-gpt4o",
    "prov-openai",
    "gpt-4o-mini",
    {
      max_completion_tokens: 16384,
      temperature: 0.85,
      top_p: 0.9,
      frequency_penalty: 0.3,
      presence_penalty: 0.2,
    },
  ),
  single(
    "mdl-openai-gpt53-chat",
    "GPT-5.3 Chat",
    "gpt-5.3-chat",
    "fam-openai-gpt53-chat",
    "prov-openai",
    "gpt-5.3-chat",
    {
      max_completion_tokens: 8192,
      temperature: 0.85,
      top_p: 0.9,
      summary: "concise",
      frequency_penalty: 0.3,
      presence_penalty: 0.2,
    },
  ),
  single(
    "mdl-openai-gpt54",
    "GPT-5.4",
    "gpt-5.4",
    "fam-openai-gpt54-thinking",
    "prov-openai",
    "gpt-5.4",
    {
      reasoning_effort: "medium",
      max_completion_tokens: 16384,
      summary: "concise",
    },
  ),
  single(
    "mdl-openai-gpt54-mini",
    "GPT-5.4 Mini",
    "gpt-5.4-mini",
    "fam-openai-gpt54-thinking",
    "prov-openai",
    "gpt-5.4-mini",
    {
      reasoning_effort: "low",
      max_completion_tokens: 8192,
      summary: "concise",
    },
  ),
  single(
    "mdl-openai-gpt54-nano",
    "GPT-5.4 Nano",
    "gpt-5.4-nano",
    "fam-openai-gpt54-thinking",
    "prov-openai",
    "gpt-5.4-nano",
    {
      reasoning_effort: "low",
      max_completion_tokens: 4096,
      summary: "concise",
    },
  ),

  // =====================
  // Anthropic (5 models)
  // =====================
  single(
    "mdl-anthropic-claude45-haiku",
    "Claude 4.5 Haiku",
    "claude-4.5-haiku",
    "fam-anthropic-claude45-std",
    "prov-anthropic",
    "claude-4.5-haiku",
    { temperature: 0.8, max_tokens: 4096 },
  ),
  single(
    "mdl-anthropic-claude45-sonnet",
    "Claude 4.5 Sonnet",
    "claude-4.5-sonnet",
    "fam-anthropic-claude45-std",
    "prov-anthropic",
    "claude-4.5-sonnet",
    { temperature: 0.8, max_tokens: 8192 },
  ),
  single(
    "mdl-anthropic-claude45-opus",
    "Claude 4.5 Opus",
    "claude-4.5-opus",
    "fam-anthropic-claude45-opus",
    "prov-anthropic",
    "claude-4.5-opus",
    { temperature: 0.8, max_tokens: 8192 },
  ),
  single(
    "mdl-anthropic-claude46-sonnet",
    "Claude 4.6 Sonnet",
    "claude-4.6-sonnet",
    "fam-anthropic-claude46-sonnet",
    "prov-anthropic",
    "claude-4.6-sonnet",
    { temperature: 0.8, max_tokens: 8192, effort: "high" },
  ),
  single(
    "mdl-anthropic-claude46-opus",
    "Claude 4.6 Opus",
    "claude-4.6-opus",
    "fam-anthropic-claude46-opus",
    "prov-anthropic",
    "claude-4.6-opus",
    { temperature: 0.8, max_tokens: 16384, effort: "high" },
  ),

  // =====================
  // Google (4 models)
  // =====================
  single(
    "mdl-google-gemini25-flash",
    "Gemini 2.5 Flash",
    "gemini-2.5-flash",
    "fam-google-gemini25",
    "prov-google",
    "gemini-2.5-flash",
    { temperature: 0.9, max_output_tokens: 8192 },
  ),
  single(
    "mdl-google-gemini25-pro",
    "Gemini 2.5 Pro",
    "gemini-2.5-pro",
    "fam-google-gemini25",
    "prov-google",
    "gemini-2.5-pro",
    { temperature: 0.9, max_output_tokens: 8192 },
  ),
  single(
    "mdl-google-gemini3-flash",
    "Gemini 3 Flash",
    "gemini-3.0-flash",
    "fam-google-gemini3-preview",
    "prov-google",
    "gemini-3.0-flash",
    { temperature: 0.9, max_output_tokens: 8192, thinking_level: "medium" },
  ),
  single(
    "mdl-google-gemini31-pro",
    "Gemini 3.1 Pro",
    "gemini-3.1-pro",
    "fam-google-gemini3-preview",
    "prov-google",
    "gemini-3.1-pro",
    { temperature: 0.9, max_output_tokens: 8192, thinking_level: "high" },
  ),

  // =====================
  // xAI (3 models)
  // =====================
  single("mdl-xai-grok4", "Grok 4.0", "grok-4", "fam-xai-grok4", "prov-xai", "grok-4", {
    temperature: 0.8,
    max_completion_tokens: 4096,
  }),
  single(
    "mdl-xai-grok41-fast",
    "Grok 4.1 Fast",
    "grok-4.1-fast",
    "fam-xai-grok41-fast",
    "prov-xai",
    "grok-4.1-fast",
    { temperature: 0.8, max_completion_tokens: 4096 },
  ),
  single("mdl-xai-grok420", "Grok 4.20", "grok-4.20", "fam-xai-grok420", "prov-xai", "grok-4.20", {
    temperature: 0.8,
    max_completion_tokens: 8192,
  }),

  // =====================
  // OpenRouter (10 models — incl. the multi-route DeepSeek V4 Pro)
  // =====================
  single(
    "mdl-or-euryale-70b",
    "Sao10K L3 Euryale 70B",
    "l3-euryale-70b",
    "fam-openrouter-llama3-rp",
    "prov-openrouter",
    "sao10k/l3-euryale-70b",
    { temperature: 0.85, top_p: 0.9, max_tokens: 4096 },
  ),
  single(
    "mdl-or-lumimaid-70b",
    "Lumimaid 70B",
    "llama-3-lumimaid-70b",
    "fam-openrouter-llama3-rp",
    "prov-openrouter",
    "neversleep/llama-3-lumimaid-70b",
    { temperature: 0.85, top_p: 0.9, max_tokens: 4096 },
  ),
  deepseekV4Pro,
  single(
    "mdl-or-deepseek-r1",
    "DeepSeek R1",
    "deepseek-r1",
    "fam-openrouter-deepseek",
    "prov-openrouter",
    "deepseek/deepseek-r1",
    { temperature: 0.7, max_tokens: 8192 },
  ),
  single(
    "mdl-or-glm4-9b",
    "GLM-4 9B",
    "glm-4-9b",
    "fam-openrouter-glm",
    "prov-openrouter",
    "zhipu/glm-4-9b",
    { temperature: 0.7, max_tokens: 4096 },
  ),
  single(
    "mdl-or-glm4-32b",
    "GLM-4 32B",
    "glm-4-32b",
    "fam-openrouter-glm",
    "prov-openrouter",
    "zhipu/glm-4-32b",
    { temperature: 0.7, max_tokens: 8192 },
  ),
  single(
    "mdl-or-minimax-01",
    "MiniMax-01",
    "minimax-01",
    "fam-openrouter-minimax",
    "prov-openrouter",
    "minimax/minimax-01",
    { temperature: 0.8, max_tokens: 4096 },
  ),
  single(
    "mdl-or-minimax-text",
    "MiniMax Text-01",
    "minimax-text-01",
    "fam-openrouter-minimax",
    "prov-openrouter",
    "minimax/minimax-text-01",
    { temperature: 0.8, max_tokens: 8192 },
  ),
  single(
    "mdl-or-qwen-72b",
    "Qwen 2.5 72B Instruct",
    "qwen-2.5-72b-instruct",
    "fam-openrouter-misc",
    "prov-openrouter",
    "qwen/qwen-2.5-72b-instruct",
    { temperature: 0.8, top_p: 0.9, max_tokens: 4096 },
  ),
  single(
    "mdl-or-cohere-command",
    "Cohere Command R+",
    "command-r-plus",
    "fam-openrouter-misc",
    "prov-openrouter",
    "cohere/command-r-plus",
    { temperature: 0.8, top_p: 0.9, max_tokens: 4096 },
  ),

  // =====================
  // Ollama (6 models)
  // =====================
  single(
    "mdl-ollama-drummer-anubis",
    "TheDrummer Anubis Pro 105B",
    "anubis-pro-105b-v1:Q4_K_M",
    "fam-ollama-thedrummer-rp",
    "prov-ollama",
    "thedrummer/anubis-pro-105b-v1:Q4_K_M",
    { temperature: 0.85, num_ctx: 8192 },
  ),
  single(
    "mdl-ollama-drummer-skyfall",
    "TheDrummer Skyfall 36B",
    "skyfall-36b-v2:Q4_K_M",
    "fam-ollama-thedrummer-rp",
    "prov-ollama",
    "thedrummer/skyfall-36b-v2:Q4_K_M",
    { temperature: 0.85, num_ctx: 8192 },
  ),
  single(
    "mdl-ollama-drummer-big-tiger",
    "TheDrummer Big Tiger Gemma 27B",
    "big-tiger-gemma-27b-v1:Q4_K_M",
    "fam-ollama-thedrummer-rp",
    "prov-ollama",
    "thedrummer/big-tiger-gemma-27b-v1:Q4_K_M",
    { temperature: 0.85, num_ctx: 8192 },
  ),
  single(
    "mdl-ollama-gemma4-12b",
    "Gemma 4 12B",
    "gemma4:12b",
    "fam-ollama-gemma4",
    "prov-ollama",
    "gemma4:12b",
    { temperature: 0.7, num_ctx: 32768 },
  ),
  single(
    "mdl-ollama-gemma4-27b",
    "Gemma 4 27B",
    "gemma4:27b",
    "fam-ollama-gemma4",
    "prov-ollama",
    "gemma4:27b",
    { temperature: 0.7, num_ctx: 32768 },
  ),
  single(
    "mdl-ollama-gemma4-4b",
    "Gemma 4 4B",
    "gemma4:4b",
    "fam-ollama-gemma4",
    "prov-ollama",
    "gemma4:4b",
    { temperature: 0.7, num_ctx: 16384 },
  ),
];
