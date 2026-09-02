import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, nextTick } from "vue";

beforeEach(() => {
  localStorage.clear();
  delete document.documentElement.dataset.typography;
  delete document.documentElement.dataset.chatFont;
  delete document.documentElement.dataset.narrativeItalics;
  vi.resetModules();
});

describe("useTypography", () => {
  it("applies and persists the selected typography preferences", async () => {
    const { useTypography } = await import("../useTypography");
    const typography = useTypography();

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

  it("keeps applying changes after its initializing component scope is destroyed", async () => {
    const { useTypography } = await import("../useTypography");
    const ownerScope = effectScope();
    const typography = ownerScope.run(() => useTypography());
    ownerScope.stop();

    typography?.setTypographyPreset("modern");
    await nextTick();

    expect(document.documentElement.dataset.typography).toBe("modern");
    expect(localStorage.getItem("typography-preset")).toBe("modern");
  });
});
