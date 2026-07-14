import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import AppToggle from "../AppToggle.vue";

// Harness smoke test (FE-C1): proves SFCs compile, happy-dom provides a DOM,
// and @vue/test-utils can mount a component and observe rendering + events.
describe("AppToggle (harness smoke test)", () => {
  it("renders a switch input reflecting modelValue + aria-label", () => {
    const wrapper = mount(AppToggle, { props: { modelValue: true, ariaLabel: "Test toggle" } });
    const input = wrapper.get('input[role="switch"]');
    expect((input.element as HTMLInputElement).checked).toBe(true);
    expect(input.attributes("aria-label")).toBe("Test toggle");
  });

  it("emits update:modelValue and change when toggled", async () => {
    const wrapper = mount(AppToggle, { props: { modelValue: false } });
    await wrapper.get('input[role="switch"]').setValue(true);
    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual([true]);
    expect(wrapper.emitted("change")?.[0]).toEqual([true]);
  });
});
