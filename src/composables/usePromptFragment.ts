import { ref } from "vue";
import type { components } from "@/api/schema";

type FragmentResponse = components["schemas"]["FragmentResponse"];

export function usePromptFragment() {
  const fragment = ref<FragmentResponse | null>(null);
  const loading = ref(false);
  const saving = ref(false);
  const deleting = ref(false);
  const error = ref<Error | null>(null);

  async function fetchFragment(id: string) {
    loading.value = true;
    error.value = null;
    try {
      const response = await fetch(`/api/prompt-fragments/${id}`);
      if (!response.ok) throw new Error(`Failed to load fragment: ${response.status}`);
      fragment.value = await response.json();
    } catch (e) {
      error.value = e instanceof Error ? e : new Error("Unknown error");
    } finally {
      loading.value = false;
    }
  }

  async function saveFragment(id: string, updates: Record<string, unknown>) {
    saving.value = true;
    try {
      const response = await fetch(`/api/prompt-fragments/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });
      if (!response.ok) throw new Error(`Save failed: ${response.status}`);
      const data = await response.json();
      fragment.value = data;
      return data;
    } finally {
      saving.value = false;
    }
  }

  async function deleteFragment(id: string) {
    deleting.value = true;
    try {
      const response = await fetch(`/api/prompt-fragments/${id}`, {
        method: "DELETE",
      });
      if (!response.ok && response.status !== 204) throw new Error(`Delete failed: ${response.status}`);
    } finally {
      deleting.value = false;
    }
  }

  return {
    fragment,
    loading,
    saving,
    deleting,
    error,
    fetchFragment,
    saveFragment,
    deleteFragment,
  };
}
