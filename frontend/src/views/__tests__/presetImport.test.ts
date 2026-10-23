import { expect, it } from "vite-plus/test";
import { nextTick } from "vue";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia } from "pinia";
import { http, HttpResponse } from "msw";
import ImportPresetModal from "@/components/connections/ImportPresetModal.vue";
import ProfilesView from "../ProfilesView.vue";
import { installAppApi } from "@/test/appApi";
import { mountView, button } from "@/test/views";
import { server } from "@/mocks/server";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
it("imports a preset by dropping or selecting a file, resets and reports failures", async () => {
  installAppApi();
  let fail = false;
  let minimal = false;
  server.use(
    http.post("/api/presets/import", () =>
      fail
        ? HttpResponse.json({ detail: "Invalid preset" }, { status: 422 })
        : HttpResponse.json({
            template_id: "tpl",
            template_name: "Imported template",
            fragment_ids: minimal ? [] : ["frag"],
            preset_name: minimal ? null : "Imported parameters",
            profile_name: minimal ? null : "Imported loadout",
            warnings: minimal ? [] : ["Unsupported option ignored"],
          }),
    ),
  );
  const wrapper = mount(ImportPresetModal, { global: { plugins: [createPinia()] } });
  const file = new File(["{}"], "preset.json", { type: "application/json" });
  const input = wrapper.get("input[type=file]");
  let drop = wrapper.get("button[type=button]");
  await drop.trigger("dragover");
  await drop.trigger("dragleave");
  await drop.trigger("drop", { dataTransfer: { files: [] } });
  await drop.trigger("drop", { dataTransfer: { files: [file] } });
  await flushPromises();
  expect(wrapper.text()).toContain("Imported template");
  expect(wrapper.text()).toContain("Unsupported option ignored");
  expect(wrapper.emitted("imported")).toHaveLength(1);
  await button(wrapper, t("presetImport.importAnother")).trigger("click");
  fail = true;
  Object.defineProperty(input.element, "files", { value: [file], configurable: true });
  await input.trigger("change");
  await flushPromises();
  expect(wrapper.text()).toContain(t("presetImport.failed"));
  fail = false;
  minimal = true;
  await input.trigger("change");
  await flushPromises();
  expect(wrapper.text()).toContain("Imported template");
  expect(wrapper.text()).not.toContain("Imported parameters");
  await button(wrapper, t("presetImport.done")).trigger("click");
  expect(wrapper.emitted("close")).toHaveLength(1);
  await button(wrapper, t("presetImport.importAnother")).trigger("click");
  drop = wrapper.get("button[type=button]");
  await drop.trigger("click");
  Object.defineProperty(input.element, "files", { value: [] });
  await input.trigger("change");
  await wrapper.get(`button[aria-label="${t("common.cancel")}"]`).trigger("click");
  expect(wrapper.emitted("close")).toHaveLength(2);
});
it("opens preset import from the loadouts tab and refreshes on import", async () => {
  installAppApi();
  server.use(
    http.post("/api/presets/import", () =>
      HttpResponse.json({ template_name: "Imported", fragment_ids: [], warnings: [] }),
    ),
  );
  const { wrapper } = await mountView(ProfilesView, "/loadouts?tab=presets", "/loadouts");
  await flushPromises();
  await button(wrapper, t("presetImport.button")).trigger("click");
  await nextTick();
  const modal = wrapper.findComponent(ImportPresetModal);
  const input = modal.get("input[type=file]");
  Object.defineProperty(input.element, "files", { value: [new File(["{}"], "preset.json")] });
  await input.trigger("change");
  await flushPromises();
  expect(modal.text()).toContain("Imported");
  await button(modal, t("presetImport.done")).trigger("click");
  expect(wrapper.findComponent(ImportPresetModal).exists()).toBe(false);
});
