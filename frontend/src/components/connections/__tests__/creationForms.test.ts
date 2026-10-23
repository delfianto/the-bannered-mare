import { describe, expect, it } from "vite-plus/test";
import { mount } from "@vue/test-utils";
import ModelForm from "../ModelForm.vue";
import ProviderForm from "../ProviderForm.vue";
import SelectMenu from "@/components/shared/SelectMenu.vue";
import { providers } from "@/mocks/data/providers";
import { allModelFamiliesMock } from "@/mocks/data/model-families-data";
import { button, pickOption } from "@/test/views";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);

describe("provider creation", () => {
  it("custom providers require a URL and key environment variable", async () => {
    const wrapper = mount(ProviderForm, { attachTo: document.body });
    await wrapper.get('input[placeholder="Provider name"]').setValue("  My endpoint  ");
    await pickOption(wrapper.get("button[type=button]"), "Custom");
    expect(button(wrapper, "Create Provider").element.disabled).toBe(true);
    await wrapper
      .get('input[placeholder="https://api.example.com/v1"]')
      .setValue(" https://api.test/v1 ");
    await wrapper.get('input[placeholder="E.G. MY_PROVIDER_API_KEY"]').setValue(" MY_KEY ");
    await button(wrapper, "Create Provider").trigger("click");
    expect(wrapper.emitted("submit")?.[0]).toEqual([
      {
        name: "My endpoint",
        provider_type: "custom",
        base_url: "https://api.test/v1",
        api_key_env_var: "MY_KEY",
      },
    ]);
  });

  it("switching to a native provider omits the custom key and allows default URL", async () => {
    const wrapper = mount(ProviderForm, { attachTo: document.body });
    await wrapper.get("input").setValue("Native");
    await pickOption(wrapper.get("button[type=button]"), "Custom");
    await wrapper.get('input[placeholder="E.G. MY_PROVIDER_API_KEY"]').setValue("OLD_KEY");
    await pickOption(wrapper.get("button[type=button]"), "OpenAI");
    await button(wrapper, "Create Provider").trigger("click");
    expect(wrapper.emitted("submit")?.[0]?.[0]).toMatchObject({
      provider_type: "openai",
      api_key_env_var: null,
      base_url: null,
    });
    await button(wrapper, t("common.cancel")).trigger("click");
    expect(wrapper.emitted("cancel")).toHaveLength(1);
  });
});

describe("model creation", () => {
  const families = [
    {
      ...allModelFamiliesMock[0],
      id: "or-family",
      name: "Router family",
      description: null,
      provider_types: ["openrouter"],
    },
    {
      ...allModelFamiliesMock[0],
      id: "native-family",
      name: "Native family",
      description: null,
      provider_types: ["openai"],
    },
  ];
  it("family selection constrains providers and restores a compatible discovery prefill", async () => {
    const wrapper = mount(ModelForm, {
      props: {
        providers,
        families,
        prefill: {
          provider_id: "prov-openrouter",
          model_identifier: " meta/muse ",
          name: " Muse ",
        },
      },
      attachTo: document.body,
    });
    const menus = wrapper.findAllComponents(SelectMenu);
    expect(menus[1].get<HTMLButtonElement>("button").element.disabled).toBe(true);
    await pickOption(menus[0].get("button"), "Router family");
    expect(menus[1].text()).toContain("OpenRouter");
    await button(wrapper, t("connections.model.createModel")).trigger("click");
    expect(wrapper.emitted("submit")?.[0]).toEqual([
      {
        display_name: "Muse",
        model_family_id: "or-family",
        enabled: true,
        routes: [{ provider_id: "prov-openrouter", model_identifier: "meta/muse", enabled: true }],
      },
    ]);
    await pickOption(menus[0].get("button"), "Native family");
    expect(button(wrapper, t("connections.model.createModel")).element.disabled).toBe(true);
    await pickOption(menus[1].get("button"), "OpenAI");
    await wrapper.get('input[role="switch"]').setValue(false);
    await button(wrapper, t("connections.model.createModel")).trigger("click");
    expect(wrapper.emitted("submit")?.at(-1)?.[0]).toMatchObject({
      enabled: false,
      routes: [{ provider_id: "prov-openai", model_identifier: "meta/muse", enabled: true }],
    });
  });

  it("empty name or identifier prevents submission and saving disables duplicate submits", async () => {
    const wrapper = mount(ModelForm, { props: { providers, families } });
    expect(button(wrapper, t("connections.model.createModel")).element.disabled).toBe(true);
    await wrapper.setProps({ saving: true });
    expect(button(wrapper, t("connections.model.creating")).element.disabled).toBe(true);
    await button(wrapper, t("common.cancel")).trigger("click");
    expect(wrapper.emitted("cancel")).toHaveLength(1);
  });
});
