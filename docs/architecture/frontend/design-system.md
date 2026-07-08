# Design System

The Bannered Mare wears a warm, literary fantasy aesthetic — parchment, walnut ink, and
medieval-library tones. The system is built from CSS variables, custom typography, Tailwind
CSS v4, and DaisyUI 5 token configuration.


## 1. Color Palette Tokens

The default theme uses **Amber** (`primary`) and **Stone** (`neutral`) color settings. Custom CSS colors are defined in [main.css](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/assets/main.css) (the default `:root` / `.dark` token sets):

| Mode      | Token      | Value                    | Visual Role                      |
| :-------- | :--------- | :----------------------- | :------------------------------- |
| **Light** | Background | `#FFFFFF` (Parchment)    | Screen base layer                |
|           | Text       | `#2C2418` (Walnut Ink)   | Headers and body text            |
|           | Primary    | `#C9922E` (Deep Gold)    | Focus rings, selections, buttons |
|           | Card       | `#FFFFFF`                | Card surfaces                    |
| **Dark**  | Background | `#0F0D0B` (Deep Walnut)  | Screen base layer                |
|           | Text       | `#E8DFD0` (Soft Cream)   | Headers and body text            |
|           | Primary    | `#D4A544` (Bright Amber) | Focus rings, selections, buttons |
|           | Card       | `#1E1B17`                | Card surfaces                    |

- **Cards**: Rendered with translucent backgrounds (`bg-card/50`) overlaying fine borders (`border-color: var(--color-border)`) to maintain a clean layered effect.

### Selectable Color Schemes

Amber is the default, but the interface ships alternate palettes defined in
[themes.css](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/assets/themes.css)
and listed in `constants/colorPresets.ts`: **Amber Dawn** (default, no class), **Emerald Glade**
(`theme-emerald`), **Sapphire Archive** (`theme-sapphire`), **Crimson Sanctum** (`theme-crimson`),
and **Violet** (`theme-violet`). Each preset overrides the token set via an `html.theme-*` class,
with matching light and `.dark` variants. `useTheme()` applies the chosen preset's `cssClass` to
`<html>` and persists the selection to `localStorage` under key `"color-scheme"`.


## 2. Typography

Three core font families are integrated:

1. **Cinzel** (`font-cinzel`):
   - **Role**: Classic serif display typeface, loaded from Google Fonts.
   - **Usage**: Main page headers, character card titles, section labels, and dialogue names.
2. **Inter** (Default):
   - **Role**: Highly legible clean sans-serif typeface.
   - **Usage**: Standard interface text, settings toggles, and code parameters.
3. **BlackChancery** (`font-medieval`):
   - **Role**: Script calligraphy medieval typeface, bundled locally via `@font-face` (`blackchancery.ttf`).
   - **Usage**: Reserved exclusively for the main brand wordmark logo "The Bannered Mare".


## 3. Theme State Management (`useTheme`)

The interface theme state is synchronized using a singleton composable
([useTheme.ts](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/composables/useTheme.ts)):

- **Theming Composable**: `useTheme()` maintains a shared `isDark` boolean ref and a `colorScheme` string ref (both module-level singletons).
- **Dark-mode persistence**: Saves the mode to `localStorage` under key `"theme-mode"` (values `"dark"` / `"light"`). On first run, with no stored value it falls back to the OS `prefers-color-scheme: dark` media query.
- **Color-scheme persistence**: Saves the active palette to `localStorage` under key `"color-scheme"`.
- **DOM Injection**: Adds or removes the `.dark` class directly on the `<html>` document root (so Tailwind's dark selectors activate instantly), and swaps the `theme-*` palette class for the chosen color scheme.


## 4. UI Transitions and Animations

To increase premium feel, the application applies soft transitions and entry movements:

- **Entry Animation**: `animate-fade-in-up` moves elements slightly upward while fading them in when views change.
- **Transitions**: Buttons and input borders fade dynamically using `transition-all duration-200` to prevent abrupt flashing when hovered or focused.
