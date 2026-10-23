import { afterEach, describe, expect, it, vi } from "vite-plus/test";
import { http, HttpResponse } from "msw";
import SetupWizardView from "../SetupWizardView.vue";
import ProfileForm from "@/components/profiles/ProfileForm.vue";
import SelectMenu from "@/components/shared/SelectMenu.vue";
import { profiles } from "@/mocks/data/profiles";
import { personas } from "@/mocks/data/personas";
import { providers } from "@/mocks/data/providers";
import { allModelsMock } from "@/mocks/data/models-data";
import { allModelFamiliesMock } from "@/mocks/data/model-families-data";
import { server } from "@/mocks/server";
import { useToastState } from "@/composables/useToast";
import { mountView, button, pickOption } from "@/test/views";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
afterEach(() => {
  useToastState().value = [];
  vi.restoreAllMocks();
});
async function setup(unfinished = false, noPersona = false) {
  const local = { ...providers.find((p) => p.provider_type === "ollama")! };
  const cloud = { ...providers[0], enabled: true, api_key_configured: true };
  const model = {
    ...allModelsMock[0],
    id: "usable",
    display_name: "Usable model",
    enabled: true,
    provider_enabled: true,
  };
  const writes: unknown[] = [];
  server.use(
    http.get("/api/providers", () => HttpResponse.json({ items: [local, cloud] })),
    http.get("/api/providers/:id/models/available", () =>
      HttpResponse.json({
        models: [{ identifier: "local", display_name: "Local" }],
        last_synced_at: null,
      }),
    ),
    http.get("/api/models", () =>
      HttpResponse.json({ items: [model], meta: { page: 1, total: 1, has_more: false } }),
    ),
    http.get("/api/model-families/:id", () => HttpResponse.json(allModelFamiliesMock[0])),
    http.get("/api/profiles/", () =>
      HttpResponse.json({
        items: unfinished ? [{ ...profiles[0], name: "Unfinished", model_id: null }] : [],
      }),
    ),
    http.get("/api/prompt-templates/", () => HttpResponse.json({ items: [] })),
    http.get("/api/presets/", () => HttpResponse.json({ items: [] })),
    http.get("/api/personas/", () => HttpResponse.json({ items: noPersona ? [] : [personas[0]] })),
    http.post("/api/profiles/", async ({ request }) => {
      const body = await request.json();
      writes.push(body);
      return HttpResponse.json({ ...profiles[0], ...(body as object) });
    }),
    http.put("/api/profiles/:id", async ({ request }) => {
      const body = await request.json();
      writes.push(body);
      return HttpResponse.json({ ...profiles[0], ...(body as object) });
    }),
  );
  const host = await mountView(SetupWizardView, "/setup");
  await vi.waitFor(() => expect(host.wrapper.text()).toContain("1 models found"));
  await button(host.wrapper, t("setup.next")).trigger("click");
  return { ...host, writes, model };
}

describe("first-run setup journey", () => {
  it("creates a manual profile with a model and completes navigation home", async () => {
    const { wrapper, writes, router } = await setup();
    await wrapper
      .findAll("button")
      .find((b) => b.text().includes(t("setup.createManually")))!
      .trigger("click");
    const form = wrapper.getComponent(ProfileForm);
    await form.get("input[type=text]").setValue("My first tale");
    await pickOption(form.findAllComponents(SelectMenu)[3].get("button"), "Usable model");
    await button(form, t("profiles.form.create")).trigger("click");
    await vi.waitFor(() => expect(wrapper.text()).toContain(t("setup.allSet")));
    expect(writes[0]).toMatchObject({
      name: "My first tale",
      model_id: "usable",
      is_default: true,
    });
    await button(wrapper, t("common.done")).trigger("click");
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe("/"));
  });

  it("rejects manual profiles without a model and keeps the draft editable", async () => {
    const { wrapper, writes } = await setup();
    await wrapper
      .findAll("button")
      .find((b) => b.text().includes(t("setup.createManually")))!
      .trigger("click");
    const form = wrapper.getComponent(ProfileForm);
    await form.get("input[type=text]").setValue("Incomplete");
    await button(form, t("profiles.form.create")).trigger("click");
    expect(writes).toEqual([]);
    expect(useToastState().value.at(-1)?.title).toBe(t("setup.toast.pickModel"));
    expect(wrapper.findComponent(ProfileForm).exists()).toBe(true);
  });

  it("resumes an unfinished import and requires a model before finalizing it", async () => {
    const { wrapper, writes } = await setup(true);
    await button(wrapper, t("setup.finishSetup")).trigger("click");
    await button(wrapper, t("setup.finish")).trigger("click");
    expect(writes).toEqual([]);
    await pickOption(button(wrapper, t("setup.selectModel")), "Usable model");
    await button(wrapper, t("setup.finish")).trigger("click");
    await vi.waitFor(() => expect(wrapper.text()).toContain(t("setup.allSet")));
    expect(writes[0]).toEqual({ model_id: "usable", persona_id: null, is_default: true });
  });

  it("failed completion keeps the profile picker available for retry", async () => {
    const { wrapper } = await setup(true);
    server.use(
      http.put("/api/profiles/:id", () =>
        HttpResponse.json({ detail: "Offline" }, { status: 503 }),
      ),
    );
    await button(wrapper, t("setup.finishSetup")).trigger("click");
    await pickOption(button(wrapper, t("setup.selectModel")), "Usable model");
    await button(wrapper, t("setup.finish")).trigger("click");
    await vi.waitFor(() => expect(useToastState().value.at(-1)?.type).toBe("error"));
    expect(button(wrapper, t("setup.finish")).element.disabled).toBe(false);
    expect(wrapper.text()).not.toContain(t("setup.allSet"));
  });

  it("creates an optional persona inline before building a manual profile", async () => {
    const { wrapper } = await setup(false, true);
    server.use(
      http.post("/api/personas/", async ({ request }) => {
        const body = await request.formData();
        expect(body.get("name")).toBe("Traveler");
        return HttpResponse.json({ ...personas[0], id: "new-persona", name: "Traveler" });
      }),
    );
    await wrapper
      .findAll("button")
      .find((b) => b.text().includes(t("setup.createManually")))!
      .trigger("click");
    await wrapper
      .get('input[placeholder="' + t("setup.personaNamePlaceholder") + '"]')
      .setValue(" Traveler ");
    await button(wrapper, t("setup.create")).trigger("click");
    await vi.waitFor(() =>
      expect(
        wrapper.find('input[placeholder="' + t("setup.personaNamePlaceholder") + '"]').exists(),
      ).toBe(false),
    );
    expect(useToastState().value.at(-1)?.type).toBe("success");
  });
});
