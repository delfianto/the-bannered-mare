import { ref, onMounted } from "vue";
import type { components } from "@/api/schema";
import { client } from "@/api/client";

export type PromptFragment = components["schemas"]["FragmentResponse"];

export function usePromptFragments() {
  const fragments = ref<PromptFragment[]>([]);
  const loading = ref(false);
  const error = ref<Error | null>(null);

  const fetchFragments = async () => {
    loading.value = true;
    error.value = null;

    try {
      const { data, error: apiError } = await client.GET("/api/prompt-fragments/");

      if (apiError) {
        throw new Error(`Failed to load prompt fragments: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        fragments.value = data;
      }
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error("Error loading prompt fragments:", err);
    } finally {
      loading.value = false;
    }
  };

  const refresh = () => {
    fetchFragments();
  };

  onMounted(() => {
    fetchFragments();
  });

  return {
    fragments,
    loading,
    error,
    refresh,
  };
}
