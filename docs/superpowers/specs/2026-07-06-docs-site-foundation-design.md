# Docs Site — Foundation (Design Spec)

- **Date:** 2026-07-06
- **Status:** Approved (design); pending spec review
- **Scope:** Foundation sub-project only (see §3). Content rewrites are separate specs.
- **Repo:** `delfianto/the-bannered-mare` (GitHub project repo)

## 1. Context & Problem

Documentation is scattered across ~57 markdown files in two domain-specific trees
(`backend/docs/`, `frontend/docs/`) plus three product `README.md` files. There is no
browsable, linkable home for it: setup instructions, implementation deep-dives, the LLM
provider reference, and the SillyTavern analysis/comparison study all live as loose files a
reader has to navigate by hand on GitHub.

The content itself is in good shape for a static-site generator: every file has a single
clean `# H1` and well-nested headings, so navigation and per-page tables of contents can be
generated automatically. The gaps are structural, not editorial: no landing/overview pages,
relative links into source code (`../src/…`) that break once files relocate, and two orphaned
`PRESET.md` files linked from nothing.

## 2. Goal & Non-Goals

**Goal:** Stand up a single, structured, deployed documentation website — a VitePress site on
GitHub Pages — that makes the *existing* documentation browsable end to end, from "how to use
and set up the app" through "how it's implemented" to "what we learned analyzing SillyTavern."

**Non-goals (this sub-project):** Rewriting doc bodies, authoring new user guides/tutorials,
adding screenshots, restructuring the SillyTavern study prose, or polishing the provider
reference. Those are follow-on sub-projects (§10). Foundation migrates content **as-is** —
links fixed, nav labels tidied, landing pages added — so the site ships and is browsable.

## 3. Overall Decomposition (context)

The full "docs overhaul" is decomposed into sequenced sub-projects, each with its own
spec → plan → implementation cycle:

1. **Foundation** ← *this spec*. SSG, repo layout, information architecture, GitHub Pages CI,
   migrate existing content in (cleaned up, links fixed, orphans placed, landing pages added).
2. **User & operator docs** — task-based getting-started, install/setup, how-to-use, screenshots.
3. **Developer / architecture docs** — polish backend + frontend guides; durable source-link convention.
4. **SillyTavern study** — restructure analysis + comparison into coherent research prose.
5. **LLM provider reference** — polish the provider API reference.

Sub-projects 2–5 slot into the navigation this Foundation defines.

## 4. Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **VitePress** as the SSG | Vue 3 + Vite native — same toolchain family as the frontend, installs under Bun; markdown-first, built-in local search, auto sidebar/TOC, easy Pages deploy. |
| D2 | Site rooted at **`docs/`** (repo root); `backend/docs/` + `frontend/docs/` content **consolidated** into it via `git mv` | Single source tree VitePress can serve; matches the earlier "consolidate docs to root" instinct; preserves file history. |
| D3 | **Isolated `docs/package.json`** (VitePress-only), Bun scripts | Keeps docs tooling out of the frontend app's dependency graph. |
| D4 | **Exclude** `AGENTS.md`/`CLAUDE.md` family and `superpowers/` from the built site | They are AI-agent instructions and work artifacts, not product docs. |
| D5 | Rewrite source-code links to **GitHub blob permalinks** pinned to `main` | Keeps jump-to-source working from the deployed site (relative `../src/…` links can't). |
| D6 | Deploy to **GitHub Pages** via a dedicated `docs.yml` Action; `base: '/the-bannered-mare/'` | Project repo → Pages serves under `/the-bannered-mare/`. Sibling to existing `backend-ci.yml`/`frontend-ci.yml`. |
| D7 | **Built-in local search** (MiniSearch) | No external service, no keys. |

## 5. Architecture & Tooling

### 5.1 Repo layout (target)

```
docs/
├── package.json                 # vitepress devDep + scripts (docs:dev/build/preview)
├── .vitepress/
│   └── config.mts               # site config: title, base, nav, sidebar, search, srcExclude
├── index.md                     # home (hero) — seeded from root README
├── guide/
│   ├── index.md                 # Introduction
│   ├── quick-start.md           # combined quick start (both halves)
│   ├── setup-backend.md         # seeded from backend/README
│   └── setup-frontend.md        # seeded from frontend/README
├── architecture/
│   ├── index.md
│   ├── backend/
│   │   ├── index.md
│   │   ├── project-structure.md
│   │   ├── persistence.md
│   │   ├── llm-integration.md
│   │   ├── prompt-system.md
│   │   └── characters-and-personas.md
│   └── frontend/
│       ├── index.md
│       ├── design-system.md
│       ├── main-screens.md
│       ├── core-components.md
│       ├── llm-harness.md
│       ├── mock-harness.md
│       ├── backend-connection.md
│       └── state-and-localization.md
├── providers/
│   ├── index.md                 # seeded from llm_providers/README
│   ├── landscape.md             # from PROVIDERS.md
│   ├── openai.md · anthropic.md · gemini.md · xai.md · openrouter.md · ollama.md · local-backends.md
├── sillytavern/
│   ├── index.md                 # study intro + per-topic Analysis/Comparison pairing table
│   ├── analysis/                # 13 topic files (kebab-case)
│   └── comparison/              # 13 topic files (kebab-case)
└── superpowers/                 # specs + moved plans — EXCLUDED from build (srcExclude)
    ├── specs/
    └── plans/
```

`.vitepress/dist/` (build output) and `.vitepress/cache/` are gitignored.

### 5.2 Scripts (`docs/package.json`)

- `docs:dev` → `vitepress dev`
- `docs:build` → `vitepress build`
- `docs:preview` → `vitepress preview`

Run via Bun. VitePress dead-link checking stays on (build fails on broken internal links).

## 6. Information Architecture (nav)

Top-level nav ordered to match the reading arc *use it → set it up → how it's built → what we
learned*:

- **Guide** — Introduction · Quick Start · Setup (Backend) · Setup (Frontend)
- **Architecture** → **Backend** (Project Structure · Persistence · LLM Integration · Prompt
  System · Characters & Personas) · **Frontend** (Design System · Main Screens · Core
  Components · LLM Harness · Mock Harness · Backend Connection · State & Localization)
- **LLM Providers** — Overview · Landscape · OpenAI · Anthropic · Gemini · xAI · OpenRouter ·
  Ollama · Local Backends
- **SillyTavern Study** — landing page pairs each topic's *Analysis* and *Comparison* links in a
  table; sidebar exposes two groups (**Analysis**, **Comparison**) in matching topic order.
  Topics: Code Structure · Prompting · Providers · Streaming · Character Cards · World/Lore ·
  Chat System · RAG · Slash Commands · Tool Calling · Extensions · Tags/Stats · Presets.

**Nav labels are defined in `config.mts`** (clean, short) — the site does not depend on
rewriting the body `# H1` prefixes. This keeps title normalization to config, not body edits.

Each top-level section has an `index.md` landing page. The two orphaned `PRESET.md` files
become the "Presets" topic under both Analysis and Comparison.

## 7. Content Migration Plan

### 7.1 File move map (`git mv`, history preserved)

| From | To |
|------|----|
| `backend/docs/implementation/PROJECT_STRUCTURE.md` | `docs/architecture/backend/project-structure.md` |
| `backend/docs/implementation/PERSISTENCE_LAYER.md` | `docs/architecture/backend/persistence.md` |
| `backend/docs/implementation/LLM_INTEGRATION.md` | `docs/architecture/backend/llm-integration.md` |
| `backend/docs/implementation/PROMPT_SYSTEM.md` | `docs/architecture/backend/prompt-system.md` |
| `backend/docs/implementation/CHARACTERS_AND_PERSONAS.md` | `docs/architecture/backend/characters-and-personas.md` |
| `frontend/docs/DESIGN_SYSTEM.md` | `docs/architecture/frontend/design-system.md` |
| `frontend/docs/MAIN_SCREENS.md` | `docs/architecture/frontend/main-screens.md` |
| `frontend/docs/CORE_COMPONENTS.md` | `docs/architecture/frontend/core-components.md` |
| `frontend/docs/LLM_HARNESS_AGENT.md` | `docs/architecture/frontend/llm-harness.md` |
| `frontend/docs/MOCK_HARNESS.md` | `docs/architecture/frontend/mock-harness.md` |
| `frontend/docs/BACKEND_CONNECTION.md` | `docs/architecture/frontend/backend-connection.md` |
| `frontend/docs/STATE_AND_LOCALIZATION.md` | `docs/architecture/frontend/state-and-localization.md` |
| `backend/docs/llm_providers/README.md` | `docs/providers/index.md` (adapted) |
| `backend/docs/llm_providers/PROVIDERS.md` | `docs/providers/landscape.md` |
| `backend/docs/llm_providers/{OPENAI,ANTHROPIC,GEMINI,XAI,OPENROUTER,OLLAMA,LOCAL_BACKENDS}.md` | `docs/providers/{openai,anthropic,gemini,xai,openrouter,ollama,local-backends}.md` |
| `backend/docs/st_analysis/{TOPIC}.md` | `docs/sillytavern/analysis/{topic}.md` (kebab-case; `PRESET.md`→`presets.md`) |
| `backend/docs/st_comparison/{TOPIC}.md` | `docs/sillytavern/comparison/{topic}.md` (kebab-case) |
| `backend/docs/st_analysis/README.md`, `st_comparison/README.md` | folded into `docs/sillytavern/index.md` |
| `backend/docs/README.md` | folded into section index pages (`architecture/index.md`, etc.); not the home page |
| `backend/docs/superpowers/plans/*` | `docs/superpowers/plans/*` (excluded from build) |

Topic kebab-case map: `CODE_STRUCTURE`→`code-structure`, `LLM_PROVIDER`→`providers`,
`PROMPTING`→`prompting`, `STREAMING_HANDLER`→`streaming`, `CHARACTER_CARD`→`character-cards`,
`WORLD_LORE`→`world-lore`, `CHAT_SYSTEM`→`chat-system`, `RAG_PIPELINE`→`rag`,
`SLASH_COMMANDS`→`slash-commands`, `TOOL_CALLING`→`tool-calling`, `EXTENSIONS`→`extensions`,
`TAGS_STATS_DATA`→`tags-stats-data`, `PRESET`→`presets`.

After the moves, `backend/docs/` and `frontend/docs/` are removed (empty).

### 7.2 Guide pages vs READMEs

`docs/index.md` and `docs/guide/*` are **seeded** from the three `README.md` files (light
extraction: intro, quick start, setup). The repo `README.md` files **stay in place** as the
GitHub repo entry points and gain a link to the docs site. Some overlap is accepted for
Foundation; the richer user-guide content is sub-project 2.

### 7.3 Link handling

- **Doc-to-doc links:** rewrite the handful of cross-folder links to their new paths; VitePress
  dead-link checking enforces correctness at build time.
- **Source-code links:** rewrite `../src/…` (frontend docs) and `../../src/…` (backend docs) to
  `https://github.com/delfianto/the-bannered-mare/blob/main/<frontend|backend>/src/…`.
  Backend docs' `../../src/X` → `…/blob/main/backend/src/X`; frontend docs' `../src/X` →
  `…/blob/main/frontend/src/X`. Plain-text `file.py:line` references are left as code spans.
- **`AGENTS.md`/`CLAUDE.md` doc links:** repoint the now-dangling relative links (e.g.
  `backend/AGENTS.md` → `docs/implementation/*`, `frontend/AGENTS.md` → `docs/*`) to the new
  `docs/…` locations. Add a docs-site pointer to the root `README.md`/`AGENTS.md`.
- **Frontend scripts:** `frontend/package.json` `fmt`/`fmt:check` list a `docs` path argument
  that no longer exists after the move — remove it.

### 7.4 Title normalization

Handled in `config.mts` nav/sidebar labels (short, prefix-free). No body `# H1` edits required.
Optional per-page `title` frontmatter only where the browser tab title needs to differ from H1.

## 8. Build & Deploy

- **Workflow:** `.github/workflows/docs.yml`, triggered on push to `main` touching `docs/**`
  (plus manual `workflow_dispatch`). Steps: checkout → setup Bun → `bun install` (in `docs/`) →
  `bun run docs:build` → upload `docs/.vitepress/dist` as a Pages artifact → deploy via
  `actions/deploy-pages`. Permissions: `pages: write`, `id-token: write`; concurrency guard on
  the `pages` group.
- **Config:** `base: '/the-bannered-mare/'`; `srcExclude` covers `superpowers/**` (and any
  `README`-only fragments not meant as pages).
- **Search:** `themeConfig.search.provider = 'local'`.
- **Operator step (one-time, manual):** enable GitHub Pages with source = **GitHub Actions** in
  repo settings. Documented in the plan; cannot be done from the repo alone.

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Base-path breakage if a custom domain is added later | Single `base` constant in `config.mts`; documented. |
| Blob URLs pinned to `main` rot as code moves | Acceptable for Foundation; can pin to a tag/commit in a later pass. |
| README ↔ guide-page content drift | Keep READMEs concise and link to the site; deeper guides in sub-project 2. |
| SillyTavern study is dated (ST v1.17.0, 2026-04-07) | Surface the date on the study landing page; content refresh is sub-project 4. |
| Large reference pages (e.g. Gemini ~1600 lines) | VitePress handles them; deep on-page TOC renders well. |

## 10. Acceptance Criteria

1. `bun run docs:dev` serves the site locally with the full §6 navigation.
2. `bun run docs:build` succeeds with **zero dead internal links**.
3. All in-scope docs are reachable from the nav; both orphaned `PRESET.md` files are placed.
4. Source-code references resolve to GitHub blob URLs (spot-checked across backend + frontend docs).
5. `AGENTS.md`/`CLAUDE.md` doc links resolve (no dangling relative links); `frontend` `fmt`
   script no longer references a missing `docs` path.
6. `AGENTS.md` family and `superpowers/**` are absent from the built site.
7. `docs.yml` builds and deploys; the site loads at `https://delfianto.github.io/the-bannered-mare/`.

## 11. Follow-on Sub-Projects (not this spec)

Sub-projects 2–5 from §3, each brainstormed → spec'd → planned separately, filling in the
Guide, Architecture, SillyTavern Study, and Provider sections with rewritten, richer content.
