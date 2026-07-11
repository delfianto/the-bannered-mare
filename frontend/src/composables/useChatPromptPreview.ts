import { ref } from "vue";
import type { components } from "@/api/schema";
import { client } from "@/api/client";

export type ChatPromptPreview = components["schemas"]["ChatPromptPreviewResponse"];

/**
 * Fetches a chat's resolved prompt scaffolding + effective sampler params on
 * demand (the chat drawer's Session-info tab). Read-only, no LLM call.
 * Deliberately no auto-load — the caller triggers `load(chatId)`; the last fetch
 * is cached by id so reopening the drawer on the same chat won't refetch.
 */
export function useChatPromptPreview() {
  const preview = ref<ChatPromptPreview | null>(null);
  const loading = ref(false);
  const error = ref<Error | null>(null);
  let lastId: string | null = null;

  const load = async (chatId: string, force = false) => {
    if (!chatId) return;
    if (!force && chatId === lastId && preview.value) return;

    loading.value = true;
    error.value = null;

    try {
      const { data, error: apiError } = await client.GET("/api/chats/{chat_id}/prompt-preview", {
        params: { path: { chat_id: chatId } },
      });

      if (apiError) {
        throw new Error(`Failed to load prompt preview: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        preview.value = data;
        lastId = chatId;
      }
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error("Error loading prompt preview:", err);
    } finally {
      loading.value = false;
    }
  };

  return { preview, loading, error, load };
}
