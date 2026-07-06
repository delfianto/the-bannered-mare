import { ref } from "vue";
import type { components } from "@/api/schema";

export type STImportResult = components["schemas"]["STImportResult"];

export function usePresetImport() {
  const importing = ref(false);
  const result = ref<STImportResult | null>(null);
  const error = ref<Error | null>(null);

  // Multipart upload — use raw fetch per the project's FormData exception
  // (openapi-fetch does not handle multipart well).
  const importPreset = async (file: File): Promise<STImportResult | null> => {
    importing.value = true;
    error.value = null;
    result.value = null;

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("/api/presets/import", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Import failed: ${response.status}`);
      }

      const data = (await response.json()) as STImportResult;
      result.value = data;
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
