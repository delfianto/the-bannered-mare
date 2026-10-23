import { describe, expect, it } from "vite-plus/test";
import { mount } from "@vue/test-utils";
import LoreEntryForm from "../LoreEntryForm.vue";
import { lorebooks } from "@/mocks/data/lorebooks";
import { button } from "@/test/views";
import i18n from "@/i18n";
const t = (k: string) => i18n.global.t(k);

describe("lore entry form", () => {
  it("requires name and content, trims comma-separated keywords and emits typed defaults", async () => {
    const wrapper = mount(LoreEntryForm);
    expect(button(wrapper, t("lorebooks.entryForm.add")).element.disabled).toBe(true);
    await wrapper.findAll("input[type=text]")[0].setValue(" Name ");
    await wrapper.findAll("input[type=text]")[1].setValue(" dragon, , fire , ");
    await wrapper.get("textarea").setValue(" Lore ");
    await wrapper.get("select").setValue("at_depth");
    await button(wrapper, t("lorebooks.entryForm.add")).trigger("click");
    expect(wrapper.emitted("submit")?.[0]?.[0]).toMatchObject({
      name: "Name",
      content: "Lore",
      keys: ["dragon", "fire"],
      position: "at_depth",
      priority: 100,
      secondary_logic: "and_any",
      depth: 4,
      role: "system",
    });
  });

  it("editing visible fields preserves advanced matching settings", async () => {
    const entry = {
      ...lorebooks[0].entries[0],
      case_sensitive: true,
      use_regex: true,
      depth: 8,
      ignore_budget: true,
    };
    const wrapper = mount(LoreEntryForm, { props: { initial: entry } });
    await wrapper.get("textarea").setValue("Updated");
    await button(wrapper, t("lorebooks.entryForm.save")).trigger("click");
    expect(wrapper.emitted("submit")?.[0]?.[0]).toMatchObject({
      content: "Updated",
      case_sensitive: true,
      use_regex: true,
      secondary_keys: entry.secondary_keys,
      depth: 8,
      ignore_budget: true,
    });
  });

  it("reusing the editor for a new entry clears previously carried advanced fields", async () => {
    const wrapper = mount(LoreEntryForm, {
      props: { initial: { ...lorebooks[0].entries[0], use_regex: true, depth: 9 } },
    });
    await wrapper.setProps({ initial: null });
    await wrapper.findAll("input[type=text]")[0].setValue("Fresh");
    await wrapper.get("textarea").setValue("Fresh lore");
    await button(wrapper, t("lorebooks.entryForm.add")).trigger("click");
    expect(wrapper.emitted("submit")?.[0]?.[0]).toMatchObject({
      use_regex: false,
      depth: 4,
      secondary_keys: [],
    });
  });
});

it("emits switches, ordering and priority without altering advanced defaults, and supports cancel", async () => {
  const wrapper = mount(LoreEntryForm);
  await wrapper.findAll("input[type=text]")[0].setValue("Always included");
  await wrapper.get("textarea").setValue("Context");
  await wrapper.findAll("input[type=number]")[0].setValue("2");
  await wrapper.findAll("input[type=number]")[1].setValue("50");
  await wrapper.findAll("input[role=switch]")[0].setValue(false);
  await wrapper.findAll("input[role=switch]")[1].setValue(true);
  await button(wrapper, t("lorebooks.entryForm.add")).trigger("click");
  expect(wrapper.emitted("submit")?.[0]?.[0]).toMatchObject({
    enabled: false,
    constant: true,
    order: 2,
    priority: 50,
  });
  await button(wrapper, t("common.cancel")).trigger("click");
  expect(wrapper.emitted("cancel")).toHaveLength(1);
});
