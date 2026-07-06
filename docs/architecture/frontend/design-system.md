# The Bannered Mare: Design System and Aesthetics

The Bannered Mare is built with a warm, literary fantasy aesthetic designed to emulate parchment, walnut ink, and medieval library tones. This design system is built using CSS variables, custom typography, Tailwind CSS v4, and Nuxt UI v4 token configurations.

---

## 1. Color Palette Tokens

The primary theme uses **Amber** (`primary`) and **Stone** (`neutral`) color settings. Custom CSS colors are defined in [main.css](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/assets/main.css):

| Mode      | Token      | Value                       | Visual Role                      |
| :-------- | :--------- | :-------------------------- | :------------------------------- |
| **Light** | Background | `#FCF8F2` (Parchment)       | Screen base layer                |
|           | Text       | `#2C2418` (Walnut Ink)      | Headers and body text            |
|           | Primary    | `#C9922E` (Deep Gold)       | Focus rings, selections, buttons |
| **Dark**  | Background | `#0F0D0B` (Midnight Walnut) | Screen base layer                |
|           | Text       | `#E8DFD0` (Soft Cream)      | Headers and body text            |
|           | Primary    | `#D4A544` (Bright Amber)    | Focus rings, selections, buttons |

- **Cards**: Rendered with translucent backgrounds (`bg-card/50`) overlaying fine borders (`border-color: var(--color-border)`) to maintain a clean layered effect.

---

## 2. Typography

Three core font families are integrated:

1. **Cinzel** (`.font-cinzel`):
   - **Role**: Classic serif display typeface.
   - **Usage**: Main page headers, character card titles, section labels, and dialogues names.
2. **Inter** (Default):
   - **Role**: Highly legible clean sans-serif typeface.
   - **Usage**: Standard interface text, settings toggles, and code parameters.
3. **BlackChancery** (`.font-medieval`):
   - **Role**: Script calligraphy medieval typeface.
   - **Usage**: Reserved exclusively for the main brand wordmark logo "The Bannered Mare".

---

## 3. Theme State Management (`useTheme`)

The interface theme state is synchronized using a singleton composable:

- **Theming Composable**: `useTheme()` maintains a shared `isDark` boolean reference.
- **Persistence**: Saves state in the client's `localStorage` as `"theme:is-dark"`.
- **DOM Injection**: Appends or removes the `.dark` class directly on the HTML document root tag $\langle\text{html}\rangle$, allowing Tailwind dark selectors to activate instantly.

---

## 4. UI Transitions and Animations

To increase premium feel, the application applies soft transitions and entry movements:

- **Entry Animation**: `animate-fade-in-up` moves elements slightly upward while fading them in when views change.
- **Transitions**: Buttons and input borders fade dynamically using `transition-all duration-200` to prevent abrupt flashing when hovered or focused.
