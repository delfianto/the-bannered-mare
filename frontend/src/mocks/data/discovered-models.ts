import type { components } from "@/api/schema";

type DiscoveredModel = components["schemas"]["DiscoveredModel"];

export const discoveredModelsByProvider: Record<string, DiscoveredModel[]> = {
  "prov-ollama": [
    {
      identifier: "llama3:8b",
      display_name: "llama3:8b",
      state: "loaded",
      size_bytes: 4700000000,
      quantization: "Q4_K_M",
      max_context_length: null,
    },
    {
      identifier: "mistral:7b",
      display_name: "mistral:7b",
      state: "not-loaded",
      size_bytes: 4100000000,
      quantization: "Q4_0",
      max_context_length: null,
    },
  ],
  "prov-lmstudio": [
    {
      identifier: "google/gemma-4-26b-a4b",
      display_name: "Gemma 4 26B A4B",
      state: "not-loaded",
      size_bytes: 17990911801,
      quantization: "Q4_K_M",
      max_context_length: 262144,
    },
  ],
};
