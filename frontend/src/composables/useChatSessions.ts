import { ref, onMounted } from "vue";
import type { components } from "@/api/schema";
import { client } from "@/api/client";

type Chat = components["schemas"]["ChatResponse"];
type ChatUpdate = components["schemas"]["ChatUpdate"];

interface UseChatSessionsOptions {
  pageSize?: number;
}

export function useChatSessions(options: UseChatSessionsOptions = {}) {
  const { pageSize = 20 } = options;

  const chatSessions = ref<Chat[]>([]);
  const loading = ref(false);
  const hasMore = ref(true);
  const cursor = ref<string | null>(null);
  const error = ref<Error | null>(null);

  const loadSessions = async (nextCursor?: string) => {
    loading.value = true;
    error.value = null;

    try {
      const { data, error: apiError } = await client.GET("/api/chats", {
        params: {
          query: {
            limit: pageSize,
            cursor: nextCursor || undefined,
          },
        },
      });

      if (apiError) {
        throw new Error(`Failed to load chats: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        const newSessions: Chat[] = Array.isArray(data) ? data : data.items;
        const meta = Array.isArray(data) ? null : data.meta;

        if (nextCursor) {
          chatSessions.value = [...chatSessions.value, ...newSessions];
        } else {
          chatSessions.value = newSessions;
        }

        if (meta) {
          hasMore.value = meta.has_more;
          cursor.value = meta.cursor || null;
        } else {
          hasMore.value = newSessions.length >= pageSize;
          cursor.value = hasMore.value ? newSessions[newSessions.length - 1].updated_at : null;
        }
      }
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error("Error loading chats:", err);
    } finally {
      loading.value = false;
    }
  };

  const loadMore = async () => {
    if (hasMore.value && !loading.value && cursor.value) {
      await loadSessions(cursor.value);
    }
  };

  const refresh = () => {
    chatSessions.value = [];
    hasMore.value = true;
    cursor.value = null;
    loadSessions();
  };

  const updateChat = async (chatId: string, updates: ChatUpdate) => {
    try {
      const { data, error: apiError } = await client.PUT("/api/chats/{chat_id}", {
        params: { path: { chat_id: chatId } },
        body: updates,
      });
      if (apiError) {
        throw new Error(`Failed to update chat: ${JSON.stringify(apiError)}`);
      }
      if (data) {
        // Merge the fresh response back so consumers (e.g. the header's model
        // label) reflect the update.
        const idx = chatSessions.value.findIndex((c) => c.id === chatId);
        if (idx !== -1) chatSessions.value[idx] = data;
        return data;
      }
      return null;
    } catch (err) {
      console.error("Error updating chat:", err);
      throw err;
    }
  };

  const deleteChat = async (chatId: string) => {
    try {
      const response = await fetch(`/api/chats/${chatId}`, { method: "DELETE" });
      if (!response.ok && response.status !== 204) throw new Error("Failed to delete");
      chatSessions.value = chatSessions.value.filter((c) => c.id !== chatId);
    } catch (err) {
      console.error("Error deleting chat:", err);
      throw err;
    }
  };

  const applyProfile = async (chatId: string, profileId: string) => {
    try {
      const { data, error: apiError } = await client.POST("/api/chats/{chat_id}/profile", {
        params: { path: { chat_id: chatId } },
        body: { profile_id: profileId },
      });
      if (apiError) {
        throw new Error(`Failed to apply profile: ${JSON.stringify(apiError)}`);
      }
      if (data) {
        const idx = chatSessions.value.findIndex((c) => c.id === chatId);
        if (idx !== -1) chatSessions.value[idx] = data;
        return data;
      }
      return null;
    } catch (err) {
      console.error("Error applying profile:", err);
      return null;
    }
  };

  // Auto-generate a concise title (via the chat's task model) and patch it into
  // the local session list. Best-effort — a failure just leaves the title unset.
  const generateTitle = async (chatId: string): Promise<string | null> => {
    try {
      const { data, error: apiError } = await client.POST("/api/chats/{chat_id}/messages/title", {
        params: { path: { chat_id: chatId } },
      });
      if (apiError || !data?.title) return null;
      const idx = chatSessions.value.findIndex((c) => c.id === chatId);
      if (idx !== -1) chatSessions.value[idx] = { ...chatSessions.value[idx], title: data.title };
      return data.title;
    } catch (err) {
      console.error("Error generating title:", err);
      return null;
    }
  };

  onMounted(() => {
    loadSessions();
  });

  return {
    chatSessions,
    loading,
    hasMore,
    error,
    loadMore,
    refresh,
    updateChat,
    deleteChat,
    applyProfile,
    generateTitle,
  };
}
