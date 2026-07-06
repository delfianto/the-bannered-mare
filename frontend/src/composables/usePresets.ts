import { ref, onMounted } from "vue";
import type { components } from "@/api/schema";
import { client } from "@/api/client";

export type Preset = components["schemas"]["PresetResponse"];

export function usePresets() {
  const presets = ref<Preset[]>([]);
  const loading = ref(false);
  const error = ref<Error | null>(null);

  const fetchPresets = async () => {
    loading.value = true;
    error.value = null;

    try {
      const { data, error: apiError } = await client.GET("/api/presets/", {
        params: {
          query: { limit: 50 },
        },
      });

      if (apiError) {
        throw new Error(`Failed to load presets: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        presets.value = data.items;
      }
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error("Error loading presets:", err);
    } finally {
      loading.value = false;
    }
  };

  const refresh = () => {
    fetchPresets();
  };

  onMounted(() => {
    fetchPresets();
  });

  return {
    presets,
    loading,
    error,
    refresh,
  };
}
