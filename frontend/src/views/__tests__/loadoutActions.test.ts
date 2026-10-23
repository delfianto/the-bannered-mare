import { afterEach, expect, it, vi } from "vite-plus/test";
import { DOMWrapper } from "@vue/test-utils";
import { http, HttpResponse } from "msw";
import ProfilesView from "../ProfilesView.vue";
import Modal from "@/components/shared/Modal.vue";
import ProfileCard from "@/components/profiles/ProfileCard.vue";
import { installAppApi } from "@/test/appApi";
import { mountView, button } from "@/test/views";
import { server } from "@/mocks/server";
import { useToastState } from "@/composables/useToast";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
const dialog = () => new DOMWrapper(document.querySelector<HTMLElement>('[role="dialog"]')!);
afterEach(() => {
  vi.restoreAllMocks();
  useToastState().value = [];
});
it("creates, edits, defaults and deletes profiles using their cards", async () => {
  const { db, requests } = installAppApi();
  server.use(
    http.post("/api/profiles/:id/default", ({ params }) => {
      const row = db.profiles.find((p) => p.id === params.id)!;
      row.is_default = true;
      return HttpResponse.json(row);
    }),
  );
  const { wrapper } = await mountView(ProfilesView, "/loadouts?tab=profiles", "/loadouts");
  await vi.waitFor(() =>
    expect(wrapper.findAllComponents(ProfileCard).length).toBe(db.profiles.length),
  );
  await button(wrapper, t("profiles.newProfile")).trigger("click");
  await dialog().get("input[type=text]").setValue("New loadout");
  await button(dialog(), t("profiles.form.create")).trigger("click");
  await vi.waitFor(() => expect(wrapper.text()).toContain("New loadout"));
  expect(requests.find((r) => r.method === "POST")?.body).toMatchObject({ name: "New loadout" });
  const card = wrapper.findAllComponents(ProfileCard)[0]!;
  await button(card, t("common.edit")).trigger("click");
  await dialog().get("input[type=text]").setValue("Revised loadout");
  await button(dialog(), t("profiles.form.save")).trigger("click");
  await vi.waitFor(() => expect(wrapper.text()).toContain("Revised loadout"));
  await button(card, t("profiles.setDefault")).trigger("click");
  await vi.waitFor(() => expect(card.text()).toContain(t("profiles.default")));
  await button(card, t("common.delete")).trigger("click");
  await card.trigger("mouseleave");
  await button(card, t("common.delete")).trigger("click");
  await button(card, t("profiles.confirmDelete")).trigger("click");
  await vi.waitFor(() => expect(wrapper.text()).not.toContain("Revised loadout"));
  await button(wrapper, t("profiles.newProfile")).trigger("click");
  await button(dialog(), t("common.cancel")).trigger("click");
});
it("retains a profile draft when saving fails", async () => {
  installAppApi();
  server.use(
    http.post("/api/profiles/", () => HttpResponse.json({ detail: "Read only" }, { status: 403 })),
  );
  const { wrapper } = await mountView(ProfilesView, "/loadouts?tab=profiles", "/loadouts");
  await vi.waitFor(() => expect(wrapper.findAllComponents(ProfileCard).length).toBeGreaterThan(0));
  await button(wrapper, t("profiles.newProfile")).trigger("click");
  await dialog().get("input[type=text]").setValue("Unsaved loadout");
  await button(dialog(), t("profiles.form.create")).trigger("click");
  await vi.waitFor(() =>
    expect(useToastState().value.at(-1)?.title).toBe(t("profiles.toast.createFailed")),
  );
  expect(wrapper.findComponent(Modal).props("show")).toBe(true);
  expect((dialog().get("input[type=text]").element as HTMLInputElement).value).toBe(
    "Unsaved loadout",
  );
});
it("creates, edits and deletes personas with multipart avatars", async () => {
  const { db, requests } = installAppApi();
  server.use(
    http.post("/api/personas/:id/set-default", ({ params }) => {
      const row = db.personas.find((p) => p.id === params.id)!;
      row.is_default = true;
      return HttpResponse.json(row);
    }),
  );
  const { wrapper } = await mountView(ProfilesView, "/loadouts?tab=personas", "/loadouts");
  await vi.waitFor(() => expect(wrapper.text()).toContain(db.personas[0].name));
  await button(wrapper, t("settings.persona.createPersona")).trigger("click");
  await dialog().get("input[type=text]").setValue("A wanderer");
  await dialog().get("textarea").setValue("A keen eye");
  await dialog().get("input[type=checkbox]").setValue(true);
  const file = dialog().get("input[type=file]");
  Object.defineProperty(file.element, "files", {
    value: [new File(["portrait"], "portrait.png", { type: "image/png" })],
  });
  await file.trigger("change");
  await button(dialog(), t("settings.persona.createPersona")).trigger("click");
  await vi.waitFor(() => expect(wrapper.text()).toContain("A wanderer"));
  expect(requests.find((r) => r.method === "POST")?.body).toMatchObject({
    name: "A wanderer",
    description: "A keen eye",
  });
  await wrapper.findAll('button[aria-label="Edit persona"]')[0]!.trigger("click");
  await dialog().get("input[type=text]").setValue("A ranger");
  await button(dialog(), t("settings.persona.saveChanges")).trigger("click");
  await vi.waitFor(() => expect(wrapper.text()).toContain("A ranger"));
  await wrapper.findAll('button[title="Set as default"]')[0]!.trigger("click");
  await wrapper.findAll('button[aria-label="Delete persona"]')[0]!.trigger("click");
  await wrapper.get('button[aria-label="Click again to confirm"]').trigger("mouseleave");
  await wrapper.findAll('button[aria-label="Delete persona"]')[0]!.trigger("click");
  await wrapper.get('button[aria-label="Click again to confirm"]').trigger("click");
  await vi.waitFor(() => expect(wrapper.text()).not.toContain("A ranger"));
  await button(wrapper, t("settings.persona.createPersona")).trigger("click");
  await button(dialog(), t("common.cancel")).trigger("click");
});
it("preserves persona edits on an API rejection", async () => {
  installAppApi();
  server.use(
    http.put("/api/personas/:id", () =>
      HttpResponse.json({ detail: "Avatar rejected" }, { status: 422 }),
    ),
  );
  const { wrapper } = await mountView(ProfilesView, "/loadouts?tab=personas", "/loadouts");
  await vi.waitFor(() =>
    expect(wrapper.find('button[aria-label="Edit persona"]').exists()).toBe(true),
  );
  await wrapper.findAll('button[aria-label="Edit persona"]')[0]!.trigger("click");
  await dialog().get("textarea").setValue("Keep my draft");
  await button(dialog(), t("settings.persona.saveChanges")).trigger("click");
  await vi.waitFor(() => expect(wrapper.text()).toContain("Avatar rejected"));
  expect((dialog().get("textarea").element as HTMLTextAreaElement).value).toBe("Keep my draft");
});
