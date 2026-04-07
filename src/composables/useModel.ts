import { ref } from "vue";
import { client } from "@/api/client";
import type { components } from "@/api/schema";

type ModelDetailResponse = components["schemas"]["ModelDetailResponse"];

export function useModel() {
  const model = ref<ModelDetailResponse | null>(null);
  const loading = ref(false);
  const saving = ref(false);
  const deleting = ref(false);
  const error = ref<Error | null>(null);

  async function fetchModel(id: string) {
    loading.value = true;
    error.value = null;
    try {
      const { data, error: apiError } = await client.GET("/api/models/{model_id}", {
        params: { path: { model_id: id } },
      });
      if (apiError || !data) throw new Error("Failed to load model");
      model.value = data;
    } catch (e) {
      error.value = e instanceof Error ? e : new Error("Unknown error");
    } finally {
      loading.value = false;
    }
  }

  async function saveModel(id: string, updates: Record<string, unknown>) {
    saving.value = true;
    try {
      const response = await fetch(`/api/models/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });
      if (!response.ok) throw new Error(`Save failed: ${response.status}`);
      const data = await response.json();
      model.value = data;
      return data;
    } finally {
      saving.value = false;
    }
  }

  async function deleteModel(id: string) {
    deleting.value = true;
    try {
      const response = await fetch(`/api/models/${id}`, {
        method: "DELETE",
      });
      if (!response.ok && response.status !== 204) throw new Error(`Delete failed: ${response.status}`);
    } finally {
      deleting.value = false;
    }
  }

  async function toggleFlags(id: string, flags: Record<string, unknown>) {
    try {
      const response = await fetch(`/api/models/${id}/flags`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(flags),
      });
      if (!response.ok) throw new Error(`Toggle failed: ${response.status}`);
      return await response.json();
    } catch (e) {
      throw e;
    }
  }

  return { model, loading, saving, deleting, error, fetchModel, saveModel, deleteModel, toggleFlags };
}
