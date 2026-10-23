import { afterEach, beforeEach, describe, expect, it, vi } from "vite-plus/test";
import { http, HttpResponse } from "msw";
import { useChatLlmLogs } from "@/composables/useChatLlmLogs";
import { useChatPromptPreview } from "@/composables/useChatPromptPreview";
import { server } from "@/mocks/server";
import { deferred } from "@/test/helpers";

beforeEach(() => vi.spyOn(console, "error").mockImplementation(() => {}));
afterEach(() => vi.restoreAllMocks());
describe("chat drawer caches", () => {
  it("empty audit results are cached; invalidation and force refresh fetch again", async () => {
    let reads = 0;
    server.use(
      http.get("/admin/logs/llm", ({ request }) => {
        reads++;
        const q = new URL(request.url).searchParams;
        expect(q.get("limit")).toBe("25");
        expect(q.get("chat_id")).toBe("c");
        return HttpResponse.json({ items: [] });
      }),
    );
    const api = useChatLlmLogs();
    await api.load("");
    expect(reads).toBe(0);
    await api.load("c");
    await api.load("c");
    expect(reads).toBe(1);
    api.invalidate();
    await api.load("c");
    await api.load("c", true);
    expect(reads).toBe(3);
  });

  it("switching chats drops old logs immediately while same-chat refresh keeps them visible", async () => {
    const gate = deferred<void>();
    server.use(
      http.get("/admin/logs/llm", async ({ request }) => {
        const id = new URL(request.url).searchParams.get("chat_id");
        if (id === "new") await gate.promise;
        return HttpResponse.json({ items: [{ id }] });
      }),
    );
    const api = useChatLlmLogs();
    await api.load("old");
    expect(api.logs.value).toHaveLength(1);
    const pending = api.load("new");
    expect(api.logs.value).toEqual([]);
    gate.resolve();
    await pending;
    expect(api.logs.value[0].id).toBe("new");
  });

  it("failed audit loads are retryable and reset the busy flag", async () => {
    server.use(
      http.get("/admin/logs/llm", () =>
        HttpResponse.json({ detail: "Audit disabled" }, { status: 503 }),
      ),
    );
    const api = useChatLlmLogs();
    await api.load("c");
    expect(api.error.value?.message).toBe("Audit disabled");
    expect(api.loading.value).toBe(false);
    server.use(http.get("/admin/logs/llm", () => HttpResponse.json({ items: [] })));
    await api.load("c");
    expect(api.error.value).toBeNull();
  });

  it("prompt preview caches by chat ID and supports explicit refresh", async () => {
    let reads = 0;
    server.use(
      http.get("/api/chats/:id/prompt-preview", ({ params }) => {
        reads++;
        return HttpResponse.json({
          model_identifier: params.id,
          parameters: { temperature: 0.8 },
          messages: [],
        });
      }),
    );
    const api = useChatPromptPreview();
    await api.load("");
    await api.load("a");
    await api.load("a");
    expect(reads).toBe(1);
    expect(api.preview.value?.parameters).toEqual({ temperature: 0.8 });
    await api.load("a", true);
    await api.load("b");
    expect(reads).toBe(3);
    expect(api.preview.value?.model_identifier).toBe("b");
  });

  it("failed prompt-preview requests show the error and can be retried", async () => {
    server.use(
      http.get("/api/chats/:id/prompt-preview", () =>
        HttpResponse.json({ detail: "No model configured" }, { status: 422 }),
      ),
    );
    const api = useChatPromptPreview();
    await api.load("a");
    expect(api.loading.value).toBe(false);
    expect(api.error.value?.message).toBe("No model configured");
    server.use(
      http.get("/api/chats/:id/prompt-preview", () =>
        HttpResponse.json({ parameters: {}, messages: [] }),
      ),
    );
    await api.load("a");
    expect(api.error.value).toBeNull();
    expect(api.preview.value).not.toBeNull();
  });
});
