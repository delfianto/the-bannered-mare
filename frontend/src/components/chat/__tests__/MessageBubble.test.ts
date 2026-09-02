import { afterEach, describe, it, expect } from "vitest";
import { nextTick } from "vue";
import { mount } from "@vue/test-utils";
import MessageBubble from "../MessageBubble.vue";
import i18n from "@/i18n";
import { useTypography } from "@/composables/useTypography";
import type { Message } from "@/types/chat";

// Resolve labels through the same i18n instance the component uses, so selectors
// stay correct regardless of the active locale / exact wording.
const t = (key: string) => i18n.global.t(key);

afterEach(() => {
  useTypography().setNarrativeItalics(false);
});

function makeMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: "m1",
    chat_id: "c1",
    role: "assistant",
    content: "Hail, traveler.",
    active_index: 0,
    created_at: "2026-07-16T12:00:00Z",
    ...overrides,
  };
}

// Smoke tests on a real risk-surface component. Proves the mount harness
// carries i18n + the global primitives (AppIcon), and pins the emit contract
// ChatView depends on (edit / action / swipe).
describe("MessageBubble", () => {
  it("renders an assistant message's content, name, and action buttons", () => {
    const wrapper = mount(MessageBubble, {
      props: { message: makeMessage(), index: 0, characterName: "Lydia" },
    });
    expect(wrapper.text()).toContain("Hail, traveler.");
    expect(wrapper.text()).toContain("Lydia");
    expect(wrapper.find(`button[title="${t("chat.actions.regenerate")}"]`).exists()).toBe(true);
  });

  it("emits `action` with the message id + key when a character action is clicked", async () => {
    const wrapper = mount(MessageBubble, {
      props: { message: makeMessage({ id: "abc" }), index: 0, characterName: "Lydia" },
    });
    await wrapper.get(`button[title="${t("chat.actions.regenerate")}"]`).trigger("click");
    expect(wrapper.emitted("action")?.[0]).toEqual(["abc", "regen"]);
  });

  it("enters inline edit on a user message and emits `edit` with the new content", async () => {
    const wrapper = mount(MessageBubble, {
      props: { message: makeMessage({ id: "u1", role: "user", content: "old" }), index: 1 },
    });
    await wrapper.get(`button[title="${t("chat.actions.edit")}"]`).trigger("click");
    await wrapper.get("textarea").setValue("new tale");
    const save = wrapper.findAll("button").find((b) => b.text() === t("common.save"));
    await save!.trigger("click");
    expect(wrapper.emitted("edit")?.[0]).toEqual(["u1", "new tale"]);
  });

  it("keeps action markup upright in long-form chat", () => {
    const wrapper = mount(MessageBubble, {
      props: {
        message: makeMessage({ content: "*She opens the old journal.*" }),
        index: 1,
      },
    });

    expect(wrapper.text()).toContain("She opens the old journal.");
    expect(wrapper.find(".italic").exists()).toBe(false);
  });

  it("can render model narration in italics when the preference is enabled", async () => {
    const typography = useTypography();
    typography.setNarrativeItalics(true);
    await nextTick();

    const wrapper = mount(MessageBubble, {
      props: {
        message: makeMessage({ content: "*She opens the old journal.*" }),
        index: 1,
      },
    });

    expect(wrapper.get(".italic").text()).toBe("She opens the old journal.");
  });

  it("shows swipe arrows and emits `swipe` when alternatives exist", async () => {
    const wrapper = mount(MessageBubble, {
      props: {
        message: makeMessage({ id: "a2" }),
        index: 0,
        characterName: "Lydia",
        alternativeCount: 3,
        currentAltIndex: 0,
      },
    });
    await wrapper.get(`button[aria-label="${t("chat.swipe.next")}"]`).trigger("click");
    expect(wrapper.emitted("swipe")?.[0]).toEqual(["a2", "right"]);
  });
});
