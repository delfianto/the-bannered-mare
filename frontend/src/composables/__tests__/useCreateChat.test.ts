import { afterEach, describe, expect, it, vi } from "vite-plus/test";
import { createMemoryHistory, createRouter } from "vue-router";
import { http, HttpResponse } from "msw";
import { useCreateChat } from "@/composables/useCreateChat";
import { useToastState } from "@/composables/useToast";
import { profiles } from "@/mocks/data/profiles";
import { server } from "@/mocks/server";
import { mountComposable } from "@/test/helpers";
import { nextTick } from "vue";

async function setup(items = profiles) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: { template: "<div/>" } },
      { path: "/setup", component: { template: "<div/>" } },
      { path: "/chats/:chatId", name: "chat", component: { template: "<div/>" } },
    ],
  });
  await router.push("/");
  await router.isReady();
  server.use(http.get("/api/profiles/", () => HttpResponse.json({ items })));
  const { api } = mountComposable(useCreateChat, { global: { plugins: [router] } });
  return { api, router };
}
afterEach(() => {
  useToastState().value = [];
  vi.restoreAllMocks();
});

describe("starting a tale", () => {
  it("routes to setup if no profile has a model attached", async () => {
    const { api, router } = await setup([{ ...profiles[0], model_id: null }]);
    await api.startTale("character");
    expect(router.currentRoute.value.path).toBe("/setup");
    expect(useToastState().value.at(-1)?.type).toBe("info");
    expect(api.creating.value).toBe(false);
  });

  it("immediately creates a chat when exactly one ready profile exists", async () => {
    const { api, router } = await setup([{ ...profiles[0], model_id: null }, profiles[1]]);
    server.use(
      http.post("/api/chats", async ({ request }) => {
        expect(await request.json()).toEqual({
          character_id: "character",
          profile_id: profiles[1].id,
          is_bookmarked: false,
        });
        return HttpResponse.json({ id: "chat-new" });
      }),
    );
    await api.startTale("character");
    expect(router.currentRoute.value.params.chatId).toBe("chat-new");
    expect(api.profileChoices.value).toBeNull();
  });

  it("offers ready profiles and creates with the selected profile only after confirmation", async () => {
    const { api, router } = await setup([
      profiles[0],
      profiles[1],
      { ...profiles[2], model_id: null },
    ]);
    let writes = 0;
    server.use(
      http.post("/api/chats", async ({ request }) => {
        writes++;
        expect(await request.json()).toMatchObject({
          character_id: "character",
          profile_id: profiles[1].id,
        });
        return HttpResponse.json({ id: "picked" });
      }),
    );
    await api.startTale("character");
    expect(api.profileChoices.value).toHaveLength(2);
    expect(writes).toBe(0);
    await api.chooseProfile(profiles[1].id);
    expect(router.currentRoute.value.params.chatId).toBe("picked");
    expect(api.profileChoices.value).toBeNull();
    expect(writes).toBe(1);
    await api.chooseProfile(profiles[1].id);
    expect(writes).toBe(1);
  });

  it("cancel clears the pending character and prevents accidental later creation", async () => {
    const { api, router } = await setup();
    await api.startTale("character");
    api.cancelProfilePick();
    await api.chooseProfile(profiles[0].id);
    await nextTick();
    expect(api.profileChoices.value).toBeNull();
    expect(router.currentRoute.value.path).toBe("/");
  });

  it("profile load errors reject to the caller, show a toast, and release the busy state", async () => {
    const { api } = await setup();
    server.use(http.get("/api/profiles/", () => HttpResponse.json({}, { status: 503 })));
    await expect(api.startTale("character")).rejects.toThrow("Failed to load profiles");
    expect(api.creating.value).toBe(false);
    expect(useToastState().value.at(-1)?.type).toBe("error");
  });

  it("failed creation after choosing a profile keeps the route unchanged", async () => {
    const { api, router } = await setup();
    await api.startTale("character");
    server.use(http.post("/api/chats", () => HttpResponse.json({}, { status: 422 })));
    await api.chooseProfile(profiles[0].id);
    expect(router.currentRoute.value.path).toBe("/");
    expect(api.creating.value).toBe(false);
    expect(useToastState().value.at(-1)?.type).toBe("error");
  });
});
