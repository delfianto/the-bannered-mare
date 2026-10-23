import { expect, it } from "vite-plus/test";
import { mount } from "@vue/test-utils";
import AppTooltip from "../AppTooltip.vue";
import AppPagination from "../AppPagination.vue";
import { button } from "@/test/views";
it.each(["top", "right", "bottom", "left"] as const)(
  "positions %s tooltips on hover/focus and hides on leave",
  async (side) => {
    const wrapper = mount(AppTooltip, {
      props: { text: "Help", side, wide: true },
      slots: { default: "<button>Control</button>" },
    });
    await wrapper.trigger("mouseenter");
    expect(document.querySelector("[role=tooltip]")?.textContent).toBe("Help");
    await wrapper.trigger("mouseleave");
    expect(document.querySelector("[role=tooltip]")).toBeNull();
    await wrapper.trigger("focusin");
    await wrapper.trigger("focusout");
    expect(document.querySelector("[role=tooltip]")).toBeNull();
    await wrapper.setProps({ disabled: true });
    await wrapper.trigger("mouseenter");
    expect(document.querySelector("[role=tooltip]")).toBeNull();
    await wrapper.setProps({ disabled: false, text: "" });
    await wrapper.trigger("mouseenter");
    expect(document.querySelector("[role=tooltip]")).toBeNull();
  },
);
it("windows pagination, navigates and disables boundary controls", async () => {
  const wrapper = mount(AppPagination, { props: { page: 5, totalPages: 10 } });
  expect(wrapper.text()).toContain("…");
  await wrapper.get('button[aria-label="Previous page"]').trigger("click");
  expect(wrapper.emitted("update:page")?.[0]).toEqual([4]);
  await wrapper.get('button[aria-label="Next page"]').trigger("click");
  expect(wrapper.emitted("update:page")?.[1]).toEqual([6]);
  await button(wrapper, "1").trigger("click");
  await button(wrapper, "5").trigger("click");
  expect(wrapper.emitted("update:page")).toHaveLength(3);
  await wrapper.setProps({ page: 1, totalPages: 3 });
  expect(wrapper.get('button[aria-label="Previous page"]').attributes("disabled")).toBeDefined();
  await wrapper.setProps({ page: 3 });
  expect(wrapper.get('button[aria-label="Next page"]').attributes("disabled")).toBeDefined();
});
