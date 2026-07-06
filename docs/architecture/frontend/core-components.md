# The Bannered Mare: Core & Shared Components

This document outlines the frontend component architecture of the The Bannered Mare. The application uses Vue 3 components styled with Tailwind CSS and Nuxt UI v4 primitives.


## 1. App Shell and Navigation Layout

### `AppShell.vue` and `AppSidebar.vue`

- **Role**: Manages the core screen structure, sidebar drawer, and responsive view containers.
- **Sidebar Actions**:
  - Exposes main application navigation tabs (Chat, Library, Memory, Connections, Admin Logs).
  - Features the **Brand Wordmark** ("The Bannered Mare") using the `font-medieval` (BlackChancery) font.
  - Hosts the **Profile Picker** allowing users to switch active profile settings.
  - Hosts the **Theme Switcher** (toggled via a custom toggle div).


## 2. Text and Markdown Rendering

### `MessageBubble.vue`

- **Role**: Renders chat history dialogue bubbles for both the user and assistant.
- **Markdown Parsing**: Integrates `markdown-it` to parse text streams into formatted HTML.
- **Security Sanitization**: Wraps HTML outputs in `dompurify` (`DOMPurify.sanitize`) to shield the client from XSS injection vulnerabilities.
- **Reasoning Display**: Supports collapsing sections to display chain-of-thought/reasoning output blocks from reasoning models.


## 3. Specialized Parameter Input Handlers

### `ParamInput.vue`

- **Role**: A recursive component designed to dynamically render input controls based on JSON schema definitions.
- **Recursive Schemas**: Maps different parameter types automatically:
  - **Boolean** $\rightarrow$ Checkbox or toggle.
  - **Enum** $\rightarrow$ Dropdown selector.
  - **Number / Integer** $\rightarrow$ Slider or numeric input field with min/max bounds.
  - **String** $\rightarrow$ Text area or input field.
  - **List / Object** $\rightarrow$ Nested recursive calls to self.


## 4. Chat Input Elements

### `ParchmentInput.vue`

- **Role**: The primary chat message text area.
- **Features**:
  - **Auto-Grow**: Automatically grows in height as the user inputs multi-line messages, resetting upon submission.
  - **Fantasy Aesthetic**: Styled with cream borders, warm box shadows, and transition effects.
  - **Key Bindings**: Submits on `Enter` (unless `Shift+Enter` is pressed for a newline).


## 5. Modals and Action Banners

- **`ProfilePickerModal.vue`**: Allows users to quickly switch active settings, presets, and active user profiles.
- **`ImportPresetModal.vue`**: Handles importing SillyTavern JSON settings configurations.
- **`SetupPromptBanner.vue`**: Top-anchored alert banner guiding users to complete LLM provider setups if no active model is configured.
