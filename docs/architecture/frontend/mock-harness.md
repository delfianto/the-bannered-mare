# Mock Harness

For offline work and fast frontend iteration, The Bannered Mare ships an integrated mock
network harness built on **Mock Service Worker (MSW)**. Because it intercepts at the network
layer, the rest of the app is completely unaware it's talking to fixtures rather than the real
backend.

## 1. How the Mock Harness Works

Instead of mock data hardcoded inside components, MSW registers a **Service Worker** in the
browser. When the app makes an API `fetch`, the Service Worker intercepts it, matches it to a
handler, reads a fixture, and resolves the original network promise with a mock response:

<Figure tag="Figure 1" title="MSW intercepts at the network layer" id="fig-msw">
<svg viewBox="0 0 720 290" role="img" aria-label="Mock Service Worker request interception" style="font-family:var(--vp-font-family-base)">
  <defs>
    <marker id="tbm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-arrow)"/>
    </marker>
  </defs>
  <rect x="30" y="96" width="150" height="76" rx="10" fill="var(--tbm-dgm-frontend-soft)" stroke="var(--tbm-dgm-frontend)"/>
  <text x="105" y="128" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">Vue 3 SPA</text>
  <text x="105" y="146" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">standard fetch</text>
  <rect x="270" y="96" width="176" height="76" rx="10" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/>
  <text x="358" y="128" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">Service Worker</text>
  <text x="358" y="146" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">intercepts in-browser</text>
  <rect x="536" y="52" width="150" height="72" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
  <text x="611" y="82" text-anchor="middle" font-size="12" font-weight="700" fill="var(--tbm-dgm-ink)">handlers.ts</text>
  <text x="611" y="100" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">40+ endpoints</text>
  <rect x="536" y="184" width="150" height="62" rx="10" fill="var(--tbm-dgm-data-soft)" stroke="var(--tbm-dgm-data)"/>
  <text x="611" y="212" text-anchor="middle" font-size="12" font-weight="700" fill="var(--tbm-dgm-ink)">data/ fixtures</text>
  <text x="611" y="230" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">seed-mirroring JSON</text>
  <!-- Forward + return arrows -->
  <g stroke="var(--tbm-dgm-arrow)" stroke-width="1.6" fill="none" marker-end="url(#tbm-ah)">
    <path d="M180 120 L268 120"/>
    <path d="M268 150 L182 150"/>
    <path d="M446 114 L534 92"/>
    <path d="M534 120 L448 148"/>
    <path d="M611 124 L611 182"/>
  </g>
  <g font-size="10.5" fill="var(--tbm-dgm-ink-2)">
    <text x="224" y="112" text-anchor="middle">fetch /api/providers</text>
    <text x="224" y="168" text-anchor="middle">4 · resolve promise</text>
    <text x="470" y="84">1 · match</text>
    <text x="470" y="162">3 · respond</text>
    <text x="624" y="160">2 · read fixtures</text>
  </g>
</svg>
<template #caption>

**The app never knows.** MSW resolves the very promise the app's `fetch` returned, so
components run their normal HTTP code paths — headers, status codes, error handling — against
fixtures that mirror the backend's seed data.

</template>
</Figure>

## 2. Activation Controls

The mock harness is toggled with environment variables:

```bash
# Enable MSW mock mode
VITE_USE_MOCKS=true vp dev --host

# Enable mock mode and log requests to the developer console
VITE_USE_MOCKS=true VITE_DEBUG_REQUEST=true vp dev --host
```

### Conditional Vite Proxy

In
[vite.config.ts](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/vite.config.ts),
the config branches on the `VITE_USE_MOCKS` flag:

- **`false`** — proxies `/api` requests to the real FastAPI backend at `http://localhost:8000`.
- **`true`** — disables the proxy target entirely, delegating all interception to MSW.

## 3. Directory Layout

Mock logic is encapsulated under
[src/mocks/](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/mocks/):

- **`handlers.ts`** — implements 40+ endpoints mimicking backend behavior: CRUD, pagination,
  filtering, and model load-state mutations.
- **`data/`** — JSON/JS files with realistic test data mirroring the seed fixtures:
  - **6 providers** (OpenAI, Anthropic, Ollama, LM Studio, …)
  - **19 model families** and **34 models**
  - **20 characters** (with Unsplash avatar photos)
  - **20 chats** linked to YAML dialogue scripts
  - **presets, templates, prompt fragments, and RAG data-bank entries**
- **`data/scenarios/`** — YAML scenario scripts describing multi-turn dialogues for character
  cards.
