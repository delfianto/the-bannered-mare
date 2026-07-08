# Core Components

This page outlines The Bannered Mare's frontend component architecture — Vue 3 components
styled with Tailwind CSS and DaisyUI 5 primitives.


## 1. App Shell and Navigation Layout

### `AppShell.vue` and `AppSidebar.vue`

- **`AppShell.vue`**: The root layout — a flex row holding `AppSidebar` and a `<main>` scroll container that renders the active `<RouterView />`.
- **`AppSidebar.vue`**: The fixed left navigation rail. It collapses/expands between an icon rail (68px) and the full panel (260px); the collapsed state comes from `useSidebar()` and is toggled by clicking the brand flame button.
- **Sidebar Actions**:
  - Exposes the main navigation entries: **Home**, **Sessions** (`/chats`), **Discover** (`/characters`), **Lorebooks**, **Data Bank** (`/memory`), **Bookmarks**, **Connections**, and **Loadouts** (`/loadouts`, the profiles page).
  - Renders the app name as the **Brand Wordmark** using the `font-cinzel` heading font (the `font-medieval` BlackChancery face is used elsewhere for the wordmark).
  - Shows a **Favorites** list of recent bookmarked sessions (avatars linking straight into a chat).
  - Footer holds the **Settings** link and the **Theme Switcher** — a custom toggle button (not `USwitch`) wired to `useTheme().toggleTheme()`.


## 2. Message and Narrative Rendering

### `MessageBubble.vue`

- **Role**: Renders chat history dialogue bubbles for both the user and assistant, including inline edit mode, per-message action icons, and swipe arrows / an alternative-count badge for assistant replies.
- **Narrative Rendering**: Delegates message text to `NarrativeText.vue` rather than parsing Markdown. `NarrativeText` splits the content with a regex into typed nodes — `*action*` (asterisk-wrapped stage directions), `"dialogue"` (quoted speech), and plain narration — and styles each differently. It does **not** use `markdown-it`, `dompurify`, or `v-html`; text is rendered through normal template bindings, so no HTML sanitization step is needed.
- **Note**: `markdown-it` and `dompurify` are still listed as dependencies but are not currently wired into the chat rendering path.


## 3. Specialized Parameter Input Handlers

### `ParamInput.vue`

- **Role**: A recursive component that dynamically renders the right input control from a parameter's schema definition (`schema.type`).
- **Type mapping**: Branches on the schema type:
  - **`boolean`** → toggle switch.
  - **enabled/disabled enum** → a two-state toggle (special-cased when an `enum` has exactly the `str_values` `enabled` / `disabled`).
  - **`enum`** → dropdown selector over `str_values`.
  - **`int` / `float` with `min_value` + `max_value`** → slider (step `0.01` for floats, `1` for ints).
  - **`int` / `float` without a range** → plain numeric input.
  - **`string`** → text input, or a textarea in the vertical layout.
  - **`list`** → a tag/row editor; a `list` of `object` items recurses into `ParamInput` per property.
  - **`object`** → recurses into `ParamInput` for each declared property.
  - **`json`** → a raw JSON text area.
  - Anything else falls through to an "Unsupported type" label.


## 4. Chat Input Elements

### `ParchmentInput.vue`

- **Role**: The primary chat message text area.
- **Features**:
  - **Auto-Grow**: Automatically grows in height as the user inputs multi-line messages, resetting upon submission.
  - **Fantasy Aesthetic**: Styled with cream borders, warm box shadows, and transition effects.
  - **Key Bindings**: Submits on `Enter` (unless `Shift+Enter` is pressed for a newline).


## 5. Modals and Action Banners

- **`ProfilePickerModal.vue`**: Shown when starting a new tale and more than one profile (loadout) exists. Lists the profiles with their resolved model and template names and emits the chosen `profileId`.
- **`ImportPresetModal.vue`**: Handles importing a SillyTavern preset JSON via file browse or drag-and-drop, driving `usePresetImport` and reporting the `STImportResult`.
- **`SetupPromptBanner.vue`**: Inline banner (rendered on Home) that nudges users to create their first profile when no profile with a model attached exists. It links to `/setup` and can be dismissed (persisted to `localStorage` under `"bannered-mare:setup-dismissed"`).
