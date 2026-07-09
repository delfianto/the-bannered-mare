import { ref, watch } from "vue";

// Root font size (px). Because the whole UI is sized in rem, this scales text
// AND spacing together — the same effect as browser zoom, but persisted per
// user. The default is a touch larger than the browser's 16px since this is a
// text-heavy, reading-first app.
export const DEFAULT_FONT_SIZE = 18;
export const MIN_FONT_SIZE = 14;
export const MAX_FONT_SIZE = 24;

const STORAGE_KEY = "font-size";

const fontSize = ref(DEFAULT_FONT_SIZE);
let initialized = false;

function clamp(px: number) {
  return Math.min(MAX_FONT_SIZE, Math.max(MIN_FONT_SIZE, Math.round(px)));
}

function apply() {
  document.documentElement.style.fontSize = `${fontSize.value}px`;
}

function init() {
  if (initialized) return;
  initialized = true;

  const stored = Number(localStorage.getItem(STORAGE_KEY));
  if (stored) fontSize.value = clamp(stored);

  apply();

  watch(fontSize, () => {
    apply();
    localStorage.setItem(STORAGE_KEY, String(fontSize.value));
  });
}

export function useFontSize() {
  init();

  function setFontSize(px: number) {
    fontSize.value = clamp(px);
  }

  function resetFontSize() {
    fontSize.value = DEFAULT_FONT_SIZE;
  }

  return { fontSize, setFontSize, resetFontSize };
}
