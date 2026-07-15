import { defineComponent, h } from "vue";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { useChatMessages } from "@/composables/useChatMessages";

const CHAT_ID = "chat-1";

// Build a fake SSE Response whose body streams the given events (+ [DONE]).
function sseResponse(events: object[]): Response {
  const body = events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join("") + "data: [DONE]\n\n";
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(body));
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

// Instantiate the composable inside a real mounted component so its onMounted
// lifecycle runs (autoLoad is off, so no initial fetch fires).
function mountComposable() {
  let api!: ReturnType<typeof useChatMessages>;
  mount(
    defineComponent({
      setup() {
        api = useChatMessages(() => CHAT_ID, { autoLoad: false });
        return () => h("div");
      },
    }),
  );
  return api;
}

describe("useChatMessages — FE-C3: reconcile the optimistic user-message id", () => {
  // The setup file's MSW server patched global.fetch; save it and restore after
  // each test so this suite's per-request mock doesn't leak.
  let realFetch: typeof globalThis.fetch;
  beforeEach(() => {
    realFetch = globalThis.fetch;
  });
  afterEach(() => {
    globalThis.fetch = realFetch;
  });

  it("swaps the client uuid for the persisted id after send, so editing it targets the real row (not a 404)", async () => {
    let editPutUrl = "";
    globalThis.fetch = vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
      const req = input instanceof Request ? input : null;
      const url = req ? req.url : String(input);
      const method = (init?.method ?? req?.method ?? "GET").toUpperCase();

      // 1) The streaming send: assistant adopts a real id via `start`; the user id is never streamed.
      if (method === "POST" && url.includes("/messages?stream=true")) {
        return sseResponse([
          { type: "start", message_id: "asst-real" },
          { type: "text", content: "Greetings." },
          { type: "done", finish_reason: "stop" },
        ]);
      }
      // 2) The reconciliation fetch (2 newest, newest->oldest = assistant, then the user turn).
      if (method === "GET" && url.includes("/messages")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: "asst-real",
                role: "assistant",
                content: "Greetings.",
                active_index: 0,
                created_at: "2026-07-15T00:00:01Z",
                chat_id: CHAT_ID,
              },
              {
                id: "user-real",
                role: "user",
                content: "Hail",
                active_index: 0,
                created_at: "2026-07-15T00:00:00Z",
                chat_id: CHAT_ID,
              },
            ],
            meta: { limit: 2, has_more: false, cursor: null, total: 2, page: 1 },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      // 3) The edit PUT — capture the id it targets.
      if (method === "PUT" && url.includes("/messages/")) {
        editPutUrl = url;
        return new Response(
          JSON.stringify({
            id: "user-real",
            role: "user",
            content: "Hail, friend",
            active_index: 0,
            created_at: "2026-07-15T00:00:00Z",
            chat_id: CHAT_ID,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      throw new Error(`unexpected request: ${method} ${url}`);
    }) as typeof globalThis.fetch;

    const chat = mountComposable();
    await chat.sendMessage("Hail");

    const userMsg = chat.messages.value.find((m) => m.role === "user");
    // Pre-fix this would still be the client `crypto.randomUUID()`.
    expect(userMsg?.id).toBe("user-real");

    // Editing the just-sent message must hit the persisted row, not a phantom uuid.
    await expect(chat.editMessage(userMsg!.id, "Hail, friend")).resolves.toBeUndefined();
    expect(editPutUrl).toContain("/messages/user-real");
  });
});
