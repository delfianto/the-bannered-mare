import { ref, onMounted } from "vue";
import type { components } from "@/api/schema";
import { client } from "@/api/client";

export type Persona = components["schemas"]["PersonaResponse"];

export function usePersonas() {
  const personas = ref<Persona[]>([]);
  const loading = ref(false);
  const error = ref<Error | null>(null);

  const fetchPersonas = async () => {
    loading.value = true;
    error.value = null;

    try {
      const { data, error: apiError } = await client.GET("/api/personas/", {
        params: { query: { limit: 50 } },
      });

      if (apiError) {
        throw new Error(`Failed to load personas: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        personas.value = data.items;
      }
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error("Error loading personas:", err);
    } finally {
      loading.value = false;
    }
  };

  const refresh = () => {
    fetchPersonas();
  };

  onMounted(() => {
    fetchPersonas();
  });

  return {
    personas,
    loading,
    error,
    refresh,
  };
}
