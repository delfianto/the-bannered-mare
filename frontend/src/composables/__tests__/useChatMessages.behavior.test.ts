import { afterEach, describe, expect, it, vi } from "vite-plus/test";
import { ref, nextTick } from "vue";
import { http, HttpResponse } from "msw";
import { flushPromises } from "@vue/test-utils";
import { useChatMessages } from "@/composables/useChatMessages";
import { useCompletionSignal } from "@/composables/useCompletionSignal";
import { server } from "@/mocks/server";
import { mountComposable, deferred } from "@/test/helpers";
import type { components } from "@/api/schema";

type Message = components["schemas"]["MessageResponse"];
const message = (id = "m", content = "Original"): Message => ({
  id,
  chat_id: "c",
  role: "assistant",
  content,
  active_index: 0,
  created_at: "2026-10-23T00:00:00Z",
});
function setup(chatId = ref<string | null>("c")) {
  server.use(
    http.get("/api/chats/:id/messages", () =>
      HttpResponse.json({ items: [message()], meta: { has_more: false } }),
    ),
  );
  const host = mountComposable(() => useChatMessages(() => chatId.value, { autoLoad: false }));
  return { ...host, chatId };
}
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("chat actions", () => {
  it("missing chat IDs make all network actions no-ops", async () => {
    const { api } = setup(ref(null));
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    await api.sendMessage("hello");
    await api.regenerate();
    await api.editMessage("m", "edit");
    await api.activateAlternative("m", "a");
    expect(await api.fetchAlternatives("m")).toEqual([]);
    expect(await api.fetchSuggestions({ mode: "reply" })).toEqual([]);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("edits only the selected message after the server accepts the change", async () => {
    const { api } = setup();
    api.messages.value = [message(), message("other")];
    server.use(
      http.put("/api/chats/:id/messages/:message", async ({ request }) => {
        expect(await request.json()).toEqual({ content: "Edited" });
        return HttpResponse.json(message("m", "Edited"));
      }),
    );
    await api.editMessage("m", "Edited");
    expect(api.messages.value.map((m) => m.content)).toEqual(["Edited", "Original"]);
  });

  it("a rejected edit preserves the message and rejects with a useful error", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    const { api } = setup();
    api.messages.value = [message()];
    server.use(
      http.put("/api/chats/:id/messages/:message", () =>
        HttpResponse.json({ detail: "Cannot edit" }, { status: 409 }),
      ),
    );
    await expect(api.editMessage("m", "Lost")).rejects.toThrow("Cannot edit");
    expect(api.messages.value[0].content).toBe("Original");
  });

  it("suggestions send mode/tone/count and notify completion for audit refresh", async () => {
    const { api } = setup();
    const signal = useCompletionSignal();
    const tick = signal.tick.value;
    server.use(
      http.post("/api/chats/:id/messages/suggestions", async ({ request }) => {
        expect(await request.json()).toEqual({ mode: "impersonate", tone: "gentle", count: 1 });
        return HttpResponse.json({ suggestions: ["Hello, friend"] });
      }),
    );
    const pending = api.fetchSuggestions({ mode: "impersonate", tone: "gentle", count: 1 });
    expect(api.suggesting.value).toBe(true);
    expect(await pending).toEqual(["Hello, friend"]);
    expect(api.suggesting.value).toBe(false);
    expect(signal.tick.value).toBe(tick + 1);
    expect(signal.chatId.value).toBe("c");
  });

  it("suggestion failures return no candidates and expose the failure", async () => {
    const { api } = setup();
    server.use(
      http.post("/api/chats/:id/messages/suggestions", async ({ request }) => {
        expect(await request.json()).toEqual({ mode: "reply", tone: null, count: 3 });
        return HttpResponse.json({ detail: "Provider unavailable" }, { status: 503 });
      }),
    );
    expect(await api.fetchSuggestions({ mode: "reply" })).toEqual([]);
    expect(api.error.value?.message).toBe("Provider unavailable");
    expect(api.suggesting.value).toBe(false);
  });

  it("swipes wrap, reuse cached alternatives and apply the server's active index", async () => {
    const { api } = setup();
    api.messages.value = [message()];
    let reads = 0;
    server.use(
      http.get("/api/chats/:id/messages/:message/alternatives", () => {
        reads++;
        return HttpResponse.json([{ id: "a0" }, { id: "a1" }, { id: "a2" }]);
      }),
      http.put("/api/chats/:id/messages/:message/alternatives/:alt/activate", ({ params }) => {
        const index = Number(String(params.alt).slice(1));
        return HttpResponse.json({ content: `Reply ${index}`, active_index: index });
      }),
    );
    expect(api.getAlternativeCount("m")).toBeUndefined();
    await api.handleSwipe("m", "left");
    expect(api.messages.value[0].content).toBe("Reply 2");
    expect(api.getAlternativeCount("m")).toBe(3);
    expect(api.getCurrentAltIndex("m")).toBe(2);
    await api.handleSwipe("m", "right");
    expect(api.messages.value[0].active_index).toBe(0);
    expect(reads).toBe(1);
  });

  it("failed alternative activation leaves the displayed reply intact", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    const { api } = setup();
    api.messages.value = [message()];
    server.use(
      http.put("/api/chats/:id/messages/:message/alternatives/:alt/activate", () =>
        HttpResponse.json({ detail: "Missing alternative" }, { status: 404 }),
      ),
    );
    await api.activateAlternative("m", "missing");
    expect(api.messages.value[0]).toEqual(message());
  });

  it("a failed regeneration restores the prior reply and keeps the error visible", async () => {
    const { api } = setup();
    api.messages.value = [message()];
    server.use(
      http.post("/api/chats/:id/messages", () =>
        HttpResponse.json({ detail: "Provider quota exceeded" }, { status: 429 }),
      ),
    );
    await api.regenerate();
    expect(api.messages.value).toEqual([message()]);
    expect(api.isGenerating.value).toBe(false);
    expect(api.error.value?.message).toBe("Provider quota exceeded");
  });

  it("stopping before response headers removes the empty assistant placeholder", async () => {
    const { api } = setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url: string, init: RequestInit) =>
          new Promise<Response>((_resolve, reject) => {
            init.signal?.addEventListener("abort", () =>
              reject(new DOMException("Aborted", "AbortError")),
            );
          }),
      ),
    );
    const pending = api.sendMessage("Hello");
    expect(api.isGenerating.value).toBe(true);
    api.stop();
    await pending;
    expect(api.isGenerating.value).toBe(false);
    expect(api.messages.value.filter((m) => m.role === "assistant")).toEqual([]);
    expect(api.error.value).toBeNull();
  });

  it("unmount aborts a pending generation so a departed view cannot keep streaming", async () => {
    const { api, wrapper } = setup();
    let signal: AbortSignal | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url: string, init: RequestInit) =>
          new Promise<Response>((_resolve, reject) => {
            signal = init.signal!;
            signal.addEventListener("abort", () =>
              reject(new DOMException("Aborted", "AbortError")),
            );
          }),
      ),
    );
    const pending = api.sendMessage("Hello");
    wrapper.unmount();
    expect(signal?.aborted).toBe(true);
    await pending;
    expect(api.isGenerating.value).toBe(false);
  });

  it("stream decoder preserves multibyte text split inside a UTF-8 character", async () => {
    const { api } = setup();
    const bytes = new TextEncoder().encode('data: {"type":"text","content":"雪🐉"}\n\n');
    const split = bytes.indexOf(0xe9) + 1;
    server.use(
      http.post(
        "/api/chats/:id/messages",
        () =>
          new HttpResponse(
            new ReadableStream({
              start(controller) {
                controller.enqueue(bytes.slice(0, split));
                controller.enqueue(bytes.slice(split));
                controller.close();
              },
            }),
            { headers: { "Content-Type": "text/event-stream" } },
          ),
      ),
    );
    await api.sendMessage("Hi");
    expect(api.messages.value.at(-1)?.content).toBe("雪🐉");
  });

  it("a superseded request cannot clear the busy flag of a newer generation", async () => {
    const { api, chatId } = setup();
    const first = deferred<Response>(),
      second = deferred<Response>();
    let secondSignal: AbortSignal | undefined;
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockReturnValueOnce(first.promise)
        .mockImplementationOnce((_url: string, init: RequestInit) => {
          secondSignal = init.signal!;
          return second.promise;
        }),
    );
    const p1 = api.sendMessage("old");
    chatId.value = "new-chat";
    await nextTick();
    const p2 = api.sendMessage("new");
    first.reject(new DOMException("Aborted", "AbortError"));
    await p1;
    expect(api.isGenerating.value).toBe(true);
    api.stop();
    second.reject(new DOMException("Aborted", "AbortError"));
    await p2;
    await flushPromises();
    expect(secondSignal?.aborted).toBe(true);
  });
});

it("unmounting during regeneration aborts without starting a restoration fetch", async () => {
  const { api, wrapper } = setup();
  api.messages.value = [message()];
  const fetch = vi.fn((_url: string, init: RequestInit) => {
    if (init?.method === "POST")
      return new Promise<Response>((_resolve, reject) => {
        init.signal?.addEventListener("abort", () =>
          reject(new DOMException("Aborted", "AbortError")),
        );
      });
    return Promise.resolve(
      new Response(JSON.stringify({ items: [message()], meta: { has_more: false } })),
    );
  });
  vi.stubGlobal("fetch", fetch);
  const pending = api.regenerate();
  wrapper.unmount();
  await pending;
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("an SSE error cancels the unfinished body reader and preserves the provider error", async () => {
  const { api } = setup();
  const cancel = vi.fn();
  const response = new Response(
    new ReadableStream({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode('data: {"type":"error","message":"Provider disconnected"}\n\n'),
        );
      },
      cancel,
    }),
  );
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
  await api.sendMessage("hello");
  expect(cancel).toHaveBeenCalledTimes(1);
  expect(response.body?.locked).toBe(false);
  expect(api.error.value?.message).toBe("Provider disconnected");
  expect(api.isGenerating.value).toBe(false);
});
