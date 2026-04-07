import { ref } from "vue";
import { client } from "@/api/client";
import type { components } from "@/api/schema";

type ProviderResponse = components["schemas"]["ProviderResponse"];

export function useProvider() {
  const provider = ref<ProviderResponse | null>(null);
  const loading = ref(false);
  const saving = ref(false);
  const error = ref<Error | null>(null);

  async function fetchProvider(id: string) {
    loading.value = true;
    error.value = null;
    try {
      const { data, error: apiError } = await client.GET("/api/providers/{provider_id}", {
        params: { path: { provider_id: id } },
      });
      if (apiError || !data) throw new Error("Failed to load provider");
      provider.value = data;
    } catch (e) {
      error.value = e instanceof Error ? e : new Error("Unknown error");
    } finally {
      loading.value = false;
    }
  }

  async function saveProvider(id: string, updates: Record<string, unknown>) {
    saving.value = true;
    try {
      const response = await fetch(`/api/providers/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });
      if (!response.ok) throw new Error(`Save failed: ${response.status}`);
      const data = await response.json();
      provider.value = data;
      return data;
    } finally {
      saving.value = false;
    }
  }

  return { provider, loading, saving, error, fetchProvider, saveProvider };
}
