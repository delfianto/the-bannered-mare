import type { components } from "@/api/schema";

type Preset = components["schemas"]["PresetResponse"];
const NOW = new Date().toISOString();

export const presets: Preset[] = [
  {
    id: "preset-default-rp",
    name: "Default RP",
    description: "Balanced settings for general roleplay scenarios with natural language flow and moderate creativity.",
    parameters: {
      temperature: 0.85,
      top_p: 0.9,
      max_tokens: 2048,
      frequency_penalty: 0.1,
      presence_penalty: 0.15,
    },
    is_default: true,
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "preset-creative-writing",
    name: "Creative Writing",
    description: "Higher temperature and top_p for more creative, varied, and surprising prose output.",
    parameters: {
      temperature: 1.2,
      top_p: 0.95,
      max_tokens: 4096,
      frequency_penalty: 0.3,
      presence_penalty: 0.2,
    },
    is_default: false,
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "preset-precise",
    name: "Precise",
    description: "Low temperature for deterministic, focused responses. Best for factual or structured output.",
    parameters: {
      temperature: 0.3,
      top_p: 0.5,
      max_tokens: 1024,
    },
    is_default: false,
    created_at: NOW,
    updated_at: NOW,
  },
];
