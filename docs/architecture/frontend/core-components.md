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
  - Footer holds the **Settings** link and the **Theme Switcher** — an `AppToggle` (DaisyUI `toggle`) when expanded, or an icon button when collapsed, wired to `useTheme().toggleTheme()`.


## 2. Message and Narrative Rendering

### `MessageBubble.vue`

- **Role**: Renders chat history dialogue bubbles for both the user and assistant, including inline edit mode, per-message action icons, and swipe arrows / an alternative-count badge for assistant replies.
- **Narrative Rendering**: Delegates message text to `NarrativeText.vue` rather than parsing Markdown. `NarrativeText` splits the content with a regex into typed nodes — `*action*` (asterisk-wrapped stage directions), `"dialogue"` (quoted speech), plain narration, `break` paragraph gaps, and `gfx` blocks (model-drawn HTML cards wrapped in `<!-- GFX_START -->…<!-- GFX_END -->` markers) — and styles each differently. It does **not** use `markdown-it`, but it **does** use `dompurify` and `v-html`: each `gfx` block is sanitized with `DOMPurify.sanitize` (a presentational tag/attr allowlist matching the backend's `nh3` config) and injected via `v-html`, while all other text is rendered through normal template bindings.
- **Note**: `markdown-it` is still listed as a dependency but is not currently wired into the chat rendering path; `dompurify` **is** in use — it sanitizes the `gfx` HTML blocks described above before injection.


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


## 6. Shared UI Primitives

DaisyUI is CSS-only, so the app's interactive building blocks live as a small set of shared Vue
components under `components/shared/`. **Three** are registered globally in `main.ts` (usable in
any template without an import) — `AppIcon`, `SelectMenu`, and `AppToggle`; the rest (e.g.
`AppTooltip`) are imported per-component from `@/components/shared/`:

- **`AppIcon`** (global): the single icon component, backed by `lucide-vue-next` (a name → component registry in `icons.ts`). Always `<AppIcon name="i-lucide-*" />` — never a raw icon `<span>`.
- **`SelectMenu`** (global): a searchable, teleported dropdown — the replacement for a listbox. Supports `v-model`, `items`, `value-key`, `search-input`, and keyboard navigation; the default slot is the trigger button, and the listbox width matches it automatically.
- **`AppToggle`** (global): a DaisyUI `toggle` switch (`v-model` / `change` / `disabled`) used for every on/off control.
- **`AppTooltip`** (imported per-component, **not** global): a hover/focus tooltip that **teleports** its bubble to `<body>`, so it escapes ancestor `overflow-hidden` (e.g. the collapsed sidebar). Props: `text`, `side`, `disabled`.

Everything else is hand-rolled Tailwind using DaisyUI's component classes (`btn`, `badge`, `tabs`,
`card`, …) and the token utilities described in the [Design System](./design-system).
