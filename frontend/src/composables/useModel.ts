import { client, extractApiError } from "@/api/client";
import { useEntityCrud } from "@/composables/useEntityCrud";
import type { components } from "@/api/schema";

type ModelDetailResponse = components["schemas"]["ModelDetailResponse"];
type ModelResponse = components["schemas"]["ModelResponse"];
type ModelCreate = components["schemas"]["ModelCreate"];
type ModelUpdate = components["schemas"]["ModelUpdate"];
type ModelFlagsUpdate = components["schemas"]["ModelFlagsUpdate"];

export function useModel() {
  // Shared loading/saving/deleting/error + item come from the factory; the
  // route/flag mutations below stay bespoke because they return a ModelResponse
  // that must be *merged* into the detail (not clobber it) and run under the
  // shared `saving` flag via runSaving.
  const crud = useEntityCrud<ModelDetailResponse>({
    label: "model",
    fetchOne: (id) => client.GET("/api/models/{model_id}", { params: { path: { model_id: id } } }),
    remove: (id) =>
      client.DELETE("/api/models/{model_id}", { params: { path: { model_id: id } } }),
  });

  const model = crud.item;

  // PUT / route mutations return a ModelResponse (the registry with its routes
  // but no embedded model_family); merge into the existing detail so the family
  // object and other detail-only fields survive instead of being clobbered.
  function mergeIntoDetail(data: ModelResponse) {
    if (model.value) model.value = { ...model.value, ...data };
  }

  function createModel(payload: ModelCreate) {
    return crud.runSaving(() => client.POST("/api/models", { body: payload }), "Failed to create model");
  }

  async function saveModel(id: string, updates: ModelUpdate) {
    const data = await crud.runSaving(
      () => client.PUT("/api/models/{model_id}", { params: { path: { model_id: id } }, body: updates }),
      "Failed to save model",
    );
    mergeIntoDetail(data);
    return data;
  }

  async function addRoute(
    modelId: string,
    route: { provider_id: string; model_identifier: string },
  ) {
    const data = await crud.runSaving(
      () =>
        client.POST("/api/models/{model_id}/routes", {
          params: { path: { model_id: modelId } },
          body: { ...route, enabled: true },
        }),
      "Failed to add route",
    );
    mergeIntoDetail(data);
    return data;
  }

  async function deleteRoute(modelId: string, routeId: string) {
    const data = await crud.runSaving(
      () =>
        client.DELETE("/api/models/{model_id}/routes/{route_id}", {
          params: { path: { model_id: modelId, route_id: routeId } },
        }),
      "Failed to remove route",
    );
    mergeIntoDetail(data);
    return data;
  }

  // Flip which route the model resolves through (redirects existing chats on
  // the backend). Returns the registry with its refreshed active_route_id.
  async function setActiveRoute(modelId: string, routeId: string) {
    const data = await crud.runSaving(
      () =>
        client.PUT("/api/models/{model_id}/active-route", {
          params: { path: { model_id: modelId } },
          body: { route_id: routeId },
        }),
      "Failed to set active route",
    );
    mergeIntoDetail(data);
    return data;
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
    loading: crud.loading,
    saving: crud.saving,
    deleting: crud.deleting,
    error: crud.error,
    fetchModel: crud.fetchItem,
    createModel,
    saveModel,
    deleteModel: crud.removeItem,
    toggleFlags,
    addRoute,
    deleteRoute,
    setActiveRoute,
  };
}
