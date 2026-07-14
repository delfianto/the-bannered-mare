import type { components } from "@/api/schema";
import { client } from "@/api/client";
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

  return {
    characters: list.items,
    loading: list.loading,
    error: list.error,
    hasMore: list.hasMore,
    loadMore: list.loadMore,
    refresh: list.refresh,
  };
}
