---
title: Architecture
---

# Architecture

The Bannered Mare is a monorepo with two independent halves that meet at a single,
typed HTTP contract. The **backend** is a headless FastAPI service — a modular
monolith organized as vertical domain slices — that owns providers, characters,
prompts, RAG, and streaming. The **frontend** is a Vue 3 single-page app that talks
to it exclusively through a generated `openapi-fetch` client, with a bespoke parser
for the server-sent event (SSE) stream that carries live completions.

<Figure tag="Figure 1" title="System map — one request's worth of the platform" id="fig-system-map">
<svg viewBox="0 0 900 640" role="img" aria-label="The Bannered Mare system map" style="font-family:var(--vp-font-family-base)">
  <defs>
    <marker id="tbm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-arrow)"/>
    </marker>
  </defs>
  <!-- Actor -->
  <rect x="350" y="14" width="200" height="38" rx="10" fill="var(--tbm-dgm-surface-3)" stroke="var(--tbm-dgm-border-strong)"/>
  <text x="450" y="38" text-anchor="middle" font-size="13" font-weight="700" fill="var(--tbm-dgm-ink)">👤 User · Web browser</text>
  <!-- ===== Frontend tier ===== -->
  <rect x="110" y="82" width="680" height="150" rx="14" fill="var(--tbm-dgm-frontend-soft)" stroke="var(--tbm-dgm-frontend)" stroke-opacity=".55" stroke-dasharray="5 4"/>
  <text x="126" y="106" font-size="12" font-weight="700" letter-spacing=".08em" fill="var(--tbm-dgm-frontend)">FRONTEND · Vue 3 single-page app</text>
  <g font-size="12" text-anchor="middle">
    <rect x="126" y="120" width="150" height="42" rx="9" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <text x="201" y="146" fill="var(--tbm-dgm-ink)">Screens &amp; Components</text>
    <rect x="292" y="120" width="150" height="42" rx="9" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <text x="367" y="146" fill="var(--tbm-dgm-ink)">State — Pinia</text>
    <rect x="458" y="120" width="166" height="42" rx="9" fill="var(--tbm-dgm-frontend-soft)" stroke="var(--tbm-dgm-frontend)"/>
    <text x="541" y="140" font-weight="700" fill="var(--tbm-dgm-frontend)">openapi-fetch client</text>
    <text x="541" y="155" font-size="10" fill="var(--tbm-dgm-ink-2)">typed from openapi.json</text>
    <rect x="640" y="120" width="134" height="42" rx="9" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <text x="707" y="140" fill="var(--tbm-dgm-ink)">LLM · Mock</text>
    <text x="707" y="155" font-size="10" fill="var(--tbm-dgm-ink-2)">harness</text>
  </g>
  <text x="126" y="212" font-size="11" fill="var(--tbm-dgm-faint)">Vue 3.5 · DaisyUI 5 · TypeScript · Vite · vue-i18n · custom SSE stream parser</text>
  <!-- ===== Backend tier ===== -->
  <rect x="70" y="272" width="760" height="170" rx="14" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)" stroke-opacity=".55" stroke-dasharray="5 4"/>
  <text x="86" y="296" font-size="12" font-weight="700" letter-spacing=".08em" fill="var(--tbm-dgm-backend)">BACKEND · FastAPI modular monolith · Python 3.14</text>
  <g font-size="11.5" text-anchor="middle">
    <rect x="86" y="308" width="106" height="30" rx="7" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="139" y="327" fill="var(--tbm-dgm-ink)">characters</text>
    <rect x="210" y="308" width="106" height="30" rx="7" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="263" y="327" fill="var(--tbm-dgm-ink)">personas</text>
    <rect x="334" y="308" width="106" height="30" rx="7" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="387" y="327" fill="var(--tbm-dgm-ink)">prompts</text>
    <rect x="458" y="308" width="106" height="30" rx="7" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="511" y="327" fill="var(--tbm-dgm-ink)">chat</text>
    <rect x="582" y="308" width="106" height="30" rx="7" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="635" y="327" fill="var(--tbm-dgm-ink)">providers</text>
    <rect x="706" y="308" width="106" height="30" rx="7" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="759" y="327" fill="var(--tbm-dgm-ink)">rag</text>
  </g>
  <text x="86" y="360" font-size="11" fill="var(--tbm-dgm-faint)">Each domain slice: router · service · repository · models · schemas · dependencies</text>
  <rect x="86" y="374" width="728" height="52" rx="9" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <text x="450" y="400" text-anchor="middle" font-size="12" font-weight="600" fill="var(--tbm-dgm-ink)">Core kernel</text>
  <text x="450" y="416" text-anchor="middle" font-size="11" fill="var(--tbm-dgm-ink-2)">config · persistence (SQLAlchemy 2.0) · structured logging · exception handlers</text>
  <!-- ===== Data + Providers tier ===== -->
  <rect x="70" y="486" width="350" height="128" rx="14" fill="var(--tbm-dgm-data-soft)" stroke="var(--tbm-dgm-data)" stroke-opacity=".55" stroke-dasharray="5 4"/>
  <text x="86" y="510" font-size="12" font-weight="700" letter-spacing=".05em" fill="var(--tbm-dgm-data)">🗄  PostgreSQL + VectorChord</text>
  <text x="86" y="540" font-size="11.5" fill="var(--tbm-dgm-ink)">Persistence — sessions, characters, messages</text>
  <text x="86" y="562" font-size="11.5" fill="var(--tbm-dgm-ink)">Vector embeddings — RAG retrieval</text>
  <text x="86" y="590" font-size="10.5" fill="var(--tbm-dgm-faint)">One store, one owner: the backend</text>
  <rect x="480" y="486" width="350" height="128" rx="14" fill="var(--tbm-dgm-provider-soft)" stroke="var(--tbm-dgm-provider)" stroke-opacity=".55" stroke-dasharray="5 4"/>
  <text x="496" y="510" font-size="12" font-weight="700" letter-spacing=".05em" fill="var(--tbm-dgm-provider)">🔌  LLM Providers</text>
  <g font-size="10.5" text-anchor="middle" fill="var(--tbm-dgm-ink)">
    <rect x="496" y="522" width="74" height="26" rx="7" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="533" y="539">OpenAI</text>
    <rect x="578" y="522" width="82" height="26" rx="7" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="619" y="539">Anthropic</text>
    <rect x="668" y="522" width="70" height="26" rx="7" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="703" y="539">Gemini</text>
    <rect x="746" y="522" width="68" height="26" rx="7" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="780" y="539">xAI</text>
    <rect x="496" y="556" width="98" height="26" rx="7" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="545" y="573">OpenRouter</text>
    <rect x="602" y="556" width="68" height="26" rx="7" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="636" y="573">Ollama</text>
    <rect x="678" y="556" width="136" height="26" rx="7" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="746" y="573">Local backends</text>
  </g>
  <!-- ===== Connective arrows ===== -->
  <g stroke="var(--tbm-dgm-arrow)" stroke-width="1.6" fill="none" marker-end="url(#tbm-ah)">
    <path d="M450 52 L450 80"/>
    <path d="M450 232 L450 270"/>
    <path d="M250 442 L250 484"/>
    <path d="M650 442 L650 484"/>
  </g>
  <text x="462" y="256" font-size="10.5" fill="var(--tbm-dgm-ink-2)">HTTPS · JSON · SSE stream</text>
  <text x="262" y="470" font-size="10.5" fill="var(--tbm-dgm-ink-2)">SQLAlchemy 2.0 (async)</text>
  <text x="662" y="470" font-size="10.5" fill="var(--tbm-dgm-ink-2)">HTTPS · SSE stream</text>
</svg>
<template #caption>

**The whole platform on one page.** A browser drives the Vue SPA; every call crosses
a single typed HTTP boundary into the FastAPI service, whose domain slices all share
one shape (`router · service · repository`). The backend is the sole owner of the
PostgreSQL + VectorChord store and the sole caller of the external LLM providers —
completions stream back the same way they came, over SSE. Click the diagram to enlarge.

</template>
</Figure>

## Backend

- [Project Structure](/architecture/backend/project-structure) — the modular-monolith / vertical-slice layout
- [Data Model](/architecture/backend/data-model) — the entities, their ownership, and the domain boundaries
- [Persistence Layer](/architecture/backend/persistence) — SQLAlchemy 2.0, repositories, migrations
- [LLM Integration](/architecture/backend/llm-integration) — the provider adapters and streaming
- [Prompt System](/architecture/backend/prompt-system) — how prompts are assembled
- [Characters & Personas](/architecture/backend/characters-and-personas) — the character/persona model

## Frontend

- [Project Structure](/architecture/frontend/project-structure) — the feature-based, layered `src/` layout
- [Design System](/architecture/frontend/design-system) — DaisyUI 5 and the visual language
- [Main Screens](/architecture/frontend/main-screens) — the app's top-level surfaces
- [Core Components](/architecture/frontend/core-components) — the reusable building blocks
- [LLM Harness](/architecture/frontend/llm-harness) — driving live inference from the client
- [Mock Harness](/architecture/frontend/mock-harness) — developing against a simulated backend
- [Backend Connection](/architecture/frontend/backend-connection) — the typed client and SSE parser
- [State & Localization](/architecture/frontend/state-and-localization) — Pinia stores and vue-i18n

## API Reference

The single HTTP contract between the two halves has its own
[**API Reference**](/api/) section — every endpoint, grouped by domain, with the
cross-cutting conventions (base URL, the response envelope, pagination, filtering, and
errors) documented up front.
