import { expect, it, vi } from "vite-plus/test";
import { flushPromises, DOMWrapper } from "@vue/test-utils";
import { http, HttpResponse } from "msw";
import HomeView from "../HomeView.vue";
import CharactersView from "../CharactersView.vue";
import CharacterDetailView from "../CharacterDetailView.vue";
import CharacterCard from "@/components/discover/CharacterCard.vue";
import CharacterContextMenu from "@/components/discover/CharacterContextMenu.vue";
import { installAppApi } from "@/test/appApi";
import { mountView, button } from "@/test/views";
import { server } from "@/mocks/server";
import { useToastState } from "@/composables/useToast";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
it("offers setup for an unconfigured library and remembers dismissal", async () => {
  const { db } = installAppApi();
  db.profiles.splice(0);
  localStorage.removeItem("bannered-mare:setup-dismissed");
  const { wrapper, router } = await mountView(HomeView, "/");
  await flushPromises();
  await button(wrapper, "I'll do it manually").trigger("click");
  expect(localStorage.getItem("bannered-mare:setup-dismissed")).toBe("true");
  localStorage.removeItem("bannered-mare:setup-dismissed");
  const second = await mountView(HomeView, "/");
  await flushPromises();
  await button(second.wrapper, "Get Started").trigger("click");
  await vi.waitFor(() => expect(second.router.currentRoute.value.path).toBe("/setup"));
  expect(router.currentRoute.value.path).toBe("/");
  localStorage.removeItem("bannered-mare:setup-dismissed");
});
it("handles context actions and preserves characters when deletion fails", async () => {
  const { db } = installAppApi();
  server.use(
    http.delete("/api/characters/:id", () =>
      HttpResponse.json({ detail: "In use" }, { status: 409 }),
    ),
  );
  const { wrapper, router } = await mountView(CharactersView, "/characters");
  await flushPromises();
  const log = vi.spyOn(console, "log").mockImplementation(() => {});
  const card = wrapper.findAllComponents(CharacterCard)[0]!;
  const menu = card.findComponent(CharacterContextMenu);
  for (const label of ["Duplicate", "Export JSON"]) {
    await menu.get("button").trigger("click");
    await button(menu, label).trigger("click");
  }
  expect(log).toHaveBeenCalledTimes(2);
  log.mockRestore();
  await menu.get("button").trigger("click");
  await button(menu, "Delete").trigger("click");
  const dialog = new DOMWrapper(document.querySelector<HTMLElement>('[role="dialog"]')!);
  await button(dialog, t("common.delete")).trigger("click");
  await flushPromises();
  expect(useToastState().value.at(-1)?.title).toBe(t("characters.deleteFailed"));
  expect(wrapper.text()).toContain(db.characters[0].name);
  await menu.get("button").trigger("click");
  await button(menu, "Edit").trigger("click");
  await vi.waitFor(() =>
    expect(router.currentRoute.value.path).toBe(`/characters/${db.characters[0].id}/edit`),
  );
  useToastState().value = [];
});
it.each(["others", null])(
  "renders sparse character metadata with gender %s and safe avatar fallback",
  async (gender) => {
    const { db } = installAppApi();
    const char = db.characters[0];
    Object.assign(char, {
      gender,
      custom_gender: "Nonbinary",
      avatar_large: null,
      avatar: null,
      scenario: "A distant island",
      tags: [],
      description: null,
      personality: null,
      first_message: null,
      example_messages: [],
      creator_notes: null,
    });
    const { wrapper } = await mountView(
      CharacterDetailView,
      `/characters/${char.id}`,
      "/characters/:id",
    );
    await flushPromises();
    expect(wrapper.text()).toContain(char.name);
    if (gender) expect(wrapper.text()).toContain("Nonbinary");
    expect(wrapper.get("img").attributes("src")).toBeTruthy();
  },
);
