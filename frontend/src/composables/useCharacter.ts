import { ref } from "vue";
import type { components } from "@/api/schema";
import { client } from "@/api/client";

export type Character = components["schemas"]["CharacterResponse"];

/**
 * Fetches a single character on demand (e.g. the chat drawer's Character tab).
 * Deliberately separate from `useCharacters` (the paginated library list) — this
 * pulls the full record for one id and caches the last fetch to avoid refetching
 * while the drawer stays mounted across opens.
 */
export function useCharacter() {
  const character = ref<Character | null>(null);
  const loading = ref(false);
  const error = ref<Error | null>(null);
  let lastId: string | null = null;

  const load = async (id: string, force = false) => {
    if (!id) return;
    if (!force && id === lastId && character.value) return;

    loading.value = true;
    error.value = null;

    try {
      const { data, error: apiError } = await client.GET("/api/characters/{character_id}", {
        params: { path: { character_id: id } },
      });

      if (apiError) {
        throw new Error(`Failed to load character: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        character.value = data;
        lastId = id;
      }
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error("Error loading character:", err);
    } finally {
      loading.value = false;
    }
  };

  return { character, loading, error, load };
}
