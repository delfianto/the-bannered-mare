import { ref } from "vue";
import { client } from "@/api/client";
import { useEntityCrud } from "@/composables/useEntityCrud";
import { useSettingsStore } from "@/stores/settings";
import type { components } from "@/api/schema";

type ProviderResponse = components["schemas"]["ProviderResponse"];
type ProviderCreate = components["schemas"]["ProviderCreate"];
type ProviderUpdate = components["schemas"]["ProviderUpdate"];
type DiscoveredModel = components["schemas"]["DiscoveredModel"];

export function useProvider() {
  // Core provider CRUD (item/loading/saving/error + fetch/create/save) comes from
  // the shared factory; the model-discovery/sync/filter state below is
  // provider-specific and stays local.
  const crud = useEntityCrud<ProviderResponse, ProviderCreate, ProviderUpdate>({
    label: "provider",
    fetchOne: (id) =>
      client.GET("/api/providers/{provider_id}", { params: { path: { provider_id: id } } }),
    create: (body) => client.POST("/api/providers", { body }),
    update: (id, body) =>
      client.PUT("/api/providers/{provider_id}", { params: { path: { provider_id: id } }, body }),
  });
  const provider = crud.item;

  // The provider *list* is a shared store singleton (FE-M1); after a create/edit
  // refresh it here so every consumer (Providers/Models/Family tabs) stays in
  // sync — no call site has to remember to invalidate.
  const store = useSettingsStore();
  const createProvider = async (body: ProviderCreate) => {
    const created = await crud.createItem(body);
    await store.fetchProviders(true);
    return created;
  };
  const saveProvider = async (id: string, body: ProviderUpdate) => {
    const saved = await crud.updateItem(id, body);
    await store.fetchProviders(true);
    return saved;
  };

  const availableModels = ref<DiscoveredModel[]>([]);
  const modelsLoading = ref(false);
  const syncing = ref(false);
  const modelsError = ref<Error | null>(null);
  const pendingModelAction = ref<string | null>(null);

  const searchResults = ref<DiscoveredModel[]>([]);
  const searchingModels = ref(false);
  const savingFilter = ref(false);

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

  async function searchModels(id: string, query: string) {
    searchingModels.value = true;
    try {
      const { data, error: apiError } = await client.GET(
        "/api/providers/{provider_id}/models/search",
        { params: { path: { provider_id: id }, query: { q: query } } },
      );
      if (apiError || !data) throw new Error("Failed to search models");
      searchResults.value = data.models;
      return data.models;
    } finally {
      searchingModels.value = false;
    }
  }

  function clearSearch() {
    searchResults.value = [];
  }

  // Persists the curated allow-list; the response carries the freshly-filtered
  // available list so the caller doesn't need a separate refetch.
  async function setModelFilter(id: string, allowedModels: string[]) {
    savingFilter.value = true;
    try {
      const { data, error: apiError } = await client.PUT(
        "/api/providers/{provider_id}/models/filter",
        { params: { path: { provider_id: id } }, body: { allowed_models: allowedModels } },
      );
      if (apiError || !data) throw new Error("Failed to update model filter");
      availableModels.value = [...data.models].sort((a, b) =>
        a.display_name.localeCompare(b.display_name),
      );
      if (provider.value) provider.value.allowed_models = allowedModels;
      return data.models;
    } finally {
      savingFilter.value = false;
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
    loading: crud.loading,
    saving: crud.saving,
    error: crud.error,
    fetchProvider: crud.fetchItem,
    createProvider,
    saveProvider,
    availableModels,
    modelsLoading,
    syncing,
    modelsError,
    pendingModelAction,
    searchResults,
    searchingModels,
    savingFilter,
    fetchAvailableModels,
    syncNow,
    searchModels,
    clearSearch,
    setModelFilter,
    loadModel,
    unloadModel,
    deleteModel,
    persistModel,
  };
}
