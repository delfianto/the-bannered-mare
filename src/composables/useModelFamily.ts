import { ref } from "vue";
import { client } from "@/api/client";
import type { components } from "@/api/schema";

type ModelFamilyResponse = components["schemas"]["ModelFamilyResponse"];

export function useModelFamily() {
  const family = ref<ModelFamilyResponse | null>(null);
  const loading = ref(false);
  const saving = ref(false);
  const deleting = ref(false);
  const error = ref<Error | null>(null);

  async function fetchFamily(id: string) {
    loading.value = true;
    error.value = null;
    try {
      const { data, error: apiError } = await client.GET("/api/model-families/{family_id}", {
        params: { path: { family_id: id } },
      });
      if (apiError || !data) throw new Error("Failed to load model family");
      family.value = data;
    } catch (e) {
      error.value = e instanceof Error ? e : new Error("Unknown error");
    } finally {
      loading.value = false;
    }
  }

  async function saveFamily(id: string, updates: Record<string, unknown>) {
    saving.value = true;
    try {
      const response = await fetch(`/api/model-families/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });
      if (!response.ok) throw new Error(`Save failed: ${response.status}`);
      const data = await response.json();
      family.value = data;
      return data;
    } finally {
      saving.value = false;
    }
  }

  async function deleteFamily(id: string) {
    deleting.value = true;
    try {
      const response = await fetch(`/api/model-families/${id}`, {
        method: "DELETE",
      });
      if (!response.ok && response.status !== 204) throw new Error(`Delete failed: ${response.status}`);
    } finally {
      deleting.value = false;
    }
  }

  return { family, loading, saving, deleting, error, fetchFamily, saveFamily, deleteFamily };
}
