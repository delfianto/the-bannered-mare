import { ref } from "vue";
import { client } from "@/api/client";
import type { components } from "@/api/schema";

type ProviderResponse = components["schemas"]["ProviderResponse"];
type DiscoveredModel = components["schemas"]["DiscoveredModel"];

export function useProvider() {
  const provider = ref<ProviderResponse | null>(null);
  const loading = ref(false);
  const saving = ref(false);
  const error = ref<Error | null>(null);

  const availableModels = ref<DiscoveredModel[]>([]);
  const modelsLoading = ref(false);
  const syncing = ref(false);
  const modelsError = ref<Error | null>(null);
  const pendingModelAction = ref<string | null>(null);

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

  async function fetchAvailableModels(id: string) {
    modelsLoading.value = true;
    modelsError.value = null;
    try {
      const { data, error: apiError } = await client.GET(
        "/api/providers/{provider_id}/models/available",
        { params: { path: { provider_id: id } } },
      );
      if (apiError || !data) throw new Error("Failed to load available models");
      availableModels.value = [...data.models].sort((a, b) =>
        a.display_name.localeCompare(b.display_name),
      );
      if (provider.value) provider.value.last_synced_at = data.last_synced_at;
    } catch (e) {
      modelsError.value = e instanceof Error ? e : new Error("Unknown error");
    } finally {
      modelsLoading.value = false;
    }
  }

  async function syncNow(id: string) {
    syncing.value = true;
    modelsError.value = null;
    try {
      const { data, error: apiError } = await client.POST(
        "/api/providers/{provider_id}/models/sync",
        { params: { path: { provider_id: id } } },
      );
      if (apiError || !data) throw new Error("Failed to sync models");
      availableModels.value = [...data.models].sort((a, b) =>
        a.display_name.localeCompare(b.display_name),
      );
      if (provider.value) provider.value.last_synced_at = data.last_synced_at;
    } catch (e) {
      modelsError.value = e instanceof Error ? e : new Error("Unknown error");
    } finally {
      syncing.value = false;
    }
  }

  async function loadModel(id: string, identifier: string) {
    pendingModelAction.value = identifier;
    try {
      const { error: apiError } = await client.POST("/api/providers/{provider_id}/models/load", {
        params: { path: { provider_id: id } },
        body: { model_identifier: identifier },
      });
      if (apiError) throw new Error("Failed to load model");
      await fetchAvailableModels(id);
    } finally {
      pendingModelAction.value = null;
    }
  }

  async function unloadModel(id: string, identifier: string) {
    pendingModelAction.value = identifier;
    try {
      const { error: apiError } = await client.POST("/api/providers/{provider_id}/models/unload", {
        params: { path: { provider_id: id } },
        body: { model_identifier: identifier },
      });
      if (apiError) throw new Error("Failed to unload model");
      await fetchAvailableModels(id);
    } finally {
      pendingModelAction.value = null;
    }
  }

  async function deleteModel(id: string, identifier: string) {
    pendingModelAction.value = identifier;
    try {
      const { error: apiError } = await client.DELETE("/api/providers/{provider_id}/models", {
        params: {
          path: { provider_id: id },
          query: { model_identifier: identifier },
        },
      });
      if (apiError) throw new Error("Failed to delete model");
      await fetchAvailableModels(id);
    } finally {
      pendingModelAction.value = null;
    }
  }

  async function persistModel(id: string, identifier: string) {
    pendingModelAction.value = identifier;
    try {
      const { data, error: apiError } = await client.POST(
        "/api/providers/{provider_id}/models/persist",
        {
          params: { path: { provider_id: id } },
          body: { model_identifier: identifier },
        },
      );
      if (apiError) throw new Error("Failed to persist model");
      return data;
    } finally {
      pendingModelAction.value = null;
    }
  }

  return {
    provider,
    loading,
    saving,
    error,
    fetchProvider,
    saveProvider,
    availableModels,
    modelsLoading,
    syncing,
    modelsError,
    pendingModelAction,
    fetchAvailableModels,
    syncNow,
    loadModel,
    unloadModel,
    deleteModel,
    persistModel,
  };
}
