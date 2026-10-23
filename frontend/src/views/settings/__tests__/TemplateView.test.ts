import { afterEach, describe, expect, it, vi } from "vite-plus/test";
import { http, HttpResponse } from "msw";
import TemplateView from "../TemplateView.vue";
import { promptTemplates, templateFragments } from "@/mocks/data/prompt-templates";
import { server } from "@/mocks/server";
import { useToastState } from "@/composables/useToast";
import { mountView, button } from "@/test/views";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
afterEach(() => (useToastState().value = []));
async function setup() {
  let row = { ...structuredClone(promptTemplates[0]), id: "template" };
  const fragments = structuredClone(templateFragments.get(promptTemplates[0].id) ?? []);
  const writes: unknown[] = [];
  server.use(
    http.get("/api/prompt-templates/template", () => HttpResponse.json(row)),
    http.get("/api/prompt-templates/", () => HttpResponse.json({ items: [row] })),
    http.get("/api/prompt-templates/template/fragments/", () =>
      HttpResponse.json({ items: fragments }),
    ),
    http.put("/api/prompt-templates/template", async ({ request }) => {
      const body = (await request.json()) as object;
      writes.push(body);
      row = { ...row, ...body };
      return HttpResponse.json(row);
    }),
    http.delete("/api/prompt-templates/template", () => new HttpResponse(null, { status: 204 })),
    http.delete(
      "/api/prompt-templates/template/fragments/:fragment",
      () => new HttpResponse(null, { status: 204 }),
    ),
    http.post("/api/prompt-templates/template/preview", async ({ request }) => {
      expect(await request.json()).toMatchObject({ character_name: "Alice", persona_name: "User" });
      return HttpResponse.json({ rendered: "<b>Alice</b> welcomes User" });
    }),
  );
  const host = await mountView(TemplateView, "/templates/template", "/templates/:id");
  await vi.waitFor(() =>
    expect(host.wrapper.find('input[placeholder="Template name"]').exists()).toBe(true),
  );
  await vi.waitFor(() =>
    expect(
      host.wrapper.findAll('button[aria-label="' + t("connections.template.detachFragment") + '"]'),
    ).toHaveLength(fragments.length),
  );
  return { ...host, writes, fragments };
}
describe("template settings screen", () => {
  it("edits prompt text, component switches and token budget without mutating the loaded template", async () => {
    const { wrapper, writes } = await setup();
    await wrapper.get('input[placeholder="Template name"]').setValue("Edited template");
    await wrapper.findAll("textarea")[1].setValue("You are {{character_name}}");
    await wrapper.get('input[aria-label="Default template"]').setValue(false);
    await wrapper.get('input[aria-label="persona"]').setValue(false);
    await wrapper.get("input[type=number]").setValue("2048");
    await button(wrapper, t("common.save")).trigger("click");
    await vi.waitFor(() => expect(useToastState().value.at(-1)?.type).toBe("success"));
    expect(writes[0]).toMatchObject({
      name: "Edited template",
      system_template: "You are {{character_name}}",
      is_default: false,
      max_history_tokens: 2048,
      components_enabled: { persona: false, character: true },
    });
  });

  it("previews resolved sample data as text and detaches a fragment", async () => {
    const { wrapper, fragments } = await setup();
    await button(wrapper, t("connections.template.previewTemplate")).trigger("click");
    await vi.waitFor(() => expect(wrapper.find("pre").exists()).toBe(true));
    expect(wrapper.get("pre").text()).toBe("<b>Alice</b> welcomes User");
    expect(wrapper.find("pre b").exists()).toBe(false);
    if (fragments.length) {
      await wrapper
        .findAll('button[aria-label="' + t("connections.template.detachFragment") + '"]')[0]
        .trigger("click");
      await vi.waitFor(() =>
        expect(
          wrapper.findAll('button[aria-label="' + t("connections.template.detachFragment") + '"]'),
        ).toHaveLength(fragments.length - 1),
      );
    }
  });

  it("failed previews surface an error and leave the action available for retry", async () => {
    const { wrapper } = await setup();
    server.use(
      http.post("/api/prompt-templates/template/preview", () =>
        HttpResponse.json({ detail: "Invalid template" }, { status: 422 }),
      ),
    );
    await button(wrapper, t("connections.template.previewTemplate")).trigger("click");
    await vi.waitFor(() => expect(useToastState().value.at(-1)?.type).toBe("error"));
    expect(button(wrapper, t("connections.template.previewTemplate")).element.disabled).toBe(false);
  });

  it("confirms deletion and navigates back to the templates tab", async () => {
    const { wrapper, router } = await setup();
    await button(wrapper, t("common.delete")).trigger("click");
    await button(wrapper, t("common.deleteConfirm")).trigger("click");
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe("/loadouts"));
    expect(router.currentRoute.value.query.tab).toBe("templates");
  });
});
