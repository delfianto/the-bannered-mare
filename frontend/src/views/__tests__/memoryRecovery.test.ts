import { expect, it } from "vite-plus/test";
import { flushPromises } from "@vue/test-utils";
import { http, HttpResponse } from "msw";
import MemoryView from "../MemoryView.vue";
import { installAppApi } from "@/test/appApi";
import { mountView, button } from "@/test/views";
import { server } from "@/mocks/server";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
it("retains memory drafts after failed creates and updates", async () => {
  installAppApi();
  server.use(
    http.post("/api/data-bank/", () => HttpResponse.json({ detail: "Read only" }, { status: 403 })),
    http.put("/api/data-bank/:id", () =>
      HttpResponse.json({ detail: "Read only" }, { status: 403 }),
    ),
  );
  const { wrapper } = await mountView(MemoryView, "/memory");
  await flushPromises();
  await button(wrapper, t("memory.addEntry")).trigger("click");
  await button(wrapper, t("memory.form.createEntry")).trigger("click");
  expect(wrapper.find("textarea").exists()).toBe(true);
  await wrapper.get("input").setValue("Draft");
  await wrapper.get("textarea").setValue("Preserve me");
  await button(wrapper, t("memory.form.createEntry")).trigger("click");
  await flushPromises();
  expect((wrapper.get("textarea").element as HTMLTextAreaElement).value).toBe("Preserve me");
  await button(wrapper, t("common.cancel")).trigger("click");
  // Cancellation reveals the API error; retry restores the list before editing.
  await button(wrapper, t("common.retry")).trigger("click");
  await flushPromises();
  await wrapper
    .findAll("button")
    .find((b) => b.text() === t("common.edit"))!
    .trigger("click");
  await wrapper.get("textarea").setValue("Edited draft");
  await button(wrapper, t("memory.form.saveChanges")).trigger("click");
  await flushPromises();
  expect((wrapper.get("textarea").element as HTMLTextAreaElement).value).toBe("Edited draft");
});
it("recovers an unavailable bank and switches scope filters", async () => {
  installAppApi();
  let fail = true;
  server.use(
    http.get("/api/data-bank/", () =>
      fail ? HttpResponse.json({ detail: "Bank unavailable" }, { status: 500 }) : undefined,
    ),
  );
  const { wrapper } = await mountView(MemoryView, "/memory");
  await flushPromises();
  expect(wrapper.text()).toContain("Bank unavailable");
  fail = false;
  await button(wrapper, t("common.retry")).trigger("click");
  await flushPromises();
  for (const scope of ["character", "chat", "all"]) {
    await button(wrapper, t(`memory.scopes.${scope}`)).trigger("click");
    await flushPromises();
  }
  expect(wrapper.findAll("h3").length).toBeGreaterThan(0);
});
it("creates from an empty bank and cancels without a request", async () => {
  const { db, requests } = installAppApi();
  db.memories.splice(0);
  const { wrapper } = await mountView(MemoryView, "/memory");
  await flushPromises();
  expect(wrapper.text()).toContain(t("memory.noEntries"));
  await button(wrapper, "Add Memory Entry").trigger("click");
  await button(wrapper, t("common.cancel")).trigger("click");
  expect(requests.some((r) => r.method === "POST")).toBe(false);
});
