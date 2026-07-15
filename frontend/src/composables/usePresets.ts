import type { components } from "@/api/schema";
import { client } from "@/api/client";
import { useListCrud } from "@/composables/useListCrud";

export type Preset = components["schemas"]["PresetResponse"];

export function usePresets() {
  const {
    items: presets,
    loading,
    error,
    refresh,
  } = useListCrud<Preset>({
    label: "preset",
    list: () => client.GET("/api/presets/", { params: { query: { limit: 50 } } }),
  });

  return { presets, loading, error, refresh };
}
