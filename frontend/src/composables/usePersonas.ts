import type { components } from "@/api/schema";
import { client, multipartFetch } from "@/api/client";
import { useListCrud } from "@/composables/useListCrud";

export type Persona = components["schemas"]["PersonaResponse"];

export function usePersonas() {
  // Create/update is multipart (avatar upload) — openapi-fetch can't do that, so
  // savePersona is hand-rolled below; list/delete/set-default ride the factory.
  const {
    items: personas,
    loading,
    error,
    refresh,
    removeItem,
    setDefaultItem,
  } = useListCrud<Persona>({
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

  // Reconcile the local list after a save, keeping the single-default invariant
  // and either replacing the edited row or prepending a new one.
  const upsertLocal = (persona: Persona) => {
    if (persona.is_default) {
      for (const p of personas.value) if (p.id !== persona.id) p.is_default = false;
    }
    const idx = personas.value.findIndex((p) => p.id === persona.id);
    if (idx !== -1) personas.value[idx] = persona;
    else personas.value.unshift(persona);
  };

  // Multipart create/update via multipartFetch (base URL + reachability tracking).
  // Pass an id to update, omit it to create. Records failures on the shared
  // `error` ref (like the factory) and returns null.
  const savePersona = async (formData: FormData, id?: string | null): Promise<Persona | null> => {
    error.value = null;
    try {
      const { data, error: apiError } = id
        ? await multipartFetch<Persona>(`/api/personas/${id}`, { method: "PUT", body: formData })
        : await multipartFetch<Persona>("/api/personas/", { method: "POST", body: formData });
      if (apiError || !data) throw apiError ?? new Error("Failed to save persona");
      upsertLocal(data);
      return data;
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
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
    deletePersona: removeItem,
    setDefaultPersona: setDefaultItem,
    refresh,
  };
}
