import { afterEach, describe, expect, it, vi } from "vite-plus/test";
import { http, HttpResponse } from "msw";
import LorebooksView from "../LorebooksView.vue";
import LoreEntryForm from "@/components/lorebooks/LoreEntryForm.vue";
import LoreEntryCard from "@/components/lorebooks/LoreEntryCard.vue";
import { lorebooks } from "@/mocks/data/lorebooks";
import { server } from "@/mocks/server";
import { useToastState } from "@/composables/useToast";
import { mountView, button } from "@/test/views";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
afterEach(() => {
  useToastState().value = [];
  vi.restoreAllMocks();
});
async function setup(empty = false) {
  let books = empty ? [] : structuredClone(lorebooks.slice(0, 2));
  const first = structuredClone(lorebooks[0]);
  const writes: { method: string; body?: unknown }[] = [];
  server.use(
    http.get("/api/lorebooks", () => HttpResponse.json({ items: books })),
    http.get("/api/lorebooks/:id", ({ params }) =>
      HttpResponse.json(books.find((b) => b.id === params.id)),
    ),
    http.post("/api/lorebooks", async ({ request }) => {
      const body = (await request.json()) as { name: string };
      writes.push({ method: "create-book", body });
      const book = { ...first, ...body, id: "created", entries: [] };
      books.unshift(book);
      return HttpResponse.json(book);
    }),
    http.put("/api/lorebooks/:id", async ({ request, params }) => {
      const body = (await request.json()) as { name: string };
      writes.push({ method: "edit-book", body });
      const book = { ...books.find((b) => b.id === params.id)!, ...body };
      books = books.map((b) => (b.id === params.id ? book : b));
      return HttpResponse.json(book);
    }),
    http.delete("/api/lorebooks/:id", ({ params }) => {
      books = books.filter((b) => b.id !== params.id);
      return new HttpResponse(null, { status: 204 });
    }),
    http.post("/api/lorebooks/:id/entries", async ({ request }) => {
      const body = (await request.json()) as { name: string };
      writes.push({ method: "create-entry", body });
      return HttpResponse.json({ ...first.entries[0], ...body, id: "created-entry" });
    }),
    http.put("/api/lorebooks/:id/entries/:entry", async ({ request }) => {
      const body = (await request.json()) as { name: string };
      writes.push({ method: "edit-entry", body });
      return HttpResponse.json({ ...first.entries[0], ...body });
    }),
    http.delete("/api/lorebooks/:id/entries/:entry", () => new HttpResponse(null, { status: 204 })),
  );
  const host = await mountView(LorebooksView, "/lorebooks");
  if (!empty)
    await vi.waitFor(() => expect(host.wrapper.findAllComponents(LoreEntryCard)).toHaveLength(2));
  else
    await vi.waitFor(() =>
      expect(button(host.wrapper, t("lorebooks.form.create")).exists()).toBe(true),
    );
  return { ...host, writes };
}

describe("lorebook editing screen", () => {
  it("creates the first book, selects it, and displays its empty entry state", async () => {
    const { wrapper, writes } = await setup(true);
    await button(wrapper, t("lorebooks.form.create")).trigger("click");
    await wrapper.get("input[type=text]").setValue("  New lore  ");
    await wrapper.get("textarea").setValue("  Description  ");
    await button(wrapper, t("lorebooks.form.create")).trigger("click");
    await vi.waitFor(() => expect(wrapper.text()).toContain("New lore"));
    expect(writes[0]).toEqual({
      method: "create-book",
      body: { name: "New lore", description: "Description", is_global: true },
    });
    await vi.waitFor(() => expect(wrapper.text()).toContain(t("lorebooks.noEntries")));
  });

  it("edits book metadata and reloads the selected detail", async () => {
    const { wrapper, writes } = await setup();
    await wrapper.get('button[title="' + t("lorebooks.editLorebook") + '"]').trigger("click");
    await wrapper.get("input[type=text]").setValue("Renamed book");
    await button(wrapper, t("lorebooks.form.save")).trigger("click");
    await vi.waitFor(() =>
      expect(wrapper.findAll("h2").some((h) => h.text() === "Renamed book")).toBe(true),
    );
    expect(writes[0].method).toBe("edit-book");
  });

  it("adds, edits, toggles and deletes entries through their actual controls", async () => {
    const { wrapper, writes } = await setup();
    await button(wrapper, t("lorebooks.addEntry")).trigger("click");
    const form = wrapper.getComponent(LoreEntryForm);
    await form.findAll("input[type=text]")[0].setValue("New entry");
    await form.get("textarea").setValue("New content");
    await button(form, t("lorebooks.entryForm.add")).trigger("click");
    await vi.waitFor(() => expect(wrapper.findAllComponents(LoreEntryCard)).toHaveLength(3));
    expect(writes[0].method).toBe("create-entry");
    const card = wrapper.findAllComponents(LoreEntryCard)[0];
    await button(card, t("common.edit")).trigger("click");
    await wrapper.getComponent(LoreEntryForm).get("textarea").setValue("Edited content");
    await button(wrapper.getComponent(LoreEntryForm), t("lorebooks.entryForm.save")).trigger(
      "click",
    );
    await vi.waitFor(() => expect(card.text()).toContain("Edited content"));
    await card.get("input[role=switch]").setValue(false);
    await vi.waitFor(() => expect(writes.at(-1)?.body).toEqual({ enabled: false }));
    await vi.waitFor(() =>
      expect(card.get<HTMLInputElement>("input[role=switch]").element.checked).toBe(false),
    );
    await button(card, t("common.delete")).trigger("click");
    await button(card, t("lorebooks.confirmDelete")).trigger("click");
    await vi.waitFor(() => expect(wrapper.findAllComponents(LoreEntryCard)).toHaveLength(2));
  });

  it.each(["book", "entry"])(
    "rejected %s saves retain the draft and display an error toast",
    async (kind) => {
      vi.spyOn(console, "error").mockImplementation(() => {});
      const { wrapper } = await setup();
      if (kind === "book") {
        await wrapper.get('button[title="' + t("lorebooks.editLorebook") + '"]').trigger("click");
        await wrapper.get("input[type=text]").setValue("Unsaved book");
        server.use(
          http.put("/api/lorebooks/:id", () =>
            HttpResponse.json({ detail: "Rejected" }, { status: 422 }),
          ),
        );
        await button(wrapper, t("lorebooks.form.save")).trigger("click");
      } else {
        await button(wrapper, t("lorebooks.addEntry")).trigger("click");
        const form = wrapper.getComponent(LoreEntryForm);
        await form.findAll("input[type=text]")[0].setValue("Unsaved entry");
        await form.get("textarea").setValue("Draft content");
        server.use(
          http.post("/api/lorebooks/:id/entries", () =>
            HttpResponse.json({ detail: "Rejected" }, { status: 422 }),
          ),
        );
        await button(form, t("lorebooks.entryForm.add")).trigger("click");
      }
      await vi.waitFor(() => expect(useToastState().value.at(-1)?.type).toBe("error"));
      expect(wrapper.get<HTMLInputElement>("input[type=text]").element.value).toContain("Unsaved");
    },
  );
});
