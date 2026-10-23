import { afterEach, describe, expect, it, vi } from "vite-plus/test";
import { http, HttpResponse } from "msw";
import FragmentCreateView from "../settings/FragmentCreateView.vue";
import TemplateCreateView from "../settings/TemplateCreateView.vue";
import FragmentView from "../settings/FragmentView.vue";
import ModelFamilyView from "../settings/ModelFamilyView.vue";
import { installAppApi } from "@/test/appApi";
import { mountView, button, pickOption } from "@/test/views";
import { server } from "@/mocks/server";
import { useConfirmState } from "@/composables/useConfirm";
import { useToastState } from "@/composables/useToast";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
afterEach(() => {
  useConfirmState().onCancel();
  useToastState().value = [];
});
for (const [kind, component, endpoint] of [
  ["Fragment", FragmentCreateView, "prompt-fragments"],
  ["Template", TemplateCreateView, "prompt-templates"],
] as const)
  describe(`${kind} creation`, () => {
    it("preserves a rejected draft and redirects after saving", async () => {
      const { requests } = installAppApi();
      let reject = true;
      server.use(
        http.post(`/api/${endpoint}/`, () =>
          reject ? HttpResponse.json({ detail: "Unavailable" }, { status: 503 }) : undefined,
        ),
      );
      const { wrapper, router } = await mountView(
        component,
        `/settings/${kind.toLowerCase()}s/new`,
      );
      expect(button(wrapper, `Create ${kind}`).attributes("disabled")).toBeDefined();
      await wrapper.get(`input[placeholder="${kind} name"]`).setValue("  My resource  ");
      await wrapper.get("textarea").setValue("{{ character.name }}");
      await wrapper
        .get(`input[placeholder="What is this ${kind.toLowerCase()} for?"]`)
        .setValue("  Purpose  ");
      await wrapper.get('input[role="switch"]').setValue(true);
      if (kind === "Fragment") await wrapper.get('input[placeholder="instruction"]').setValue("");
      await button(wrapper, `Create ${kind}`).trigger("click");
      await vi.waitFor(() =>
        expect(useToastState().value.at(-1)?.title).toBe(
          t(`connections.${kind.toLowerCase()}.toast.createFailed`),
        ),
      );
      expect((wrapper.get("textarea").element as HTMLTextAreaElement).value).toBe(
        "{{ character.name }}",
      );
      reject = false;
      await button(wrapper, `Create ${kind}`).trigger("click");
      await vi.waitFor(() => expect(router.currentRoute.value.path).toMatch(/\/created-/));
      expect(requests.find((r) => r.method === "POST")?.body).toMatchObject({
        name: "My resource",
        description: "Purpose",
        [kind === "Fragment" ? "is_global" : "is_default"]: true,
      });
      expect(useConfirmState().state.value.open).toBe(false);
    });
    it("protects drafts on reload and lets users cancel or accept leaving", async () => {
      installAppApi();
      const { wrapper, router, root } = await mountView(
        component,
        `/settings/${kind.toLowerCase()}s/new`,
      );
      const clean = new Event("beforeunload", { cancelable: true });
      window.dispatchEvent(clean);
      expect(clean.defaultPrevented).toBe(false);
      await wrapper.get("input").setValue("Draft");
      const dirty = new Event("beforeunload", { cancelable: true });
      window.dispatchEvent(dirty);
      expect(dirty.defaultPrevented).toBe(true);
      await wrapper.get(`button[aria-label="Back to ${kind.toLowerCase()}s"]`).trigger("click");
      await vi.waitFor(() => expect(useConfirmState().state.value.open).toBe(true));
      useConfirmState().onCancel();
      await vi.waitFor(() => expect(useConfirmState().state.value.open).toBe(false));
      expect(router.currentRoute.value.path).toContain("new");
      const navigation = router.push("/loadouts");
      await vi.waitFor(() => expect(useConfirmState().state.value.open).toBe(true));
      useConfirmState().onConfirm();
      await navigation;
      expect(router.currentRoute.value.path).toBe("/loadouts");
      root.unmount();
      const after = new Event("beforeunload", { cancelable: true });
      window.dispatchEvent(after);
      expect(after.defaultPrevented).toBe(false);
    });
    it("allows leaving an untouched form", async () => {
      installAppApi();
      const { wrapper, router } = await mountView(
        component,
        `/settings/${kind.toLowerCase()}s/new`,
      );
      await wrapper.get(`button[aria-label="Back to ${kind.toLowerCase()}s"]`).trigger("click");
      await vi.waitFor(() => expect(router.currentRoute.value.path).toBe("/loadouts"));
    });
  });
for (const [kind, component, key, path] of [
  ["fragment", FragmentView, "fragments", "prompt-fragments"],
  ["family", ModelFamilyView, "families", "model-families"],
] as const)
  describe(`${kind} details`, () => {
    it("sends changed fields and confirms deletion", async () => {
      const { db, requests } = installAppApi();
      const row = db[key][0];
      const { wrapper, router } = await mountView(
        component,
        `/settings/${path}/${row.id}`,
        `/settings/${path}/:id`,
      );
      await vi.waitFor(() => expect(wrapper.find("input").exists()).toBe(true));
      await button(wrapper, t("common.save")).trigger("click");
      expect(useToastState().value.at(-1)?.title).toBe(t(`connections.${kind}.toast.noChanges`));
      await wrapper.get("input").setValue("Revised name");
      await wrapper.get("textarea").setValue("");
      if (kind === "fragment") {
        await wrapper.findAll("textarea")[1]!.setValue("Revised prompt");
        await wrapper.get('input[role="switch"]').setValue(!("is_global" in row && row.is_global));
        await pickOption(
          wrapper.get('[aria-haspopup="listbox"]'),
          t("connections.fragment.typeContext"),
        );
      } else await wrapper.findAll("input")[1]!.setValue("custom-family");
      await button(wrapper, t("common.save")).trigger("click");
      await vi.waitFor(() => expect(requests.some((r) => r.method === "PUT")).toBe(true));
      expect(requests.find((r) => r.method === "PUT")?.body).toMatchObject({
        name: "Revised name",
        description: null,
      });
      await button(wrapper, t("common.delete")).trigger("click");
      expect(requests.some((r) => r.method === "DELETE")).toBe(false);
      await button(wrapper, t("common.deleteConfirm")).trigger("click");
      await vi.waitFor(() =>
        expect(router.currentRoute.value.path).toBe(
          kind === "fragment" ? "/loadouts" : "/connections",
        ),
      );
    });
    it("surfaces load, save and delete failures", async () => {
      const { db } = installAppApi();
      const row = db[key][0];
      server.use(
        http.put(`/api/${path}/${row.id}`, () =>
          HttpResponse.json({ detail: "Read only" }, { status: 403 }),
        ),
        http.delete(`/api/${path}/${row.id}`, () =>
          HttpResponse.json({ detail: "In use" }, { status: 409 }),
        ),
      );
      const { wrapper } = await mountView(
        component,
        `/settings/${path}/${row.id}`,
        `/settings/${path}/:id`,
      );
      await vi.waitFor(() => expect(wrapper.find("input").exists()).toBe(true));
      await wrapper.get("input").setValue("Unsent");
      await button(wrapper, t("common.save")).trigger("click");
      await vi.waitFor(() =>
        expect(useToastState().value.at(-1)?.title).toBe(t(`connections.${kind}.toast.saveFailed`)),
      );
      await button(wrapper, t("common.delete")).trigger("click");
      await button(wrapper, t("common.deleteConfirm")).trigger("click");
      await vi.waitFor(() =>
        expect(useToastState().value.at(-1)?.title).toBe(
          t(`connections.${kind}.toast.deleteFailed`),
        ),
      );
      const missing = await mountView(
        component,
        `/settings/${path}/missing`,
        `/settings/${path}/:id`,
      );
      await vi.waitFor(() => expect(missing.wrapper.text()).toContain("Not found"));
      await button(missing.wrapper, t("common.goBack")).trigger("click");
    });
  });
it("renders family parameter defaults, bounds and capabilities", async () => {
  const { db } = installAppApi();
  Object.assign(db.families[0], {
    provider_types: [],
    extra_metadata: {
      supports_vision: true,
      supports_function_calling: true,
      supports_prompt_caching: true,
      reasoning_mode: "adaptive",
    },
    unsupported_parameters: ["seed"],
    parameters: {
      missing: null,
      empty: {},
      object: { type: "object", default: { mode: "auto" } },
      min: { type: "float", min_value: 0, default: 0 },
      max: { type: "integer", max_value: 100 },
      range: {
        type: "enum",
        min_value: 1,
        max_value: 5,
        default: "auto",
        str_values: ["auto", "off"],
      },
    },
  });
  const { wrapper } = await mountView(
    ModelFamilyView,
    `/settings/model-families/${db.families[0].id}`,
    "/settings/model-families/:id",
  );
  await vi.waitFor(() => expect(wrapper.text()).toContain(">= 0"));
  for (const text of ["<= 100", "1 - 5", '"mode":"auto"', "unknown", "none", "auto, off", "seed"])
    expect(wrapper.text()).toContain(text);
  await wrapper
    .get(`button[aria-label="${t("connections.family.backToFamilies")}"]`)
    .trigger("click");
});
