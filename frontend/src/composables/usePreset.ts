import { client } from "@/api/client";
import { useEntityCrud } from "@/composables/useEntityCrud";
import { usePresetsStore } from "@/composables/usePresets";
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

  // Invalidate the shared presets list after a mutation (FE-M2), so the cached
  // singleton every list consumer reads stays in sync — mirrors useProvider.
  const store = usePresetsStore();

  async function savePreset(id: string, body: PresetUpdate) {
    const saved = await crud.updateItem(id, body);
    await store.refresh();
    return saved;
  }

  async function deletePreset(id: string) {
    await crud.removeItem(id);
    await store.refresh();
  }

  async function setDefault(id: string) {
    const data = await crud.runSaving(
      () =>
        client.POST("/api/presets/{preset_id}/default", { params: { path: { preset_id: id } } }),
      "Failed to set preset as default",
    );
    crud.item.value = data;
    await store.refresh();
    return data;
  }

  return {
    preset: crud.item,
    loading: crud.loading,
    saving: crud.saving,
    deleting: crud.deleting,
    error: crud.error,
    fetchPreset: crud.fetchItem,
    savePreset,
    deletePreset,
    setDefault,
  };
}
