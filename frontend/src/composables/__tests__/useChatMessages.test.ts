import { defineComponent, h, ref } from "vue";
import { describe, it, expect, afterEach, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
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

// Encode a single SSE `data:` frame (one event) as bytes — the unit the manual
// stream builders below enqueue.
function sseFrame(event: object): Uint8Array {
  return new TextEncoder().encode(`data: ${JSON.stringify(event)}\n\n`);
}

// Like sseResponse, but streams each string as its OWN chunk (one reader.read()
// apiece) so a single `data: {...}\n\n` frame can be split across reads — the
// buffer-reassembly path in readStream. The caller supplies raw wire text.
function sseResponseChunks(chunks: string[]): Response {
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(new TextEncoder().encode(chunk));
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

// AbortError as the fetch layer raises it when a body read is cancelled.
// readStream only checks `.name`, so a tagged Error works if a runtime somehow
// lacks DOMException.
function abortError(): Error {
  if (typeof DOMException !== "undefined") return new DOMException("Aborted", "AbortError");
  const err = new Error("Aborted");
  err.name = "AbortError";
  return err;
}

// A never-closing SSE Response that emits `events` up front, then errors its
// stream once `signal` aborts — mirroring how a real fetch body rejects the
// in-flight read on abort (stop() / chat switch). Without wiring the signal the
// mock stream would ignore the composable's AbortController entirely.
function abortableSse(events: object[], signal?: AbortSignal): Response {
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const event of events) controller.enqueue(sseFrame(event));
      signal?.addEventListener("abort", () => controller.error(abortError()));
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

// The cursor-list GET that reconcile / (auto)load fire around a send. These
// suites don't exercise reconciliation, so an empty page keeps
// them no-ops.
function emptyMessagesResponse(): Response {
  return new Response(
    JSON.stringify({
      items: [],
      meta: { limit: 2, has_more: false, cursor: null, total: 0, page: 1 },
    }),
    { status: 200, headers: { "Content-Type": "application/json" } },
  );
}

// Install a per-test fetch that routes the streaming POST (send/regenerate) to
// `stream` and every messages GET to `messages` (empty by default). Returns the
// recorded request lines so tests can assert on them (e.g. regenerate=true).
function installFetch(routes: {
  stream: (init: RequestInit) => Response | Promise<Response>;
  messages?: () => Response;
}): { calls: { method: string; url: string }[] } {
  const calls: { method: string; url: string }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
      const req = input instanceof Request ? input : null;
      const url = req ? req.url : String(input);
      const method = (init?.method ?? req?.method ?? "GET").toUpperCase();
      calls.push({ method, url });
      if (method === "POST" && url.includes("/messages?stream=true")) {
        return routes.stream(init ?? {});
      }
      if (method === "GET" && url.includes("/messages")) {
        return (routes.messages ?? emptyMessagesResponse)();
      }
      throw new Error(`unexpected request: ${method} ${url}`);
    }),
  );
  return { calls };
}

// Instantiate the composable inside a real mounted component so its onMounted
// lifecycle runs. autoLoad defaults off (no initial fetch); the chat-switch test
// opts in with a dynamic getChatId to drive the watch.
function mountComposable(getChatId: () => string | null = () => CHAT_ID, autoLoad = false) {
  let api!: ReturnType<typeof useChatMessages>;
  mount(
    defineComponent({
      setup() {
        api = useChatMessages(getChatId, { autoLoad });
        return () => h("div");
      },
    }),
  );
  return api;
}

describe("useChatMessages — reconcile the optimistic user-message id", () => {
  // The setup file's MSW server patched global.fetch; save it and restore after
  // each test so this suite's per-request mock doesn't leak.
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("swaps the client uuid for the persisted id after send, so editing it targets the real row (not a 404)", async () => {
    let editPutUrl = "";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
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
      }),
    );

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

describe("useChatMessages — SSE state machine (readStream + send/regenerate)", () => {
  // Same fetch save/restore discipline as the reconcile suite: MSW patched
  // global.fetch, so stash it and restore after each test so these per-request
  // mocks (and any console spies) don't leak into other files.
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("reassembles a data frame split across multiple reads", async () => {
    installFetch({
      stream: () =>
        sseResponseChunks([
          `data: {"type":"start","message_id":"a1"}\n\ndata: {"type":"text","content":"Hel`,
          `lo, `,
          `trav`,
          `eller"}\n\n`,
          `data: [DONE]\n\n`,
        ]),
    });

    const chat = mountComposable();
    await chat.sendMessage("hi");

    const assistant = chat.messages.value.find((m) => m.role === "assistant");
    expect(assistant?.content).toBe("Hello, traveller");
    expect(assistant?.id).toBe("a1");
  });

  it("treats [DONE] as end-of-stream — one bubble, no parse warning", async () => {
    installFetch({
      stream: () =>
        sseResponse([
          { type: "start", message_id: "a1" },
          { type: "text", content: "Done and dusted." },
          { type: "done", finish_reason: "stop" },
        ]),
    });

    const chat = mountComposable();
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    await chat.sendMessage("hi");

    const assistants = chat.messages.value.filter((m) => m.role === "assistant");
    expect(assistants).toHaveLength(1);
    expect(assistants[0]?.content).toBe("Done and dusted.");
    expect(chat.isGenerating.value).toBe(false);
    // `[DONE]` short-circuits before JSON.parse (never warns); the unhandled
    // `done` event simply matches no branch.
    expect(warn).not.toHaveBeenCalled();
  });

  it("tolerates a malformed-JSON frame — warns once and keeps streaming", async () => {
    installFetch({
      stream: () =>
        sseResponseChunks([
          `data: {"type":"start","message_id":"a1"}\n\n` +
            `data: {oops not valid json}\n\n` +
            `data: {"type":"text","content":"survived"}\n\n` +
            `data: [DONE]\n\n`,
        ]),
    });

    const chat = mountComposable();
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    await chat.sendMessage("hi");

    const assistant = chat.messages.value.find((m) => m.role === "assistant");
    expect(assistant?.content).toBe("survived");
    expect(warn).toHaveBeenCalledTimes(1);
    expect(warn.mock.calls[0]?.[0]).toContain("Stream parse error");
  });

  it("accumulates reasoning into reasoning_content, separate from text", async () => {
    installFetch({
      stream: () =>
        sseResponse([
          { type: "start", message_id: "a1" },
          { type: "reasoning", content: "Let me think. " },
          { type: "reasoning", content: "Almost there." },
          { type: "text", content: "The answer is 42." },
        ]),
    });

    const chat = mountComposable();
    await chat.sendMessage("hi");

    const assistant = chat.messages.value.find((m) => m.role === "assistant");
    expect(assistant?.reasoning_content).toBe("Let me think. Almost there.");
    expect(assistant?.content).toBe("The answer is 42.");
  });

  it("adopts the backend message id from the start event", async () => {
    installFetch({
      stream: () =>
        sseResponse([
          { type: "start", message_id: "srv-42" },
          { type: "text", content: "hail" },
        ]),
    });

    const chat = mountComposable();
    await chat.sendMessage("hi");

    const assistant = chat.messages.value.find((m) => m.role === "assistant");
    expect(assistant?.id).toBe("srv-42");
    expect(assistant?.content).toBe("hail");
  });

  it("keeps the optimistic placeholder id when start carries no message_id", async () => {
    installFetch({
      stream: () => sseResponse([{ type: "start" }, { type: "text", content: "hi" }]),
    });

    const chat = mountComposable();
    await chat.sendMessage("hi");

    const assistant = chat.messages.value.find((m) => m.role === "assistant");
    expect(assistant?.content).toBe("hi");
    // No backend id offered → the client uuid from addAssistantPlaceholder stays.
    expect(assistant?.id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-/i);
  });

  it("error event: resolves (does not reject), sets error.value, drops the empty placeholder", async () => {
    installFetch({
      stream: () =>
        sseResponse([
          { type: "start", message_id: "a1" },
          { type: "error", message: "boom" },
        ]),
    });

    const chat = mountComposable();
    // readStream throws on the error event, but sendMessage catches it into
    // error.value rather than rejecting to the caller.
    await expect(chat.sendMessage("x")).resolves.toBeUndefined();

    expect(chat.error.value?.message).toBe("boom");
    expect(chat.isGenerating.value).toBe(false);
    expect(chat.messages.value.some((m) => m.role === "assistant")).toBe(false);
  });

  it("non-OK send response: surfaces the detail and drops the placeholder", async () => {
    installFetch({
      stream: () =>
        new Response(JSON.stringify({ detail: "nope" }), {
          status: 500,
          headers: { "Content-Type": "application/json" },
        }),
    });

    const chat = mountComposable();
    await expect(chat.sendMessage("x")).resolves.toBeUndefined();

    expect(chat.error.value?.message).toBe("nope");
    expect(chat.isGenerating.value).toBe(false);
    expect(chat.messages.value.some((m) => m.role === "assistant")).toBe(false);
  });

  it("abort mid-stream: quiet return, no throw, no blank placeholder", async () => {
    installFetch({
      stream: (init) =>
        abortableSse([{ type: "start", message_id: "a1" }], init.signal ?? undefined),
    });

    const chat = mountComposable();
    const p = chat.sendMessage("x");
    await flushPromises(); // first (start) frame read; the reader is now parked
    expect(chat.isGenerating.value).toBe(true);

    chat.stop(); // aborts the signal -> stream errors -> read rejects (AbortError)
    await expect(p).resolves.toBeUndefined(); // swallowed, not rethrown

    expect(chat.isGenerating.value).toBe(false);
    expect(chat.error.value).toBeNull(); // abort is expected, not an error
    expect(chat.messages.value.some((m) => m.role === "assistant")).toBe(false);
  });

  it("chat switch mid-stream: post-switch tokens don't land in the new chat", async () => {
    const chatId = ref<string | null>("chat-A");
    let streamController!: ReadableStreamDefaultController<Uint8Array>;

    installFetch({
      stream: () => {
        const stream = new ReadableStream<Uint8Array>({
          start(controller) {
            streamController = controller;
            controller.enqueue(sseFrame({ type: "start", message_id: "a1" }));
            controller.enqueue(sseFrame({ type: "text", content: "Alpha" }));
            // Stay open — the switch happens while this stream is mid-flight.
          },
        });
        return new Response(stream, {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        });
      },
    });

    const chat = mountComposable(() => chatId.value, true);
    await flushPromises(); // chat-A initial load settles (empty)

    const p = chat.sendMessage("hi");
    await flushPromises(); // "Alpha" lands in the placeholder
    expect(chat.messages.value.some((m) => m.content === "Alpha")).toBe(true);

    // Switch chats: the watch aborts the read and (autoLoad) resets + reloads
    // into chat-B, so readStream's re-find-by-id now misses.
    chatId.value = "chat-B";
    await flushPromises();

    // A token that arrives AFTER the switch must not leak into chat-B.
    streamController.enqueue(sseFrame({ type: "text", content: "Beta" }));
    streamController.close();
    await flushPromises();
    await p;

    expect(chat.messages.value.some((m) => (m.content ?? "").includes("Alpha"))).toBe(false);
    expect(chat.messages.value.some((m) => (m.content ?? "").includes("Beta"))).toBe(false);
    expect(chat.messages.value).toHaveLength(0);
    expect(chat.isGenerating.value).toBe(false);
  });

  it("regenerate drops the prior assistant reply and streams a fresh one", async () => {
    let call = 0;
    const { calls } = installFetch({
      stream: () => {
        call += 1;
        return sseResponse([
          { type: "start", message_id: call === 1 ? "a1" : "a2" },
          { type: "text", content: call === 1 ? "First reply." : "Second reply." },
        ]);
      },
    });

    const chat = mountComposable();
    await chat.sendMessage("hi");
    expect(chat.messages.value.at(-1)?.content).toBe("First reply.");

    await chat.regenerate();

    const assistants = chat.messages.value.filter((m) => m.role === "assistant");
    expect(assistants).toHaveLength(1); // old reply dropped, new one in its place
    expect(assistants[0]?.content).toBe("Second reply.");
    expect(assistants[0]?.id).toBe("a2");
    expect(calls.some((c) => c.method === "POST" && c.url.includes("regenerate=true"))).toBe(true);
  });
});

describe("useChatMessages — stopping a regenerate restores the prior reply", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("restores the optimistically-removed reply when a regen is aborted mid-stream", async () => {
    // Regenerate persists only on completion, so an aborted regen leaves the prior
    // reply as the server's truth; loadMessages refetches it. GET is newest-first
    // (loadMessages reverses → [user, assistant]).
    const page = () =>
      new Response(
        JSON.stringify({
          items: [
            {
              id: "asst-1",
              role: "assistant",
              content: "The original reply.",
              active_index: 0,
              created_at: "2020-01-02T00:00:00Z",
              chat_id: CHAT_ID,
            },
            {
              id: "user-1",
              role: "user",
              content: "Hello",
              active_index: 0,
              created_at: "2020-01-01T00:00:00Z",
              chat_id: CHAT_ID,
            },
          ],
          meta: { limit: 30, has_more: false, cursor: null, total: 2, page: 1 },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );

    installFetch({
      // A regen stream that emits only `start` (no content), then hangs until abort.
      stream: (init) =>
        abortableSse([{ type: "start", message_id: "asst-2" }], init.signal ?? undefined),
      messages: page,
    });

    const chat = mountComposable(() => CHAT_ID, true);
    await flushPromises();
    expect(chat.messages.value.at(-1)?.content).toBe("The original reply.");

    const regen = chat.regenerate(); // removes asst-1, adds an empty placeholder
    await flushPromises(); // stream starts; `start` swaps the placeholder id
    chat.stop(); // abort → readStream re-throws AbortError → regenerate refetches
    await regen;
    await flushPromises();

    // The prior reply is back, with no empty placeholder / lost message.
    const assistants = chat.messages.value.filter((m) => m.role === "assistant");
    expect(assistants).toHaveLength(1);
    expect(assistants[0]?.content).toBe("The original reply.");
    expect(chat.messages.value.some((m) => m.content === "")).toBe(false);
  });
});
