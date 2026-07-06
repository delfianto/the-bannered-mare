import { ref } from "vue";
import type { components } from "@/api/schema";

type PresetResponse = components["schemas"]["PresetResponse"];

export function usePreset() {
  const preset = ref<PresetResponse | null>(null);
  const loading = ref(false);
  const saving = ref(false);
  const deleting = ref(false);
  const error = ref<Error | null>(null);

  async function fetchPreset(id: string) {
    loading.value = true;
    error.value = null;
    try {
      const response = await fetch(`/api/presets/${id}`);
      if (!response.ok) throw new Error(`Failed to load preset: ${response.status}`);
      preset.value = await response.json();
    } catch (e) {
      error.value = e instanceof Error ? e : new Error("Unknown error");
    } finally {
      loading.value = false;
    }
  }

  async function savePreset(id: string, updates: Record<string, unknown>) {
    saving.value = true;
    try {
      const response = await fetch(`/api/presets/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });
      if (!response.ok) throw new Error(`Save failed: ${response.status}`);
      const data = await response.json();
      preset.value = data;
      return data;
    } finally {
      saving.value = false;
    }
  }

  async function deletePreset(id: string) {
    deleting.value = true;
    try {
      const response = await fetch(`/api/presets/${id}`, {
        method: "DELETE",
      });
      if (!response.ok && response.status !== 204)
        throw new Error(`Delete failed: ${response.status}`);
    } finally {
      deleting.value = false;
    }
  }

  async function setDefault(id: string) {
    saving.value = true;
    try {
      const response = await fetch(`/api/presets/${id}/default`, {
        method: "POST",
      });
      if (!response.ok) throw new Error(`Set default failed: ${response.status}`);
      const data = await response.json();
      preset.value = data;
      return data;
    } finally {
      saving.value = false;
    }
  }

  return {
    preset,
    loading,
    saving,
    deleting,
    error,
    fetchPreset,
    savePreset,
    deletePreset,
    setDefault,
  };
}
