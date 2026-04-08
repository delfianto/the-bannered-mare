import { ref, onMounted, computed } from "vue";

export interface BookmarkedMessage {
  id: string;
  role: string;
  content: string;
  character: { id: string; name: string; avatar: string };
  chat: { id: string; title: string };
  bookmarked_at: string;
  created_at: string;
}

export function useBookmarks() {
  const characters = ref<any[]>([]);
  const sessions = ref<any[]>([]);
  const messages = ref<BookmarkedMessage[]>([]);
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
        fetch("/api/bookmarks/characters").then((r) => r.json()),
        fetch("/api/bookmarks/sessions").then((r) => r.json()),
        fetch("/api/bookmarks/messages").then((r) => r.json()),
      ]);

      characters.value = charRes?.items ?? [];
      sessions.value = sessRes?.items ?? [];
      messages.value = msgRes?.items ?? [];
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Failed to load bookmarks");
    } finally {
      loading.value = false;
    }
  }

  onMounted(load);

  return { characters, sessions, messages, loading, error, totalCount, refresh: load };
}
