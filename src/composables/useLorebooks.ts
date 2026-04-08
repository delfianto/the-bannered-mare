import { ref } from "vue";
import type { components } from "@/api/schema";
import { client } from "@/api/client";

export type LorebookResponse = components["schemas"]["LorebookResponse"];
export type LorebookDetail = components["schemas"]["LorebookDetailResponse"];
export type LorebookCreate = components["schemas"]["LorebookCreate"];
export type LorebookUpdate = components["schemas"]["LorebookUpdate"];
export type LoreEntryResponse = components["schemas"]["LoreEntryResponse"];
export type LoreEntryCreate = components["schemas"]["LoreEntryCreate"];
export type LoreEntryUpdate = components["schemas"]["LoreEntryUpdate"];

export function useLorebooks() {
  const lorebooks = ref<LorebookResponse[]>([]);
  const currentLorebook = ref<LorebookDetail | null>(null);
  const loading = ref(false);
  const error = ref<Error | null>(null);

  const fetchLorebooks = async (characterId?: string) => {
    loading.value = true;
    error.value = null;

    try {
      const { data, error: apiError } = await client.GET("/api/lorebooks", {
        params: {
          query: characterId ? { character_id: characterId } : {},
        },
      });

      if (apiError) {
        throw new Error(`Failed to load lorebooks: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        lorebooks.value = data;
      }
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error("Error loading lorebooks:", err);
    } finally {
      loading.value = false;
    }
  };

  const fetchLorebook = async (id: string) => {
    loading.value = true;
    error.value = null;

    try {
      const { data, error: apiError } = await client.GET("/api/lorebooks/{lorebook_id}", {
        params: { path: { lorebook_id: id } },
      });

      if (apiError) {
        throw new Error(`Failed to load lorebook: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        currentLorebook.value = data;
      }
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error("Error loading lorebook:", err);
    } finally {
      loading.value = false;
    }
  };

  const createLorebook = async (payload: LorebookCreate): Promise<LorebookResponse | null> => {
    try {
      const { data, error: apiError } = await client.POST("/api/lorebooks", {
        body: payload,
      });

      if (apiError) {
        throw new Error(`Failed to create lorebook: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        lorebooks.value.unshift(data);
        return data;
      }
      return null;
    } catch (err) {
      console.error("Error creating lorebook:", err);
      return null;
    }
  };

  const updateLorebook = async (
    id: string,
    payload: LorebookUpdate,
  ): Promise<LorebookResponse | null> => {
    try {
      const { data, error: apiError } = await client.PUT("/api/lorebooks/{lorebook_id}", {
        params: { path: { lorebook_id: id } },
        body: payload,
      });

      if (apiError) {
        throw new Error(`Failed to update lorebook: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        const idx = lorebooks.value.findIndex((l) => l.id === id);
        if (idx !== -1) lorebooks.value[idx] = data;
        return data;
      }
      return null;
    } catch (err) {
      console.error("Error updating lorebook:", err);
      return null;
    }
  };

  const deleteLorebook = async (id: string): Promise<boolean> => {
    try {
      const { error: apiError } = await client.DELETE("/api/lorebooks/{lorebook_id}", {
        params: { path: { lorebook_id: id } },
      });

      if (apiError) {
        throw new Error(`Failed to delete lorebook: ${JSON.stringify(apiError)}`);
      }

      lorebooks.value = lorebooks.value.filter((l) => l.id !== id);
      return true;
    } catch (err) {
      console.error("Error deleting lorebook:", err);
      return false;
    }
  };

  const createEntry = async (
    lorebookId: string,
    payload: LoreEntryCreate,
  ): Promise<LoreEntryResponse | null> => {
    try {
      const { data, error: apiError } = await client.POST(
        "/api/lorebooks/{lorebook_id}/entries",
        {
          params: { path: { lorebook_id: lorebookId } },
          body: payload,
        },
      );

      if (apiError) {
        throw new Error(`Failed to create entry: ${JSON.stringify(apiError)}`);
      }

      if (data && currentLorebook.value?.id === lorebookId) {
        currentLorebook.value.entries.push(data);
      }
      return data ?? null;
    } catch (err) {
      console.error("Error creating lore entry:", err);
      return null;
    }
  };

  const updateEntry = async (
    lorebookId: string,
    entryId: string,
    payload: LoreEntryUpdate,
  ): Promise<LoreEntryResponse | null> => {
    try {
      const { data, error: apiError } = await client.PUT(
        "/api/lorebooks/{lorebook_id}/entries/{entry_id}",
        {
          params: { path: { lorebook_id: lorebookId, entry_id: entryId } },
          body: payload,
        },
      );

      if (apiError) {
        throw new Error(`Failed to update entry: ${JSON.stringify(apiError)}`);
      }

      if (data && currentLorebook.value?.id === lorebookId) {
        const idx = currentLorebook.value.entries.findIndex((e) => e.id === entryId);
        if (idx !== -1) currentLorebook.value.entries[idx] = data;
      }
      return data ?? null;
    } catch (err) {
      console.error("Error updating lore entry:", err);
      return null;
    }
  };

  const deleteEntry = async (lorebookId: string, entryId: string): Promise<boolean> => {
    try {
      const { error: apiError } = await client.DELETE(
        "/api/lorebooks/{lorebook_id}/entries/{entry_id}",
        {
          params: { path: { lorebook_id: lorebookId, entry_id: entryId } },
        },
      );

      if (apiError) {
        throw new Error(`Failed to delete entry: ${JSON.stringify(apiError)}`);
      }

      if (currentLorebook.value?.id === lorebookId) {
        currentLorebook.value.entries = currentLorebook.value.entries.filter(
          (e) => e.id !== entryId,
        );
      }
      return true;
    } catch (err) {
      console.error("Error deleting lore entry:", err);
      return false;
    }
  };

  return {
    lorebooks,
    currentLorebook,
    loading,
    error,
    fetchLorebooks,
    fetchLorebook,
    createLorebook,
    updateLorebook,
    deleteLorebook,
    createEntry,
    updateEntry,
    deleteEntry,
  };
}
