import { client } from "@/api/client";
import { useEntityCrud } from "@/composables/useEntityCrud";
import type { components } from "@/api/schema";

type ModelFamilyResponse = components["schemas"]["ModelFamilyResponse"];
type ModelFamilyCreate = components["schemas"]["ModelFamilyCreate"];
type ModelFamilyUpdate = components["schemas"]["ModelFamilyUpdate"];

export function useModelFamily() {
  const crud = useEntityCrud<ModelFamilyResponse, ModelFamilyCreate, ModelFamilyUpdate>({
    label: "model family",
    fetchOne: (id) =>
      client.GET("/api/model-families/{family_id}", { params: { path: { family_id: id } } }),
    create: (body) => client.POST("/api/model-families", { body }),
    update: (id, body) =>
      client.PUT("/api/model-families/{family_id}", { params: { path: { family_id: id } }, body }),
    remove: (id) =>
      client.DELETE("/api/model-families/{family_id}", { params: { path: { family_id: id } } }),
  });

  return {
    family: crud.item,
    loading: crud.loading,
    saving: crud.saving,
    deleting: crud.deleting,
    error: crud.error,
    fetchFamily: crud.fetchItem,
    createFamily: crud.createItem,
    saveFamily: crud.updateItem,
    deleteFamily: crud.removeItem,
  };
}
