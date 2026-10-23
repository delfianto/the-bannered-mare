import { afterEach, expect, it, vi } from "vite-plus/test";
import { DOMWrapper } from "@vue/test-utils";
import { http, HttpResponse } from "msw";
import CharactersView from "../CharactersView.vue";
import CharacterCard from "@/components/discover/CharacterCard.vue";
import CharacterListRow from "@/components/discover/CharacterListRow.vue";
import { installAppApi } from "@/test/appApi";
import { mountView, button, pickOption } from "@/test/views";
import { server } from "@/mocks/server";
import { useToastState } from "@/composables/useToast";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
afterEach(() => {
  vi.restoreAllMocks();
  useToastState().value = [];
});
it("filters, sorts, switches views, selects and bulk deletes characters", async () => {
  const { db, requests } = installAppApi();
  const { wrapper, router } = await mountView(CharactersView, "/characters");
  await vi.waitFor(() => expect(wrapper.text()).toContain(db.characters[0].name));
  const search = wrapper.get('input[aria-label="Search characters"]');
  await search.trigger("focus");
  await search.setValue("no-match");
  expect(wrapper.findAllComponents(CharacterCard)).toHaveLength(0);
  await search.setValue("");
  await search.trigger("blur");
  await pickOption(wrapper.get('[aria-haspopup="listbox"]'), t("characters.sort.nameAsc"));
  await vi.waitFor(() => expect(router.currentRoute.value.query.sort).toBe("name-asc"));
  await button(wrapper, "Fantasy").trigger("click");
  await button(wrapper, "All").trigger("click");
  await wrapper.get(`button[aria-label="${t("characters.view.list")}"]`).trigger("click");
  expect(wrapper.findAllComponents(CharacterListRow)).toHaveLength(db.characters.length);
  await button(wrapper, t("characters.view.select")).trigger("click");
  const rows = wrapper.findAllComponents(CharacterListRow);
  await rows[0]!.trigger("click");
  await rows[0]!.trigger("click");
  await rows[1]!.trigger("click");
  await button(wrapper, t("common.delete")).trigger("click");
  await vi.waitFor(() => expect(document.querySelector('[role="dialog"]')).not.toBeNull());
  const dialog = new DOMWrapper(document.querySelector<HTMLElement>('[role="dialog"]')!);
  await button(dialog, t("common.delete")).trigger("click");
  await vi.waitFor(() => expect(requests.some((r) => r.method === "DELETE")).toBe(true));
  await vi.waitFor(() => expect(wrapper.findAllComponents(CharacterListRow)).toHaveLength(19));
  await wrapper.get(`button[aria-label="${t("characters.view.grid")}"]`).trigger("click");
  await button(wrapper, t("characters.view.select")).trigger("click");
  await wrapper.findAllComponents(CharacterCard)[0]!.trigger("click");
  await wrapper.get(`button[aria-label="${t("characters.cancelSelection")}"]`).trigger("click");
});
it("imports cards with success/failure feedback and resets the file input", async () => {
  installAppApi();
  let fail = false;
  server.use(
    http.post("/api/characters/import", () =>
      fail
        ? HttpResponse.json({ detail: "Invalid card" }, { status: 400 })
        : HttpResponse.json({ id: "imported" }, { status: 201 }),
    ),
  );
  const { wrapper } = await mountView(CharactersView, "/characters");
  await vi.waitFor(() =>
    expect(wrapper.findAllComponents(CharacterCard).length).toBeGreaterThan(0),
  );
  const input = wrapper.get('input[type="file"]');
  Object.defineProperty(input.element, "files", {
    value: [new File(["{}"], "card.json", { type: "application/json" })],
    configurable: true,
  });
  await input.trigger("change");
  await vi.waitFor(() =>
    expect(useToastState().value.at(-1)?.title).toBe(t("characters.imported")),
  );
  fail = true;
  await input.trigger("change");
  await vi.waitFor(() =>
    expect(useToastState().value.at(-1)?.title).toBe(t("characters.importFailed")),
  );
  expect((input.element as HTMLInputElement).value).toBe("");
});
it("restores URL filters, renders an empty library, and navigates to creation", async () => {
  const { db } = installAppApi();
  db.characters.splice(0);
  const { wrapper, router } = await mountView(
    CharactersView,
    "/characters?sort=newest&view=list",
    "/characters",
  );
  await vi.waitFor(() => expect(wrapper.text()).toContain(t("characters.libraryAwaits")));
  await button(wrapper, t("characters.createNew")).trigger("click");
  await vi.waitFor(() => expect(router.currentRoute.value.path).toBe("/characters/create"));
});
