# Main Screens

The client is a single-page application (SPA) organized around a set of routed views (wired up in
[router/index.ts](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/router/index.ts)),
each mapping to a core feature of the roleplay app. Detail/edit pages for connection resources
live under `views/settings/`.


## 1. Home Dashboard (`HomeView.vue`)

- **Route**: `/`
- **Role**: The landing view presenting a warm literary welcome.
- **Key Elements**:
  - **Setup Prompt**: `SetupPromptBanner` nudges first-run users toward the setup wizard when no ready profile exists.
  - **Continue Your Tale**: A row of recent chat sessions pulled from the API.
  - **Discover**: Character cards to jump into or start a new tale, plus a `SearchBar`.
  - **Empty State**: A welcome call-to-action to create the first character when nothing exists yet.


## 2. Chat Workspace (`views/chat/ChatView.vue`)

- **Routes**: `/chats` and `/chats/:chatId`
- **Role**: The central roleplay interaction canvas.
- **Key Features**:
  - **Session List**: `ChatSessionList` in a side column; auto-selects the first session when none is in the route.
  - **Dialogue Panel**: `MessageBubble` list with a `QuillTypingIndicator` while generating; supports edit, regenerate, and swiping through alternative responses. Messages stream in over SSE (see [Backend Connection](backend-connection.md)).
  - **Chat Header**: `ChatHeader` shows the character/title and hosts the per-session **profile picker** (`ChatProfilePicker`) to apply a different loadout (model + template + preset) to the active chat on the fly.


## 3. Characters / Discover (`CharactersView.vue`)

- **Route**: `/characters`
- **Role**: Browses and manages the character library.
- **Key Functions**:
  - **Filtering & Searching**: `useLibraryFilters` filters and sorts the fetched characters client-side (search, category, sort, grid/list view mode).
  - **Grid / List**: Renders `CharacterCard` (grid) or `CharacterListRow` (list) with a `DiscoverHeader`, `FilterBar`, and `CategoryPills`.
  - **Selection & Bulk Actions**: A multi-select mode with a `BulkActionBar` and delete confirmation.
  - **Start a Tale**: Uses `useCreateChat`; if multiple profiles exist, a `ProfilePickerModal` asks which loadout to use.


## 4. Character Detail & Creator

- **`CharacterDetailView.vue`** (`/characters/:id`) — Read-only character sheet fetched by id, rendering the avatar and narrative fields, with a "start a tale" action.
- **`CharacterCreateView.vue`** (`/characters/create` and `/characters/:id/edit`) — The character creator/editor. Tabbed across **Character**, **Behavior**, and **World** (`CharacterTab` / `BehaviorTab` / `WorldTab`) with a live `CharacterPreview`, backed by `useCharacterForm`; in edit mode it also loads the character's lorebook entries.


## 5. Connections Manager (`ConnectionsView.vue`)

- **Route**: `/connections`
- **Role**: Hub for model infrastructure. Tabs are selected via the `?tab=` query param.
- **Tabs**:
  - **Providers** (`ProvidersTab`): Configure API endpoints and credentials (OpenAI, Anthropic, Google, OpenRouter, xAI, Ollama, LM Studio).
  - **Models** (`ModelsTab`): Manage individual models, their families, and providers.
  - **Model Families** (`ModelFamiliesTab`): Configure per-family parameters and metadata.
- Prompt-side configuration (presets, templates, fragments) now lives on the **Loadouts** page, not here. Editing a row opens a dedicated detail view under `views/settings/` (see §10).


## 6. Loadouts / Profiles (`ProfilesView.vue`)

- **Route**: `/loadouts`
- **Role**: Manages roleplay "profiles" (loadouts) and the prompt-building resources they compose. Tabs via `?tab=`.
- **Tabs**:
  - **Profiles** (`ProfilesTab`): Named loadouts bundling a model, template, and preset.
  - **Presets** (`PresetsTab`): Inference-parameter sets (temperature, penalties, …).
  - **Templates** (`TemplatesTab`): Prompt templates — component order, system template, history limits.
  - **Fragments** (`FragmentsTab`): Reusable prompt fragments (system, NSFW, jailbreak, instruction, context).


## 7. Lorebooks (`LorebooksView.vue`)

- **Route**: `/lorebooks`
- **Role**: Manage lorebooks and their keyword-triggered lore entries. Provides inline lorebook create/edit and entry create/edit/delete (`LoreEntryCard`, `LoreEntryForm`) backed by `useLorebooks`.


## 8. Data Bank / Memory (`MemoryView.vue`)

- **Route**: `/memory` (labeled "Data Bank" in navigation)
- **Role**: Manage the RAG data bank and test retrieval.
- **Key Functions**:
  - **Data Bank Entries**: CRUD over entries with a scope filter (all / global / character / chat), via `useDataBank`.
  - **RAG Search**: Runs a semantic search (`POST /api/rag/search`) and lists retrieved chunks annotated with similarity scores; also surfaces the indexed-chunk count from `/api/rag/status`.


## 9. Bookmarks (`BookmarksView.vue`)

- **Route**: `/bookmarks`
- **Role**: A saved-items view collecting bookmarked characters, sessions, and messages (via `useBookmarks`), with an empty state when nothing is bookmarked.


## 10. Settings & Detail Views (`views/settings/`)

- **`SettingsView.vue`** (`/settings`, also the target of `/persona`) — App settings with tabs: **Interface**, **Persona**, **Logs**, and **About**.
- **Detail / edit pages** opened from Connections and Loadouts rows:
  - `ProviderView.vue` (`/settings/providers/:id`) — provider credentials, model sync, and load/unload actions (see [LLM Harness](llm-harness.md)).
  - `ModelCreateView.vue` (`/settings/models/create`) and `ModelView.vue` (`/settings/models/:id`) — create/edit a model.
  - `ModelFamilyView.vue` (`/settings/model-families/:id`) — edit a model family.
  - `TemplateView.vue`, `FragmentView.vue`, `PresetView.vue` (`/settings/templates|fragments|presets/:id`) — edit a prompt template, fragment, or preset.

> A standalone `PersonaView.vue` file exists but is a stub and is not routed; the `/persona` route resolves to `SettingsView.vue`.


## 11. Setup Wizard (`SetupWizardView.vue`)

- **Route**: `/setup`
- **Role**: Guides new users to a working first profile.
- **Steps**:
  - **Provider readiness**: Confirms at least one provider/model is available.
  - **Create a profile**: Either build one manually or import a SillyTavern preset (`ImportPresetModal`); can quick-create a persona inline when none exists.
  - **Done**: Confirmation before returning to the app.
