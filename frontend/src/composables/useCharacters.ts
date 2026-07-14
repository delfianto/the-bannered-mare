import type { components } from "@/api/schema";
import { client, multipartFetch } from "@/api/client";
import { usePaginatedList } from "@/composables/usePaginatedList";

export type Character = components["schemas"]["CharacterResponse"];

interface UseCharactersOptions {
  pageSize?: number;
}

export function useCharacters(options: UseCharactersOptions = {}) {
  const { pageSize = 50 } = options;

  // Infinite-scroll style: loadMore appends the next page.
  const list = usePaginatedList<Character>(
    (page, limit) => client.GET("/api/characters", { params: { query: { page, limit } } }),
    { pageSize, append: true, errorContext: "Failed to load characters" },
  );

  // Multipart character-card import (PNG/JSON) — routed through multipartFetch so
  // it honors VITE_API_URL + reachability tracking like the rest of the client.
  const importCharacter = async (file: File): Promise<Character> => {
    const formData = new FormData();
    formData.append("file", file);
    const { data, error } = await multipartFetch<Character>("/api/characters/import", {
      method: "POST",
      body: formData,
    });
    if (error || !data) throw error ?? new Error("Import failed");
    return data;
  };

  return {
    characters: list.items,
    loading: list.loading,
    error: list.error,
    hasMore: list.hasMore,
    loadMore: list.loadMore,
    refresh: list.refresh,
    importCharacter,
  };
}
