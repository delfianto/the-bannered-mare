import { afterEach, describe, expect, it, vi } from "vite-plus/test";
import { http, HttpResponse } from "msw";
import PresetView from "../PresetView.vue";
import { presets } from "@/mocks/data/presets";
import { server } from "@/mocks/server";
import { useToastState } from "@/composables/useToast";
import { mountView, button } from "@/test/views";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
afterEach(() => (useToastState().value = []));
async function setup(parameters: Record<string, unknown> = { temperature: 0.8 }) {
  let row = { ...structuredClone(presets[0]), id: "preset", is_default: false, parameters };
  const writes: unknown[] = [];
  server.use(
    http.get("/api/presets/preset", () => HttpResponse.json(row)),
    http.get("/api/presets/", () => HttpResponse.json({ items: [row] })),
    http.put("/api/presets/preset", async ({ request }) => {
      const body = (await request.json()) as object;
      writes.push(body);
      row = { ...row, ...body };
      return HttpResponse.json(row);
    }),
    http.post("/api/presets/preset/default", () => {
      row.is_default = true;
      return HttpResponse.json(row);
    }),
    http.delete("/api/presets/preset", () => new HttpResponse(null, { status: 204 })),
  );
  const host = await mountView(PresetView, "/presets/preset", "/presets/:id");
  await vi.waitFor(() => expect(host.wrapper.find("input[type=text]").exists()).toBe(true));
  return { ...host, writes };
}
describe("preset editor", () => {
  it("preserves object, list, boolean, null and numeric-string parameter types on a round trip", async () => {
    const parameters = {
      thinking: { type: "adaptive" },
      stop: ["User:"],
      enabled: false,
      optional: null,
      label: "123",
      temperature: 0.8,
    };
    const { wrapper, writes } = await setup(parameters);
    await wrapper
      .get('input[placeholder="' + t("connections.preset.namePlaceholder") + '"]')
      .setValue("Renamed");
    await button(wrapper, t("common.save")).trigger("click");
    await vi.waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]).toMatchObject({ name: "Renamed", parameters });
  });

  it("adds numeric and text sampler overrides and removes a row", async () => {
    const { wrapper, writes } = await setup();
    await button(wrapper, t("connections.preset.addParam")).trigger("click");
    const keys = () =>
      wrapper.findAll('input[placeholder="' + t("connections.preset.paramNamePlaceholder") + '"]');
    const values = () =>
      wrapper.findAll('input[placeholder="' + t("connections.preset.paramValuePlaceholder") + '"]');
    await keys()[1].setValue(" max_tokens ");
    await values()[1].setValue("2048");
    await button(wrapper, t("connections.preset.addParam")).trigger("click");
    await keys()[2].setValue("mode");
    await values()[2].setValue("creative");
    await wrapper
      .findAll('button[aria-label="' + t("connections.preset.removeParam") + '"]')[0]
      .trigger("click");
    await button(wrapper, t("common.save")).trigger("click");
    await vi.waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]).toMatchObject({ parameters: { max_tokens: 2048, mode: "creative" } });
  });

  it("sets the default and requires confirmation before deleting", async () => {
    const { wrapper, router } = await setup();
    await button(wrapper, t("connections.preset.setDefault")).trigger("click");
    await vi.waitFor(() => expect(useToastState().value.at(-1)?.type).toBe("success"));
    await button(wrapper, t("common.delete")).trigger("click");
    await button(wrapper, t("common.deleteConfirm")).trigger("click");
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe("/loadouts"));
    expect(router.currentRoute.value.query.tab).toBe("presets");
  });

  it("failed saves preserve edited parameter text for retry", async () => {
    const { wrapper } = await setup();
    server.use(
      http.put("/api/presets/preset", () =>
        HttpResponse.json({ detail: "Rejected" }, { status: 422 }),
      ),
    );
    await wrapper
      .get('input[placeholder="' + t("connections.preset.paramValuePlaceholder") + '"]')
      .setValue("0.42");
    await button(wrapper, t("common.save")).trigger("click");
    await vi.waitFor(() => expect(useToastState().value.at(-1)?.type).toBe("error"));
    expect(
      wrapper.get<HTMLInputElement>(
        'input[placeholder="' + t("connections.preset.paramValuePlaceholder") + '"]',
      ).element.value,
    ).toBe("0.42");
  });
});

it("parses edited structured values while preserving unquoted text", async () => {
  const { wrapper, writes } = await setup({
    thinking: { type: "adaptive" },
    stop: ["old"],
    enabled: true,
  });
  const values = wrapper.findAll(
    'input[placeholder="' + t("connections.preset.paramValuePlaceholder") + '"]',
  );
  await values[0].setValue('{"type":"disabled"}');
  await values[1].setValue('["User:","Assistant:"]');
  await values[2].setValue("false");
  await button(wrapper, t("common.save")).trigger("click");
  await vi.waitFor(() => expect(writes).toHaveLength(1));
  expect(writes[0]).toMatchObject({
    parameters: { thinking: { type: "disabled" }, stop: ["User:", "Assistant:"], enabled: false },
  });
});
