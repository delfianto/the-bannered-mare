import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import { DEFAULT_CHAT_FONT, DEFAULT_TYPOGRAPHY_PRESET, useTypography } from "../useTypography";

const typography = useTypography();

afterEach(async () => {
  typography.setTypographyPreset(DEFAULT_TYPOGRAPHY_PRESET);
  typography.setChatFont(DEFAULT_CHAT_FONT);
  typography.setNarrativeItalics(false);
  await nextTick();
});

describe("useTypography", () => {
  it("applies and persists the selected typography preferences", async () => {
    typography.setTypographyPreset("literary");
    typography.setChatFont("inter");
    typography.setNarrativeItalics(true);
    await nextTick();

    expect(document.documentElement.dataset.typography).toBe("literary");
    expect(document.documentElement.dataset.chatFont).toBe("inter");
    expect(document.documentElement.dataset.narrativeItalics).toBe("true");
    expect(localStorage.getItem("typography-preset")).toBe("literary");
    expect(localStorage.getItem("chat-font")).toBe("inter");
    expect(localStorage.getItem("narrative-italics")).toBe("true");
  });
});
