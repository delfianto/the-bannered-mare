import { afterEach, beforeEach, describe, expect, it, vi } from "vite-plus/test";
import { http, HttpResponse } from "msw";
import { useLorebooks } from "@/composables/useLorebooks";
import { lorebooks } from "@/mocks/data/lorebooks";
import { server } from "@/mocks/server";

beforeEach(() => vi.spyOn(console, "error").mockImplementation(() => {}));
afterEach(() => vi.restoreAllMocks());
function setup() {
  const book = structuredClone(lorebooks[0]);
  const entry = book.entries[0];
  server.use(
    http.get("/api/lorebooks", () => HttpResponse.json({ items: [book] })),
    http.get("/api/lorebooks/:id", () => HttpResponse.json(book)),
  );
  return { api: useLorebooks(), book, entry };
}

describe("lorebook and entry persistence", () => {
  it("loads character-scoped and unfiltered collections", async () => {
    const { api } = setup();
    const queries: string[] = [];
    server.use(
      http.get("/api/lorebooks", ({ request }) => {
        queries.push(new URL(request.url).search);
        return HttpResponse.json({ items: [lorebooks[0]] });
      }),
    );
    await api.fetchLorebooks("character/one");
    await api.fetchLorebooks();
    expect(queries).toEqual(["?character_id=character%2Fone", ""]);
    expect(api.lorebooks.value).toHaveLength(1);
    expect(api.loading.value).toBe(false);
  });

  it("chat context combines global and character books without duplicate entries", async () => {
    const { api, book } = setup();
    const personal = { ...book, id: "personal", is_global: false };
    server.use(
      http.get("/api/lorebooks", ({ request }) =>
        HttpResponse.json({
          items: new URL(request.url).searchParams.has("character_id") ? [book, personal] : [book],
        }),
      ),
    );
    await api.fetchForChat("c");
    expect(api.lorebooks.value.map((b) => b.id)).toEqual([book.id, "personal"]);
    await api.fetchForChat();
    expect(api.lorebooks.value.map((b) => b.id)).toEqual([book.id]);
  });

  it("failure in either chat-context query retains the last complete snapshot", async () => {
    const { api, book } = setup();
    api.lorebooks.value = [book];
    server.use(
      http.get("/api/lorebooks", ({ request }) =>
        new URL(request.url).searchParams.has("character_id")
          ? HttpResponse.json({ detail: "Denied" }, { status: 403 })
          : HttpResponse.json({ items: [] }),
      ),
    );
    await api.fetchForChat("c");
    expect(api.error.value?.message).toBe("Denied");
    expect(api.lorebooks.value).toEqual([book]);
    expect(api.loading.value).toBe(false);
  });

  it("creates, edits and removes collection rows after successful HTTP responses", async () => {
    const { api, book } = setup();
    await api.fetchLorebooks();
    server.use(
      http.post("/api/lorebooks", async ({ request }) => {
        expect(await request.json()).toEqual({ name: "New", is_global: true });
        return HttpResponse.json({ ...book, id: "new", name: "New" });
      }),
      http.put("/api/lorebooks/:id", () => HttpResponse.json({ ...book, name: "Edited" })),
      http.delete("/api/lorebooks/:id", () => new HttpResponse(null, { status: 204 })),
    );
    await api.createLorebook({ name: "New", is_global: true });
    expect(api.lorebooks.value[0].id).toBe("new");
    await api.updateLorebook(book.id, { name: "Edited" });
    expect(api.lorebooks.value[1].name).toBe("Edited");
    expect(await api.deleteLorebook("new")).toBe(true);
    expect(api.lorebooks.value.map((b) => b.id)).toEqual([book.id]);
  });

  it("entry mutations reconcile the open detail without losing other entries", async () => {
    const { api, book, entry } = setup();
    await api.fetchLorebook(book.id);
    server.use(
      http.post("/api/lorebooks/:id/entries", () => HttpResponse.json({ ...entry, id: "new" })),
      http.put("/api/lorebooks/:id/entries/:entry", () =>
        HttpResponse.json({ ...entry, content: "Updated lore" }),
      ),
      http.delete(
        "/api/lorebooks/:id/entries/:entry",
        () => new HttpResponse(null, { status: 204 }),
      ),
    );
    expect(await api.createEntry(book.id, entry)).toMatchObject({ id: "new" });
    expect(api.currentLorebook.value?.entries).toHaveLength(3);
    await api.updateEntry(book.id, entry.id, { content: "Updated lore" });
    expect(api.currentLorebook.value?.entries[0].content).toBe("Updated lore");
    await api.deleteEntry(book.id, "new");
    expect(api.currentLorebook.value?.entries).toHaveLength(2);
  });

  it("writes to another book do not alter the currently open book", async () => {
    const { api, book, entry } = setup();
    await api.fetchLorebook(book.id);
    server.use(
      http.post("/api/lorebooks/:id/entries", () => HttpResponse.json(entry)),
      http.put("/api/lorebooks/:id/entries/:entry", () =>
        HttpResponse.json({ ...entry, content: "Other" }),
      ),
      http.delete(
        "/api/lorebooks/:id/entries/:entry",
        () => new HttpResponse(null, { status: 204 }),
      ),
    );
    await api.createEntry("other", entry);
    await api.updateEntry("other", entry.id, { content: "Other" });
    await api.deleteEntry("other", entry.id);
    expect(api.currentLorebook.value).toEqual(book);
  });

  it.each(["fetchLorebooks", "fetchLorebook"] as const)(
    "%s exposes errors, retains data and recovers on retry",
    async (method) => {
      const { api, book } = setup();
      await api.fetchLorebook(book.id);
      await api.fetchLorebooks();
      server.use(
        http.get("/api/lorebooks", () => HttpResponse.json({ detail: "Offline" }, { status: 503 })),
        http.get("/api/lorebooks/:id", () =>
          HttpResponse.json({ detail: "Offline" }, { status: 503 }),
        ),
      );
      await api[method](book.id);
      expect(api.error.value?.message).toBe("Offline");
      expect(api.currentLorebook.value).toEqual(book);
      expect(api.lorebooks.value).toEqual([book]);
      expect(api.loading.value).toBe(false);
    },
  );

  it.each([
    "createLorebook",
    "updateLorebook",
    "deleteLorebook",
    "createEntry",
    "updateEntry",
    "deleteEntry",
  ] as const)("failed %s preserves the last confirmed state", async (method) => {
    const { api, book, entry } = setup();
    await api.fetchLorebooks();
    await api.fetchLorebook(book.id);
    server.use(
      http.all("/api/lorebooks", () => HttpResponse.json({ detail: "Rejected" }, { status: 422 })),
      http.all("/api/lorebooks/*", () =>
        HttpResponse.json({ detail: "Rejected" }, { status: 422 }),
      ),
    );
    const result =
      method === "createLorebook"
        ? await api.createLorebook({ name: "No", is_global: false })
        : method === "updateLorebook"
          ? await api.updateLorebook(book.id, { name: "No" })
          : method === "deleteLorebook"
            ? await api.deleteLorebook(book.id)
            : method === "createEntry"
              ? await api.createEntry(book.id, entry)
              : method === "updateEntry"
                ? await api.updateEntry(book.id, entry.id, { content: "No" })
                : await api.deleteEntry(book.id, entry.id);
    expect(result).toBe(method.startsWith("delete") ? false : null);
    expect(api.currentLorebook.value).toEqual(book);
    expect(api.lorebooks.value).toEqual([book]);
  });
});
