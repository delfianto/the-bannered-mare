import { afterEach, describe, expect, it, vi } from "vite-plus/test";
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import SelectMenu from "../SelectMenu.vue";

const items = [
  { value: "a", label: "Amber" },
  { value: "b", label: "Blue" },
  { value: "c", label: "Copper" },
];
function setup(extra = {}) {
  return mount(SelectMenu, {
    props: { items, ...extra },
    slots: { default: "<button>Select model</button>" },
    attachTo: document.body,
  });
}
const options = () => Array.from(document.querySelectorAll<HTMLElement>('[role="option"]'));
const search = () => document.querySelector<HTMLInputElement>('[role="combobox"]')!;
async function key(element: Element, key: string) {
  element.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }));
  await nextTick();
}
afterEach(() => vi.restoreAllMocks());

describe("searchable dropdown", () => {
  it("opens a real teleported list, marks the selected option and emits its raw value", async () => {
    const wrapper = setup({ modelValue: "b" });
    await wrapper.get("button").trigger("click");
    expect(wrapper.get('[aria-haspopup="listbox"]').attributes("aria-expanded")).toBe("true");
    expect(options()).toHaveLength(3);
    expect(options()[1].getAttribute("aria-selected")).toBe("true");
    expect(document.activeElement).toBe(search());
    options()[2].click();
    await nextTick();
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual(["c"]);
    expect(options()).toHaveLength(0);
  });

  it("filters case-insensitively, shows no results and clears the query when reopened", async () => {
    const wrapper = setup();
    await wrapper.get("button").trigger("click");
    search().value = " BLUE ";
    search().dispatchEvent(new Event("input", { bubbles: true }));
    await nextTick();
    expect(options().map((el) => el.textContent?.trim())).toEqual(["Blue"]);
    search().value = "missing";
    search().dispatchEvent(new Event("input", { bubbles: true }));
    await nextTick();
    expect(document.body.textContent).toContain("No results");
    expect(search().hasAttribute("aria-activedescendant")).toBe(false);
    document.body.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
    await nextTick();
    await wrapper.get("button").trigger("click");
    expect(options()).toHaveLength(3);
    expect(search().value).toBe("");
  });

  it("arrows and Enter work from the focused search input inside the teleport", async () => {
    const wrapper = setup();
    await wrapper.get("button").trigger("keydown", { key: "ArrowDown" });
    await key(search(), "ArrowDown");
    expect(search().getAttribute("aria-activedescendant")).toBe(options()[1].id);
    await key(search(), "ArrowDown");
    await key(search(), "ArrowDown");
    expect(search().getAttribute("aria-activedescendant")).toBe(options()[2].id);
    await key(search(), "ArrowUp");
    await key(search(), "Enter");
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual(["b"]);
  });

  it("Escape from the focused input closes without changing the selection", async () => {
    const wrapper = setup();
    await wrapper.get("button").trigger("click");
    await key(search(), "Escape");
    expect(options()).toHaveLength(0);
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
  });

  it("disabled controls cannot open", async () => {
    const wrapper = setup({ disabled: true });
    await wrapper.get("button").trigger("click");
    await wrapper.get("button").trigger("keydown", { key: "ArrowDown" });
    expect(options()).toHaveLength(0);
  });

  it("non-searchable enums support keyboard selection from their trigger", async () => {
    const wrapper = setup({ searchInput: false });
    await wrapper.get("button").trigger("keydown", { key: "ArrowDown" });
    expect(search()).toBeNull();
    await wrapper.get("button").trigger("keydown", { key: "ArrowDown" });
    await wrapper.get("button").trigger("keydown", { key: "Enter" });
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual(["b"]);
  });

  it("unmount removes teleported content and document listeners", async () => {
    const wrapper = setup();
    await wrapper.get("button").trigger("click");
    const remove = vi.spyOn(document, "removeEventListener");
    wrapper.unmount();
    expect(options()).toHaveLength(0);
    expect(remove).toHaveBeenCalledWith("pointerdown", expect.any(Function), true);
  });
});
