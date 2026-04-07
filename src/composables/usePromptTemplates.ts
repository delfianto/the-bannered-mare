import { ref, onMounted } from "vue";
import type { components } from "@/api/schema";
import { client } from "@/api/client";

export type PromptTemplate = components["schemas"]["PromptTemplateResponse"];

export function usePromptTemplates() {
  const templates = ref<PromptTemplate[]>([]);
  const loading = ref(false);
  const error = ref<Error | null>(null);

  const fetchTemplates = async () => {
    loading.value = true;
    error.value = null;

    try {
      const { data, error: apiError } = await client.GET("/api/prompt-templates/", {
        params: {
          query: { limit: 50 },
        },
      });

      if (apiError) {
        throw new Error(`Failed to load prompt templates: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        templates.value = data.items;
      }
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error("Error loading prompt templates:", err);
    } finally {
      loading.value = false;
    }
  };

  const refresh = () => {
    fetchTemplates();
  };

  onMounted(() => {
    fetchTemplates();
  });

  return {
    templates,
    loading,
    error,
    refresh,
  };
}
