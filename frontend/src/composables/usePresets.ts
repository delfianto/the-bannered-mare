import { onMounted } from "vue";
import { storeToRefs } from "pinia";
import type { components } from "@/api/schema";
import { client } from "@/api/client";
import { defineListStore } from "@/stores/listStore";

export type Preset = components["schemas"]["PresetResponse"];

/**
 * Presets list, backed by a shared cached store singleton so every
 * consumer (PresetsTab, ProfilesTab, ProfileForm, setup wizard) shares one fetch
 * and one copy. The single-item `usePreset` / `usePresetImport` mutators call
 * `refresh()` to invalidate this cache after they write.
 */
export const usePresetsStore = defineListStore<Preset>("presets", {
  label: "preset",
  list: () => client.GET("/api/presets/", { params: { query: { limit: 50 } } }),
});

export function usePresets() {
  const store = usePresetsStore();
  const { items: presets, loading, error } = storeToRefs(store);
  onMounted(() => store.ensureLoaded());
  return { presets, loading, error, refresh: store.refresh };
}
