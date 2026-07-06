# The Bannered Mare: State Management and Localization

This document explains the global state management patterns, persistence layers, data type mappings, and internationalization (i18n) setup inside The Bannered Mare.

---

## 1. Global State Management (Pinia)

App-wide state that crosses multiple feature layers is managed using **Pinia** (defined in [src/stores/](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/stores/)):

### `useSettingsStore`

- **Role**: Pre-fetches and caches static metadata to prevent redundant API queries.
- **Key State**:
  - `parameterDocs`: Stores parameter tooltips and detailed help data fetched from `/api/model-families/parameter-docs`.
  - `providers`: Stores the sorted list of active LLM provider connections fetched from `/api/providers`.

---

## 2. Shared State and local Persistence (Composables)

For UI states (such as active theme or sidebar view toggles), the application uses module-level singleton refs returned by composables:

- **`useTheme()`**: Manages the `isDark` state, saving it to `localStorage` under key `"theme:is-dark"`.
- **`useSidebar()`**: Manages the collapsed/expanded state of the main navigation drawer, saving it to `localStorage` under key `"sidebar:collapsed"`.

---

## 3. Data Types and Mappings (`src/types/`)

The Bannered Mare combines backend DTO schemas with frontend-specific types:

- **API Types**: Imported directly from `src/api/schema.d.ts` (e.g., `components["schemas"]["ChatResponse"]`).
- **Frontend Types**:
  - `DialoguePair` (used in character creator forms).
  - `MoodChip` (used in chat UI to customize dialogue triggers).
  - `LorebookEntry` (used in character card construction forms).

---

## 4. Internationalization (i18n)

The application supports multiple languages using `vue-i18n` (initialized in `src/i18n.ts`):

- **Translation Catalogs**: Stored as JSON files in [src/locales/](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/locales/):
  - `en.json` (English - authoritative key mapping reference)
  - `de.json` (German)
  - `es.json` (Spanish)
  - `fr.json` (French)
  - `pt.json` (Portuguese)
- **Interpolation**: Utilizes dynamic parameters (e.g. `{name}`, `{count}`) to format contextual labels at runtime.
