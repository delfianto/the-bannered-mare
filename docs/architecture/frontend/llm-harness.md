# LLM Harness

The LLM harness is the frontend's connection-management surface. It lets users define
credentials, inspect active services, sync available models, load and unload local weights,
and tune parameters — all by driving backend endpoints through composables, never by talking
to providers directly.

## 1. Architectural Role

The harness sits between UI state and the backend. Views trigger actions on composables, the
composables call the typed client, and the backend fans out to the database and to the actual
local or cloud providers:

<Figure tag="Figure 1" title="From UI action to provider" id="fig-harness">
<svg viewBox="0 0 720 430" role="img" aria-label="LLM harness request path" style="font-family:var(--vp-font-family-base)">
  <defs>
    <marker id="tbm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-arrow)"/>
    </marker>
  </defs>
  <rect x="240" y="16" width="240" height="56" rx="10" fill="var(--tbm-dgm-frontend-soft)" stroke="var(--tbm-dgm-frontend)"/>
  <text x="360" y="40" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">ProviderView.vue</text>
  <text x="360" y="58" text-anchor="middle" font-size="11" fill="var(--tbm-dgm-ink-2)">provider detail view</text>
  <rect x="235" y="112" width="250" height="56" rx="10" fill="var(--tbm-dgm-frontend-soft)" stroke="var(--tbm-dgm-frontend)"/>
  <text x="360" y="136" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">useProvider.ts · useModels.ts</text>
  <text x="360" y="154" text-anchor="middle" font-size="11" fill="var(--tbm-dgm-ink-2)">composables — state + orchestration</text>
  <rect x="250" y="208" width="220" height="56" rx="10" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/>
  <text x="360" y="232" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">FastAPI backend</text>
  <text x="360" y="250" text-anchor="middle" font-size="11" fill="var(--tbm-dgm-ink-2)">/api/providers</text>
  <!-- Bottom row -->
  <rect x="40" y="322" width="190" height="64" rx="10" fill="var(--tbm-dgm-data-soft)" stroke="var(--tbm-dgm-data)"/>
  <text x="135" y="350" text-anchor="middle" font-size="12" font-weight="700" fill="var(--tbm-dgm-ink)">Database / cache</text>
  <text x="135" y="368" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">providers · models</text>
  <rect x="265" y="322" width="190" height="64" rx="10" fill="var(--tbm-dgm-provider-soft)" stroke="var(--tbm-dgm-provider)"/>
  <text x="360" y="350" text-anchor="middle" font-size="12" font-weight="700" fill="var(--tbm-dgm-ink)">Local providers</text>
  <text x="360" y="368" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">Ollama · LM Studio</text>
  <rect x="490" y="322" width="190" height="64" rx="10" fill="var(--tbm-dgm-provider-soft)" stroke="var(--tbm-dgm-provider)"/>
  <text x="585" y="350" text-anchor="middle" font-size="12" font-weight="700" fill="var(--tbm-dgm-ink)">Cloud providers</text>
  <text x="585" y="368" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">OpenAI · Anthropic</text>
  <!-- Arrows -->
  <path d="M135 294 H585" stroke="var(--tbm-dgm-arrow)" stroke-width="1.6" fill="none"/>
  <g stroke="var(--tbm-dgm-arrow)" stroke-width="1.6" fill="none" marker-end="url(#tbm-ah)">
    <path d="M360 72 V110"/>
    <path d="M360 168 V206"/>
    <path d="M360 264 V320"/>
    <path d="M135 294 V320"/>
    <path d="M585 294 V320"/>
  </g>
  <g font-size="10.5" fill="var(--tbm-dgm-ink-2)">
    <text x="372" y="94">triggers actions</text>
    <text x="372" y="190">API via client</text>
    <text x="200" y="288" text-anchor="middle">query / sync</text>
    <text x="500" y="288" text-anchor="middle">network request</text>
  </g>
</svg>
<template #caption>

**Everything routes through the backend.** The composables never reach a provider directly;
they call `/api/providers`, and the backend is the single point that queries the database and
issues the outbound network request to a local or cloud provider.

</template>
</Figure>

It manages:

- **Provider status** — active/disabled toggles, base URLs, and environment variables.
- **Model synchronization** — triggering sync calls to discover new local downloads.
- **Dynamic loading/unloading** — spinning up or releasing model weights on local nodes
  (LM Studio).
- **Inference parameter overrides** — key/value editors for defaults on model families or
  session presets.

## 2. The `useProvider` Composable

State and orchestration for the connection manager are encapsulated in `useProvider`
([useProvider.ts](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/composables/useProvider.ts)):

```typescript
export function useProvider() {
  const provider = ref<ProviderResponse | null>(null);
  const loading = ref(false);
  const saving = ref(false);
  const error = ref<Error | null>(null);

  const availableModels = ref<DiscoveredModel[]>([]);
  const modelsLoading = ref(false);
  const syncing = ref(false);
  const modelsError = ref<Error | null>(null);
  const pendingModelAction = ref<string | null>(null);

  const searchResults = ref<DiscoveredModel[]>([]);
  const searchingModels = ref(false);
  const savingFilter = ref(false);

  // API operations...
  async function fetchProvider(id: string) { ... }
  async function saveProvider(id: string, updates: Record<string, unknown>) { ... }
  async function fetchAvailableModels(id: string) { ... }
  async function syncNow(id: string) { ... }
  async function searchModels(id: string, query: string) { ... }
  async function setModelFilter(id: string, allowedModels: string[]) { ... }
  async function loadModel(id: string, identifier: string) { ... }
  async function unloadModel(id: string, identifier: string) { ... }
  async function deleteModel(id: string, identifier: string) { ... }
  async function persistModel(id: string, identifier: string) { ... }
}
```

### Key Operations

- **`syncNow(id)`** — forces the backend to re-query the provider for its model list and refresh
  the cached available models.
- **`searchModels(id, query)`** — searches the provider's catalog (used to add models beyond the
  synced set).
- **`setModelFilter(id, allowedModels)`** — persists a curated allow-list; the response carries the
  freshly-filtered available list, so no separate refetch is needed.
- **`loadModel(id, identifier)`** — tells the local provider (e.g., LM Studio) to load the
  specified weights into memory.
- **`unloadModel(id, identifier)`** — tells the local provider to release the weights.
- **`deleteModel(id, identifier)`** / **`persistModel(id, identifier)`** — remove a discovered model
  or persist it as a first-class registered model.

## 3. UI Components and Views

LLM configuration is split between the tabbed **Connections** list page and dedicated
detail/edit views under `views/settings/`.

### Connections List (`ConnectionsView.vue` + `src/components/connections/`)

[ConnectionsView.vue](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/views/ConnectionsView.vue)
hosts three tabs (selected via the `?tab=` query param):

- **`ProvidersTab.vue`** — lists all configured API connections (OpenAI, Anthropic, Google,
  OpenRouter, xAI, Ollama, LM Studio, OpenCode Zen/Go) with active indicators.
- **`ModelsTab.vue`** — shows all registered models with their families, native providers, and
  active route (native, or the aggregator a routing override points at).
- **`ModelFamiliesTab.vue`** — lists model families.

Prompt-side resources (presets, templates, fragments) are **not** here — they live on the
Loadouts page (`ProfilesView.vue`); see [Main Screens](main-screens.md).

### Detail / Edit Views (`views/settings/`)

Clicking a row opens a full-page editor:

- **`ProviderView.vue`** (`/settings/providers/:id`) — the central provider hub: change API keys,
  environment-variable names, and endpoints; trigger a model sync; and manage discovered models
  (load, unload, delete, persist, and curate the allow-list via the model filter). This view
  drives `useProvider`.
- **`ModelCreateView.vue`** / **`ModelView.vue`** — create or edit a model: assign its family and
  native provider, edit inference parameters, and optionally set a **routing override** (a
  "Route via" provider dropdown + identifier) so the model runs through an aggregator
  (OpenRouter, OpenCode Zen/Go, …) instead of its native provider.
- **`ModelFamilyView.vue`** — edit a model family's name, identifier, and description.
- **`TemplateView.vue`**, **`FragmentView.vue`**, **`PresetView.vue`** — edit a prompt template,
  fragment, or preset.

### Shared Parameter Inputs

- **`ModelInferenceParams.vue`** — parameter editor used when editing a model; renders each
  parameter through the recursive **`ParamInput.vue`** (sliders for ranged numbers, toggles,
  enums, lists, nested objects — see [Core Components](core-components.md)), with tooltip help
  sourced from the `useSettingsStore` parameter docs.
