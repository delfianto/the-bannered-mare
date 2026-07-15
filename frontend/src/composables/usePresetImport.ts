import { ref } from "vue";
import type { components } from "@/api/schema";
import { multipartFetch } from "@/api/client";
import { usePresetsStore } from "@/composables/usePresets";

export type STImportResult = components["schemas"]["STImportResult"];

export function usePresetImport() {
  const importing = ref(false);
  const result = ref<STImportResult | null>(null);
  const error = ref<Error | null>(null);

  // A successful import creates a preset — invalidate the shared list (FE-M2).
  const store = usePresetsStore();

  // Multipart upload — use raw fetch per the project's FormData exception
  // (openapi-fetch does not handle multipart well).
  const importPreset = async (file: File): Promise<STImportResult | null> => {
    importing.value = true;
    error.value = null;
    result.value = null;

    try {
      const formData = new FormData();
      formData.append("file", file);

      const { data, error: apiError } = await multipartFetch<STImportResult>(
        "/api/presets/import",
        { method: "POST", body: formData },
      );
      if (apiError || !data) throw apiError ?? new Error("Import failed");

      result.value = data;
      await store.refresh();
      return data;
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error("Error importing preset:", err);
      return null;
    } finally {
      importing.value = false;
    }
  };

  const reset = () => {
    result.value = null;
    error.value = null;
  };

  return { importing, result, error, importPreset, reset };
}
