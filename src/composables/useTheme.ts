import { ref, watch } from "vue";
import { COLOR_PRESETS } from "@/constants/colorPresets";

// Singleton state — shared across all components
const isDark = ref(false);
const colorScheme = ref("amber");
let initialized = false;

function init() {
  if (initialized) return;
  initialized = true;

  // Dark mode
  const storedMode = localStorage.getItem("theme-mode");
  if (
    storedMode === "dark" ||
    (!storedMode && typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches)
  ) {
    isDark.value = true;
  }

  // Color scheme
  const storedScheme = localStorage.getItem("color-scheme");
  if (storedScheme) {
    colorScheme.value = storedScheme;
  }

  // Apply initial state
  syncDom(isDark.value);
  applyColorScheme(colorScheme.value);

  watch(isDark, (val) => {
    syncDom(val);
    localStorage.setItem("theme-mode", val ? "dark" : "light");
  });
}

function syncDom(dark: boolean) {
  if (dark) {
    document.documentElement.classList.add("dark");
  } else {
    document.documentElement.classList.remove("dark");
  }
}

function applyColorScheme(presetId: string) {
  const el = document.documentElement;
  // Remove all theme classes
  el.classList.forEach((c) => {
    if (c.startsWith("theme-")) el.classList.remove(c);
  });
  // Apply new one (amber = no class, uses default :root/.dark)
  const preset = COLOR_PRESETS.find((p) => p.id === presetId);
  if (preset?.cssClass) {
    el.classList.add(preset.cssClass);
  }
}

export function useTheme() {
  init();

  function toggleTheme() {
    isDark.value = !isDark.value;
  }

  function setColorScheme(presetId: string) {
    colorScheme.value = presetId;
    localStorage.setItem("color-scheme", presetId);
    applyColorScheme(presetId);
  }

  return { isDark, toggleTheme, colorScheme, setColorScheme };
}
