import { ref, onMounted } from "vue";
import type { components } from "@/api/schema";
import { client, extractApiError, multipartFetch } from "@/api/client";

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
        throw extractApiError(apiError, "Failed to load personas");
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

  // Reconcile the local list after a create/update, keeping the single-default
  // invariant and either replacing the edited row or prepending a new one.
  const upsertLocal = (persona: Persona) => {
    if (persona.is_default) {
      personas.value.forEach((p) => {
        if (p.id !== persona.id) p.is_default = false;
      });
    }
    const idx = personas.value.findIndex((p) => p.id === persona.id);
    if (idx !== -1) personas.value[idx] = persona;
    else personas.value.unshift(persona);
  };

  // Multipart create/update — openapi-fetch doesn't handle multipart, so this
  // goes through multipartFetch (base URL + reachability tracking). Pass an id to
  // update, omit it to create.
  const savePersona = async (formData: FormData, id?: string | null): Promise<Persona | null> => {
    try {
      const { data, error: apiError } = id
        ? await multipartFetch<Persona>(`/api/personas/${id}`, { method: "PUT", body: formData })
        : await multipartFetch<Persona>("/api/personas/", { method: "POST", body: formData });
      if (apiError || !data) throw apiError ?? new Error("Failed to save persona");
      upsertLocal(data);
      return data;
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error("Error saving persona:", err);
      return null;
    }
  };

  // Convenience wrapper kept for callers that only set a name (e.g. setup wizard).
  const createPersona = async (name: string, isDefault = false): Promise<Persona | null> => {
    const formData = new FormData();
    formData.append("name", name);
    formData.append("is_default", String(isDefault));
    return savePersona(formData);
  };

  const deletePersona = async (id: string): Promise<boolean> => {
    const { error: apiError } = await client.DELETE("/api/personas/{persona_id}", {
      params: { path: { persona_id: id } },
    });
    if (apiError) {
      error.value = extractApiError(apiError, "Failed to delete persona");
      return false;
    }
    personas.value = personas.value.filter((p) => p.id !== id);
    return true;
  };

  const setDefaultPersona = async (id: string): Promise<boolean> => {
    const { data, error: apiError } = await client.POST("/api/personas/{persona_id}/set-default", {
      params: { path: { persona_id: id } },
    });
    if (apiError || !data) {
      error.value = extractApiError(apiError, "Failed to set default persona");
      return false;
    }
    personas.value.forEach((p) => (p.is_default = p.id === id));
    return true;
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
    savePersona,
    createPersona,
    deletePersona,
    setDefaultPersona,
    refresh,
  };
}
