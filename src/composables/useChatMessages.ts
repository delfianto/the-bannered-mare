import { ref, watch } from "vue";
import type { components } from "@/api/schema";
import { client } from "@/api/client";

type Message = components["schemas"]["MessageResponse"];

interface UseChatMessagesOptions {
  pageSize?: number;
  autoLoad?: boolean;
}

export function useChatMessages(
  getChatId: () => string | null,
  options: UseChatMessagesOptions = {},
) {
  const { pageSize = 20, autoLoad = true } = options;

  const messages = ref<Message[]>([]);
  const loading = ref(false);
  const hasMore = ref(false);
  const nextCursor = ref<string | null>(null);
  const error = ref<Error | null>(null);

  const loadMessages = async (cursor?: string) => {
    const currentChatId = getChatId();
    if (!currentChatId) return;

    loading.value = true;
    error.value = null;

    try {
      const { data, error: apiError } = await client.GET("/api/chats/{chat_id}/messages", {
        params: {
          path: { chat_id: currentChatId },
          query: {
            limit: pageSize,
            cursor: cursor || undefined,
          },
        },
      });

      if (apiError) {
        throw new Error(`Failed to load messages: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        const newMessages: Message[] = Array.isArray(data) ? data : data.items;
        const meta = Array.isArray(data) ? null : data.meta;

        // The API returns Newest -> Oldest.
        // batch = [Latest_in_batch, ..., Oldest_in_batch]

        if (meta) {
          hasMore.value = meta.has_more;
          nextCursor.value = meta.cursor || null;
        } else {
          hasMore.value = newMessages.length >= pageSize;
          nextCursor.value = hasMore.value ? newMessages[newMessages.length - 1].created_at : null;
        }

        // We want to display Oldest -> Newest in the UI state.
        // [Oldest_in_batch, ..., Latest_in_batch]
        const sortedBatch = [...newMessages].reverse();

        if (cursor) {
          messages.value = [...sortedBatch, ...messages.value];
        } else {
          messages.value = sortedBatch;
        }
      }
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error("Error loading messages:", err);
    } finally {
      loading.value = false;
    }
  };

  const loadMore = async () => {
    if (hasMore.value && !loading.value && nextCursor.value) {
      await loadMessages(nextCursor.value);
    }
  };

  const refresh = () => {
    messages.value = [];
    hasMore.value = false;
    nextCursor.value = null;
    loadMessages();
  };

  // Track if we are currently generating (prevents double clicks and triggers scroll)
  const isGenerating = ref(false);

  // Helper to process the SSE stream (Shared logic)
  const readStream = async (response: Response) => {
    if (!response.body) return;
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    // Create a temporary "pending" message
    const tempMsg: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      active_index: 0,
      created_at: new Date().toISOString(),
      chat_id: getChatId()!,
    };

    // Add to UI immediately
    messages.value = [...messages.value, tempMsg];

    const assistantMsgIndex = messages.value.length - 1;
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6);
            if (dataStr === "[DONE]") break;

            try {
              const data = JSON.parse(dataStr);
              if (data.error) throw new Error(data.error);
              if (data.text) {
                // Mutate the reactive message object
                // We use a new object reference to ensure standard watchers trigger
                const currentMsg = messages.value[assistantMsgIndex];
                if (currentMsg) {
                  messages.value[assistantMsgIndex] = {
                    ...currentMsg,
                    content: currentMsg.content + data.text,
                  };
                }
              }
            } catch (e) {
              console.warn("Stream parse error", e);
            }
          }
        }
      }
    } finally {
      isGenerating.value = false;
    }
  };

  const regenerate = async () => {
    const chatId = getChatId();
    if (!chatId || isGenerating.value) return;

    // Optimistic UI Update: Remove the "bad" response immediately
    const lastMsg = messages.value.at(-1);
    if (lastMsg?.role === "assistant") {
      messages.value = messages.value.slice(0, -1);
    }

    isGenerating.value = true;
    error.value = null;

    try {
      const response = await fetch(`/api/chats/${chatId}/messages?stream=true&regenerate=true`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(null),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Regeneration failed");
      }

      await readStream(response);
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Regeneration failed");
      isGenerating.value = false;
      await loadMessages();
    }
  };

  const sendMessage = async (content: string) => {
    const chatId = getChatId();
    if (!chatId || isGenerating.value) return;

    // Optimistic Update (User Message)
    const tempUserMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: content,
      active_index: 0,
      created_at: new Date().toISOString(),
      chat_id: chatId,
    };
    messages.value = [...messages.value, tempUserMsg];

    isGenerating.value = true;
    error.value = null;

    try {
      const response = await fetch(`/api/chats/${chatId}/messages?stream=true`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ content }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Failed to send message");
      }

      await readStream(response);
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Failed to send message");
      isGenerating.value = false;
    }
  };

  const editMessage = async (messageId: string, newContent: string) => {
    const chatId = getChatId();
    if (!chatId) return;
    try {
      const response = await fetch(`/api/chats/${chatId}/messages/${messageId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: newContent }),
      });
      if (!response.ok) throw new Error("Failed to edit");
      // Optimistic update
      const idx = messages.value.findIndex((m) => m.id === messageId);
      if (idx !== -1) {
        messages.value[idx] = { ...messages.value[idx], content: newContent };
      }
    } catch (err) {
      console.error("Error editing message:", err);
      throw err;
    }
  };

  const fetchAlternatives = async (messageId: string): Promise<any[]> => {
    const chatId = getChatId();
    if (!chatId) return [];
    try {
      const response = await fetch(`/api/chats/${chatId}/messages/${messageId}/alternatives`);
      if (!response.ok) return [];
      return await response.json();
    } catch {
      return [];
    }
  };

  const activateAlternative = async (messageId: string, alternativeId: string) => {
    const chatId = getChatId();
    if (!chatId) return;
    try {
      const response = await fetch(
        `/api/chats/${chatId}/messages/${messageId}/alternatives/${alternativeId}/activate`,
        { method: "PUT" },
      );
      if (!response.ok) throw new Error("Failed to activate");
      const updated = await response.json();
      // Update message content locally
      const idx = messages.value.findIndex((m) => m.id === messageId);
      if (idx !== -1) {
        messages.value[idx] = { ...messages.value[idx], content: updated.content, active_index: updated.active_index };
      }
    } catch (err) {
      console.error("Error activating alternative:", err);
    }
  };

  watch(
    () => getChatId(),
    (newChatId) => {
      if (autoLoad && newChatId) {
        messages.value = [];
        hasMore.value = false;
        nextCursor.value = null;
        loadMessages();
      } else if (!newChatId) {
        messages.value = [];
        hasMore.value = false;
        nextCursor.value = null;
      }
    },
    { immediate: true },
  );

  return {
    messages,
    loading,
    hasMore,
    error,
    isGenerating,
    regenerate,
    loadMore,
    refresh,
    sendMessage,
    editMessage,
    fetchAlternatives,
    activateAlternative,
  };
}
