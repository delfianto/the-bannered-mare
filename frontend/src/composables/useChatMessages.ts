import { ref, watch } from "vue";
import type { components } from "@/api/schema";
import { client, extractApiError, streamFetch } from "@/api/client";
import { useCompletionSignal } from "@/composables/useCompletionSignal";
import { useCursorList } from "@/composables/useCursorList";
import type { StreamEvent } from "@/types/chat";

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

  // The API returns messages Newest -> Oldest; we display Oldest -> Newest, so
  // each batch is reversed and older pages are prepended on top. `items` is
  // returned as-is (aliased to `messages`) so the streaming path below can keep
  // mutating it directly. The chat-switch watch drives the initial load, so the
  // factory doesn't autoLoad.
  const {
    items: messages,
    loading,
    hasMore,
    error,
    load: loadMessages,
    loadMore,
    reset,
  } = useCursorList<Message>({
    pageSize,
    hasMoreInitial: false,
    autoLoad: false,
    errorContext: "Failed to load messages",
    fetchPage: (cursor, limit) => {
      const chatId = getChatId();
      if (!chatId) return null;
      return client.GET("/api/chats/{chat_id}/messages", {
        params: { path: { chat_id: chatId }, query: { limit, cursor: cursor || undefined } },
      });
    },
    merge: (existing, batch, isInitial) => {
      const sortedBatch = [...batch].reverse();
      return isInitial ? sortedBatch : [...sortedBatch, ...existing];
    },
  });

  const refresh = () => {
    reset();
    loadMessages();
  };

  // Track if we are currently generating (prevents double clicks and triggers scroll)
  const isGenerating = ref(false);

  // Aborts the in-flight SSE generation (chat switch or an explicit stop), so we
  // don't keep reading tokens for a chat the user already left.
  let abortController: AbortController | null = null;

  const stop = () => {
    abortController?.abort();
    abortController = null;
    isGenerating.value = false;
  };

  // Announce every settled LLM call (success or error — both write audit rows)
  // so listeners like the drawer's Logs tab can refresh without a page reload.
  const { notify: notifyCompletion } = useCompletionSignal();

  // Next-turn suggestions (reply candidates / tone-steered impersonation)
  const suggesting = ref(false);

  const fetchSuggestions = async (opts: {
    mode: "reply" | "impersonate" | "tones";
    tone?: string | null;
    count?: number;
  }): Promise<string[]> => {
    const chatId = getChatId();
    if (!chatId) return [];
    suggesting.value = true;
    try {
      const { data, error: apiError } = await client.POST(
        "/api/chats/{chat_id}/messages/suggestions",
        {
          params: { path: { chat_id: chatId } },
          body: { mode: opts.mode, tone: opts.tone ?? null, count: opts.count ?? 3 },
        },
      );
      if (apiError) throw extractApiError(apiError, "Failed to get suggestions");
      return data?.suggestions ?? [];
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Failed to get suggestions");
      return [];
    } finally {
      suggesting.value = false;
      notifyCompletion(chatId);
    }
  };

  // Append an empty assistant bubble up front so the UI can show the "pending"
  // (quill) state inside it while we wait for the first token. readStream then
  // fills this same message as events arrive.
  const addAssistantPlaceholder = (): string => {
    const placeholder: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      active_index: 0,
      created_at: new Date().toISOString(),
      chat_id: getChatId()!,
    };
    messages.value = [...messages.value, placeholder];
    return placeholder.id;
  };

  // Helper to process the SSE stream (Shared logic). The empty assistant
  // placeholder is created by the caller so the bubble shows immediately.
  const readStream = async (response: Response, placeholderId: string) => {
    if (!response.body) return;
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    let buffer = "";
    let streamError: string | null = null;
    // The backend's `start` event carries the persisted message id; adopt it so
    // post-stream edits/alternatives target the real row, not the client uuid.
    let currentId = placeholderId;

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const dataStr = line.slice(6);
          if (dataStr === "[DONE]") continue;

          // Discriminated StreamEvent (mirrors the backend); JSON.parse is
          // untyped, so assert to the union and narrow on `type` below.
          let event: StreamEvent | null = null;
          try {
            event = JSON.parse(dataStr) as StreamEvent;
          } catch (e) {
            console.warn("Stream parse error", e);
          }
          if (!event) continue;

          if (event.type === "start") {
            // Swap the placeholder's client uuid for the backend id up front so
            // the freshly-streamed reply can be edited/re-rolled without a reload.
            if (event.message_id) {
              const startIdx = messages.value.findIndex((m) => m.id === currentId);
              if (startIdx === -1) return;
              messages.value[startIdx] = { ...messages.value[startIdx], id: event.message_id };
              currentId = event.message_id;
            }
            continue;
          }

          // Re-find by id every write: a chat switch resets `messages`, so a
          // cached index would write tokens into the wrong (or gone) message.
          const idx = messages.value.findIndex((m) => m.id === currentId);
          if (idx === -1) return;
          const currentMsg = messages.value[idx];

          if (event.type === "text" && event.content) {
            // New object reference so standard watchers trigger.
            messages.value[idx] = {
              ...currentMsg,
              content: currentMsg.content + event.content,
            };
          } else if (event.type === "reasoning" && event.content) {
            messages.value[idx] = {
              ...currentMsg,
              reasoning_content: (currentMsg.reasoning_content ?? "") + event.content,
            };
          } else if (event.type === "error") {
            streamError = event.message ?? "Generation failed";
            break;
          }
        }

        if (streamError) break;
      }
    } catch (err) {
      // Drop the placeholder if nothing streamed yet (kept once it accumulated
      // content) so an early stop or mid-stream failure never leaves a blank
      // assistant bubble. The id may already be the backend id (start event).
      messages.value = messages.value.filter((m) => m.id !== currentId || m.content);
      // Re-throw everything, incl. AbortError, so the caller can react: sendMessage
      // returns quietly, regenerate restores the reply it optimistically removed.
      throw err;
    } finally {
      isGenerating.value = false;
    }

    if (streamError) {
      // Drop the empty placeholder so an error never lingers as a blank reply.
      messages.value = messages.value.filter((m) => m.id !== currentId || m.content);
      throw new Error(streamError);
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

    const placeholderId = addAssistantPlaceholder();
    isGenerating.value = true;
    error.value = null;
    abortController = new AbortController();

    try {
      const response = await streamFetch(
        `/api/chats/${chatId}/messages?stream=true&regenerate=true`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(null),
          signal: abortController.signal,
        },
      );

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Regeneration failed");
      }

      await readStream(response, placeholderId);
    } catch (err) {
      if ((err as Error)?.name === "AbortError") {
        // Stopped mid-regen: readStream dropped the placeholder, so the reply we
        // optimistically removed would otherwise vanish. Refetch to bring it back
        // — but only if we're still on this chat (a chat switch reloads on its own).
        if (getChatId() === chatId) await loadMessages();
        return;
      }
      error.value = err instanceof Error ? err : new Error("Regeneration failed");
      isGenerating.value = false;
      await loadMessages();
    } finally {
      abortController = null;
      notifyCompletion(chatId);
    }
  };

  // After a send, the optimistic user bubble still holds its client uuid — only the
  // assistant placeholder adopted a real id (via the stream `start` event); the
  // backend never streams the user message's id. Fetch the two newest persisted
  // messages and swap the just-sent user message's id (matched by its temp id) in
  // place, so editing/regenerating it targets the real row instead of 404ing
  //. Surgical — it mutates `messages` directly rather than resetting the
  // cursor list, so pagination and scroll are preserved. Best-effort: on failure
  // the message still renders and editing it stays broken until the next reload
  // (the pre-fix behavior), so this never breaks a successful send.
  const reconcileSentUserMessage = async (chatId: string, tempId: string) => {
    try {
      const { data } = await client.GET("/api/chats/{chat_id}/messages", {
        params: { path: { chat_id: chatId }, query: { limit: 2 } },
      });
      const serverUser = data?.items?.find((m) => m.role === "user");
      if (!serverUser) return;
      const idx = messages.value.findIndex((m) => m.id === tempId);
      if (idx !== -1) messages.value[idx] = { ...messages.value[idx], ...serverUser };
    } catch {
      // Non-fatal: leave the optimistic id in place.
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

    const placeholderId = addAssistantPlaceholder();
    isGenerating.value = true;
    error.value = null;
    abortController = new AbortController();

    try {
      const response = await streamFetch(`/api/chats/${chatId}/messages?stream=true`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
        signal: abortController.signal,
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Failed to send message");
      }

      await readStream(response, placeholderId);
      // Swap the optimistic user-message id for its persisted one.
      await reconcileSentUserMessage(chatId, tempUserMsg.id);
    } catch (err) {
      if ((err as Error)?.name === "AbortError") return;
      error.value = err instanceof Error ? err : new Error("Failed to send message");
      isGenerating.value = false;
      // Drop the empty placeholder so a failed send doesn't leave a blank bubble.
      messages.value = messages.value.filter((m) => m.id !== placeholderId || m.content);
    } finally {
      abortController = null;
      notifyCompletion(chatId);
    }
  };

  const editMessage = async (messageId: string, newContent: string) => {
    const chatId = getChatId();
    if (!chatId) return;
    try {
      const { error: apiError } = await client.PUT("/api/chats/{chat_id}/messages/{message_id}", {
        params: { path: { chat_id: chatId, message_id: messageId } },
        body: { content: newContent },
      });
      if (apiError) throw extractApiError(apiError, "Failed to edit message");
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

  const fetchAlternatives = async (messageId: string) => {
    const chatId = getChatId();
    if (!chatId) return [];
    const { data, error: apiError } = await client.GET(
      "/api/chats/{chat_id}/messages/{message_id}/alternatives",
      { params: { path: { chat_id: chatId, message_id: messageId } } },
    );
    if (apiError || !data) return [];
    return data;
  };

  const activateAlternative = async (messageId: string, alternativeId: string) => {
    const chatId = getChatId();
    if (!chatId) return;
    try {
      const { data, error: apiError } = await client.PUT(
        "/api/chats/{chat_id}/messages/{message_id}/alternatives/{alternative_id}/activate",
        {
          params: {
            path: { chat_id: chatId, message_id: messageId, alternative_id: alternativeId },
          },
        },
      );
      if (apiError || !data) throw extractApiError(apiError, "Failed to activate alternative");
      // Update message content locally
      const idx = messages.value.findIndex((m) => m.id === messageId);
      if (idx !== -1) {
        messages.value[idx] = {
          ...messages.value[idx],
          content: data.content,
          active_index: data.active_index,
        };
      }
    } catch (err) {
      console.error("Error activating alternative:", err);
    }
  };

  // Swipe between an assistant message's alternatives — lazy-loads + caches the
  // list, then activates the neighbour. Moved out of ChatView; operates
  // purely on `messages` + fetchAlternatives/activateAlternative above.
  type Alternative = Awaited<ReturnType<typeof fetchAlternatives>>[number];
  const alternativesCache = ref(new Map<string, Alternative[]>());

  function getAlternativeCount(messageId: string): number | undefined {
    const alts = alternativesCache.value.get(messageId);
    return alts ? alts.length : undefined;
  }

  function getCurrentAltIndex(messageId: string): number | undefined {
    const msg = messages.value.find((m) => m.id === messageId);
    if (!msg) return undefined;
    return msg.active_index ?? 0;
  }

  async function handleSwipe(messageId: string, direction: "left" | "right") {
    // Lazy-load alternatives if not cached
    if (!alternativesCache.value.has(messageId)) {
      const alts = await fetchAlternatives(messageId);
      if (alts.length === 0) return;
      alternativesCache.value.set(messageId, alts);
      // Force reactivity by reassigning
      alternativesCache.value = new Map(alternativesCache.value);
    }

    const alts = alternativesCache.value.get(messageId);
    if (!alts || alts.length === 0) return;

    const msg = messages.value.find((m) => m.id === messageId);
    if (!msg) return;

    const currentIdx = msg.active_index ?? 0;
    let newIdx: number;

    if (direction === "left") {
      newIdx = currentIdx > 0 ? currentIdx - 1 : alts.length - 1;
    } else {
      newIdx = currentIdx < alts.length - 1 ? currentIdx + 1 : 0;
    }

    if (newIdx !== currentIdx && alts[newIdx]) {
      await activateAlternative(messageId, alts[newIdx].id);
    }
  }

  watch(
    () => getChatId(),
    (newChatId) => {
      // Cancel any in-flight generation for the chat we're leaving before we
      // reset messages, so its reader can't write into the new chat's array.
      stop();
      if (autoLoad && newChatId) {
        reset();
        loadMessages();
      } else if (!newChatId) {
        reset();
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
    stop,
    suggesting,
    fetchSuggestions,
    regenerate,
    loadMore,
    refresh,
    sendMessage,
    editMessage,
    fetchAlternatives,
    activateAlternative,
    getAlternativeCount,
    getCurrentAltIndex,
    handleSwipe,
  };
}
