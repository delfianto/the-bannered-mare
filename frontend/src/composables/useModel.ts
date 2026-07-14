import { ref } from "vue";
import { client, extractApiError } from "@/api/client";
import type { components } from "@/api/schema";

type ModelDetailResponse = components["schemas"]["ModelDetailResponse"];
type ModelResponse = components["schemas"]["ModelResponse"];
type ModelCreate = components["schemas"]["ModelCreate"];
type ModelUpdate = components["schemas"]["ModelUpdate"];
type ModelFlagsUpdate = components["schemas"]["ModelFlagsUpdate"];

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
      if (apiError || !data) throw extractApiError(apiError, "Failed to load model");
      model.value = data;
    } catch (e) {
      error.value = e instanceof Error ? e : new Error("Unknown error");
    } finally {
      loading.value = false;
    }
  }

  // PUT / route mutations return a ModelResponse (the registry with its routes
  // but no embedded model_family); merge into the existing detail so the family
  // object and other detail-only fields survive instead of being clobbered.
  function mergeIntoDetail(data: ModelResponse) {
    if (model.value) model.value = { ...model.value, ...data };
  }

  async function saveModel(id: string, updates: ModelUpdate) {
    saving.value = true;
    try {
      const { data, error: apiError } = await client.PUT("/api/models/{model_id}", {
        params: { path: { model_id: id } },
        body: updates,
      });
      if (apiError || !data) throw extractApiError(apiError, "Failed to save model");
      mergeIntoDetail(data);
      return data;
    } finally {
      saving.value = false;
    }
  }

  async function createModel(payload: ModelCreate) {
    saving.value = true;
    try {
      const { data, error: apiError } = await client.POST("/api/models", { body: payload });
      if (apiError || !data) throw extractApiError(apiError, "Failed to create model");
      return data;
    } finally {
      saving.value = false;
    }
  }

  async function addRoute(
    modelId: string,
    route: { provider_id: string; model_identifier: string },
  ) {
    saving.value = true;
    try {
      const { data, error: apiError } = await client.POST("/api/models/{model_id}/routes", {
        params: { path: { model_id: modelId } },
        body: { ...route, enabled: true },
      });
      if (apiError || !data) throw extractApiError(apiError, "Failed to add route");
      mergeIntoDetail(data);
      return data;
    } finally {
      saving.value = false;
    }
  }

  async function deleteRoute(modelId: string, routeId: string) {
    saving.value = true;
    try {
      const { data, error: apiError } = await client.DELETE(
        "/api/models/{model_id}/routes/{route_id}",
        { params: { path: { model_id: modelId, route_id: routeId } } },
      );
      if (apiError || !data) throw extractApiError(apiError, "Failed to remove route");
      mergeIntoDetail(data);
      return data;
    } finally {
      saving.value = false;
    }
  }

  // Flip which route the model resolves through (redirects existing chats on
  // the backend). Returns the registry with its refreshed active_route_id.
  async function setActiveRoute(modelId: string, routeId: string) {
    saving.value = true;
    try {
      const { data, error: apiError } = await client.PUT("/api/models/{model_id}/active-route", {
        params: { path: { model_id: modelId } },
        body: { route_id: routeId },
      });
      if (apiError || !data) throw extractApiError(apiError, "Failed to set active route");
      mergeIntoDetail(data);
      return data;
    } finally {
      saving.value = false;
    }
  }

  async function deleteModel(id: string) {
    deleting.value = true;
    try {
      const { error: apiError } = await client.DELETE("/api/models/{model_id}", {
        params: { path: { model_id: id } },
      });
      if (apiError) throw extractApiError(apiError, "Failed to delete model");
    } finally {
      deleting.value = false;
    }
  }

  async function toggleFlags(id: string, flags: ModelFlagsUpdate) {
    const { data, error: apiError } = await client.PATCH("/api/models/{model_id}/flags", {
      params: { path: { model_id: id } },
      body: flags,
    });
    if (apiError || !data) throw extractApiError(apiError, "Failed to update model flags");
    return data;
  }

  return {
    model,
    loading,
    saving,
    deleting,
    error,
    fetchModel,
    createModel,
    saveModel,
    deleteModel,
    toggleFlags,
    addRoute,
    deleteRoute,
    setActiveRoute,
  };
}
