# Design System

The Bannered Mare wears a warm, literary fantasy aesthetic — parchment, walnut ink, and
medieval-library tones. It is built on **Tailwind CSS v4** and **DaisyUI 5**: DaisyUI supplies the
semantic colour tokens and component classes, and each palette is a DaisyUI theme switched at
runtime through the `data-theme` attribute.


## 1. Colour Tokens

DaisyUI themes expose a small set of semantic CSS variables that every component consumes via
utility classes (`bg-base-100`, `text-base-content`, `bg-primary`, `text-error`, …). The surface
"ladder" has three steps — `base-100` (page) → `base-200` (raised cards/panels) → `base-300`
(recessed fills / hover) — plus a `primary` brand colour. A few tokens DaisyUI does not provide are
**retained** for the app's needs: `--color-border` / `--color-input` (hairlines), `--color-ring`
(focus), and `--color-muted-foreground` (secondary text). The default **Amber Dawn** palette:

| Mode      | Token (utility)                      | Value                    | Visual role                              |
| :-------- | :----------------------------------- | :----------------------- | :--------------------------------------- |
| **Light** | `base-100` (`bg-base-100`)           | `#FFFFFF` (Parchment)    | Page background                          |
|           | `base-200` (`bg-base-200`)           | `#FFFFFF`                | Raised card / panel surface              |
|           | `base-300` (`bg-base-300`)           | `#F5F0E8`                | Recessed fills, hover states             |
|           | `base-content` (`text-base-content`) | `#2C2418` (Walnut Ink)   | Headings + body text                     |
|           | `primary` (`bg-primary`)             | `#C9922E` (Deep Gold)    | Focus rings, selections, primary buttons |
| **Dark**  | `base-100`                           | `#0F0D0B` (Deep Walnut)  | Page background                          |
|           | `base-200`                           | `#1E1B17`                | Raised card / panel surface              |
|           | `base-300`                           | `#2A2520`                | Recessed fills, hover states             |
|           | `base-content`                       | `#E8DFD0` (Soft Cream)   | Headings + body text                     |
|           | `primary`                            | `#D4A544` (Bright Amber) | Focus rings, selections, primary buttons |

- **Cards**: translucent raised surfaces (`bg-base-200/50`) over a fine hairline (`border`, whose colour comes from the retained `--color-border`) for a clean layered look.
- **Legacy aliases**: `text-foreground` is kept as an alias of `base-content` and `text-muted-foreground` as a retained token; everything else uses DaisyUI's vocabulary directly. Colours are defined in [main.css](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/assets/main.css).


## 2. Palettes (DaisyUI themes)

Amber is the default, but the app ships **six palettes**, each as a pair of DaisyUI themes
(`tbm-<palette>` and `tbm-<palette>-dark`) declared in
[themes.css](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/assets/themes.css)
and listed in `constants/colorPresets.ts`:

| Palette             | Feel                    |
| :------------------ | :---------------------- |
| **Amber Dawn**      | Warm gold & parchment (default) |
| **Emerald Glade**   | Sage green & earth      |
| **Sapphire Archive**| Scholarly ink & paper   |
| **Crimson Sanctum** | Wine & aged leather     |
| **Violet Arcane**   | Moonlight indigo        |
| **Obsidian Night**  | Antique bronze & shadow |

Switching is driven entirely by the `data-theme` attribute on `<html>` (e.g.
`data-theme="tbm-emerald-dark"`) — there is **no `.dark` class**. Tailwind's `dark:` variant is
re-pointed to match any active theme whose name ends in `-dark`, so `dark:` utilities keep working.


## 3. Typography

Three core font families are integrated:

1. **Cinzel** (`font-cinzel`):
   - **Role**: Classic serif display typeface, loaded from Google Fonts.
   - **Usage**: Main page headers, character card titles, section labels, and dialogue names.
2. **Inter** (Default):
   - **Role**: Highly legible clean sans-serif typeface.
   - **Usage**: Standard interface text, settings toggles, and code parameters.
3. **BlackChancery** (`font-medieval`):
   - **Role**: Script calligraphy medieval typeface, bundled locally via `@font-face` (`blackchancery.ttf`).
   - **Usage**: Reserved exclusively for the main brand wordmark "The Bannered Mare".


## 4. Theme State (`useTheme`)

Theme state is a singleton composable
([useTheme.ts](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/composables/useTheme.ts)):

- `useTheme()` holds a shared `isDark` boolean ref and a `colorScheme` string ref (module-level singletons).
- **Dark-mode persistence**: `localStorage["theme-mode"]` (`"dark"` / `"light"`); on first run with no stored value it falls back to the OS `prefers-color-scheme: dark` media query.
- **Palette persistence**: `localStorage["color-scheme"]` (the preset id, e.g. `emerald`).
- **DOM injection**: it computes the theme name from palette + mode and writes it to `document.documentElement.dataset.theme` (e.g. `tbm-crimson`, `tbm-amber-dark`). An inline snippet in `index.html` applies the stored theme **before paint** to avoid a flash of the default theme.


## 5. Theme Builder (custom palettes)

Beyond the six presets, users can **author their own palette** in-app. The **Interface** settings
tab shows a **Custom** card that opens a live editor
([ThemeEditor.vue](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/components/settings/ThemeEditor.vue))
with five colour pickers — primary, background, surface, muted, and text — backed by
[useCustomTheme.ts](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/composables/useCustomTheme.ts):

- Selecting **Custom** sets `data-theme="tbm-custom"` (a base theme in `themes.css`) and then applies the chosen colours as **inline CSS custom properties on `<html>`** (`--color-base-100`, `--color-primary`, …). Because CSS variables inherit and inline styles beat the theme rule, the whole app — DaisyUI components included — restyles **live** as you pick.
- Supporting tokens are **derived automatically**: `primary-content` (black or white by luminance, for readable text on the brand colour), `ring` (= primary), `border` / `input` (= the muted surface), and `muted-foreground` (a `color-mix` of text over background).
- The palette persists to `localStorage["custom-theme"]` and is restored before paint by the same no-flash snippet.

This mirrors how DaisyUI's own theme generator works (a named theme + a set of CSS variables), so a
hand-authored theme is indistinguishable from a built-in preset to the rest of the app.


## 6. UI Transitions and Animations

To increase the premium feel, the application applies soft transitions and entry movements:

- **Entry Animation**: `animate-fade-in-up` moves elements slightly upward while fading them in when views change.
- **Transitions**: Buttons and input borders fade dynamically using `transition-all duration-200` to prevent abrupt flashing when hovered or focused.
