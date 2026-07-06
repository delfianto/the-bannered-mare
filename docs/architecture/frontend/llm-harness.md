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
  <text x="360" y="58" text-anchor="middle" font-size="11" fill="var(--tbm-dgm-ink-2)">connection tabs</text>
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
  <g stroke="var(--tbm-dgm-arrow)" stroke-width="1.6" fill="none" marker-end="url(#tbm-ah)">
    <path d="M360 72 L360 110"/>
    <path d="M360 168 L360 206"/>
    <path d="M340 264 L150 320"/>
    <path d="M360 264 L360 320"/>
    <path d="M380 264 L570 320"/>
  </g>
  <g font-size="10.5" fill="var(--tbm-dgm-ink-2)">
    <text x="372" y="94">triggers actions</text>
    <text x="372" y="190">API via client</text>
    <text x="210" y="300" text-anchor="middle">query / sync</text>
    <text x="520" y="300" text-anchor="middle">network request</text>
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

  // API operations...
  async function fetchProvider(id: string) { ... }
  async function saveProvider(id: string, updates: Record<string, unknown>) { ... }
  async function fetchAvailableModels(id: string) { ... }
  async function syncNow(id: string) { ... }
  async function loadModel(id: string, identifier: string) { ... }
  async function unloadModel(id: string, identifier: string) { ... }
}
```

### Key Operations

- **`syncNow(id)`** — forces the backend to query local model directories and cache new
  entries in the database.
- **`loadModel(id, identifier)`** — tells the local provider (e.g., LM Studio) to load the
  specified weights into memory.
- **`unloadModel(id, identifier)`** — tells the local provider to release the weights.

## 3. UI Components and Views

LLM configuration is presented through modular tabs and dedicated views.

### Provider Details View (`ProviderView.vue`)

[ProviderView.vue](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/views/settings/ProviderView.vue)
is the central hub for:

- changing API keys, environment-variable names, and endpoints;
- verifying connection status;
- listing discovered models with their status (`loaded`, `cached`, `unloaded`) and action
  buttons to load, unload, or toggle availability.

### Connection Sub-Tabs (`src/components/connections/`)

- **`ProvidersTab.vue`** — lists all configured API connections (OpenAI, Anthropic, Ollama,
  …) with active indicators.
- **`ModelsTab.vue`** — shows all registered models with their families and active providers.
- **`ModelFamiliesTab.vue`** — configures global parameters (temperature, penalties, limits)
  and formatting guidelines per family.
- **`ModelInferenceParams.vue`** — standardized parameter inputs (sliders for
  temperature/top_p, lists for stop sequences) shared across presets and templates.
