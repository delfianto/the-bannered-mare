import { ref, onMounted, computed } from "vue";
import type { components } from "@/api/schema";
import { client, extractApiError } from "@/api/client";

type CharacterResponse = components["schemas"]["CharacterResponse"];
type ChatResponse = components["schemas"]["ChatResponse"];
type MessageResponse = components["schemas"]["MessageResponse"];

export function useBookmarks() {
  const characters = ref<CharacterResponse[]>([]);
  const sessions = ref<ChatResponse[]>([]);
  const messages = ref<MessageResponse[]>([]);
  const loading = ref(true);
  const error = ref<Error | null>(null);

  const totalCount = computed(
    () => characters.value.length + sessions.value.length + messages.value.length,
  );

  async function load() {
    loading.value = true;
    error.value = null;

    try {
      const [charRes, sessRes, msgRes] = await Promise.all([
        client.GET("/api/bookmarks/characters"),
        client.GET("/api/bookmarks/sessions"),
        client.GET("/api/bookmarks/messages"),
      ]);

      const firstError = charRes.error || sessRes.error || msgRes.error;
      if (firstError) throw extractApiError(firstError, "Failed to load bookmarks");

      characters.value = charRes.data?.items ?? [];
      sessions.value = sessRes.data?.items ?? [];
      messages.value = msgRes.data?.items ?? [];
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Failed to load bookmarks");
    } finally {
      loading.value = false;
    }
  }

  onMounted(load);

  return { characters, sessions, messages, loading, error, totalCount, refresh: load };
}
