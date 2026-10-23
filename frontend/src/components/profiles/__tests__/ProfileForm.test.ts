import { afterEach, describe, expect, it, vi } from "vite-plus/test";
import { mount } from "@vue/test-utils";
import { http, HttpResponse } from "msw";
import ProfileForm from "../ProfileForm.vue";
import SelectMenu from "@/components/shared/SelectMenu.vue";
import { allModelsMock } from "@/mocks/data/models-data";
import { allModelFamiliesMock } from "@/mocks/data/model-families-data";
import { presets } from "@/mocks/data/presets";
import { personas } from "@/mocks/data/personas";
import { promptTemplates } from "@/mocks/data/prompt-templates";
import { profiles } from "@/mocks/data/profiles";
import { server } from "@/mocks/server";
import { button, pickOption } from "@/test/views";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
async function setup(initial = false) {
  const models = [
    {
      ...allModelsMock[0],
      id: "active",
      display_name: "Active model",
      enabled: true,
      provider_enabled: true,
    },
    {
      ...allModelsMock[1],
      id: "disabled",
      display_name: "Disabled model",
      enabled: false,
      provider_enabled: true,
    },
    {
      ...allModelsMock[2],
      id: "offline",
      display_name: "Offline provider",
      enabled: true,
      provider_enabled: false,
    },
  ];
  server.use(
    http.get("/api/model-families/:id", ({ params }) =>
      HttpResponse.json({
        ...allModelFamiliesMock[0],
        id: params.id,
        unsupported_parameters: ["temperature"],
      }),
    ),
  );
  const listModels = models.map((m) => ({
    ...m,
    slug: m.slug ?? m.id,
    original_identifier: m.original_identifier ?? m.id,
  }));
  const wrapper = mount(ProfileForm, {
    props: {
      models: listModels,
      presets,
      personas,
      templates: promptTemplates,
      initial: initial
        ? { ...profiles[0], name: "Existing", model_id: "disabled", task_model_id: "offline" }
        : null,
    },
    attachTo: document.body,
  });
  if (initial) await vi.waitFor(() => expect(wrapper.text()).toContain("temperature"));
  return { wrapper, models };
}
afterEach(() => vi.restoreAllMocks());
describe("profile editor", () => {
  it("requires a nonblank name, trims values and maps unset options to null", async () => {
    const { wrapper } = await setup();
    expect(button(wrapper, t("profiles.form.create")).element.disabled).toBe(true);
    await wrapper.get("input[type=text]").setValue("  My tale  ");
    await wrapper.get("textarea").setValue("  ");
    await button(wrapper, t("profiles.form.create")).trigger("click");
    expect(wrapper.emitted("submit")?.[0]).toEqual([
      {
        name: "My tale",
        description: null,
        is_default: false,
        prompt_template_id: null,
        preset_id: null,
        persona_id: null,
        model_id: null,
        task_model_id: null,
      },
    ]);
  });

  it("new profiles offer only enabled models on enabled providers", async () => {
    const { wrapper } = await setup();
    await wrapper.findAllComponents(SelectMenu)[3].get("button").trigger("click");
    const labels = Array.from(document.querySelectorAll('[role="option"]')).map((el) =>
      el.textContent?.trim(),
    );
    expect(labels).toContain("Active model");
    expect(labels).not.toContain("Disabled model");
    expect(labels).not.toContain("Offline provider");
  });

  it("existing disabled models remain selected when editing and survive submission", async () => {
    const { wrapper } = await setup(true);
    const menus = wrapper.findAllComponents(SelectMenu);
    await menus[3].get("button").trigger("click");
    expect(document.body.textContent).toContain("Disabled model");
    document.body.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
    await button(wrapper, t("profiles.form.save")).trigger("click");
    expect(wrapper.emitted("submit")?.[0]?.[0]).toMatchObject({
      model_id: "disabled",
      task_model_id: "offline",
    });
  });

  it("selected model, task model, persona, template and preset are emitted independently", async () => {
    const { wrapper } = await setup();
    const menus = wrapper.findAllComponents(SelectMenu);
    await pickOption(menus[0].get("button"), presets[0].name);
    await pickOption(menus[1].get("button"), promptTemplates[0].name);
    await pickOption(menus[2].get("button"), "Active model");
    await pickOption(menus[3].get("button"), "Active model");
    await pickOption(menus[4].get("button"), personas[0].name);
    await wrapper.get("input[type=text]").setValue("Named");
    await wrapper.get("input[role=switch]").setValue(true);
    await button(wrapper, t("profiles.form.create")).trigger("click");
    expect(wrapper.emitted("submit")?.[0]?.[0]).toMatchObject({
      prompt_template_id: promptTemplates[0].id,
      preset_id: presets[0].id,
      persona_id: personas[0].id,
      model_id: "active",
      task_model_id: "active",
      is_default: true,
    });
    await vi.waitFor(() => expect(wrapper.text()).toContain("temperature"));
  });

  it("switching from an existing profile to a fresh form resets all fields", async () => {
    const { wrapper } = await setup(true);
    await wrapper.setProps({ initial: null });
    expect(wrapper.get<HTMLInputElement>("input[type=text]").element.value).toBe("");
    expect(button(wrapper, t("profiles.form.create")).element.disabled).toBe(true);
    await button(wrapper, t("common.cancel")).trigger("click");
    expect(wrapper.emitted("cancel")).toHaveLength(1);
  });
});
