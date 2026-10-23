import { afterEach, expect, it, vi } from "vite-plus/test";
import { http, HttpResponse } from "msw";
import ProfilesView from "../ProfilesView.vue";
import ConnectionsView from "../ConnectionsView.vue";
import { installAppApi } from "@/test/appApi";
import { mountView } from "@/test/views";
import { server } from "@/mocks/server";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
afterEach(() => vi.restoreAllMocks());
for (const [tab, path, component, base] of [
  ["profiles", "/api/profiles/", ProfilesView, "/loadouts"],
  ["personas", "/api/personas/", ProfilesView, "/loadouts"],
  ["templates", "/api/prompt-templates/", ProfilesView, "/loadouts"],
  ["presets", "/api/presets/", ProfilesView, "/loadouts"],
  ["fragments", "/api/prompt-fragments/", ProfilesView, "/loadouts"],
  ["providers", "/api/providers", ConnectionsView, "/connections"],
  ["models", "/api/models", ConnectionsView, "/connections"],
  ["model-families", "/api/model-families", ConnectionsView, "/connections"],
] as const) {
  it(`${tab} displays API errors and retries when a retry control is available`, async () => {
    installAppApi();
    let fail = true;
    server.use(
      http.get(path, () =>
        fail
          ? HttpResponse.json({ detail: "Resource unavailable" }, { status: 500 })
          : HttpResponse.json({ items: [], meta: { total: 0, has_more: false } }),
      ),
    );
    const { wrapper } = await mountView(component, `${base}?tab=${tab}`, base);
    await vi.waitFor(() => expect(wrapper.text()).toContain("Resource unavailable"));
    fail = false;
    const retry = wrapper.findAll("button").find((b) => b.text() === t("common.retry"));
    if (retry) {
      await retry.trigger("click");
      await vi.waitFor(() => expect(wrapper.text()).not.toContain("Resource unavailable"));
    }
  });
  it(`${tab} displays an empty collection`, async () => {
    installAppApi();
    server.use(
      http.get(path, () => HttpResponse.json({ items: [], meta: { total: 0, has_more: false } })),
    );
    const { wrapper } = await mountView(component, `${base}?tab=${tab}`, base);
    await vi.waitFor(() => expect(wrapper.find("svg.animate-spin").exists()).toBe(false));
    expect(wrapper.find("tbody tr").exists()).toBe(false);
  });
}
it("filters unused fragments and renders every fragment type and usage count", async () => {
  const { db } = installAppApi();
  db.fragments.splice(
    0,
    db.fragments.length,
    ...["system", "jailbreak", "context", "instruction", "nsfw"].map((type, i) => ({
      ...db.fragments[0]!,
      id: `fragment-${i}`,
      name: `Fragment ${i}`,
      fragment_type: type,
      content: "Prompt",
      is_global: i % 2 === 0,
      used_by:
        i === 0
          ? [{ id: "template", name: "Used template" }]
          : i === 1
            ? [
                { id: "one", name: "First" },
                { id: "two", name: "Second" },
              ]
            : undefined,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })),
  );
  const { wrapper, router } = await mountView(ProfilesView, "/loadouts?tab=fragments", "/loadouts");
  await vi.waitFor(() => expect(wrapper.text()).toContain("Fragment 4"));
  expect(wrapper.text()).toContain("2 templates");
  await wrapper
    .findAll("button")
    .find((b) => b.text() === "Unused only")!
    .trigger("click");
  await vi.waitFor(() => expect(wrapper.find("tbody tr").exists()).toBe(true));
  await wrapper
    .findAll("button")
    .find((b) => b.text() === "Unused only")!
    .trigger("click");
  await vi.waitFor(() => expect(wrapper.find("tbody tr").exists()).toBe(true));
  await wrapper.get("tbody tr").trigger("click");
  await vi.waitFor(() =>
    expect(router.currentRoute.value.path).toBe("/settings/fragments/fragment-0"),
  );
});
