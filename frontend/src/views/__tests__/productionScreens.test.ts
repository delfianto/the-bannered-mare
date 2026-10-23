import { afterEach, describe, expect, it, vi } from "vite-plus/test";
import { http, HttpResponse } from "msw";
import MemoryView from "../MemoryView.vue";
import ConnectionsView from "../ConnectionsView.vue";
import ProfilesView from "../ProfilesView.vue";
import SettingsView from "../settings/SettingsView.vue";
import HomeView from "../HomeView.vue";
import BookmarksView from "../BookmarksView.vue";
import CharacterDetailView from "../CharacterDetailView.vue";
import { installAppApi } from "@/test/appApi";
import { mountView, button } from "@/test/views";
import { server } from "@/mocks/server";
import { useToastState } from "@/composables/useToast";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
afterEach(() => {
  useToastState().value = [];
  vi.restoreAllMocks();
});

describe("library and resource screens", () => {
  it("home loads real library sections and links to creation", async () => {
    const { db } = installAppApi();
    const { wrapper } = await mountView(HomeView, "/");
    await vi.waitFor(() => expect(wrapper.text()).toContain(db.characters[0].name));
    expect(wrapper.findAll("a").length + wrapper.findAll("button").length).toBeGreaterThan(2);
  });

  it.each(["models", "providers", "model-families"])(
    "connection tab %s loads its real resource table",
    async (tab) => {
      const { db } = installAppApi();
      const { wrapper } = await mountView(
        ConnectionsView,
        `/connections?tab=${tab}`,
        "/connections",
      );
      const expected =
        tab === "models"
          ? db.models[0].display_name
          : tab === "providers"
            ? db.providers[0].name
            : db.families[0].name;
      await vi.waitFor(() => expect(wrapper.text()).toContain(expected));
      if (tab !== "providers") expect(wrapper.find("table").exists()).toBe(true);
    },
  );

  it.each(["profiles", "personas", "templates", "presets", "fragments"])(
    "loadout tab %s displays the shared resource",
    async (tab) => {
      const { db } = installAppApi();
      const { wrapper } = await mountView(ProfilesView, `/loadouts?tab=${tab}`, "/loadouts");
      const expected = {
        profiles: db.profiles[0].name,
        personas: db.personas[0].name,
        templates: db.templates[0].name,
        presets: db.presets[0].name,
        fragments: db.fragments[0].name,
      }[tab]!;
      await vi.waitFor(() => expect(wrapper.text()).toContain(expected));
    },
  );

  it("bookmarks renders saved characters and sessions and scrolls the character strip", async () => {
    const { db } = installAppApi();
    const { wrapper } = await mountView(BookmarksView, "/bookmarks");
    await vi.waitFor(() => expect(wrapper.text()).toContain(db.characters[0].name));
    expect(wrapper.text()).toContain(db.chats[0].title);
    const strip = wrapper.get(".scrollbar-hide");
    const scroll = vi.spyOn(strip.element, "scrollBy");
    await wrapper.get(`button[aria-label="${t("bookmarks.scrollLeft")}"]`).trigger("click");
    await wrapper.get(`button[aria-label="${t("bookmarks.scrollRight")}"]`).trigger("click");
    expect(scroll.mock.calls).toEqual([
      [{ left: -320, behavior: "smooth" }],
      [{ left: 320, behavior: "smooth" }],
    ]);
  });

  it("character detail renders long-form fields and starts a tale with an explicit profile", async () => {
    const { db } = installAppApi();
    const character = db.characters[0];
    const { wrapper, router } = await mountView(
      CharacterDetailView,
      `/characters/${character.id}`,
      "/characters/:id",
    );
    await vi.waitFor(() => expect(wrapper.text()).toContain(character.name));
    await button(wrapper, t("characters.detail.startTale")).trigger("click");
    await vi.waitFor(() => expect(document.body.textContent).toContain(db.profiles[0].name));
    const choice = Array.from(document.querySelectorAll<HTMLButtonElement>("button")).find(
      (b) => b.textContent?.trim() === "Start tale",
    )!;
    choice.click();
    await vi.waitFor(() => expect(router.currentRoute.value.path).toMatch(/^\/chats\//));
  });

  it("missing characters display a recovery action", async () => {
    installAppApi();
    const { wrapper, router } = await mountView(
      CharacterDetailView,
      "/characters/missing",
      "/characters/:id",
    );
    await vi.waitFor(() => expect(wrapper.text()).toContain(t("characters.detail.backToLibrary")));
    await button(wrapper, t("characters.detail.backToLibrary")).trigger("click");
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe("/characters"));
  });

  it("memory entries can be created, edited and removed without losing neighboring rows", async () => {
    const { db, requests } = installAppApi();
    const { wrapper } = await mountView(MemoryView, "/memory");
    await vi.waitFor(() => expect(wrapper.text()).toContain(db.memories[0].name));
    await button(wrapper, t("memory.addEntry")).trigger("click");
    await wrapper
      .get('input[placeholder="' + t("memory.form.namePlaceholder") + '"]')
      .setValue("New memory");
    await wrapper.get("textarea").setValue("The dragon remembers");
    await wrapper.get("select").setValue("global");
    await button(wrapper, t("memory.form.createEntry")).trigger("click");
    await vi.waitFor(() =>
      expect(wrapper.findAll("h3").some((h) => h.text() === "New memory")).toBe(true),
    );
    expect(
      requests.find((r) => r.method === "POST" && r.path === "/api/data-bank/")?.body,
    ).toMatchObject({ name: "New memory", content: "The dragon remembers", scope: "global" });
    await wrapper
      .findAll("button")
      .find((b) => b.text() === t("common.edit"))!
      .trigger("click");
    await wrapper.get("textarea").setValue("Revised");
    await button(wrapper, t("memory.form.saveChanges")).trigger("click");
    await vi.waitFor(() => expect(wrapper.text()).toContain("Revised"));
    await wrapper
      .findAll("button")
      .find((b) => b.text() === t("common.delete"))!
      .trigger("click");
    await button(wrapper, t("memory.confirmDelete")).trigger("click");
    await vi.waitFor(() =>
      expect(wrapper.findAll("h3").some((h) => h.text() === "New memory")).toBe(false),
    );
  });

  it("semantic search renders each source/relevance tier and recovers from rejection", async () => {
    installAppApi();
    let failed = false;
    server.use(
      http.post("/api/rag/search", () =>
        failed
          ? HttpResponse.json({ detail: "Search unavailable" }, { status: 503 })
          : HttpResponse.json(
              [0.9, 0.75, 0.6, 0.2].map((score, i) => ({
                score,
                source_type: ["data_bank", "lorebook", "character", "other"][i],
                content: `Retrieved ${i}`,
              })),
            ),
      ),
    );
    const { wrapper } = await mountView(MemoryView, "/memory");
    await vi.waitFor(() =>
      expect(wrapper.find('input[aria-label="Semantic search"]').exists()).toBe(true),
    );
    await wrapper.get('input[aria-label="Semantic search"]').setValue("dragon");
    await button(wrapper, t("common.search")).trigger("click");
    await vi.waitFor(() => expect(wrapper.text()).toContain("Retrieved 3"));
    failed = true;
    await button(wrapper, t("common.search")).trigger("click");
    await vi.waitFor(() =>
      expect(useToastState().value.at(-1)?.description).toBe("Search unavailable"),
    );
  });

  it("interface settings renders the actual preference controls", async () => {
    installAppApi();
    const { wrapper } = await mountView(SettingsView, "/settings");
    await vi.waitFor(() => expect(wrapper.find("input[type=range]").exists()).toBe(true));
    expect(wrapper.findAll("input[role=switch]").length).toBeGreaterThan(2);
  });
});
