import { ref, onMounted } from "vue";
import type { components } from "@/api/schema";
import { client } from "@/api/client";

export type Character = components["schemas"]["CharacterResponse"];

interface UseCharactersOptions {
  pageSize?: number;
}

export function useCharacters(options: UseCharactersOptions = {}) {
  const { pageSize = 50 } = options;

  const characters = ref<Character[]>([]);
  const loading = ref(false);
  const error = ref<Error | null>(null);
  const hasMore = ref(false);
  const page = ref(1);

  const loadCharacters = async (pageNum: number = 1) => {
    loading.value = true;
    error.value = null;

    try {
      const { data, error: apiError } = await client.GET("/api/characters", {
        params: {
          query: {
            limit: pageSize,
            page: pageNum,
          },
        },
      });

      if (apiError) {
        throw new Error(`Failed to load characters: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        const items: Character[] = Array.isArray(data) ? data : data.items;
        const meta = Array.isArray(data) ? null : data.meta;

        if (pageNum === 1) {
          characters.value = items;
        } else {
          characters.value = [...characters.value, ...items];
        }

        if (meta) {
          hasMore.value = meta.has_more;
          page.value = pageNum;
        } else {
          hasMore.value = items.length >= pageSize;
        }
      }
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error("Error loading characters:", err);
    } finally {
      loading.value = false;
    }
  };

  const loadMore = async () => {
    if (hasMore.value && !loading.value) {
      await loadCharacters(page.value + 1);
    }
  };

  const refresh = () => {
    characters.value = [];
    hasMore.value = false;
    page.value = 1;
    loadCharacters(1);
  };

  onMounted(() => {
    loadCharacters(1);
  });

  return {
    characters,
    loading,
    error,
    hasMore,
    loadMore,
    refresh,
  };
}
