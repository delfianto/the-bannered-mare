import { afterEach, expect, it, vi } from "vite-plus/test";
import { http, HttpResponse } from "msw";
import CharacterCreateView from "../CharacterCreateView.vue";
import { installAppApi } from "@/test/appApi";
import { mountView, button } from "@/test/views";
import { server } from "@/mocks/server";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
afterEach(() => vi.restoreAllMocks());
it("edits identity, behavior and world fields through the real creator controls", async () => {
  const { requests } = installAppApi();
  const { wrapper, router } = await mountView(CharacterCreateView, "/characters/create");
  await wrapper.get('input[placeholder="Isolde Fenwick"]').setValue("The Archivist");
  await wrapper
    .get('input[placeholder="Arcane Librarian of the Sunken Vaults"]')
    .setValue("Keeper");
  await wrapper.get('input[placeholder="127"]').setValue("42");
  const species = wrapper.get('input[placeholder="Half-Elf"]');
  await species.trigger("focus");
  await species.setValue("Elf");
  await button(wrapper, "Elf").trigger("click");
  const gender = wrapper.get('input[placeholder="Female"]');
  await gender.setValue("Custom");
  await gender.trigger("blur", { relatedTarget: null });
  await wrapper.findAll("textarea")[0]!.setValue("Preserves forgotten stories");
  await wrapper.findAll("textarea")[1]!.setValue("Creator note");
  const tags = wrapper.get(`input[placeholder="${t("characters.form.addTagsPlaceholder")}"]`);
  await tags.setValue("Scholar");
  await tags.trigger("keydown", { key: "Enter" });
  await wrapper.get('button[aria-label="Remove tag Scholar"]').trigger("click");
  await button(wrapper, t("characters.form.tabBehavior")).trigger("click");
  await wrapper.findAll("textarea")[0]!.setValue("Patient");
  await wrapper.findAll("textarea")[1]!.setValue("Welcome traveler");
  await wrapper.get('input[placeholder="Narrative"]').setValue("Verbose");
  await wrapper.get('input[placeholder="Narrative"]').trigger("blur");
  await button(wrapper, t("characters.form.addDialogue")).trigger("click");
  const dialogue = wrapper.findAll("textarea");
  await dialogue.at(-2)!.setValue("Hello");
  await dialogue.at(-1)!.setValue("Greetings");
  await wrapper.get(`button[aria-label="${t("characters.form.removeDialogue")}"]`).trigger("click");
  await button(wrapper, t("characters.form.tabWorld")).trigger("click");
  await wrapper.get("textarea").setValue("Ancient library");
  await button(wrapper, t("characters.form.advanced")).trigger("click");
  await wrapper.findAll("textarea").at(-1)!.setValue("Remain in character");
  await button(wrapper, t("characters.form.addLorebook")).trigger("click");
  const kw = wrapper.get(`input[placeholder="${t("characters.form.addKeywordPlaceholder")}"]`);
  await kw.setValue("library");
  await kw.trigger("keydown", { key: "Enter" });
  await wrapper.get('button[aria-label="Disable entry"]').trigger("click");
  await wrapper.get('button[aria-label="Enable entry"]').trigger("click");
  await wrapper.get('button[aria-label="Collapse entry"]').trigger("click");
  await wrapper.get('button[aria-label="Expand entry"]').trigger("click");
  await wrapper.get(`button[aria-label="${t("characters.form.removeLorebook")}"]`).trigger("click");
  await button(wrapper, t("common.save")).trigger("click");
  await vi.waitFor(() => expect(router.currentRoute.value.path).toBe("/characters"));
  expect(
    requests.find((r) => r.method === "POST" && r.path === "/api/characters")?.body,
  ).toMatchObject({
    name: "The Archivist",
    description: "Preserves forgotten stories",
    personality: "Patient",
    scenario: "Ancient library",
  });
});
it("loads an existing character, shows failed saves/deletes, then deletes successfully", async () => {
  const { db } = installAppApi();
  let fail = true;
  server.use(
    http.put("/api/characters/:id", () =>
      HttpResponse.json({ detail: "Save rejected" }, { status: 503 }),
    ),
    http.delete("/api/characters/:id", () =>
      fail ? HttpResponse.json({ detail: "Delete rejected" }, { status: 503 }) : undefined,
    ),
  );
  const { wrapper, router } = await mountView(
    CharacterCreateView,
    `/characters/${db.characters[0].id}/edit`,
    "/characters/:id/edit",
  );
  await vi.waitFor(() =>
    expect(
      (wrapper.get('input[placeholder="Isolde Fenwick"]').element as HTMLInputElement).value,
    ).toBe(db.characters[0].name),
  );
  await button(wrapper, t("common.save")).trigger("click");
  await vi.waitFor(() => expect(wrapper.text()).toContain("Save rejected"));
  await button(wrapper, t("common.delete")).trigger("click");
  await vi.waitFor(() => expect(wrapper.text()).toContain("Failed to delete character"));
  fail = false;
  await button(wrapper, t("common.delete")).trigger("click");
  await vi.waitFor(() => expect(router.currentRoute.value.path).toBe("/characters"));
});
it("renders a load failure without crashing the editable shell", async () => {
  installAppApi();
  const { wrapper } = await mountView(
    CharacterCreateView,
    "/characters/missing/edit",
    "/characters/:id/edit",
  );
  await vi.waitFor(() => expect(wrapper.text()).toContain(t("characters.failedLoad")));
});
