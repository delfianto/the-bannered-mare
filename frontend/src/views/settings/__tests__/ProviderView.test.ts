import { afterEach, describe, expect, it, vi } from "vite-plus/test";
import { http, HttpResponse } from "msw";
import ProviderView from "../ProviderView.vue";
import ModelForm from "@/components/connections/ModelForm.vue";
import { providers } from "@/mocks/data/providers";
import { allModelsMock } from "@/mocks/data/models-data";
import { allModelFamiliesMock } from "@/mocks/data/model-families-data";
import { server } from "@/mocks/server";
import { useToastState } from "@/composables/useToast";
import { mountView, button } from "@/test/views";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
afterEach(() => (useToastState().value = []));
async function setup() {
  let row = {
    ...structuredClone(providers.find((p) => p.provider_type === "openrouter")!),
    id: "provider",
    name: "My router",
    enabled: true,
    allowed_models: ["already"],
    api_key_configured: true,
  };
  const writes: unknown[] = [];
  const models = [
    {
      identifier: "already",
      display_name: "Already saved",
      state: "not-loaded",
      size_bytes: null,
      quantization: null,
    },
    {
      identifier: "new",
      display_name: "New discovered",
      state: "not-loaded",
      size_bytes: 2 * 1024 ** 3,
      quantization: "Q4",
    },
  ];
  server.use(
    http.get("/api/providers/provider", () => HttpResponse.json(row)),
    http.get("/api/providers", () => HttpResponse.json({ items: [row] })),
    http.get("/api/providers/provider/models/available", () =>
      HttpResponse.json({ models, last_synced_at: null }),
    ),
    http.post("/api/providers/provider/models/sync", () =>
      HttpResponse.json({ models, last_synced_at: new Date().toISOString() }),
    ),
    http.put("/api/providers/provider", async ({ request }) => {
      const body = (await request.json()) as object;
      writes.push(body);
      row = { ...row, ...body };
      return HttpResponse.json(row);
    }),
    http.put("/api/providers/provider/models/filter", async ({ request }) => {
      const body = (await request.json()) as { allowed_models: string[] };
      row.allowed_models = body.allowed_models;
      return HttpResponse.json({ models });
    }),
    http.get("/api/models", () =>
      HttpResponse.json({
        items: [
          {
            ...allModelsMock[0],
            routes: [
              {
                ...allModelsMock[0].routes[0],
                provider_id: "provider",
                model_identifier: "already",
              },
            ],
          },
        ],
        meta: { has_more: false, total: 1 },
      }),
    ),
    http.get("/api/model-families", () =>
      HttpResponse.json({
        items: allModelFamiliesMock,
        meta: { has_more: false, total: allModelFamiliesMock.length },
      }),
    ),
  );
  const host = await mountView(ProviderView, "/providers/provider", "/providers/:id");
  await vi.waitFor(() => expect(host.wrapper.text()).toContain("New discovered"));
  return { ...host, writes };
}
describe("provider settings screen", () => {
  it("loads provider state and saves only changed fields, mapping a cleared URL to null", async () => {
    const { wrapper, writes } = await setup();
    await button(wrapper, t("common.save")).trigger("click");
    expect(writes).toEqual([]);
    expect(useToastState().value.at(-1)?.type).toBe("info");
    await wrapper
      .get('input[placeholder="' + t("connections.provider.namePlaceholder") + '"]')
      .setValue("Renamed router");
    await wrapper
      .get('input[placeholder="' + t("connections.provider.baseUrlPlaceholder") + '"]')
      .setValue("");
    await wrapper
      .get('input[aria-label="' + t("connections.provider.enabled") + '"]')
      .setValue(false);
    await button(wrapper, t("common.save")).trigger("click");
    await vi.waitFor(() => expect(useToastState().value.at(-1)?.type).toBe("success"));
    expect(writes[0]).toMatchObject({ name: "Renamed router", base_url: null, enabled: false });
  });

  it("syncs the catalog and removes an allow-list chip", async () => {
    const { wrapper } = await setup();
    await button(wrapper, t("connections.provider.syncNow")).trigger("click");
    await vi.waitFor(() => expect(useToastState().value.at(-1)?.type).toBe("success"));
    await wrapper
      .get('button[aria-label="' + t("connections.provider.removeFromFilter") + '"]')
      .trigger("click");
    await vi.waitFor(() => expect(wrapper.text()).toContain(t("connections.provider.noFilterSet")));
  });

  it("distinguishes already-persisted routes from discoverable models and opens a prefilled editor", async () => {
    const { wrapper } = await setup();
    let row = wrapper.findAll("li").find((li) => li.text().includes("Already saved"))!;
    await row.get("button").trigger("click");
    expect(row.text()).toContain(t("connections.provider.added"));
    row = wrapper.findAll("li").find((li) => li.text().includes("New discovered"))!;
    await row.get("button").trigger("click");
    await row
      .findAll("button")
      .find((b) => b.text() === t("connections.provider.addAsModel"))!
      .trigger("click");
    await vi.waitFor(() => expect(wrapper.findComponent(ModelForm).exists()).toBe(true));
    const form = wrapper.getComponent(ModelForm);
    expect(form.findAll<HTMLInputElement>("input[type=text]").map((i) => i.element.value)).toEqual([
      "New discovered",
      "new",
    ]);
  });

  it("save failures show feedback and preserve the unsaved name", async () => {
    const { wrapper } = await setup();
    server.use(
      http.put("/api/providers/provider", () =>
        HttpResponse.json({ detail: "Rejected" }, { status: 422 }),
      ),
    );
    await wrapper
      .get('input[placeholder="' + t("connections.provider.namePlaceholder") + '"]')
      .setValue("Unsaved provider");
    await button(wrapper, t("common.save")).trigger("click");
    await vi.waitFor(() => expect(useToastState().value.at(-1)?.type).toBe("error"));
    expect(
      wrapper.get<HTMLInputElement>(
        'input[placeholder="' + t("connections.provider.namePlaceholder") + '"]',
      ).element.value,
    ).toBe("Unsaved provider");
  });
});
