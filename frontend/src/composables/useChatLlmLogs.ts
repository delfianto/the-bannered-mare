import { ref } from "vue";
import type { components } from "@/api/schema";
import { client } from "@/api/client";

export type LlmAuditLog = components["schemas"]["LlmAuditLogResponse"];

// One drawer open shouldn't drag the whole audit table over the wire — a chat's
// recent calls are all the Logs tab needs.
const LIMIT = 25;

/**
 * Fetches a chat's LLM audit records on demand (the chat drawer's Logs tab).
 * Read-only. Deliberately no auto-load — the caller triggers `load(chatId)`; the
 * last fetch is cached by id so reopening the drawer (or toggling tabs) on the
 * same chat won't refetch. An empty result is cached too, so a chat with no logs
 * doesn't refetch on every tab switch.
 */
export function useChatLlmLogs() {
  const logs = ref<LlmAuditLog[]>([]);
  const loading = ref(false);
  const error = ref<Error | null>(null);
  let lastId: string | null = null;

  const load = async (chatId: string, force = false) => {
    if (!chatId) return;
    if (!force && chatId === lastId) return;

    loading.value = true;
    error.value = null;
    // Drop the previous chat's rows so switching chats never flashes stale logs.
    logs.value = [];

    try {
      const { data, error: apiError } = await client.GET("/admin/logs/llm", {
        params: { query: { chat_id: chatId, limit: LIMIT } },
      });

      if (apiError) {
        throw new Error(`Failed to load LLM logs: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        logs.value = data.logs;
        lastId = chatId;
      }
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error("Error loading LLM logs:", err);
    } finally {
      loading.value = false;
    }
  };

  return { logs, loading, error, load };
}
