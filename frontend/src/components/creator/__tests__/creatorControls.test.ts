import { afterEach, expect, it, vi } from "vite-plus/test";
import { mount, DOMWrapper } from "@vue/test-utils";
import { nextTick } from "vue";
import AvatarUpload from "../AvatarUpload.vue";
import CharacterPreview from "../CharacterPreview.vue";
import AutoTextarea from "../AutoTextarea.vue";
import TagInput from "../TagInput.vue";
import Combobox from "../Combobox.vue";
import LorebookEntryCard from "../LorebookEntryCard.vue";
import { useCharacterForm } from "@/composables/useCharacterForm";
import { mountComposable } from "@/test/helpers";
import { button } from "@/test/views";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);
afterEach(() => vi.restoreAllMocks());
for (const component of [AvatarUpload, CharacterPreview])
  it(`${component.__name} accepts image selection/drop and rejects non-images`, async () => {
    const { api: result } = mountComposable(() => useCharacterForm());
    const data = result.data;
    const wrapper =
      component === AvatarUpload
        ? mount(AvatarUpload, { props: { avatarUrl: "" } })
        : mount(CharacterPreview, { props: { data, completeness: { filled: 0, total: 0 } } });
    const zone = wrapper.get("input[type=file]").element.parentElement!;
    const drop = new DOMWrapper(zone);
    const file = new File(["image"], "image.png", { type: "image/png" });
    await drop.trigger("dragover");
    await drop.trigger("dragleave");
    await drop.trigger("drop", { dataTransfer: { files: [] } });
    await drop.trigger("drop", {
      dataTransfer: { files: [new File(["text"], "file.txt", { type: "text/plain" })] },
    });
    expect(wrapper.emitted("change")).toBeUndefined();
    await drop.trigger("drop", { dataTransfer: { files: [file] } });
    expect(wrapper.emitted("change")?.[0]).toEqual([file]);
    const input = wrapper.get<HTMLInputElement>("input[type=file]");
    Object.defineProperty(input.element, "files", { value: [file], configurable: true });
    await input.trigger("change");
    expect(wrapper.emitted("change")).toHaveLength(2);
    Object.defineProperty(input.element, "files", { value: [] });
    await input.trigger("change");
    const click = vi.spyOn(input.element, "click").mockImplementation(() => {});
    await drop.trigger("click");
    expect(click).toHaveBeenCalled();
    if (component === AvatarUpload) await wrapper.setProps({ avatarUrl: "portrait.png" });
  });
it("previews greeting, completeness states and an expanded greeting", async () => {
  const { api: result } = mountComposable(() => useCharacterForm());
  const wrapper = mount(CharacterPreview, {
    attachTo: document.body,
    props: { data: result.data, completeness: { filled: 6, total: 12 } },
  });
  expect(wrapper.text()).toContain("Looking good");
  await wrapper.setProps({
    data: { ...result.data, avatarUrl: "avatar.png", greeting: "A tale. ".repeat(100) },
    completeness: { filled: 12, total: 12 },
  });
  expect(wrapper.text()).toContain("Character complete");
  await wrapper.get(`button[aria-label="${t("characters.form.greeting")}"]`).trigger("click");
  expect(document.querySelector('[role="dialog"]')?.textContent).toContain("A tale.");
  document
    .querySelector<HTMLButtonElement>(`[role="dialog"] button[aria-label="${t("common.close")}"]`)!
    .click();
  await nextTick();
});
it("expands a textarea, emits focused edits and returns to inline editing", async () => {
  const wrapper = mount(AutoTextarea, {
    attachTo: document.body,
    props: { modelValue: "Original" },
  });
  await wrapper.get("textarea").setValue("Inline");
  expect(wrapper.emitted("update:modelValue")?.[0]).toEqual(["Inline"]);
  await wrapper.setProps({ modelValue: "Updated externally" });
  await wrapper.get('button[aria-label="Expand editor"]').trigger("click");
  const dialog = new DOMWrapper(document.querySelector<HTMLElement>('[role="dialog"]')!);
  await dialog.get("textarea").setValue("Expanded");
  expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual(["Expanded"]);
  await button(dialog, t("common.done")).trigger("click");
  await wrapper.setProps({ expandable: false });
  expect(wrapper.find('button[aria-label^="Expand"]').exists()).toBe(false);
});
it("commits custom combobox values on blur and keeps focus inside the list", async () => {
  const wrapper = mount(Combobox, { props: { modelValue: "Elf", options: ["Elf", "Human"] } });
  await wrapper.get("button").trigger("click");
  await button(wrapper, "Human").trigger("mousedown");
  await wrapper.get("input").trigger("blur", { relatedTarget: button(wrapper, "Human").element });
  expect(wrapper.findAll("button")).toHaveLength(3);
  await button(wrapper, "Human").trigger("click");
  expect(wrapper.emitted("update:modelValue")?.[0]).toEqual(["Human"]);
  await wrapper.get("input").setValue("Custom");
  await wrapper.get("input").trigger("blur", { relatedTarget: null });
  expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual(["Custom"]);
});
it("enforces tag input limits and emits suggestion/removal actions", async () => {
  const wrapper = mount(TagInput, {
    props: { tags: [], suggestions: ["Fantasy", "Magic"], max: 1 },
  });
  await wrapper.get("input").trigger("keydown", { key: "Enter" });
  expect(wrapper.emitted("add")).toBeUndefined();
  await wrapper.get("input").setValue(" Lore ");
  await wrapper.get("input").trigger("keydown", { key: "x" });
  await wrapper.get("input").trigger("keydown", { key: "Enter" });
  expect(wrapper.emitted("add")?.[0]).toEqual(["Lore"]);
  await button(wrapper, "Magic").trigger("click");
  await wrapper.setProps({ tags: ["Lore"] });
  expect(wrapper.find("input").exists()).toBe(false);
  await wrapper.get('button[aria-label="Remove tag Lore"]').trigger("click");
  expect(wrapper.emitted("remove")?.[0]).toEqual(["Lore"]);
});
it("deduplicates lore keywords and emits edits without mutating incoming data", async () => {
  const entry = {
    id: "entry",
    keywords: ["one", "two", "three", "four"],
    content: "Lore",
    enabled: true,
  };
  const wrapper = mount(LorebookEntryCard, { props: { entry, index: 1 } });
  expect(wrapper.text()).toContain("+1");
  const input = wrapper.get("input");
  await input.setValue("one");
  await input.trigger("keydown", { key: "Enter" });
  expect(wrapper.emitted("update")).toBeUndefined();
  await input.setValue("five");
  await input.trigger("keydown", { key: "Enter" });
  expect(wrapper.emitted("update")?.[0]).toEqual([
    "entry",
    { keywords: ["one", "two", "three", "four", "five"] },
  ]);
  await wrapper.findAll('button[aria-label^="Remove keyword"]')[0]!.trigger("click");
  await wrapper.get("textarea").setValue("New lore");
  expect(entry.content).toBe("Lore");
  await wrapper.get('button[aria-label="Disable entry"]').trigger("click");
  await wrapper.setProps({ entry: { ...entry, enabled: false } });
  await wrapper.get('button[aria-label="Enable entry"]').trigger("click");
});
