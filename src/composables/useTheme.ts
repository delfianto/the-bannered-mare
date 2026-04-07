import { ref, watch } from "vue";

// Singleton state — shared across all components
const isDark = ref(false);
let initialized = false;

function init() {
  if (initialized) return;
  initialized = true;

  const stored = localStorage.getItem("theme-mode");
  if (
    stored === "dark" ||
    (!stored && typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches)
  ) {
    isDark.value = true;
  }

  // Keep DOM in sync
  syncDom(isDark.value);

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

export function useTheme() {
  init();

  function toggleTheme() {
    isDark.value = !isDark.value;
  }

  return { isDark, toggleTheme };
}
