import { afterEach, describe, expect, it, vi } from "vite-plus/test";
import { http, HttpResponse } from "msw";
import { nextTick } from "vue";
import ModelView from "../ModelView.vue";
import SelectMenu from "@/components/shared/SelectMenu.vue";
import { allModelsMock } from "@/mocks/data/models-data";
import { allModelFamiliesMock } from "@/mocks/data/model-families-data";
import { providers } from "@/mocks/data/providers";
import { useToastState } from "@/composables/useToast";
import { server } from "@/mocks/server";
import { mountView, button, pickOption } from "@/test/views";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
afterEach(() => {
  useToastState().value = [];
  vi.restoreAllMocks();
});
async function setup() {
  const family = {
    ...structuredClone(allModelFamiliesMock[0]),
    id: "family",
    name: "Test family",
    provider_types: ["openai", "openrouter"],
    parameters: { temperature: { type: "float", default: 1, min_value: 0, max_value: 2 } },
  };
  const otherFamily = {
    ...family,
    id: "other-family",
    name: "Google family",
    provider_types: ["google"],
  };
  let row = {
    ...structuredClone(allModelsMock[0]),
    id: "model",
    display_name: "Test model",
    model_family_id: family.id,
    model_family: family,
    enabled: true,
    parameters: { temperature: 1 },
    routes: [
      {
        ...allModelsMock[0].routes[0],
        id: "r1",
        provider_id: "prov-openai",
        model_registry_id: "model",
        model_identifier: "native-model",
      },
    ],
    active_route_id: "r1",
  };
  const writes: unknown[] = [];
  let reads = 0;
  server.use(
    http.get("/api/models/model", () => {
      reads++;
      return HttpResponse.json(row);
    }),
    http.get("/api/providers", () => HttpResponse.json({ items: providers })),
    http.get("/api/model-families", () =>
      HttpResponse.json({
        items: [family, otherFamily],
        meta: { page: 1, total: 2, has_more: false },
      }),
    ),
    http.get("/api/model-families/parameter-docs", () => HttpResponse.json({})),
    http.put("/api/models/model", async ({ request }) => {
      const body = (await request.json()) as object;
      writes.push(body);
      row = { ...row, ...body };
      return HttpResponse.json(row);
    }),
    http.post("/api/models/model/routes", async ({ request }) => {
      const body = (await request.json()) as (typeof row.routes)[number];
      writes.push(body);
      row = { ...row, routes: [...row.routes, { ...body, id: "r2", model_registry_id: "model" }] };
      return HttpResponse.json(row);
    }),
    http.put("/api/models/model/active-route", async ({ request }) => {
      const body = (await request.json()) as { route_id: string };
      row = { ...row, active_route_id: body.route_id };
      return HttpResponse.json(row);
    }),
    http.delete("/api/models/model/routes/:route", ({ params }) => {
      row = { ...row, routes: row.routes.filter((r) => r.id !== params.route) };
      return HttpResponse.json(row);
    }),
    http.delete("/api/models/model", () => new HttpResponse(null, { status: 204 })),
  );
  const host = await mountView(ModelView, "/models/model", "/models/:id");
  await vi.waitFor(() => expect(host.wrapper.find("input[readonly]").exists()).toBe(true));
  return { ...host, writes, family, reads: () => reads };
}
describe("model settings screen", () => {
  it("loads identity and schema defaults, and avoids unnecessary saves", async () => {
    const { wrapper, writes } = await setup();
    expect(wrapper.text()).toContain("native-model");
    expect(wrapper.get<HTMLInputElement>("input[type=number]").element.value).toBe("1");
    await button(wrapper, t("common.save")).trigger("click");
    expect(useToastState().value.at(-1)?.type).toBe("info");
    expect(writes).toEqual([]);
  });

  it("saves only changed registry fields and reloads full family detail", async () => {
    const { wrapper, writes, reads } = await setup();
    await wrapper.get("input[type=text]:not([readonly])").setValue("Renamed");
    await wrapper.get('input[aria-label="Enabled"]').setValue(false);
    await wrapper.get("input[type=number]").setValue("0.6");
    await button(wrapper, t("common.save")).trigger("click");
    await vi.waitFor(() => expect(useToastState().value.at(-1)?.type).toBe("success"));
    expect(writes[0]).toEqual({
      display_name: "Renamed",
      enabled: false,
      parameters: { temperature: 0.6 },
    });
    expect(reads()).toBe(2);
  });

  it("adding a provider route trims its identifier, allows activation and removal", async () => {
    const { wrapper, writes } = await setup();
    const menus = wrapper.findAllComponents(SelectMenu);
    await pickOption(menus[1].get("button"), "OpenRouter");
    await wrapper
      .get('input[placeholder="e.g. deepseek/deepseek-v4-pro"]')
      .setValue(" vendor/model ");
    await button(wrapper, t("connections.model.addRoute")).trigger("click");
    await vi.waitFor(() => expect(wrapper.findAll("input[type=radio]")).toHaveLength(2));
    expect(writes[0]).toEqual({
      provider_id: "prov-openrouter",
      model_identifier: "vendor/model",
      enabled: true,
    });
    await wrapper.findAll("input[type=radio]")[1].setValue();
    await vi.waitFor(() =>
      expect(wrapper.findAll<HTMLInputElement>("input[type=radio]")[1].element.checked).toBe(true),
    );
    await vi.waitFor(() =>
      expect(
        wrapper.findAll<HTMLButtonElement>(
          'button[aria-label="' + t("connections.model.removeRoute") + '"]',
        )[1].element.disabled,
      ).toBe(false),
    );
    await wrapper
      .findAll('button[aria-label="' + t("connections.model.removeRoute") + '"]')[1]
      .trigger("click");
    await vi.waitFor(() => expect(wrapper.findAll("input[type=radio]")).toHaveLength(1));
    expect(
      wrapper.get<HTMLButtonElement>(
        'button[aria-label="' + t("connections.model.removeRoute") + '"]',
      ).element.disabled,
    ).toBe(true);
  });

  it("family changes clear an incompatible pending route provider", async () => {
    const { wrapper } = await setup();
    const menus = wrapper.findAllComponents(SelectMenu);
    await pickOption(menus[1].get("button"), "OpenRouter");
    await wrapper
      .get('input[placeholder="e.g. deepseek/deepseek-v4-pro"]')
      .setValue("vendor/model");
    expect(button(wrapper, t("connections.model.addRoute")).element.disabled).toBe(false);
    await pickOption(menus[0].get("button"), "Google family");
    await nextTick();
    expect(button(wrapper, t("connections.model.addRoute")).element.disabled).toBe(true);
  });

  it("rejected saves keep the user's draft and surface an error toast", async () => {
    const { wrapper } = await setup();
    server.use(
      http.put("/api/models/model", () =>
        HttpResponse.json({ detail: "Rejected" }, { status: 422 }),
      ),
    );
    await wrapper.get("input[type=text]:not([readonly])").setValue("Unsaved draft");
    await button(wrapper, t("common.save")).trigger("click");
    await vi.waitFor(() => expect(useToastState().value.at(-1)?.type).toBe("error"));
    expect(wrapper.get<HTMLInputElement>("input[type=text]:not([readonly])").element.value).toBe(
      "Unsaved draft",
    );
  });

  it("two-click deletion navigates back to the models tab", async () => {
    const { wrapper, router } = await setup();
    await button(wrapper, t("common.delete")).trigger("click");
    expect(router.currentRoute.value.path).toBe("/models/model");
    await button(wrapper, t("common.deleteConfirm")).trigger("click");
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe("/connections"));
    expect(router.currentRoute.value.query.tab).toBe("models");
  });
});
