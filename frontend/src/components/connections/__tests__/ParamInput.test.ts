import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import ParamInput from "../ParamInput.vue";
import type { ParamSchema } from "@/types/params";

// FE-3a: exercises ParamInput's schema-type → widget mapping and, crucially, its
// recursive rendering of object schemas (the recursive param types).
describe("ParamInput", () => {
  it("renders a text input for a string schema and emits update:modelValue", async () => {
    const wrapper = mount(ParamInput, {
      props: {
        paramKey: "label",
        schema: { type: "string" } satisfies ParamSchema,
        modelValue: "",
      },
    });
    await wrapper.get('input[type="text"]').setValue("hello");
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual(["hello"]);
  });

  it("renders a toggle for a boolean schema and emits the new value", async () => {
    const wrapper = mount(ParamInput, {
      props: {
        paramKey: "stream",
        schema: { type: "boolean" } satisfies ParamSchema,
        modelValue: false,
      },
    });
    await wrapper.get('input[role="switch"]').setValue(true);
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual([true]);
  });

  it("recursively renders one child control per property of an object schema", () => {
    const schema: ParamSchema = {
      type: "object",
      properties: {
        nickname: { type: "string" },
        verbose: { type: "boolean" },
      },
    };
    const wrapper = mount(ParamInput, {
      props: { paramKey: "opts", schema, modelValue: {} },
    });
    // one nested child ParamInput per property (findAllComponents excludes the root)
    expect(wrapper.findAllComponents(ParamInput)).toHaveLength(2);
    expect(wrapper.find('input[type="text"]').exists()).toBe(true);
    expect(wrapper.find('input[role="switch"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("nickname");
    expect(wrapper.text()).toContain("verbose");
  });

  it("falls back to an 'unsupported type' notice for unknown schema types", () => {
    const wrapper = mount(ParamInput, {
      props: {
        paramKey: "weird",
        schema: { type: "matrix" } satisfies ParamSchema,
        modelValue: null,
      },
    });
    expect(wrapper.text()).toContain("Unsupported type");
    expect(wrapper.text()).toContain("matrix");
  });
});
