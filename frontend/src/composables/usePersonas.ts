import { onMounted } from "vue";
import { storeToRefs } from "pinia";
import type { components } from "@/api/schema";
import { client, multipartFetch } from "@/api/client";
import { defineListStore } from "@/stores/listStore";

export type Persona = components["schemas"]["PersonaResponse"];

/**
 * Personas list + CRUD, backed by a shared cached store singleton (FE-M2).
 * List/delete/set-default ride the store; create/update is multipart (avatar
 * upload) so it's hand-rolled below and reconciles the shared list via the
 * store's `upsert` — keeping every consumer coherent without a refetch.
 */
export const usePersonasStore = defineListStore<Persona>("personas", {
  label: "persona",
  singleDefault: true,
  list: () => client.GET("/api/personas/", { params: { query: { limit: 50 } } }),
  remove: (id) =>
    client.DELETE("/api/personas/{persona_id}", { params: { path: { persona_id: id } } }),
  setDefault: (id) =>
    client.POST("/api/personas/{persona_id}/set-default", {
      params: { path: { persona_id: id } },
    }),
});

export function usePersonas() {
  const store = usePersonasStore();
  const { items: personas, loading, error } = storeToRefs(store);
  onMounted(() => store.ensureLoaded());

  // Multipart create/update via multipartFetch (base URL + reachability tracking).
  // Pass an id to update, omit it to create. Records failures on the shared store
  // `error` (like the store's own ops) and returns null.
  const savePersona = async (formData: FormData, id?: string | null): Promise<Persona | null> => {
    store.clearError();
    try {
      const { data, error: apiError } = id
        ? await multipartFetch<Persona>(`/api/personas/${id}`, { method: "PUT", body: formData })
        : await multipartFetch<Persona>("/api/personas/", { method: "POST", body: formData });
      if (apiError || !data) throw apiError ?? new Error("Failed to save persona");
      store.upsert(data);
      return data;
    } catch (err) {
      store.recordError(err);
      return null;
    }
  };

  // Convenience wrapper kept for callers that only set a name (e.g. setup wizard).
  const createPersona = (name: string, isDefault = false): Promise<Persona | null> => {
    const formData = new FormData();
    formData.append("name", name);
    formData.append("is_default", String(isDefault));
    return savePersona(formData);
  };

  return {
    personas,
    loading,
    error,
    savePersona,
    createPersona,
    deletePersona: store.removeItem,
    setDefaultPersona: store.setDefaultItem,
    refresh: store.refresh,
  };
}
