import { afterEach, beforeEach, describe, expect, it, vi } from "vite-plus/test";
import { effectScope, nextTick, type EffectScope } from "vue";

let scope: EffectScope;
beforeEach(() => {
  vi.resetModules();
  localStorage.clear();
  scope = effectScope();
});
afterEach(() => {
  scope.stop();
  vi.useRealTimers();
  vi.restoreAllMocks();
  localStorage.clear();
  document.documentElement.removeAttribute("style");
  document.documentElement.removeAttribute("data-theme");
});

describe("persisted display preferences", () => {
  it.each([
    ["dark", true],
    ["light", false],
  ])("restores explicit %s mode before applying the saved palette", async (mode, dark) => {
    localStorage.setItem("theme-mode", mode);
    localStorage.setItem("color-scheme", "forest");
    const { useTheme } = await import("@/composables/useTheme");
    const api = scope.run(useTheme)!;
    expect(api.isDark.value).toBe(dark);
    expect(document.documentElement.dataset.theme).toBe(dark ? "tbm-forest-dark" : "tbm-forest");
    api.toggleTheme();
    await nextTick();
    expect(localStorage.getItem("theme-mode")).toBe(dark ? "light" : "dark");
    api.setColorScheme("rose");
    await nextTick();
    expect(localStorage.getItem("color-scheme")).toBe("rose");
    expect(document.documentElement.dataset.theme).toContain("tbm-rose");
  });

  it("uses the operating system preference only when no mode is stored", async () => {
    vi.spyOn(window, "matchMedia").mockReturnValue({ matches: true } as MediaQueryList);
    const { useTheme } = await import("@/composables/useTheme");
    const api = scope.run(useTheme)!;
    expect(api.isDark.value).toBe(true);
    expect(useTheme().isDark).toBe(api.isDark);
  });

  it("switching away from a custom palette removes its inline colors", async () => {
    const { useTheme } = await import("@/composables/useTheme");
    const api = scope.run(useTheme)!;
    api.setColorScheme("custom");
    await nextTick();
    expect(document.documentElement.style.getPropertyValue("--color-primary")).not.toBe("");
    api.setColorScheme("amber");
    await nextTick();
    expect(document.documentElement.style.getPropertyValue("--color-primary")).toBe("");
    expect(document.documentElement.dataset.theme).toBe("tbm-amber");
  });

  it.each([
    ["10", 14],
    ["40", 24],
    ["19.6", 20],
    ["invalid", 18],
  ])("restores and clamps font size %s", async (stored, expected) => {
    localStorage.setItem("font-size", stored);
    const { useFontSize } = await import("@/composables/useFontSize");
    const api = scope.run(useFontSize)!;
    expect(api.fontSize.value).toBe(expected);
    expect(document.documentElement.style.fontSize).toBe(`${expected}px`);
  });

  it("updates font size immediately and debounces disk writes while dragging", async () => {
    vi.useFakeTimers();
    const { useFontSize } = await import("@/composables/useFontSize");
    const api = scope.run(useFontSize)!;
    api.setFontSize(20);
    await nextTick();
    expect(document.documentElement.style.fontSize).toBe("20px");
    expect(localStorage.getItem("font-size")).toBeNull();
    vi.advanceTimersByTime(200);
    api.setFontSize(21);
    await nextTick();
    vi.advanceTimersByTime(249);
    expect(localStorage.getItem("font-size")).toBeNull();
    vi.advanceTimersByTime(1);
    expect(localStorage.getItem("font-size")).toBe("21");
    api.resetFontSize();
    await nextTick();
    vi.runAllTimers();
    expect(document.documentElement.style.fontSize).toBe("18px");
  });

  it("restores suggestion switches and shares subsequent changes between consumers", async () => {
    localStorage.setItem("setting-reply-suggestions", "false");
    localStorage.setItem("setting-auto-tones", "true");
    const { useSuggestionSettings } = await import("@/composables/useSuggestionSettings");
    const api = scope.run(useSuggestionSettings)!;
    expect(api.replySuggestionsEnabled.value).toBe(false);
    expect(api.autoGenerateTones.value).toBe(true);
    api.replySuggestionsEnabled.value = true;
    api.autoGenerateTones.value = false;
    await nextTick();
    expect(useSuggestionSettings().replySuggestionsEnabled.value).toBe(true);
    expect(localStorage.getItem("setting-reply-suggestions")).toBe("true");
    expect(localStorage.getItem("setting-auto-tones")).toBe("false");
  });

  it("restores sidebar collapse and persists toggles", async () => {
    localStorage.setItem("sidebar-collapsed", "true");
    const { useSidebar } = await import("@/composables/useSidebar");
    const api = useSidebar();
    expect(api.collapsed.value).toBe(true);
    api.toggle();
    await nextTick();
    expect(localStorage.getItem("sidebar-collapsed")).toBe("false");
    expect(useSidebar().collapsed.value).toBe(false);
  });

  it("corrupt custom-theme storage falls back to defaults and reset persists valid JSON", async () => {
    localStorage.setItem("custom-theme", "{");
    const { useCustomTheme } = await import("@/composables/useCustomTheme");
    const api = useCustomTheme();
    expect(api.custom.primary).toBe("#c9922e");
    api.set("primary", "#000000");
    expect(document.documentElement.style.getPropertyValue("--color-primary-content")).toBe(
      "#ffffff",
    );
    api.set("primary", "#ffffff");
    expect(document.documentElement.style.getPropertyValue("--color-primary-content")).toBe(
      "#0f0d0b",
    );
    api.reset();
    expect(JSON.parse(localStorage.getItem("custom-theme")!).primary).toBe("#c9922e");
  });

  it("loads a saved custom palette and chooses the matching browser color scheme", async () => {
    localStorage.setItem(
      "custom-theme",
      JSON.stringify({ base100: "#000000", primary: "#ff0000" }),
    );
    const { useCustomTheme, applyCustomTheme } = await import("@/composables/useCustomTheme");
    const api = useCustomTheme();
    applyCustomTheme();
    expect(api.custom.base100).toBe("#000000");
    expect(document.documentElement.style.colorScheme).toBe("dark");
  });
});
