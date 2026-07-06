import { ref, onMounted } from "vue";
import type { components } from "@/api/schema";
import { client } from "@/api/client";

export type DataBankEntry = components["schemas"]["DataBankResponse"];
export type DataBankCreate = components["schemas"]["DataBankCreate"];
export type DataBankUpdate = components["schemas"]["DataBankUpdate"];

export function useDataBank() {
  const entries = ref<DataBankEntry[]>([]);
  const loading = ref(false);
  const error = ref<Error | null>(null);

  const fetchEntries = async (scope?: string) => {
    loading.value = true;
    error.value = null;

    try {
      const { data, error: apiError } = await client.GET("/api/data-bank/", {
        params: {
          query: scope ? { scope } : {},
        },
      });

      if (apiError) {
        throw new Error(`Failed to load data bank entries: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        entries.value = data;
      }
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error("Error loading data bank entries:", err);
    } finally {
      loading.value = false;
    }
  };

  const createEntry = async (payload: DataBankCreate): Promise<DataBankEntry | null> => {
    try {
      const { data, error: apiError } = await client.POST("/api/data-bank/", {
        body: payload,
      });

      if (apiError) {
        throw new Error(`Failed to create entry: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        entries.value.unshift(data);
        return data;
      }
      return null;
    } catch (err) {
      console.error("Error creating data bank entry:", err);
      return null;
    }
  };

  const updateEntry = async (
    entryId: string,
    payload: DataBankUpdate,
  ): Promise<DataBankEntry | null> => {
    try {
      const { data, error: apiError } = await client.PUT("/api/data-bank/{entry_id}", {
        params: { path: { entry_id: entryId } },
        body: payload,
      });

      if (apiError) {
        throw new Error(`Failed to update entry: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        const idx = entries.value.findIndex((e) => e.id === entryId);
        if (idx !== -1) entries.value[idx] = data;
        return data;
      }
      return null;
    } catch (err) {
      console.error("Error updating data bank entry:", err);
      return null;
    }
  };

  const deleteEntry = async (entryId: string): Promise<boolean> => {
    try {
      const { error: apiError } = await client.DELETE("/api/data-bank/{entry_id}", {
        params: { path: { entry_id: entryId } },
      });

      if (apiError) {
        throw new Error(`Failed to delete entry: ${JSON.stringify(apiError)}`);
      }

      entries.value = entries.value.filter((e) => e.id !== entryId);
      return true;
    } catch (err) {
      console.error("Error deleting data bank entry:", err);
      return false;
    }
  };

  const refresh = (scope?: string) => {
    fetchEntries(scope);
  };

  onMounted(() => {
    fetchEntries();
  });

  return {
    entries,
    loading,
    error,
    fetchEntries,
    createEntry,
    updateEntry,
    deleteEntry,
    refresh,
  };
}
