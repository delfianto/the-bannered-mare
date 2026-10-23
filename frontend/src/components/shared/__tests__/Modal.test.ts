import { afterEach, describe, expect, it, vi } from "vite-plus/test";
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import Modal from "../Modal.vue";

function setup(extra = {}) {
  return mount(Modal, {
    props: { show: true, title: "Editor", ...extra },
    slots: { default: '<input aria-label="Name"><button>Save</button>' },
    attachTo: document.body,
  });
}
function key(key: string, shiftKey = false) {
  const event = new KeyboardEvent("keydown", { key, shiftKey, bubbles: true, cancelable: true });
  window.dispatchEvent(event);
  return event;
}
afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe("modal interactions", () => {
  it("labels the teleported dialog and emits close from Escape", async () => {
    const wrapper = setup();
    await nextTick();
    const dialog = document.querySelector('[role="dialog"]')!;
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    expect(document.getElementById(dialog.getAttribute("aria-labelledby")!)?.textContent).toBe(
      "Editor",
    );
    key("Escape");
    expect(wrapper.emitted("close")).toHaveLength(1);
    expect(document.body.style.overflow).toBe("hidden");
  });

  it("only the top dialog handles Escape and closing it keeps the underlying scroll lock", async () => {
    const first = setup();
    const second = setup({ title: "Confirm" });
    await nextTick();
    key("Escape");
    expect(second.emitted("close")).toHaveLength(1);
    expect(first.emitted("close")).toBeUndefined();
    await second.setProps({ show: false });
    expect(document.body.style.overflow).toBe("hidden");
    key("Escape");
    expect(first.emitted("close")).toHaveLength(1);
    first.unmount();
    second.unmount();
    expect(document.body.style.overflow).toBe("");
  });

  it("closing restores launcher focus and removes the panel after its leave delay", async () => {
    vi.useFakeTimers();
    const launcher = document.createElement("button");
    document.body.append(launcher);
    launcher.focus();
    const wrapper = setup();
    await nextTick();
    await wrapper.setProps({ show: false });
    expect(document.activeElement).toBe(launcher);
    vi.advanceTimersByTime(200);
    await nextTick();
    expect(document.querySelector('[role="dialog"]')).toBeNull();
    launcher.remove();
  });

  it("Tab and Shift+Tab wrap inside the panel, including when focus escaped", async () => {
    setup();
    await nextTick();
    const dialog = document.querySelector('[role="dialog"]')!;
    const buttons = dialog.querySelectorAll<HTMLButtonElement>("button");
    const first = buttons[0],
      last = buttons[buttons.length - 1];
    last.focus();
    expect(key("Tab").defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(first);
    first.focus();
    key("Tab", true);
    expect(document.activeElement).toBe(last);
    (dialog.querySelector('[tabindex="-1"]') as HTMLElement).focus();
    key("Tab");
    expect(document.activeElement).toBe(first);
  });

  it("reopening before the close timer fires keeps the dialog mounted", async () => {
    vi.useFakeTimers();
    const wrapper = setup();
    await wrapper.setProps({ show: false });
    vi.advanceTimersByTime(100);
    await wrapper.setProps({ show: true });
    vi.advanceTimersByTime(200);
    await nextTick();
    expect(document.querySelector('[role="dialog"]')).not.toBeNull();
  });
});
