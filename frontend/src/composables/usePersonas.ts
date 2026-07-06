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

  // Multipart upload — openapi-fetch doesn't handle multipart, per project convention.
  const createPersona = async (name: string, isDefault = false): Promise<Persona | null> => {
    try {
      const formData = new FormData();
      formData.append("name", name);
      formData.append("is_default", String(isDefault));

      const response = await fetch("/api/personas/", { method: "POST", body: formData });
      if (!response.ok) throw new Error(`Failed to create persona: ${response.status}`);

      const created: Persona = await response.json();
      if (created.is_default) personas.value.forEach((p) => (p.is_default = false));
      personas.value.unshift(created);
      return created;
    } catch (err) {
      console.error("Error creating persona:", err);
      return null;
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
    createPersona,
    refresh,
  };
}
