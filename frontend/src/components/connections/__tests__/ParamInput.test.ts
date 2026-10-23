import { describe, it, expect } from "vite-plus/test";
import { mount } from "@vue/test-utils";
import ParamInput from "../ParamInput.vue";
import type { ParamSchema } from "@/types/params";

// Exercises ParamInput's schema-type → widget mapping and, crucially, its
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

describe("ParamInput value contracts", () => {
  it.each(["int", "float"])(
    "edits %s values, keeps zero, and ignores an empty numeric input",
    async (type) => {
      const wrapper = mount(ParamInput, {
        props: { paramKey: "amount", schema: { type, default: 4 }, modelValue: 0 },
      });
      const input = wrapper.get('input[type="number"]');
      expect((input.element as HTMLInputElement).value).toBe("0");
      await input.setValue("1.6");
      expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual([type === "int" ? 2 : 1.6]);
      const count = wrapper.emitted("update:modelValue")!.length;
      await input.setValue("");
      expect(wrapper.emitted("update:modelValue")).toHaveLength(count);
    },
  );

  it("a range and numeric input emit the same float values", async () => {
    const wrapper = mount(ParamInput, {
      props: {
        paramKey: "temperature",
        schema: { type: "float", min_value: 0, max_value: 2, default: 1 },
        modelValue: undefined,
      },
    });
    expect((wrapper.get('input[type="number"]').element as HTMLInputElement).value).toBe("1");
    await wrapper.get('input[type="range"]').setValue("0.7");
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual([0.7]);
  });

  it("enabled/disabled toggles emit API tokens", async () => {
    const wrapper = mount(ParamInput, {
      props: {
        paramKey: "thinking",
        schema: { type: "enum", str_values: ["enabled", "disabled"] },
        modelValue: "enabled",
      },
    });
    await wrapper.get('input[role="switch"]').setValue(false);
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual(["disabled"]);
  });

  it("string tags trim whitespace, ignore duplicates and blanks, and remove by index", async () => {
    const wrapper = mount(ParamInput, {
      props: {
        paramKey: "stop",
        schema: { type: "list", item_schema: { type: "string" } },
        modelValue: ["User:"],
      },
    });
    const input = wrapper.get("input");
    await input.setValue("  Assistant:  ");
    await input.trigger("keydown", { key: "Enter" });
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual([["User:", "Assistant:"]]);
    await input.setValue("User:");
    await input.trigger("keydown", { key: "Enter" });
    await input.setValue(" ");
    await input.trigger("keydown", { key: "Enter" });
    expect(wrapper.emitted("update:modelValue")).toHaveLength(1);
    await wrapper.get('[aria-label="Remove User:"]').trigger("click");
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual([[]]);
  });

  it("valid JSON emits a structured value, while partial JSON does not overwrite saved data", async () => {
    const wrapper = mount(ParamInput, {
      props: { paramKey: "format", schema: { type: "json" }, modelValue: { type: "text" } },
    });
    await wrapper.get("textarea").setValue("{");
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
    await wrapper.get("textarea").setValue('{"type":"json_object"}');
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual([{ type: "json_object" }]);
  });

  it("nested object edits preserve sibling values and do not mutate the input object", async () => {
    const value = { budget: 1024, enabled: true };
    const wrapper = mount(ParamInput, {
      props: {
        paramKey: "thinking",
        schema: {
          type: "object",
          properties: { budget: { type: "int" }, enabled: { type: "boolean" } },
        },
        modelValue: value,
      },
    });
    await wrapper.get('input[type="number"]').setValue("2048");
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual([{ budget: 2048, enabled: true }]);
    expect(value.budget).toBe(1024);
  });

  it("editing one object in a list preserves the other rows and sibling properties", async () => {
    const value = [
      { category: "safe", threshold: 1 },
      { category: "other", threshold: 2 },
    ];
    const wrapper = mount(ParamInput, {
      props: {
        paramKey: "safety",
        schema: {
          type: "list",
          item_schema: { type: "object", properties: { category: { type: "string" } } },
        },
        modelValue: value,
      },
    });
    await wrapper.findAll('input[type="text"]')[0].setValue("updated");
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual([
      [{ category: "updated", threshold: 1 }, value[1]],
    ]);
    expect(value[0].category).toBe("safe");
  });
});
