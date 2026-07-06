# Docs Site Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a VitePress documentation site rooted at `docs/`, consolidating the scattered `backend/docs` + `frontend/docs` content into one browsable, GitHub Pages–deployed site — migrating existing content as-is (links fixed, nav added), with no body rewrites.

**Architecture:** A single VitePress project under `docs/` with an isolated `docs/package.json`. Existing markdown is relocated via `git mv` into a topic tree (`guide/`, `architecture/`, `providers/`, `sillytavern/`). Navigation/sidebar live in `docs/.vitepress/config.mts`, which imports one small sidebar module per section. Source-code links are rewritten to GitHub blob permalinks. A `docs.yml` GitHub Action builds with Bun and deploys to Pages.

**Tech Stack:** VitePress `^1.6.3`, Bun `1.3.x`, TypeScript config (`config.mts`), GitHub Actions + GitHub Pages.

**Design spec:** `docs/superpowers/specs/2026-07-06-docs-site-foundation-design.md` (approved).

## Global Constraints

- **VitePress:** `^1.6.3`. Config file is `docs/.vitepress/config.mts` using `defineConfig`.
- **Package manager:** Bun. All docs commands run from `docs/`.
- **Base path (exact):** `/the-bannered-mare/`
- **Repo URL for blob links (exact):** `https://github.com/delfianto/the-bannered-mare/blob/main/`
- **Filenames:** kebab-case (e.g. `PROJECT_STRUCTURE.md` → `project-structure.md`).
- **Migrate as-is:** do NOT rewrite doc bodies. Allowed body edits are limited to link fixes (source links → blob URLs; broken cross-doc links → site-absolute paths). Section `index.md` landing pages are new connective content and are allowed.
- **History:** relocate existing files with `git mv` (never delete-and-recreate).
- **Dead links:** leave VitePress dead-link checking ON (default). A green `bun run docs:build` is the primary test for every migration task.
- **VCS:** work on `main`; commit each task; never `git push` (the user does that).
- **Platform:** macOS/zsh — `sed -i` requires an empty backup arg: `sed -i '' ...`.

---

### Task 1: Scaffold the VitePress project

**Files:**
- Create: `docs/package.json`
- Create: `docs/.gitignore`
- Create: `docs/.vitepress/config.mts`
- Create: `docs/index.md` (temporary stub — replaced in Task 7)
- Create: `docs/guide/index.md` (temporary stub — fleshed out in Task 2, needed so the one nav link resolves)

**Interfaces:**
- Produces: a working `docs/` VitePress project; `config.mts` exporting `defineConfig({...})` whose `themeConfig.nav` and `themeConfig.sidebar` are extended by later tasks; the exact `base`, `srcExclude`, and `search` settings other tasks rely on.

- [ ] **Step 1: Create `docs/package.json`**

```json
{
  "name": "the-bannered-mare-docs",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "docs:dev": "vitepress dev",
    "docs:build": "vitepress build",
    "docs:preview": "vitepress preview"
  },
  "devDependencies": {
    "vitepress": "^1.6.3"
  }
}
```

- [ ] **Step 2: Create `docs/.gitignore`**

```gitignore
node_modules/
.vitepress/dist/
.vitepress/cache/
```

- [ ] **Step 3: Create `docs/.vitepress/config.mts`**

```ts
import { defineConfig } from 'vitepress'

// Sidebar modules are registered by later tasks:
//   import { guideSidebar } from './sidebar.guide'
//   import { architectureSidebar } from './sidebar.architecture'
//   import { providersSidebar } from './sidebar.providers'
//   import { sillytavernSidebar } from './sidebar.sillytavern'

export default defineConfig({
  title: 'The Bannered Mare',
  description:
    'Documentation for The Bannered Mare — an AI-powered platform for local roleplay sessions.',
  base: '/the-bannered-mare/',
  srcExclude: ['superpowers/**'],
  themeConfig: {
    search: { provider: 'local' },
    nav: [{ text: 'Guide', link: '/guide/' }],
    sidebar: {},
    socialLinks: [
      { icon: 'github', link: 'https://github.com/delfianto/the-bannered-mare' },
    ],
  },
})
```

- [ ] **Step 4: Create `docs/index.md` (temporary stub)**

```md
# The Bannered Mare

Documentation site — under construction.

[Get Started](/guide/)
```

- [ ] **Step 5: Create `docs/guide/index.md` (temporary stub)**

```md
# Guide

Getting started content lands here.
```

- [ ] **Step 6: Install dependencies**

Run: `cd docs && bun install`
Expected: VitePress installed; `docs/bun.lock` (or `bun.lockb`) and `docs/node_modules/` created.

- [ ] **Step 7: Verify the dev server boots (smoke test)**

Run: `cd docs && timeout 15 bun run docs:dev || true`
Expected: logs a local URL like `➜  Local:   http://localhost:5173/the-bannered-mare/` with no config errors before the timeout kills it.

- [ ] **Step 8: Verify the production build passes**

Run: `cd docs && bun run docs:build`
Expected: `build complete` with no dead-link errors; output in `docs/.vitepress/dist/`.

- [ ] **Step 9: Commit**

```bash
git add docs/package.json docs/.gitignore docs/.vitepress/config.mts docs/index.md docs/guide/index.md docs/bun.lock*
git commit -m "docs(site): scaffold VitePress project at docs/"
```

---

### Task 2: Guide section (seeded from the READMEs)

**Files:**
- Modify: `docs/guide/index.md` (replace stub)
- Create: `docs/guide/quick-start.md`
- Create: `docs/guide/setup-backend.md`
- Create: `docs/guide/setup-frontend.md`
- Create: `docs/.vitepress/sidebar.guide.ts`
- Modify: `docs/.vitepress/config.mts` (register guide sidebar)

**Interfaces:**
- Consumes: `config.mts` from Task 1.
- Produces: `guideSidebar` export; the `/guide/` sidebar mapping.

Content sourcing (copy verbatim from the repo READMEs — these files STAY in place):
- `docs/guide/index.md` ← intro/overview from root `README.md` (the "what it is" framing + the monorepo table, reworded to prose).
- `docs/guide/quick-start.md` ← the "Quick Start" block from root `README.md` (both terminals) **plus** the "Keeping the API Contract in Sync" block.
- `docs/guide/setup-backend.md` ← `backend/README.md` "What it is / Quick Start / tech stack" sections.
- `docs/guide/setup-frontend.md` ← `frontend/README.md` "Getting Started / Commands / Mock Mode" sections.

- [ ] **Step 1: Create `docs/.vitepress/sidebar.guide.ts`**

```ts
import type { DefaultTheme } from 'vitepress'

export const guideSidebar: DefaultTheme.SidebarItem[] = [
  { text: 'Introduction', link: '/guide/' },
  { text: 'Quick Start', link: '/guide/quick-start' },
  {
    text: 'Setup',
    items: [
      { text: 'Backend', link: '/guide/setup-backend' },
      { text: 'Frontend', link: '/guide/setup-frontend' },
    ],
  },
]
```

- [ ] **Step 2: Register the guide sidebar in `docs/.vitepress/config.mts`**

Replace the import comment block with a real import at the top:

```ts
import { defineConfig } from 'vitepress'
import { guideSidebar } from './sidebar.guide'
```

And set the `sidebar` mapping:

```ts
    sidebar: {
      '/guide/': guideSidebar,
    },
```

- [ ] **Step 3: Write `docs/guide/index.md`**

Frontmatter + prose intro (fill the body from root `README.md`'s overview; keep the monorepo table):

```md
---
title: Introduction
---

# Introduction

The Bannered Mare is an AI-powered platform for local roleplay sessions, inspired by
SillyTavern. It is a monorepo with two independent halves:

| Half | What it is |
|------|------------|
| Backend | Headless FastAPI service — providers, characters, prompts, RAG, streaming. |
| Frontend | Vue 3 SPA web client, talks to the backend via a typed `openapi-fetch` client. |

See [Quick Start](/guide/quick-start) to run both halves, or jump to the
[Architecture](/architecture/) for how it's built.
```

- [ ] **Step 4: Write `docs/guide/quick-start.md`, `setup-backend.md`, `setup-frontend.md`**

Create each with a `# H1` and the corresponding README sections copied in (see "Content sourcing" above). Use fenced `bash` blocks exactly as in the READMEs. Do not invent new instructions.

- [ ] **Step 5: Verify the build passes**

Run: `cd docs && bun run docs:build`
Expected: `build complete`, no dead links. (The `/architecture/` link in `guide/index.md` will 404 until Task 3 — VitePress does not fail the build on absolute links that are not yet present as pages, but confirm no error is reported; if the build *does* flag it, temporarily point that link at `/guide/` and restore it in Task 3.)

- [ ] **Step 6: Commit**

```bash
git add docs/guide docs/.vitepress/sidebar.guide.ts docs/.vitepress/config.mts
git commit -m "docs(site): add Guide section seeded from the READMEs"
```

---

### Task 3: Architecture section (backend + frontend migration)

**Files:**
- Move: `backend/docs/README.md` → `docs/architecture/index.md` (then rewrite as the section landing)
- Move: `backend/docs/implementation/{PROJECT_STRUCTURE,PERSISTENCE_LAYER,LLM_INTEGRATION,PROMPT_SYSTEM,CHARACTERS_AND_PERSONAS}.md` → `docs/architecture/backend/{project-structure,persistence,llm-integration,prompt-system,characters-and-personas}.md`
- Move: `frontend/docs/{DESIGN_SYSTEM,MAIN_SCREENS,CORE_COMPONENTS,LLM_HARNESS_AGENT,MOCK_HARNESS,BACKEND_CONNECTION,STATE_AND_LOCALIZATION}.md` → `docs/architecture/frontend/{design-system,main-screens,core-components,llm-harness,mock-harness,backend-connection,state-and-localization}.md`
- Create: `docs/.vitepress/sidebar.architecture.ts`
- Modify: `docs/.vitepress/config.mts` (register + nav item)

**Interfaces:**
- Produces: `architectureSidebar`; the `/architecture/` sidebar mapping; nav item `Architecture`.

- [ ] **Step 1: Move the backend implementation docs**

```bash
mkdir -p docs/architecture/backend docs/architecture/frontend
git mv backend/docs/implementation/PROJECT_STRUCTURE.md docs/architecture/backend/project-structure.md
git mv backend/docs/implementation/PERSISTENCE_LAYER.md docs/architecture/backend/persistence.md
git mv backend/docs/implementation/LLM_INTEGRATION.md docs/architecture/backend/llm-integration.md
git mv backend/docs/implementation/PROMPT_SYSTEM.md docs/architecture/backend/prompt-system.md
git mv backend/docs/implementation/CHARACTERS_AND_PERSONAS.md docs/architecture/backend/characters-and-personas.md
```

- [ ] **Step 2: Move the frontend docs**

```bash
git mv frontend/docs/DESIGN_SYSTEM.md docs/architecture/frontend/design-system.md
git mv frontend/docs/MAIN_SCREENS.md docs/architecture/frontend/main-screens.md
git mv frontend/docs/CORE_COMPONENTS.md docs/architecture/frontend/core-components.md
git mv frontend/docs/LLM_HARNESS_AGENT.md docs/architecture/frontend/llm-harness.md
git mv frontend/docs/MOCK_HARNESS.md docs/architecture/frontend/mock-harness.md
git mv frontend/docs/BACKEND_CONNECTION.md docs/architecture/frontend/backend-connection.md
git mv frontend/docs/STATE_AND_LOCALIZATION.md docs/architecture/frontend/state-and-localization.md
```

- [ ] **Step 3: Rewrite backend source-code links to blob URLs**

Backend docs referenced source with `../../src/…`. Convert to blob permalinks:

```bash
sed -i '' 's#](\.\./\.\./src/#](https://github.com/delfianto/the-bannered-mare/blob/main/backend/src/#g' docs/architecture/backend/*.md
```

- [ ] **Step 4: Rewrite frontend source-code links to blob URLs**

Frontend docs referenced source with `../src/…` and a few repo-root files (`../vite.config.ts`):

```bash
sed -i '' 's#](\.\./src/#](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/src/#g' docs/architecture/frontend/*.md
sed -i '' 's#](\.\./vite\.config\.ts#](https://github.com/delfianto/the-bannered-mare/blob/main/frontend/vite.config.ts#g' docs/architecture/frontend/*.md
```

- [ ] **Step 5: Find any remaining relative `../` links and fix them**

Run: `grep -rn '](\.\.' docs/architecture` 
Expected: ideally no output. For any hit: if it points at source, convert to the matching blob URL (`.../blob/main/backend/…` or `.../blob/main/frontend/…`); if it points at another doc now in the site, rewrite to a site-absolute path (e.g. `[…](/architecture/frontend/backend-connection)`).

- [ ] **Step 6: Turn `docs/architecture/index.md` into the section landing**

The moved `backend/docs/README.md` is a backend-only index. Replace its body with an Architecture landing that covers both halves:

```md
---
title: Architecture
---

# Architecture

How The Bannered Mare is built, split by half.

## Backend

- [Project Structure](/architecture/backend/project-structure)
- [Persistence Layer](/architecture/backend/persistence)
- [LLM Integration](/architecture/backend/llm-integration)
- [Prompt System](/architecture/backend/prompt-system)
- [Characters & Personas](/architecture/backend/characters-and-personas)

## Frontend

- [Design System](/architecture/frontend/design-system)
- [Main Screens](/architecture/frontend/main-screens)
- [Core Components](/architecture/frontend/core-components)
- [LLM Harness](/architecture/frontend/llm-harness)
- [Mock Harness](/architecture/frontend/mock-harness)
- [Backend Connection](/architecture/frontend/backend-connection)
- [State & Localization](/architecture/frontend/state-and-localization)
```

- [ ] **Step 7: Create `docs/.vitepress/sidebar.architecture.ts`**

```ts
import type { DefaultTheme } from 'vitepress'

export const architectureSidebar: DefaultTheme.SidebarItem[] = [
  { text: 'Overview', link: '/architecture/' },
  {
    text: 'Backend',
    collapsed: false,
    items: [
      { text: 'Project Structure', link: '/architecture/backend/project-structure' },
      { text: 'Persistence Layer', link: '/architecture/backend/persistence' },
      { text: 'LLM Integration', link: '/architecture/backend/llm-integration' },
      { text: 'Prompt System', link: '/architecture/backend/prompt-system' },
      { text: 'Characters & Personas', link: '/architecture/backend/characters-and-personas' },
    ],
  },
  {
    text: 'Frontend',
    collapsed: false,
    items: [
      { text: 'Design System', link: '/architecture/frontend/design-system' },
      { text: 'Main Screens', link: '/architecture/frontend/main-screens' },
      { text: 'Core Components', link: '/architecture/frontend/core-components' },
      { text: 'LLM Harness', link: '/architecture/frontend/llm-harness' },
      { text: 'Mock Harness', link: '/architecture/frontend/mock-harness' },
      { text: 'Backend Connection', link: '/architecture/frontend/backend-connection' },
      { text: 'State & Localization', link: '/architecture/frontend/state-and-localization' },
    ],
  },
]
```

- [ ] **Step 8: Register in `docs/.vitepress/config.mts`**

Add import: `import { architectureSidebar } from './sidebar.architecture'`
Add nav item after Guide: `{ text: 'Architecture', link: '/architecture/' }`
Add sidebar mapping: `'/architecture/': architectureSidebar,`

- [ ] **Step 9: Verify the build passes (dead-link check is the test)**

Run: `cd docs && bun run docs:build`
Expected: `build complete`, zero dead links. If any internal link errors, fix per Step 5 and rebuild.

- [ ] **Step 10: Spot-check a blob URL**

Run: `grep -rn 'blob/main/backend/src' docs/architecture/backend | head -1`
Expected: at least one rewritten link, e.g. `.../blob/main/backend/src/provider/gateway.py`.

- [ ] **Step 11: Commit**

```bash
git add docs/architecture docs/.vitepress/sidebar.architecture.ts docs/.vitepress/config.mts backend/docs frontend/docs
git commit -m "docs(site): migrate backend + frontend architecture docs"
```

---

### Task 4: LLM Providers section

**Files:**
- Move: `backend/docs/llm_providers/README.md` → `docs/providers/index.md` (adapt)
- Move: `backend/docs/llm_providers/PROVIDERS.md` → `docs/providers/landscape.md`
- Move: `backend/docs/llm_providers/{OPENAI,ANTHROPIC,GEMINI,XAI,OPENROUTER,OLLAMA,LOCAL_BACKENDS}.md` → `docs/providers/{openai,anthropic,gemini,xai,openrouter,ollama,local-backends}.md`
- Create: `docs/.vitepress/sidebar.providers.ts`
- Modify: `docs/.vitepress/config.mts`

**Interfaces:**
- Produces: `providersSidebar`; `/providers/` sidebar; nav item `LLM Providers`.

- [ ] **Step 1: Move the provider docs**

```bash
mkdir -p docs/providers
git mv backend/docs/llm_providers/README.md docs/providers/index.md
git mv backend/docs/llm_providers/PROVIDERS.md docs/providers/landscape.md
git mv backend/docs/llm_providers/OPENAI.md docs/providers/openai.md
git mv backend/docs/llm_providers/ANTHROPIC.md docs/providers/anthropic.md
git mv backend/docs/llm_providers/GEMINI.md docs/providers/gemini.md
git mv backend/docs/llm_providers/XAI.md docs/providers/xai.md
git mv backend/docs/llm_providers/OPENROUTER.md docs/providers/openrouter.md
git mv backend/docs/llm_providers/OLLAMA.md docs/providers/ollama.md
git mv backend/docs/llm_providers/LOCAL_BACKENDS.md docs/providers/local-backends.md
```

- [ ] **Step 2: Fix doc-to-doc links inside the moved files**

The old `README.md` and `PROVIDERS.md` linked siblings by bare uppercase filename (e.g. `](OPENAI.md)`, `](PROVIDERS.md)`). Rewrite them to the new kebab site-absolute paths:

```bash
cd docs/providers
sed -i '' \
  -e 's#](PROVIDERS\.md)#](/providers/landscape)#g' \
  -e 's#](OPENAI\.md)#](/providers/openai)#g' \
  -e 's#](ANTHROPIC\.md)#](/providers/anthropic)#g' \
  -e 's#](GEMINI\.md)#](/providers/gemini)#g' \
  -e 's#](XAI\.md)#](/providers/xai)#g' \
  -e 's#](OPENROUTER\.md)#](/providers/openrouter)#g' \
  -e 's#](OLLAMA\.md)#](/providers/ollama)#g' \
  -e 's#](LOCAL_BACKENDS\.md)#](/providers/local-backends)#g' \
  index.md landscape.md
cd ../..
```

- [ ] **Step 3: Rewrite any source-code / cross-folder links**

Run: `grep -rn '](\.\.\|](\./\|\.md)' docs/providers`
Expected: no remaining `.md)` bare links and no `../` links. Convert any `../../src/…` to `.../blob/main/backend/src/…`; convert any remaining bare `NAME.md` doc links to `/providers/<kebab>`.

- [ ] **Step 4: Add a title to `docs/providers/index.md`**

Ensure the first line is `# LLM Providers` (keep the existing official-docs links and the accuracy disclaimer blockquote from the old README body).

- [ ] **Step 5: Create `docs/.vitepress/sidebar.providers.ts`**

```ts
import type { DefaultTheme } from 'vitepress'

export const providersSidebar: DefaultTheme.SidebarItem[] = [
  { text: 'Overview', link: '/providers/' },
  { text: 'Landscape & Gaps', link: '/providers/landscape' },
  { text: 'OpenAI', link: '/providers/openai' },
  { text: 'Anthropic', link: '/providers/anthropic' },
  { text: 'Gemini', link: '/providers/gemini' },
  { text: 'xAI', link: '/providers/xai' },
  { text: 'OpenRouter', link: '/providers/openrouter' },
  { text: 'Ollama', link: '/providers/ollama' },
  { text: 'Local Backends', link: '/providers/local-backends' },
]
```

- [ ] **Step 6: Register in `docs/.vitepress/config.mts`**

Add import `import { providersSidebar } from './sidebar.providers'`, nav item `{ text: 'LLM Providers', link: '/providers/' }`, and sidebar mapping `'/providers/': providersSidebar,`.

- [ ] **Step 7: Verify the build passes**

Run: `cd docs && bun run docs:build`
Expected: `build complete`, zero dead links.

- [ ] **Step 8: Commit**

```bash
git add docs/providers docs/.vitepress/sidebar.providers.ts docs/.vitepress/config.mts backend/docs
git commit -m "docs(site): migrate LLM provider reference"
```

---

### Task 5: SillyTavern Study section

**Files:**
- Move: `backend/docs/st_analysis/README.md` → `docs/sillytavern/index.md` (rewrite as study landing with pairing table)
- Move: `backend/docs/st_analysis/{13 topic files}` → `docs/sillytavern/analysis/{kebab}.md`
- Move: `backend/docs/st_comparison/{13 topic files}` → `docs/sillytavern/comparison/{kebab}.md`
- Remove: `backend/docs/st_comparison/README.md` (content folded into the study landing)
- Create: `docs/.vitepress/sidebar.sillytavern.ts`
- Modify: `docs/.vitepress/config.mts`

Topic kebab map: `CODE_STRUCTURE→code-structure`, `LLM_PROVIDER→providers`, `PROMPTING→prompting`, `STREAMING_HANDLER→streaming`, `CHARACTER_CARD→character-cards`, `WORLD_LORE→world-lore`, `CHAT_SYSTEM→chat-system`, `RAG_PIPELINE→rag`, `SLASH_COMMANDS→slash-commands`, `TOOL_CALLING→tool-calling`, `EXTENSIONS→extensions`, `TAGS_STATS_DATA→tags-stats-data`, `PRESET→presets`.

**Interfaces:**
- Produces: `sillytavernSidebar`; `/sillytavern/` sidebar; nav item `SillyTavern Study`.

- [ ] **Step 1: Move analysis topics**

```bash
mkdir -p docs/sillytavern/analysis docs/sillytavern/comparison
git mv backend/docs/st_analysis/README.md docs/sillytavern/index.md
for pair in \
  "CODE_STRUCTURE:code-structure" "LLM_PROVIDER:providers" "PROMPTING:prompting" \
  "STREAMING_HANDLER:streaming" "CHARACTER_CARD:character-cards" "WORLD_LORE:world-lore" \
  "CHAT_SYSTEM:chat-system" "RAG_PIPELINE:rag" "SLASH_COMMANDS:slash-commands" \
  "TOOL_CALLING:tool-calling" "EXTENSIONS:extensions" "TAGS_STATS_DATA:tags-stats-data" \
  "PRESET:presets"; do
  src="${pair%%:*}"; dst="${pair##*:}"
  git mv "backend/docs/st_analysis/${src}.md" "docs/sillytavern/analysis/${dst}.md"
done
```

- [ ] **Step 2: Move comparison topics**

```bash
git rm backend/docs/st_comparison/README.md
for pair in \
  "CODE_STRUCTURE:code-structure" "LLM_PROVIDER:providers" "PROMPTING:prompting" \
  "STREAMING_HANDLER:streaming" "CHARACTER_CARD:character-cards" "WORLD_LORE:world-lore" \
  "CHAT_SYSTEM:chat-system" "RAG_PIPELINE:rag" "SLASH_COMMANDS:slash-commands" \
  "TOOL_CALLING:tool-calling" "EXTENSIONS:extensions" "TAGS_STATS_DATA:tags-stats-data" \
  "PRESET:presets"; do
  src="${pair%%:*}"; dst="${pair##*:}"
  git mv "backend/docs/st_comparison/${src}.md" "docs/sillytavern/comparison/${dst}.md"
done
```

- [ ] **Step 3: Fix cross-folder / source links in the moved topic files**

Comparison files reference analysis files (e.g. `../st_analysis/TAGS_STATS_DATA.md`). Fix the one known cross-link, then sweep for the rest (`sed` per-slug is error-prone across the uppercase→kebab rename, so the `grep` sweep is the real safety net):

```bash
sed -i '' 's#](\.\./st_analysis/TAGS_STATS_DATA\.md)#](/sillytavern/analysis/tags-stats-data)#g' docs/sillytavern/comparison/tags-stats-data.md
```

Then sweep for anything left:

Run: `grep -rn '](\.\.\|st_analysis\|st_comparison\|](\./' docs/sillytavern`
Expected: no output. Fix any remaining hit by hand to a `/sillytavern/analysis/<kebab>` or `/sillytavern/comparison/<kebab>` site path, or a blob URL if it points at source.

- [ ] **Step 4: Rewrite `docs/sillytavern/index.md` as the study landing**

Replace the body (the old analysis README) with an intro + a pairing table. Preserve the accuracy/date disclaimer from the old READMEs at the top:

```md
---
title: SillyTavern Study
---

# SillyTavern Study

> Based on SillyTavern v1.17.0 (analysis dated 2026-04-07). Two angles per topic:
> a deep **Analysis** of SillyTavern's own source, and a **Comparison** with how
> The Bannered Mare solves the same problem.

| Topic | Analysis | Comparison |
|-------|----------|------------|
| Code Structure | [Analysis](/sillytavern/analysis/code-structure) | [Comparison](/sillytavern/comparison/code-structure) |
| Prompting | [Analysis](/sillytavern/analysis/prompting) | [Comparison](/sillytavern/comparison/prompting) |
| Providers | [Analysis](/sillytavern/analysis/providers) | [Comparison](/sillytavern/comparison/providers) |
| Streaming | [Analysis](/sillytavern/analysis/streaming) | [Comparison](/sillytavern/comparison/streaming) |
| Character Cards | [Analysis](/sillytavern/analysis/character-cards) | [Comparison](/sillytavern/comparison/character-cards) |
| World / Lore | [Analysis](/sillytavern/analysis/world-lore) | [Comparison](/sillytavern/comparison/world-lore) |
| Chat System | [Analysis](/sillytavern/analysis/chat-system) | [Comparison](/sillytavern/comparison/chat-system) |
| RAG | [Analysis](/sillytavern/analysis/rag) | [Comparison](/sillytavern/comparison/rag) |
| Slash Commands | [Analysis](/sillytavern/analysis/slash-commands) | [Comparison](/sillytavern/comparison/slash-commands) |
| Tool Calling | [Analysis](/sillytavern/analysis/tool-calling) | [Comparison](/sillytavern/comparison/tool-calling) |
| Extensions | [Analysis](/sillytavern/analysis/extensions) | [Comparison](/sillytavern/comparison/extensions) |
| Tags / Stats / Data | [Analysis](/sillytavern/analysis/tags-stats-data) | [Comparison](/sillytavern/comparison/tags-stats-data) |
| Presets | [Analysis](/sillytavern/analysis/presets) | [Comparison](/sillytavern/comparison/presets) |
```

- [ ] **Step 5: Create `docs/.vitepress/sidebar.sillytavern.ts`**

```ts
import type { DefaultTheme } from 'vitepress'

const topics: [slug: string, label: string][] = [
  ['code-structure', 'Code Structure'],
  ['prompting', 'Prompting'],
  ['providers', 'Providers'],
  ['streaming', 'Streaming'],
  ['character-cards', 'Character Cards'],
  ['world-lore', 'World / Lore'],
  ['chat-system', 'Chat System'],
  ['rag', 'RAG'],
  ['slash-commands', 'Slash Commands'],
  ['tool-calling', 'Tool Calling'],
  ['extensions', 'Extensions'],
  ['tags-stats-data', 'Tags / Stats / Data'],
  ['presets', 'Presets'],
]

export const sillytavernSidebar: DefaultTheme.SidebarItem[] = [
  { text: 'Overview', link: '/sillytavern/' },
  {
    text: 'Analysis',
    collapsed: false,
    items: topics.map(([slug, label]) => ({ text: label, link: `/sillytavern/analysis/${slug}` })),
  },
  {
    text: 'Comparison',
    collapsed: false,
    items: topics.map(([slug, label]) => ({ text: label, link: `/sillytavern/comparison/${slug}` })),
  },
]
```

- [ ] **Step 6: Register in `docs/.vitepress/config.mts`**

Add import `import { sillytavernSidebar } from './sidebar.sillytavern'`, nav item `{ text: 'SillyTavern Study', link: '/sillytavern/' }`, and sidebar mapping `'/sillytavern/': sillytavernSidebar,`.

- [ ] **Step 7: Verify the build passes**

Run: `cd docs && bun run docs:build`
Expected: `build complete`, zero dead links. All 26 topic pages + landing reachable.

- [ ] **Step 8: Commit**

```bash
git add docs/sillytavern docs/.vitepress/sidebar.sillytavern.ts docs/.vitepress/config.mts backend/docs
git commit -m "docs(site): migrate SillyTavern analysis + comparison study"
```

---

### Task 6: Consolidate superpowers artifacts & drop empty dirs

**Files:**
- Move: `backend/docs/superpowers/plans/*` → `docs/superpowers/plans/`
- Verify: `backend/docs/` and `frontend/docs/` no longer exist

**Interfaces:**
- Consumes: all prior migrations (so only `superpowers/` remains under `backend/docs/`).

- [ ] **Step 1: Move the superpowers plans under the excluded root `docs/superpowers/`**

```bash
mkdir -p docs/superpowers/plans
git mv backend/docs/superpowers/plans/*.md docs/superpowers/plans/
```

- [ ] **Step 2: Confirm the old docs trees are gone**

Run: `ls backend/docs frontend/docs 2>&1`
Expected: both report "No such file or directory" (git drops now-empty tracked dirs automatically once their files are moved).

- [ ] **Step 3: Confirm superpowers is excluded from the built site**

Run: `cd docs && bun run docs:build && find .vitepress/dist -path '*superpowers*' | head`
Expected: `build complete` and **no** output from `find` (nothing under `superpowers/` was built).

- [ ] **Step 4: Commit**

```bash
git add backend/docs docs/superpowers
git commit -m "docs(site): consolidate superpowers artifacts under docs/ (excluded from build)"
```

---

### Task 7: Finalize home page & fix references outside the site

**Files:**
- Modify: `docs/index.md` (replace stub with the real home)
- Modify: `backend/AGENTS.md` (repoint doc links)
- Modify: `frontend/AGENTS.md` (repoint doc links)
- Modify: `README.md` (add docs-site pointer)
- Modify: `AGENTS.md` (root — add docs-site pointer)
- Modify: `frontend/package.json` (`fmt`/`fmt:check` no longer reference `docs`)

Note: `backend/CLAUDE.md`, `frontend/CLAUDE.md`, and root `CLAUDE.md` are symlinks to their `AGENTS.md` — editing `AGENTS.md` covers them.

**Interfaces:**
- Consumes: all section index pages (`/guide/`, `/architecture/`, `/providers/`, `/sillytavern/`) now exist, so the home hero/feature links resolve.

- [ ] **Step 1: Replace `docs/index.md` with the real home**

```md
---
layout: home
hero:
  name: The Bannered Mare
  text: AI-powered local roleplay sessions
  tagline: A self-hostable platform inspired by SillyTavern — providers, characters, prompts, RAG, and streaming.
  actions:
    - theme: brand
      text: Get Started
      link: /guide/
    - theme: alt
      text: View on GitHub
      link: https://github.com/delfianto/the-bannered-mare
features:
  - title: Guide
    details: Install and run both halves — the FastAPI backend and the Vue 3 frontend.
    link: /guide/
  - title: Architecture
    details: How it's built — modular monolith, prompt system, RAG, and the Vue SPA.
    link: /architecture/
  - title: LLM Providers
    details: Reference for the supported providers and local backends.
    link: /providers/
  - title: SillyTavern Study
    details: Deep analysis of SillyTavern and a comparison with The Bannered Mare.
    link: /sillytavern/
---
```

- [ ] **Step 2: Repoint `backend/AGENTS.md` implementation-doc links**

The header links list (and any inline links) point at `docs/implementation/…`. Update each to the new location, e.g.:

```
[Project Structure & Modular Monolith](docs/implementation/PROJECT_STRUCTURE.md)
→ [Project Structure & Modular Monolith](../docs/architecture/backend/project-structure.md)
```

Apply the same relative-path fix (`../docs/architecture/backend/<kebab>.md`) to PERSISTENCE_LAYER, LLM_INTEGRATION, PROMPT_SYSTEM, CHARACTERS_AND_PERSONAS. Verify none remain:

Run: `grep -n 'docs/implementation' backend/AGENTS.md`
Expected: no output.

- [ ] **Step 3: Repoint `frontend/AGENTS.md` doc links**

Update the intro links and the composable-reference link that point at `docs/*.md` to `../docs/architecture/frontend/<kebab>.md` (e.g. `docs/LLM_HARNESS_AGENT.md` → `../docs/architecture/frontend/llm-harness.md`; `docs/DESIGN_SYSTEM.md` → `../docs/architecture/frontend/design-system.md`). Verify:

Run: `grep -nE 'docs/[A-Z_]+\.md' frontend/AGENTS.md`
Expected: no output.

- [ ] **Step 4: Add a docs-site pointer to `README.md` and root `AGENTS.md`**

In root `README.md`, add near the top:

```md
📖 **Documentation site:** https://delfianto.github.io/the-bannered-mare/ (source in [`docs/`](docs/))
```

In root `AGENTS.md`, add `docs/` to the Repository Structure tree with the comment `# VitePress documentation site (deployed to GitHub Pages)`.

- [ ] **Step 5: Drop the stale `docs` argument from the frontend formatter**

In `frontend/package.json`, change:

```json
    "fmt": "vp fmt src docs AGENTS.md vite.config.ts",
    "fmt:check": "vp fmt --check src docs AGENTS.md vite.config.ts",
```

to (remove `docs` — that directory no longer exists under `frontend/`):

```json
    "fmt": "vp fmt src AGENTS.md vite.config.ts",
    "fmt:check": "vp fmt --check src AGENTS.md vite.config.ts",
```

- [ ] **Step 6: Verify the site still builds and the home links resolve**

Run: `cd docs && bun run docs:build`
Expected: `build complete`, zero dead links (home hero/feature links now resolve to real section pages).

- [ ] **Step 7: Commit**

```bash
git add docs/index.md backend/AGENTS.md frontend/AGENTS.md README.md AGENTS.md frontend/package.json
git commit -m "docs(site): finalize home page and repoint references to the new docs tree"
```

---

### Task 8: GitHub Pages deploy workflow

**Files:**
- Create: `.github/workflows/docs.yml`

**Interfaces:**
- Consumes: the buildable `docs/` project.

- [ ] **Step 1: Create `.github/workflows/docs.yml`**

```yaml
name: Deploy Docs

on:
  push:
    branches: [main]
    paths:
      - 'docs/**'
      - '.github/workflows/docs.yml'
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: docs
    steps:
      - uses: actions/checkout@v4
      - uses: oven-sh/setup-bun@v2
        with:
          bun-version: '1.3.14'
      - run: bun install --frozen-lockfile
      - run: bun run docs:build
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: docs/.vitepress/dist

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Validate the workflow YAML parses**

Run: `cd docs && bun x js-yaml ../.github/workflows/docs.yml >/dev/null && echo OK`
Expected: `OK` (no YAML syntax error). If `js-yaml` is unavailable, open the file and confirm indentation is consistent.

- [ ] **Step 3: Document the one-time Pages enablement (manual, cannot be scripted)**

Add to the top of `.github/workflows/docs.yml` a comment line, and note in the PR/commit body:

```yaml
# One-time setup: repo Settings → Pages → Build and deployment → Source = "GitHub Actions".
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/docs.yml
git commit -m "ci(docs): deploy the VitePress site to GitHub Pages"
```

---

## Self-Review

**1. Spec coverage:**
- D1 VitePress → Task 1. ✓
- D2 root `docs/`, consolidate via `git mv` → Tasks 1, 3, 4, 5, 6. ✓
- D3 isolated `docs/package.json` → Task 1. ✓
- D4 exclude AGENTS/superpowers → Task 1 (`srcExclude`), Task 6 (verify absent from dist). ✓
- D5 blob permalinks → Task 3 (Steps 3–5), plus provider/sillytavern sweeps (Tasks 4–5). ✓
- D6 Pages workflow + base path → Task 1 (`base`), Task 8 (`docs.yml`). ✓
- D7 local search → Task 1. ✓
- IA / nav (spec §6) → Tasks 2–5 sidebars + nav; SillyTavern pairing table → Task 5 Step 4. ✓
- File move map (spec §7.1) → Tasks 3–6 (every row covered; orphaned `PRESET.md` → `presets.md` in Task 5). ✓
- Guide vs READMEs (spec §7.2) → Task 2 (seed, READMEs stay) + Task 7 (README pointer). ✓
- Link handling & AGENTS/fmt fixups (spec §7.3) → Task 3 Steps 3–5, Task 7 Steps 2–5. ✓
- Title normalization via config (spec §7.4) → nav labels in Tasks 2–5 sidebars. ✓
- Acceptance criteria (spec §10) → build/dead-link checks each task; excluded-from-dist check Task 6 Step 3; deploy Task 8. ✓

**2. Placeholder scan:** No "TBD/TODO/handle edge cases". Doc bodies are relocated as-is (explicitly, per Global Constraints) — not placeholders. Guide pages name their exact README source sections.

**3. Type consistency:** Each sidebar module exports a distinct const (`guideSidebar`, `architectureSidebar`, `providersSidebar`, `sillytavernSidebar`) typed `DefaultTheme.SidebarItem[]`, imported by `config.mts` under matching path keys. Kebab slugs in the move maps, sidebar links, and the pairing table all match.

**Note for the implementer:** Task 5 Step 3's uppercase→kebab cross-link rename is not fully scripted — apply the one shown `sed`, then rely on the `grep` sweep to catch remaining cross-links by hand. VitePress's dead-link build check (Step 7) is the backstop: nothing broken can ship green.
