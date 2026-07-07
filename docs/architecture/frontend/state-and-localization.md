# State & Localization

This page covers the frontend's global state patterns, local persistence, data-type mappings,
and internationalization (i18n) setup.


## 1. Global State Management (Pinia)

App-wide state that crosses multiple feature layers is managed using **Pinia** (defined in [src/stores/](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/stores/)):

### `useSettingsStore`

- **Role**: Pre-fetches and caches static metadata to prevent redundant API queries.
- **Key State**:
  - `parameterDocs`: Stores parameter tooltips and detailed help data fetched from `/api/model-families/parameter-docs`.
  - `providers`: Stores the sorted list of active LLM provider connections fetched from `/api/providers`.


## 2. Shared State and Local Persistence (Composables)

For UI states (such as active theme or sidebar view toggles), the application uses module-level singleton refs returned by composables:

- **`useTheme()`**: Manages the `isDark` mode and the active `colorScheme`. The mode is saved to `localStorage` under key `"theme-mode"` (values `"dark"` / `"light"`, defaulting to the OS preference on first run); the palette is saved under key `"color-scheme"`.
- **`useSidebar()`**: Manages the collapsed/expanded state of the navigation rail (default collapsed), saving it to `localStorage` under key `"sidebar-collapsed"`.


## 3. Data Types and Mappings (`src/types/`)

The Bannered Mare combines backend DTO schemas with frontend-specific types:

- **API Types**: Imported directly from `src/api/schema.d.ts` (e.g., `components["schemas"]["ChatResponse"]`). Several `src/types/` modules re-export these under friendlier aliases — e.g. `chat.ts` (`Chat`, `Message`, `ChatCharacterInfo`) and `discover.ts` (`Character`).
- **Frontend Types**:
  - `MoodChip` — chat UI mood chips (`types/chat.ts`).
  - `DialoguePair`, `LorebookEntry`, `CharacterData`, `CreatorTab` — character creator forms (`types/creator.ts`).
  - `ViewMode`, `SortOption`, `FilterState` — library browsing state (`types/discover.ts`).
  - `yaml.d.ts` — module declaration so `.yaml` scenario files can be imported (mock harness).


## 4. Internationalization (i18n)

The application supports multiple languages using `vue-i18n` (initialized in `src/i18n.ts`):

- **Translation Catalogs**: Stored as JSON files in [src/locales/](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/locales/):
  - `en.json` (English - authoritative key mapping reference)
  - `de.json` (German)
  - `es.json` (Spanish)
  - `fr.json` (French)
  - `pt.json` (Portuguese)
- **Interpolation**: Utilizes dynamic parameters (e.g. `{name}`, `{count}`) to format contextual labels at runtime.
- **Active locale persistence**: The chosen locale is stored in `localStorage` under key `"locale"` (default `en`); `setLocale()` also updates the `<html lang>` attribute.
