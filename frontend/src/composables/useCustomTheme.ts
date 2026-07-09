import { reactive } from "vue";

// A user-authored DaisyUI theme. The five editable colors map to daisyUI's
// surface ladder + brand + text; the rest (primary-content, ring, border,
// input, muted-foreground) are derived. Applied at runtime as inline custom
// properties on <html> — CSS variables inherit + inline wins over the
// [data-theme] rule, so this overrides the tbm-custom base theme live.
export interface CustomTheme {
  primary: string;
  base100: string;
  base200: string;
  base300: string;
  baseContent: string;
}

const DEFAULT: CustomTheme = {
  primary: "#c9922e",
  base100: "#ffffff",
  base200: "#faf7f2",
  base300: "#f5f0e8",
  baseContent: "#2c2418",
};

const STORAGE_KEY = "custom-theme";

const custom = reactive<CustomTheme>({ ...DEFAULT });
let loaded = false;

function load() {
  if (loaded) return;
  loaded = true;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) Object.assign(custom, JSON.parse(raw));
  } catch {
    // Corrupt value — fall back to defaults.
  }
}

function luminance(hex: string): number {
  const c = hex.replace("#", "");
  if (c.length < 6) return 1;
  const chan = (i: number) => {
    const v = parseInt(c.slice(i, i + 2), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * chan(0) + 0.7152 * chan(2) + 0.0722 * chan(4);
}

/** Black or white, whichever reads better on the given color. */
function contrast(hex: string): string {
  return luminance(hex) > 0.5 ? "#0f0d0b" : "#ffffff";
}

const OVERRIDDEN_VARS = [
  "--color-base-100",
  "--color-base-200",
  "--color-base-300",
  "--color-base-content",
  "--color-primary",
  "--color-primary-content",
  "--color-ring",
  "--color-border",
  "--color-input",
  "--color-muted-foreground",
];

export function applyCustomTheme() {
  load();
  const el = document.documentElement;
  const s = el.style;
  s.setProperty("--color-base-100", custom.base100);
  s.setProperty("--color-base-200", custom.base200);
  s.setProperty("--color-base-300", custom.base300);
  s.setProperty("--color-base-content", custom.baseContent);
  s.setProperty("--color-primary", custom.primary);
  s.setProperty("--color-primary-content", contrast(custom.primary));
  s.setProperty("--color-ring", custom.primary);
  s.setProperty("--color-border", custom.base300);
  s.setProperty("--color-input", custom.base300);
  s.setProperty(
    "--color-muted-foreground",
    `color-mix(in srgb, ${custom.baseContent} 55%, ${custom.base100})`,
  );
  el.style.colorScheme = luminance(custom.base100) > 0.5 ? "light" : "dark";
}

export function clearCustomTheme() {
  const el = document.documentElement;
  OVERRIDDEN_VARS.forEach((v) => el.style.removeProperty(v));
  el.style.removeProperty("color-scheme");
}

export function useCustomTheme() {
  load();

  function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...custom }));
  }

  function set(key: keyof CustomTheme, value: string) {
    custom[key] = value;
    save();
    applyCustomTheme();
  }

  function reset() {
    Object.assign(custom, DEFAULT);
    save();
    applyCustomTheme();
  }

  return { custom, set, reset };
}
