import { afterEach, beforeEach, describe, expect, it, vi } from "vite-plus/test";
import { createPinia, setActivePinia } from "pinia";
import { http, HttpResponse } from "msw";
import { flushPromises } from "@vue/test-utils";
import { usePersonas } from "@/composables/usePersonas";
import { useProfiles } from "@/composables/useProfiles";
import { useDataBank } from "@/composables/useDataBank";
import { useRag } from "@/composables/useRag";
import { useBookmarks } from "@/composables/useBookmarks";
import { personas } from "@/mocks/data/personas";
import { profiles } from "@/mocks/data/profiles";
import { server } from "@/mocks/server";
import { mountComposable } from "@/test/helpers";

beforeEach(() => setActivePinia(createPinia()));
afterEach(() => vi.restoreAllMocks());

describe("shared resources over their real API contracts", () => {
  it("persona upload reconciles every consumer and enforces one default without refetching", async () => {
    let reads = 0;
    const saved = { ...personas[0], id: "new", name: "New persona", is_default: true };
    server.use(
      http.get("/api/personas/", () => {
        reads++;
        return HttpResponse.json({ items: [{ ...personas[0], is_default: true }] });
      }),
      http.post("/api/personas/", async ({ request }) => {
        const body = await request.formData();
        expect(body.get("name")).toBe("New persona");
        expect(body.get("is_default")).toBe("true");
        return HttpResponse.json(saved);
      }),
    );
    const a = mountComposable(usePersonas).api,
      b = mountComposable(usePersonas).api;
    await vi.waitFor(() => expect(a.loading.value).toBe(false));
    expect(reads).toBe(1);
    await a.createPersona("New persona", true);
    expect(b.personas.value.map((p) => p.id)).toEqual(["new", personas[0].id]);
    expect(b.personas.value.filter((p) => p.is_default).map((p) => p.id)).toEqual(["new"]);
    expect(reads).toBe(1);
  });

  it("failed persona save preserves the shared row and exposes validation detail", async () => {
    server.use(
      http.get("/api/personas/", () => HttpResponse.json({ items: [personas[0]] })),
      http.put("/api/personas/:id", () =>
        HttpResponse.json({ detail: "Name required" }, { status: 422 }),
      ),
    );
    const { api } = mountComposable(usePersonas);
    await vi.waitFor(() => expect(api.loading.value).toBe(false));
    expect(await api.savePersona(new FormData(), personas[0].id)).toBeNull();
    expect(api.personas.value[0]).toEqual(personas[0]);
    expect(api.error.value?.message).toBe("Name required");
  });

  it("profile writes update all pickers and send the correct set-default endpoint", async () => {
    const row = { ...profiles[0] };
    server.use(
      http.get("/api/profiles/", () => HttpResponse.json({ items: [row] })),
      http.put("/api/profiles/:id", async ({ request }) => {
        expect(await request.json()).toEqual({ name: "Changed" });
        return HttpResponse.json({ ...row, name: "Changed" });
      }),
      http.post("/api/profiles/:id/default", () => new HttpResponse(null, { status: 204 })),
    );
    const a = mountComposable(useProfiles).api,
      b = mountComposable(useProfiles).api;
    await vi.waitFor(() => expect(a.loading.value).toBe(false));
    await a.updateProfile(row.id, { name: "Changed" });
    expect(b.profiles.value[0].name).toBe("Changed");
    expect(await a.setDefault(row.id)).toBe(true);
    expect(b.profiles.value[0].is_default).toBe(true);
  });

  it("data-bank scope requests forward chat and character IDs without leaking old filters", async () => {
    const queries: Record<string, string>[] = [];
    server.use(
      http.get("/api/data-bank/", ({ request }) => {
        queries.push(Object.fromEntries(new URL(request.url).searchParams));
        return HttpResponse.json({ items: [] });
      }),
    );
    const { api } = mountComposable(() => useDataBank({ autoLoad: false }));
    await api.fetchEntries("chat", "chat-1", "char-1");
    await api.fetchEntries();
    expect(queries).toEqual([{ scope: "chat", chat_id: "chat-1", character_id: "char-1" }, {}]);
  });

  it("semantic search sends limits/thresholds and preserves HTTP error status", async () => {
    server.use(
      http.post("/api/rag/search", async ({ request }) => {
        expect(await request.json()).toEqual({ query: "dragon", max_results: 3, threshold: 0.6 });
        return HttpResponse.json([{ content: "Dragon lore" }]);
      }),
    );
    const api = useRag();
    expect(await api.search("dragon", 3, 0.6)).toEqual([{ content: "Dragon lore" }]);
    server.use(
      http.post("/api/rag/search", () =>
        HttpResponse.json({ detail: "Embedding provider unavailable" }, { status: 503 }),
      ),
    );
    await expect(api.search("dragon")).rejects.toMatchObject({
      message: "Embedding provider unavailable",
      statusCode: 503,
    });
  });

  it("bookmark sections load together and a failed refresh retains the prior snapshot", async () => {
    let failed = false;
    server.use(
      http.get("/api/bookmarks/characters", () =>
        HttpResponse.json({ items: [{ id: "character" }] }),
      ),
      http.get("/api/bookmarks/sessions", () =>
        failed
          ? HttpResponse.json({ detail: "Unavailable" }, { status: 503 })
          : HttpResponse.json({ items: [{ id: "session" }] }),
      ),
      http.get("/api/bookmarks/messages", () => HttpResponse.json({ items: [{ id: "message" }] })),
    );
    const { api } = mountComposable(useBookmarks);
    await vi.waitFor(() => expect(api.loading.value).toBe(false));
    expect(api.totalCount.value).toBe(3);
    failed = true;
    await api.refresh();
    await flushPromises();
    expect(api.totalCount.value).toBe(3);
    expect(api.error.value?.message).toBe("Unavailable");
    expect(api.loading.value).toBe(false);
  });
});
