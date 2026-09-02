# Theme and Design Tokens

## Compact token summary

- Stack: Tailwind CSS v4 via Vite + DaisyUI 5.
- Theme switching: `data-theme="tbm-<palette>[-dark]"`; no global `.dark` class.
- Palettes: Amber Dawn, Emerald Glade, Sapphire Archive, Crimson Sanctum, Violet Arcane, Obsidian Night, plus Custom.
- Default light: base-100/base-200 `#fff`, base-300 `#f5f0e8`, content `#2c2418`, primary `#c9922e`.
- Default dark: base-100 `#0f0d0b`, base-200 `#1e1b17`, base-300 `#2a2520`, content `#e8dfd0`, primary `#d4a544`.
- Fonts: Inter for UI/body, Cinzel for display/headings, local BlackChancery for the brand wordmark only.
- Root spacing follows Tailwind's 0.25rem scale and responds to the user-configurable root font size (14–24px, default 18px).
- Radius: `--radius-md: .5rem`, `--radius-lg: .625rem`, `--radius-xl: .875rem`, `--radius-2xl: 1rem`.
- Shadows: restrained surface shadows; image cards add deeper warm primary-tinted hover shadows.
- Motion: 200–400ms transitions, fade-in-up entrance, reduced-motion override.
- Breakpoints: Tailwind defaults; sidebar appears at `lg`, content commonly expands at `sm` and `lg`.
- Reusable utilities: `app-card`, `input-field`, `focus-ring`, `scrollbar-hide`.

## Raw source: main.css

```css
@import url("https://fonts.googleapis.com/css2?family=Cinzel:wght@400;500;600;700&display=swap");
@import "tailwindcss";
@plugin "daisyui" {
  logs: false;
}
@import "./themes.css";

/* BlackChancery — brand wordmark only */
@font-face {
  font-family: "BlackChancery";
  src: url("./blackchancery.ttf") format("truetype");
  font-weight: normal;
  font-style: normal;
  font-display: swap;
}

/* dark: variant keyed off the active theme's -dark suffix (no .dark class) */
@custom-variant dark (&:where([data-theme$="-dark"], [data-theme$="-dark"] *));

@theme {
  --font-medieval: "BlackChancery", serif;
  --font-cinzel: "Cinzel", Georgia, serif;

  /* Micro font-size scale, extending Tailwind's text-xs (0.75rem) downward for
     the sub-xs sizes the UI uses on badges, chips and meta labels — plus one
     step below text-sm. Font-size only (no paired --text-*--line-height), so
     line-height still inherits exactly like the bare arbitrary sizes they replace;
     rem-based, so they scale with the Text Size setting.
       2xs 0.6875rem/11px · 3xs 0.625rem/10px · 4xs 0.5625rem/9px
       5xs 0.5rem/8px · 2sm 0.8125rem/13px */
  --text-2xs: 0.6875rem;
  --text-3xs: 0.625rem;
  --text-4xs: 0.5625rem;
  --text-5xs: 0.5rem;
  --text-2sm: 0.8125rem;

  /* Preserve the app's rounded-* scale (independent of daisyUI's --radius-*) */
  --radius-sm: calc(0.625rem - 4px);
  --radius-md: calc(0.625rem - 2px);
  --radius-lg: 0.625rem;
  --radius-xl: calc(0.625rem + 4px);

  /* Staggered entry animation */
  --animate-fade-in-up: fade-in-up 0.45s cubic-bezier(0.16, 1, 0.3, 1) both;

  @keyframes fade-in-up {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
}

/* ── Retained tokens ──
   daisyUI has no equivalent for these, so the app keeps them: the muted
   foreground tone, the hairline border/input color, and the focus ring — each
   emitted per-theme in themes.css. Plus a `foreground` alias so the app's
   text-foreground / bg-foreground read daisyUI's base-content. */
@theme inline {
  --color-foreground: var(--color-base-content);
  --color-muted-foreground: var(--color-muted-foreground);
  --color-border: var(--color-border);
  --color-input: var(--color-input);
  --color-ring: var(--color-ring);
  /* Spoken dialogue in RP chat — the text colour tinted toward the theme
     accent, so it reads as a distinct hue while staying legible. Derived, so
     it adapts to every palette (and the custom theme) automatically. */
  --color-dialogue: color-mix(in oklab, var(--color-primary) 50%, var(--color-base-content));
}

/* Focus ring — the app-wide control focus shadow, one definition.
   Variant-agnostic (Tailwind v4 utilities compose with variants at the call
   site); used as `focus:focus-ring`, the only current usage. */
@utility focus-ring {
  @apply shadow-[0_0_0_3px_var(--color-primary)/0.08];
}

/* Input field — the app-wide single-line text-input styling, one definition
  . Builds on `focus-ring`; add `font-mono` / `pr-10` at the call site
   for the variants. */
@utility input-field {
  @apply h-11 w-full rounded-lg border bg-base-300/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:focus-ring;
}

/* Card — the app-wide raised-surface panel, one definition. Named
   `app-card` (not `card`) to avoid colliding with DaisyUI's `.card` component.
   Add hover states / extra padding at the call site. */
@utility app-card {
  @apply rounded-xl border bg-base-200/50 p-4;
}

@layer base {
  *,
  ::after,
  ::before {
    border-color: var(--color-border);
  }
  body {
    background-color: var(--color-base-100);
    color: var(--color-base-content);
    scrollbar-gutter: stable;
  }
}

/* ── Scrollbar ── */
@layer base {
  * {
    scrollbar-width: thin;
    scrollbar-color: color-mix(in srgb, var(--color-muted-foreground) 30%, transparent) transparent;
  }

  ::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }

  ::-webkit-scrollbar-track {
    background: transparent;
  }

  ::-webkit-scrollbar-thumb {
    background: color-mix(in srgb, var(--color-muted-foreground) 30%, transparent);
    border-radius: 10px;
  }

  ::-webkit-scrollbar-thumb:hover {
    background: color-mix(in srgb, var(--color-muted-foreground) 50%, transparent);
  }
}

/* ── Utility: hide scrollbar (for horizontal scroll sections) ── */
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}

/* ── Focus: visible keyboard focus ring on all buttons ── */
@layer base {
  button:focus-visible,
  [role="button"]:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }
}

/* ── Accessibility: respect reduced motion preference ── */
@media (prefers-reduced-motion: reduce) {
  *,
  ::before,
  ::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}

```

## Raw source: themes.css

```css
/* ══ The Bannered Mare — daisyUI themes ══
   One theme per palette × mode, switched at runtime via data-theme (useTheme.ts).
   base-100/200/300 are the surface ladder; border/input/ring/muted-foreground
   are retained (non-daisyUI) tokens the app still relies on. secondary/accent/
   neutral are brand slots (currently unused by the app — the bridge maps the
   app's bg-secondary/bg-accent to base surfaces). */

/* ── Amber Dawn (default) ── */
@plugin "daisyui/theme" {
  name: "tbm-amber";
  default: true;
  color-scheme: light;
  --color-base-100: #ffffff;
  --color-base-200: #ffffff;
  --color-base-300: #f5f0e8;
  --color-base-content: #2c2418;
  --color-primary: #c9922e;
  --color-primary-content: #ffffff;
  --color-secondary: #c9922e;
  --color-secondary-content: #ffffff;
  --color-accent: #c9922e;
  --color-accent-content: #ffffff;
  --color-neutral: #2c2418;
  --color-neutral-content: #ffffff;
  --color-info: #4a7aaf;
  --color-info-content: #ffffff;
  --color-success: #5c8a6c;
  --color-success-content: #ffffff;
  --color-warning: #c9922e;
  --color-warning-content: #ffffff;
  --color-error: #b84233;
  --color-error-content: #ffffff;
  --color-border: #e8dfd0;
  --color-input: #e8dfd0;
  --color-ring: #c9922e;
  --color-muted-foreground: #7a6e5d;
  --radius-selector: 0.625rem;
  --radius-field: 0.625rem;
  --radius-box: 0.875rem;
  --size-selector: 0.25rem;
  --size-field: 0.25rem;
  --border: 1px;
  --depth: 0;
  --noise: 0;
}
@plugin "daisyui/theme" {
  name: "tbm-amber-dark";
  prefersdark: true;
  color-scheme: dark;
  --color-base-100: #0f0d0b;
  --color-base-200: #1e1b17;
  --color-base-300: #2a2520;
  --color-base-content: #e8dfd0;
  --color-primary: #d4a544;
  --color-primary-content: #0f0d0b;
  --color-secondary: #d4a544;
  --color-secondary-content: #0f0d0b;
  --color-accent: #d4a544;
  --color-accent-content: #0f0d0b;
  --color-neutral: #e8dfd0;
  --color-neutral-content: #0f0d0b;
  --color-info: #6a9ad0;
  --color-info-content: #0f0d0b;
  --color-success: #7aae8a;
  --color-success-content: #0f0d0b;
  --color-warning: #d4a544;
  --color-warning-content: #0f0d0b;
  --color-error: #d45b4f;
  --color-error-content: #0f0d0b;
  --color-border: #2a2520;
  --color-input: #2a2520;
  --color-ring: #d4a544;
  --color-muted-foreground: #9b8e7a;
  --radius-selector: 0.625rem;
  --radius-field: 0.625rem;
  --radius-box: 0.875rem;
  --size-selector: 0.25rem;
  --size-field: 0.25rem;
  --border: 1px;
  --depth: 0;
  --noise: 0;
}

/* ── Emerald Glade ── */
@plugin "daisyui/theme" {
  name: "tbm-emerald";
  color-scheme: light;
  --color-base-100: #fafaf8;
  --color-base-200: #ffffff;
  --color-base-300: #eaeae4;
  --color-base-content: #2a2a24;
  --color-primary: #5c8a6c;
  --color-primary-content: #ffffff;
  --color-secondary: #5c8a6c;
  --color-secondary-content: #ffffff;
  --color-accent: #5c8a6c;
  --color-accent-content: #ffffff;
  --color-neutral: #2a2a24;
  --color-neutral-content: #ffffff;
  --color-info: #4a7aaf;
  --color-info-content: #ffffff;
  --color-success: #5c8a6c;
  --color-success-content: #ffffff;
  --color-warning: #c9922e;
  --color-warning-content: #ffffff;
  --color-error: #b84233;
  --color-error-content: #ffffff;
  --color-border: #ddddd6;
  --color-input: #ddddd6;
  --color-ring: #5c8a6c;
  --color-muted-foreground: #7a7a70;
  --radius-selector: 0.625rem;
  --radius-field: 0.625rem;
  --radius-box: 0.875rem;
  --size-selector: 0.25rem;
  --size-field: 0.25rem;
  --border: 1px;
  --depth: 0;
  --noise: 0;
}
@plugin "daisyui/theme" {
  name: "tbm-emerald-dark";
  color-scheme: dark;
  --color-base-100: #0e0e0c;
  --color-base-200: #1a1a17;
  --color-base-300: #242420;
  --color-base-content: #d4d4cc;
  --color-primary: #7aae8a;
  --color-primary-content: #0e0e0c;
  --color-secondary: #7aae8a;
  --color-secondary-content: #0e0e0c;
  --color-accent: #7aae8a;
  --color-accent-content: #0e0e0c;
  --color-neutral: #d4d4cc;
  --color-neutral-content: #0e0e0c;
  --color-info: #6a9ad0;
  --color-info-content: #0e0e0c;
  --color-success: #7aae8a;
  --color-success-content: #0e0e0c;
  --color-warning: #d4a544;
  --color-warning-content: #0e0e0c;
  --color-error: #d45b4f;
  --color-error-content: #0e0e0c;
  --color-border: #242420;
  --color-input: #242420;
  --color-ring: #7aae8a;
  --color-muted-foreground: #8a8a80;
  --radius-selector: 0.625rem;
  --radius-field: 0.625rem;
  --radius-box: 0.875rem;
  --size-selector: 0.25rem;
  --size-field: 0.25rem;
  --border: 1px;
  --depth: 0;
  --noise: 0;
}

/* ── Sapphire Archive ── */
@plugin "daisyui/theme" {
  name: "tbm-sapphire";
  color-scheme: light;
  --color-base-100: #f9f9f8;
  --color-base-200: #ffffff;
  --color-base-300: #e6e6e2;
  --color-base-content: #1e2430;
  --color-primary: #4a7aaf;
  --color-primary-content: #ffffff;
  --color-secondary: #4a7aaf;
  --color-secondary-content: #ffffff;
  --color-accent: #4a7aaf;
  --color-accent-content: #ffffff;
  --color-neutral: #1e2430;
  --color-neutral-content: #ffffff;
  --color-info: #4a7aaf;
  --color-info-content: #ffffff;
  --color-success: #5c8a6c;
  --color-success-content: #ffffff;
  --color-warning: #c9922e;
  --color-warning-content: #ffffff;
  --color-error: #b84233;
  --color-error-content: #ffffff;
  --color-border: #dadad6;
  --color-input: #dadad6;
  --color-ring: #4a7aaf;
  --color-muted-foreground: #6a7080;
  --radius-selector: 0.625rem;
  --radius-field: 0.625rem;
  --radius-box: 0.875rem;
  --size-selector: 0.25rem;
  --size-field: 0.25rem;
  --border: 1px;
  --depth: 0;
  --noise: 0;
}
@plugin "daisyui/theme" {
  name: "tbm-sapphire-dark";
  color-scheme: dark;
  --color-base-100: #0c0d10;
  --color-base-200: #14161c;
  --color-base-300: #1c1e26;
  --color-base-content: #ccd2dc;
  --color-primary: #6a9ad0;
  --color-primary-content: #0c0d10;
  --color-secondary: #6a9ad0;
  --color-secondary-content: #0c0d10;
  --color-accent: #6a9ad0;
  --color-accent-content: #0c0d10;
  --color-neutral: #ccd2dc;
  --color-neutral-content: #0c0d10;
  --color-info: #6a9ad0;
  --color-info-content: #0c0d10;
  --color-success: #7aae8a;
  --color-success-content: #0c0d10;
  --color-warning: #d4a544;
  --color-warning-content: #0c0d10;
  --color-error: #d45b4f;
  --color-error-content: #0c0d10;
  --color-border: #1c1e26;
  --color-input: #1c1e26;
  --color-ring: #6a9ad0;
  --color-muted-foreground: #7a8090;
  --radius-selector: 0.625rem;
  --radius-field: 0.625rem;
  --radius-box: 0.875rem;
  --size-selector: 0.25rem;
  --size-field: 0.25rem;
  --border: 1px;
  --depth: 0;
  --noise: 0;
}

/* ── Crimson Sanctum ── */
@plugin "daisyui/theme" {
  name: "tbm-crimson";
  color-scheme: light;
  --color-base-100: #faf9f8;
  --color-base-200: #ffffff;
  --color-base-300: #ebe6e4;
  --color-base-content: #2c2424;
  --color-primary: #8b4d50;
  --color-primary-content: #ffffff;
  --color-secondary: #8b4d50;
  --color-secondary-content: #ffffff;
  --color-accent: #8b4d50;
  --color-accent-content: #ffffff;
  --color-neutral: #2c2424;
  --color-neutral-content: #ffffff;
  --color-info: #4a7aaf;
  --color-info-content: #ffffff;
  --color-success: #5c8a6c;
  --color-success-content: #ffffff;
  --color-warning: #c9922e;
  --color-warning-content: #ffffff;
  --color-error: #b84233;
  --color-error-content: #ffffff;
  --color-border: #ded7d4;
  --color-input: #ded7d4;
  --color-ring: #8b4d50;
  --color-muted-foreground: #7a6e6e;
  --radius-selector: 0.625rem;
  --radius-field: 0.625rem;
  --radius-box: 0.875rem;
  --size-selector: 0.25rem;
  --size-field: 0.25rem;
  --border: 1px;
  --depth: 0;
  --noise: 0;
}
@plugin "daisyui/theme" {
  name: "tbm-crimson-dark";
  color-scheme: dark;
  --color-base-100: #100c0c;
  --color-base-200: #1c1616;
  --color-base-300: #262020;
  --color-base-content: #d8cccc;
  --color-primary: #b06b6e;
  --color-primary-content: #100c0c;
  --color-secondary: #b06b6e;
  --color-secondary-content: #100c0c;
  --color-accent: #b06b6e;
  --color-accent-content: #100c0c;
  --color-neutral: #d8cccc;
  --color-neutral-content: #100c0c;
  --color-info: #6a9ad0;
  --color-info-content: #100c0c;
  --color-success: #7aae8a;
  --color-success-content: #100c0c;
  --color-warning: #d4a544;
  --color-warning-content: #100c0c;
  --color-error: #d45b4f;
  --color-error-content: #100c0c;
  --color-border: #262020;
  --color-input: #262020;
  --color-ring: #b06b6e;
  --color-muted-foreground: #8a7e7e;
  --radius-selector: 0.625rem;
  --radius-field: 0.625rem;
  --radius-box: 0.875rem;
  --size-selector: 0.25rem;
  --size-field: 0.25rem;
  --border: 1px;
  --depth: 0;
  --noise: 0;
}

/* ── Violet Arcane ── */
@plugin "daisyui/theme" {
  name: "tbm-violet";
  color-scheme: light;
  --color-base-100: #faf9fb;
  --color-base-200: #ffffff;
  --color-base-300: #eaeaf0;
  --color-base-content: #22202c;
  --color-primary: #6e64a8;
  --color-primary-content: #ffffff;
  --color-secondary: #6e64a8;
  --color-secondary-content: #ffffff;
  --color-accent: #6e64a8;
  --color-accent-content: #ffffff;
  --color-neutral: #22202c;
  --color-neutral-content: #ffffff;
  --color-info: #4a7aaf;
  --color-info-content: #ffffff;
  --color-success: #5c8a6c;
  --color-success-content: #ffffff;
  --color-warning: #c9922e;
  --color-warning-content: #ffffff;
  --color-error: #b84233;
  --color-error-content: #ffffff;
  --color-border: #dddce6;
  --color-input: #dddce6;
  --color-ring: #6e64a8;
  --color-muted-foreground: #706e80;
  --radius-selector: 0.625rem;
  --radius-field: 0.625rem;
  --radius-box: 0.875rem;
  --size-selector: 0.25rem;
  --size-field: 0.25rem;
  --border: 1px;
  --depth: 0;
  --noise: 0;
}
@plugin "daisyui/theme" {
  name: "tbm-violet-dark";
  color-scheme: dark;
  --color-base-100: #0d0c10;
  --color-base-200: #16151c;
  --color-base-300: #201f28;
  --color-base-content: #d2d0da;
  --color-primary: #8a82c4;
  --color-primary-content: #0d0c10;
  --color-secondary: #8a82c4;
  --color-secondary-content: #0d0c10;
  --color-accent: #8a82c4;
  --color-accent-content: #0d0c10;
  --color-neutral: #d2d0da;
  --color-neutral-content: #0d0c10;
  --color-info: #6a9ad0;
  --color-info-content: #0d0c10;
  --color-success: #7aae8a;
  --color-success-content: #0d0c10;
  --color-warning: #d4a544;
  --color-warning-content: #0d0c10;
  --color-error: #d45b4f;
  --color-error-content: #0d0c10;
  --color-border: #201f28;
  --color-input: #201f28;
  --color-ring: #8a82c4;
  --color-muted-foreground: #807e90;
  --radius-selector: 0.625rem;
  --radius-field: 0.625rem;
  --radius-box: 0.875rem;
  --size-selector: 0.25rem;
  --size-field: 0.25rem;
  --border: 1px;
  --depth: 0;
  --noise: 0;
}

/* ── Obsidian Night ── */
@plugin "daisyui/theme" {
  name: "tbm-obsidian";
  color-scheme: light;
  --color-base-100: #f5f5f0;
  --color-base-200: #ffffff;
  --color-base-300: #e5e3de;
  --color-base-content: #1c1c1c;
  --color-primary: #a0926b;
  --color-primary-content: #ffffff;
  --color-secondary: #a0926b;
  --color-secondary-content: #ffffff;
  --color-accent: #a0926b;
  --color-accent-content: #ffffff;
  --color-neutral: #1c1c1c;
  --color-neutral-content: #ffffff;
  --color-info: #4a7aaf;
  --color-info-content: #ffffff;
  --color-success: #5c8a6c;
  --color-success-content: #ffffff;
  --color-warning: #c9922e;
  --color-warning-content: #ffffff;
  --color-error: #b84233;
  --color-error-content: #ffffff;
  --color-border: #d8d5cd;
  --color-input: #d8d5cd;
  --color-ring: #a0926b;
  --color-muted-foreground: #7a7a70;
  --radius-selector: 0.625rem;
  --radius-field: 0.625rem;
  --radius-box: 0.875rem;
  --size-selector: 0.25rem;
  --size-field: 0.25rem;
  --border: 1px;
  --depth: 0;
  --noise: 0;
}
@plugin "daisyui/theme" {
  name: "tbm-obsidian-dark";
  color-scheme: dark;
  --color-base-100: #0c0c0c;
  --color-base-200: #161614;
  --color-base-300: #1e1e1c;
  --color-base-content: #d4d0c8;
  --color-primary: #c4b68a;
  --color-primary-content: #0c0c0c;
  --color-secondary: #c4b68a;
  --color-secondary-content: #0c0c0c;
  --color-accent: #c4b68a;
  --color-accent-content: #0c0c0c;
  --color-neutral: #d4d0c8;
  --color-neutral-content: #0c0c0c;
  --color-info: #6a9ad0;
  --color-info-content: #0c0c0c;
  --color-success: #7aae8a;
  --color-success-content: #0c0c0c;
  --color-warning: #d4a544;
  --color-warning-content: #0c0c0c;
  --color-error: #d45b4f;
  --color-error-content: #0c0c0c;
  --color-border: #1e1e1c;
  --color-input: #1e1e1c;
  --color-ring: #c4b68a;
  --color-muted-foreground: #8a8880;
  --radius-selector: 0.625rem;
  --radius-field: 0.625rem;
  --radius-box: 0.875rem;
  --size-selector: 0.25rem;
  --size-field: 0.25rem;
  --border: 1px;
  --depth: 0;
  --noise: 0;
}

/* ── Custom (user-authored; colors overridden at runtime by useCustomTheme) ── */
@plugin "daisyui/theme" {
  name: "tbm-custom";
  color-scheme: light;
  --color-base-100: #ffffff;
  --color-base-200: #faf7f2;
  --color-base-300: #f5f0e8;
  --color-base-content: #2c2418;
  --color-primary: #c9922e;
  --color-primary-content: #ffffff;
  --color-secondary: #c9922e;
  --color-secondary-content: #ffffff;
  --color-accent: #c9922e;
  --color-accent-content: #ffffff;
  --color-neutral: #2c2418;
  --color-neutral-content: #ffffff;
  --color-info: #4a7aaf;
  --color-info-content: #ffffff;
  --color-success: #5c8a6c;
  --color-success-content: #ffffff;
  --color-warning: #c9922e;
  --color-warning-content: #ffffff;
  --color-error: #b84233;
  --color-error-content: #ffffff;
  --color-border: #e8dfd0;
  --color-input: #e8dfd0;
  --color-ring: #c9922e;
  --color-muted-foreground: #7a6e5d;
  --radius-selector: 0.625rem;
  --radius-field: 0.625rem;
  --radius-box: 0.875rem;
  --size-selector: 0.25rem;
  --size-field: 0.25rem;
  --border: 1px;
  --depth: 0;
  --noise: 0;
}

```

## Raw source: vite.config.ts

```ts
/// <reference types="vitest/config" />
import Terminal from "vite-plugin-terminal";
import ViteYaml from "@modyfi/vite-plugin-yaml";
import tailwindcss from "@tailwindcss/vite";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite-plus";
import { fileURLToPath, URL } from "node:url";

export default defineConfig(({ command }) => {
  const useMocks = process.env.VITE_USE_MOCKS === "true";
  console.log(
    `[vite config] VITE_USE_MOCKS=${process.env.VITE_USE_MOCKS}, proxy ${useMocks ? "DISABLED" : "ENABLED"}`,
  );

  return {
    plugins: [
      vue(),
      tailwindcss(),
      ViteYaml(),
      command === "serve" &&
        Terminal({
          console: "terminal",
          output: ["console", "terminal"],
        }),
    ],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
    server: {
      host: "0.0.0.0",
      port: 5173,
      // Disable proxy when using MSW mocks — let the service worker intercept instead
      proxy: useMocks
        ? undefined
        : {
            "/api": {
              target: "http://localhost:8000",
              changeOrigin: true,
            },
            // Admin/observability endpoints live at the server root, not under /api
            "/admin": {
              target: "http://localhost:8000",
              changeOrigin: true,
            },
          },
    },
    // `vp test` (Vitest) reuses this config's vue plugin + `@` alias, so SFCs
    // compile and mount. happy-dom supplies the DOM the UI layer needs.
    test: {
      environment: "happy-dom",
      globals: false,
      setupFiles: ["./src/test/setup-globals.ts", "./src/test/setup.ts"],
      include: ["src/**/*.{test,spec}.ts"],
      coverage: {
        provider: "v8",
        // `all` counts un-imported product files as 0%, so the number reflects
        // real coverage of the app — not just the handful of exercised modules.
        all: true,
        include: ["src/**/*.{ts,vue}"],
        exclude: [
          "src/**/*.{test,spec}.ts",
          "src/test/**",
          "src/mocks/**",
          "src/api/schema.d.ts",
          "src/**/*.d.ts",
          "src/main.ts",
          "src/types/**",
        ],
        reporter: ["text-summary", "json-summary"],
        // Floor ratchets up as coverage lands (Wave 2/3). Set just under the
        // current baseline (lines 2.66 / stmts 2.59 / fns 1.4 / branches 1.69)
        // so CI is honest and catches regressions without being red on day one.
        thresholds: { lines: 2.5, statements: 2.5, functions: 1.3, branches: 1.6 },
      },
    },
  };
});

```

## Raw source: useTheme.ts

```ts
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

```

## Raw source: colorPresets.ts

```ts
export interface ColorPreset {
  id: string;
  name: string;
  description: string;
  cssClass: string;
  preview: {
    primary: string;
    background: string;
    backgroundDark: string;
  };
}

export const COLOR_PRESETS: ColorPreset[] = [
  {
    id: "amber",
    name: "Amber Dawn",
    description: "Warm gold & parchment",
    cssClass: "",
    preview: { primary: "#C9922E", background: "#FFFFFF", backgroundDark: "#0F0D0B" },
  },
  {
    id: "emerald",
    name: "Emerald Glade",
    description: "Sage green & earth",
    cssClass: "theme-emerald",
    preview: { primary: "#5C8A6C", background: "#FAFAF8", backgroundDark: "#0E0E0C" },
  },
  {
    id: "sapphire",
    name: "Sapphire Archive",
    description: "Scholarly ink & paper",
    cssClass: "theme-sapphire",
    preview: { primary: "#4A7AAF", background: "#F9F9F8", backgroundDark: "#0C0D10" },
  },
  {
    id: "crimson",
    name: "Crimson Sanctum",
    description: "Wine & aged leather",
    cssClass: "theme-crimson",
    preview: { primary: "#8B4D50", background: "#FAF9F8", backgroundDark: "#100C0C" },
  },
  {
    id: "violet",
    name: "Violet Arcane",
    description: "Moonlight indigo",
    cssClass: "theme-violet",
    preview: { primary: "#6E64A8", background: "#FAF9FB", backgroundDark: "#0D0C10" },
  },
  {
    id: "obsidian",
    name: "Obsidian Night",
    description: "Antique bronze & shadow",
    cssClass: "theme-obsidian",
    preview: { primary: "#A0926B", background: "#F5F5F0", backgroundDark: "#0C0C0C" },
  },
];

```

