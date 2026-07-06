# The Bannered Mare: View Architecture and Main Screens

The The Bannered Mare client is a Single Page Application (SPA) structured around vertical views mapping to specific core features of the roleplay application.

---

## 1. Home Dashboard (`HomeView.vue`)

- **Role**: The landing view presenting a warm literary welcome.
- **Key Elements**:
  - **Recent Activity**: Displays grid cards of recently accessed characters and active chat sessions.
  - **Quick Start**: Allows users to instantly create a new character or jump back into their latest story.

---

## 2. Chat Workspace (`ChatView.vue`)

- **Role**: The central roleplay interaction canvas.
- **Key Features**:
  - **Dialogue Panel**: Renders chat messages, handles typing indicators, and renders reasoning/thought blocks.
  - **Interactive Messaging**: Supports editing user messages, deleting blocks, regenerating AI responses, and swiping through alternative greetings or response paths.
  - **Context Drawer**: Sidebar drawer hosting quick session configurations (e.g., changing templates, active presets, or selecting user personas on the fly).

---

## 3. Characters Library (`CharactersView.vue`)

- **Role**: Lists and manages installed NPC character cards.
- **Key Functions**:
  - **Filtering & Searching**: Uses `useLibraryFilters.ts` to filter cards by tags, species, age, gender, and creators.
  - **Card Imports**: Supports dragging and dropping PNG character cards (extracting embedded Exif metadata) or JSON files to import profiles.
  - **Detail Inspector**: Expands to view tags, version info, description overrides, and custom system templates.

---

## 4. Connections Manager (`ConnectionsView.vue`)

- **Role**: The administration hub for all model configurations and prompt parameters.
- **Tabs Layout**:
  - **Providers**: Configure API endpoints and credentials (e.g., OpenAI API keys or local Ollama endpoints).
  - **Models**: Manage individual models, loading status, and family assignments.
  - **Model Families**: Set parameters, context length, and system-compatible model architectures.
  - **Templates & Presets**: Order prompt components, set Jinja2 templates, and configure temperature/penalty parameters.
  - **Prompt Fragments**: Create reusable instructions (jailbreaks, formatting rules) to inject at target depths.

---

## 5. Memory View (`MemoryView.vue`)

- **Role**: Inspects and controls the long-term context databases.
- **Key Functions**:
  - **Data Bank Entries**: Lists text files and memory fragments stored in the RAG database.
  - **Retriever Testing**: Provides test inputs to run vector matching, returning matches annotated with similarity scores to test context activation.

---

## 6. Setup Wizard (`SetupWizardView.vue`)

- **Role**: Guides new users through the initial app configurations.
- **Steps**:
  - **Provider Config**: Sets up the first local or cloud backend.
  - **Model Setup**: Pulls and caches available model assets.
  - **Initial Persona**: Creates the user's base roleplay profile.
