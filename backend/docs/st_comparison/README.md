# The Bannered Mare vs SillyTavern — Engineering Comparison

> **Important:** These documents are **not** a "this is good, that is bad" comparison.
> There is no judgment of quality or superiority here. This is a purely technical,
> engineering-focused deep dive examining how two different systems solve the same
> problems — with different languages, different architectures, and different design
> philosophies. Both approaches have legitimate trade-offs, and both serve their users well.
>
> **Credit where credit is due.** SillyTavern is the de facto standard for AI roleplay
> tooling in the community. Its developers have built and maintained an extraordinarily
> feature-rich application (~185,000 lines of code, 40+ LLM providers, a full extension
> ecosystem) that serves thousands of users daily. The breadth and depth of what the ST
> team has accomplished — largely as an open-source, community-driven effort — deserves
> genuine respect and recognition. The Bannered Mare exists because ST proved what features
> matter. These comparison documents exist because ST's codebase is worth studying.
>
> **On methodology.** The ST codebase is massive. It is simply too much for one person to
> do a thorough side-by-side comparison manually in any reasonable timeframe. These
> documents were produced with the assistance of Claude Opus 4.6, which read and analyzed
> both codebases in parallel. While we've made every effort to be accurate and fair, some
> details may be incomplete or slightly off. If you spot an error, it reflects the
> limitations of automated analysis — not a lack of respect for the source material.

---

## Documents

### Core Systems

| Document | Scope |
|----------|-------|
| [CODE_STRUCTURE.md](CODE_STRUCTURE.md) | Project layout, module boundaries, file size discipline, dependency patterns, type systems, testing, build/config |
| [LLM_PROVIDER.md](LLM_PROVIDER.md) | Provider count, adapter architecture, auth handling, parameter management, response normalization, caching, reasoning |
| [PROMPTING.md](PROMPTING.md) | Prompt assembly pipeline, component ordering, template engines, token budgeting, lore injection, multi-template slots |
| [STREAMING_HANDLER.md](STREAMING_HANDLER.md) | Stream proxy vs typed events, provider parsing, abort mechanism, reasoning content, token usage, error handling |

### Data & Content

| Document | Scope |
|----------|-------|
| [CHARACTER_CARD.md](CHARACTER_CARD.md) | Card specs, storage model, import/export formats, PNG metadata, field mapping, avatar management, character book |
| [WORLD_LORE.md](WORLD_LORE.md) | Entry data model, activation engine, insertion positions, token budget, recursion, groups, timed effects |
| [CHAT_SYSTEM.md](CHAT_SYSTEM.md) | Chat storage, message model, swipes/alternatives, editing, regeneration, branching, group chats, presets |
| [RAG_PIPELINE.md](RAG_PIPELINE.md) | Vector storage, embedding providers, Data Bank, chat vectorization, document processing (ST-only) |

### Features & Extensibility

| Document | Scope |
|----------|-------|
| [EXTENSIONS.md](EXTENSIONS.md) | ST's two-layer plugin runtime vs The Bannered Mare's API-first extensibility model |
| [SLASH_COMMANDS.md](SLASH_COMMANDS.md) | STscript command system vs headless REST API, automation models |
| [TOOL_CALLING.md](TOOL_CALLING.md) | Function calling support, provider translation, execution loop, token budgeting |
| [TAGS_STATS_DATA.md](TAGS_STATS_DATA.md) | Tag models, search/filtering, statistics tracking, data integrity approaches |

---

## Related Documentation

- **[docs/st_analysis/](../st_analysis/)** — Pure SillyTavern v1.17.0 analysis (12 documents, no comparison)
- **[docs/llm_providers/](../llm_providers/)** — LLM provider API reference docs

---

## Tool & Version Info

- **The Bannered Mare:** v0.1.5 (at time of comparison)
- **SillyTavern:** v1.17.0 (at time of comparison)
- **Author:** Claude Opus 4.6 (1M context)
- **Date:** 2026-04-07
