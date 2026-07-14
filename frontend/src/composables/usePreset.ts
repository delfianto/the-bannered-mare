import { client } from "@/api/client";
import { useEntityCrud } from "@/composables/useEntityCrud";
import type { components } from "@/api/schema";

type PresetResponse = components["schemas"]["PresetResponse"];
type PresetUpdate = components["schemas"]["PresetUpdate"];

export function usePreset() {
  const crud = useEntityCrud<PresetResponse, never, PresetUpdate>({
    label: "preset",
    fetchOne: (id) =>
      client.GET("/api/presets/{preset_id}", { params: { path: { preset_id: id } } }),
    update: (id, body) =>
      client.PUT("/api/presets/{preset_id}", { params: { path: { preset_id: id } }, body }),
    remove: (id) =>
      client.DELETE("/api/presets/{preset_id}", { params: { path: { preset_id: id } } }),
  });

  async function setDefault(id: string) {
    const data = await crud.runSaving(
      () =>
        client.POST("/api/presets/{preset_id}/default", { params: { path: { preset_id: id } } }),
      "Failed to set preset as default",
    );
    crud.item.value = data;
    return data;
  }

  return {
    preset: crud.item,
    loading: crud.loading,
    saving: crud.saving,
    deleting: crud.deleting,
    error: crud.error,
    fetchPreset: crud.fetchItem,
    savePreset: crud.updateItem,
    deletePreset: crud.removeItem,
    setDefault,
  };
}
