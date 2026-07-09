import { ref, watch } from "vue";
import { applyCustomTheme, clearCustomTheme } from "./useCustomTheme";

// Singleton state — shared across all components
const isDark = ref(false);
const colorScheme = ref("amber");
let initialized = false;

const THEME_PREFIX = "tbm-";

function themeName(palette: string, dark: boolean) {
  return `${THEME_PREFIX}${palette}${dark ? "-dark" : ""}`;
}

function applyTheme() {
  // daisyUI switches themes via the data-theme attribute on <html>. The custom
  // theme uses a fixed name plus runtime inline color overrides (useCustomTheme).
  const el = document.documentElement;
  if (colorScheme.value === "custom") {
    el.dataset.theme = "tbm-custom";
    applyCustomTheme();
  } else {
    clearCustomTheme();
    el.dataset.theme = themeName(colorScheme.value, isDark.value);
  }
}

function init() {
  if (initialized) return;
  initialized = true;

  const storedMode = localStorage.getItem("theme-mode");
  if (
    storedMode === "dark" ||
    (!storedMode &&
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches)
  ) {
    isDark.value = true;
  }

  const storedScheme = localStorage.getItem("color-scheme");
  if (storedScheme) {
    colorScheme.value = storedScheme;
  }

  applyTheme();

  watch([isDark, colorScheme], () => {
    applyTheme();
    localStorage.setItem("theme-mode", isDark.value ? "dark" : "light");
  });
}

export function useTheme() {
  init();

  function toggleTheme() {
    isDark.value = !isDark.value;
  }

  function setColorScheme(presetId: string) {
    colorScheme.value = presetId;
    localStorage.setItem("color-scheme", presetId);
  }

  return { isDark, toggleTheme, colorScheme, setColorScheme };
}
