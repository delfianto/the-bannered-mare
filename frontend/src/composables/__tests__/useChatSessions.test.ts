import { afterEach, beforeEach, describe, expect, it, vi } from "vite-plus/test";
import { http, HttpResponse } from "msw";
import { useChatSessions } from "@/composables/useChatSessions";
import { chats } from "@/mocks/data/chats";
import { server } from "@/mocks/server";
import { mountComposable } from "@/test/helpers";
import { flushPromises } from "@vue/test-utils";

beforeEach(() => vi.spyOn(console, "error").mockImplementation(() => {}));
afterEach(() => vi.restoreAllMocks());
async function setup() {
  const row = structuredClone(chats[0]);
  server.use(
    http.get("/api/chats", () =>
      HttpResponse.json({ items: [row], meta: { has_more: false, cursor: null } }),
    ),
  );
  const { api } = mountComposable(useChatSessions);
  await vi.waitFor(() => expect(api.loading.value).toBe(false));
  return { api, row };
}
describe("chat session actions", () => {
  it("applies a saved edit to the current list", async () => {
    const { api, row } = await setup();
    server.use(
      http.put("/api/chats/:id", async ({ request }) => {
        expect(await request.json()).toEqual({ title: "Edited" });
        return HttpResponse.json({ ...row, title: "Edited" });
      }),
    );
    await api.updateChat(row.id, { title: "Edited" });
    expect(api.chatSessions.value[0].title).toBe("Edited");
  });

  it("delete removes the row only when the server accepts it", async () => {
    const { api, row } = await setup();
    server.use(
      http.delete("/api/chats/:id", () => HttpResponse.json({ detail: "In use" }, { status: 409 })),
    );
    await expect(api.deleteChat(row.id)).rejects.toThrow("In use");
    expect(api.chatSessions.value).toHaveLength(1);
    server.use(http.delete("/api/chats/:id", () => new HttpResponse(null, { status: 204 })));
    await api.deleteChat(row.id);
    expect(api.chatSessions.value).toEqual([]);
  });

  it("applies a profile and updates model-dependent session state", async () => {
    const { api, row } = await setup();
    server.use(
      http.post("/api/chats/:id/profile", async ({ request }) => {
        expect(await request.json()).toEqual({ profile_id: "profile-new" });
        return HttpResponse.json({ ...row, model: { id: "mdl-new", name: "New model" } });
      }),
    );
    expect(await api.applyProfile(row.id, "profile-new")).toMatchObject({
      model: { id: "mdl-new", name: "New model" },
    });
    expect(api.chatSessions.value[0].model.id).toBe("mdl-new");
  });

  it("failed profile application returns null without altering session state", async () => {
    const { api, row } = await setup();
    server.use(
      http.post("/api/chats/:id/profile", () =>
        HttpResponse.json({ detail: "No model" }, { status: 422 }),
      ),
    );
    expect(await api.applyProfile(row.id, "invalid")).toBeNull();
    expect(api.chatSessions.value[0]).toEqual(row);
  });

  it("generated titles update the row; failed generation leaves the last title intact", async () => {
    const { api, row } = await setup();
    server.use(
      http.post("/api/chats/:id/messages/title", () =>
        HttpResponse.json({ title: "A tale begins" }),
      ),
    );
    expect(await api.generateTitle(row.id)).toBe("A tale begins");
    expect(api.chatSessions.value[0].title).toBe("A tale begins");
    server.use(
      http.post("/api/chats/:id/messages/title", () => HttpResponse.json({}, { status: 503 })),
    );
    expect(await api.generateTitle(row.id)).toBeNull();
    expect(api.chatSessions.value[0].title).toBe("A tale begins");
    api.refresh();
    await flushPromises();
    expect(api.chatSessions.value[0].title).toBe(row.title);
  });
});
