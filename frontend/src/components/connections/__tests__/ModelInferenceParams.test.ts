import { describe, expect, it } from "vite-plus/test";
import { mount } from "@vue/test-utils";
import ModelInferenceParams from "../ModelInferenceParams.vue";
import type { ParamSchema } from "@/types/params";

const familyParameters: Record<string, ParamSchema> = {
  stream: { type: "boolean", default: true },
  temperature: { type: "float", default: 1, min_value: 0, max_value: 2 },
  system_prompt: { type: "string", default: "Default prompt" },
};
function setup(modelParameters: Record<string, unknown> = {}) {
  return mount(ModelInferenceParams, {
    props: {
      familyParameters,
      modelParameters,
      parameterDocs: {
        temperature: { label: "Creativity", short_info: "Sampling heat", detailed_info: "Details" },
      },
    },
  });
}

describe("family inference settings", () => {
  it("renders documented controls and family defaults across all groups", () => {
    const wrapper = setup();
    expect(wrapper.text()).toContain("Using family defaults");
    expect(wrapper.text()).toContain("Creativity");
    expect(wrapper.get<HTMLInputElement>('input[role="switch"]').element.checked).toBe(true);
    expect(wrapper.get<HTMLInputElement>('input[type="number"]').element.value).toBe("1");
    expect(wrapper.get<HTMLTextAreaElement>("textarea").element.value).toBe("Default prompt");
    expect(wrapper.findAll("h3").map((h) => h.text())).toEqual([
      "General",
      "Fine-Tuning",
      "Advanced",
    ]);
  });

  it("preserves false/zero overrides and merges an edit without mutating props", async () => {
    const overrides = { stream: false, temperature: 0, system_prompt: "Custom" };
    const wrapper = setup(overrides);
    expect(wrapper.get<HTMLInputElement>('input[role="switch"]').element.checked).toBe(false);
    expect(wrapper.get<HTMLInputElement>('input[type="number"]').element.value).toBe("0");
    await wrapper.get<HTMLInputElement>('input[type="number"]').setValue("0.75");
    expect(wrapper.emitted("update:modelParameters")?.at(-1)).toEqual([
      { ...overrides, temperature: 0.75 },
    ]);
    expect(overrides.temperature).toBe(0);
  });

  it("reset emits an empty override map so inheritance resumes", async () => {
    const wrapper = setup({ temperature: 0.7 });
    await wrapper.get("button").trigger("click");
    expect(wrapper.emitted("update:modelParameters")?.at(-1)).toEqual([{}]);
  });

  it("switching family removes controls absent from the new schema", async () => {
    const wrapper = setup();
    await wrapper.setProps({
      familyParameters: {
        reasoning_effort: {
          type: "enum",
          default: "medium",
          str_values: ["low", "medium", "high"],
        },
      },
    });
    expect(wrapper.find('input[type="number"]').exists()).toBe(false);
    expect(wrapper.text()).not.toContain("Creativity");
    expect(wrapper.text()).toContain("Reasoning Effort");
  });

  it("shows a useful empty state for an unknown family", () => {
    const wrapper = mount(ModelInferenceParams, {
      props: { familyParameters: {}, modelParameters: {}, parameterDocs: {} },
    });
    expect(wrapper.text()).toContain("No parameters defined");
    expect(wrapper.find("input").exists()).toBe(false);
  });
});
