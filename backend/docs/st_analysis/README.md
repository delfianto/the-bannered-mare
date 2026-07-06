# SillyTavern v1.17.0 — Codebase Analysis

> **Disclaimer:** These analyses were generated using Claude Opus 4.6 with automated
> deep-dive exploration of the SillyTavern v1.17.0 source code. While every effort was
> made to read actual source files, trace code flows, and cite specific file paths and
> line numbers, **100% accuracy is not guaranteed**. The ST codebase is massive (~185K LOC
> across 340 files) and certain details may be incomplete, slightly outdated, or
> misinterpreted. If you're making implementation decisions based on these documents,
> double-check the relevant ST source files directly.

---

## Documents

### Core Systems

| Document | Description |
|----------|-------------|
| [CODE_STRUCTURE.md](CODE_STRUCTURE.md) | Overall project architecture, directory layout, module boundaries, dependency graph, file metrics |
| [LLM_PROVIDER.md](LLM_PROVIDER.md) | 40+ LLM provider integrations, request dispatch, auth patterns, parameter allowlists, response normalization |
| [PROMPTING.md](PROMPTING.md) | Client-side prompt assembly pipeline, PromptManager, 50+ macros, token budget system, instruct mode, context templates |
| [STREAMING_HANDLER.md](STREAMING_HANDLER.md) | SSE stream proxy, 8+ provider-specific parsers, abort handling, reasoning/thinking support, smooth streaming |

### Data & Content

| Document | Description |
|----------|-------------|
| [CHARACTER_CARD.md](CHARACTER_CARD.md) | TavernCard V1/V2/V3 specs, PNG metadata encoding, 5 import formats, CharX ZIP, avatar management, caching |
| [WORLD_LORE.md](WORLD_LORE.md) | World info activation engine, 35+ entry fields, 8 insertion positions, recursive scanning, groups, timed effects |
| [CHAT_SYSTEM.md](CHAT_SYSTEM.md) | JSONL chat storage, message swipes, editing, branching/bookmarks, group chats with 4 turn strategies, personas |
| [RAG_PIPELINE.md](RAG_PIPELINE.md) | Vectra vector DB, 19 embedding providers, document processing, three-tier Data Bank, chat vectorization |

### Features & Extensibility

| Document | Description |
|----------|-------------|
| [SLASH_COMMANDS.md](SLASH_COMMANDS.md) | 286 registered commands, recursive descent parser, pipe chaining, closures, 3-tier variable system, Quick Replies |
| [TOOL_CALLING.md](TOOL_CALLING.md) | Function calling across 26 providers, multi-turn recursion (depth 5), provider schema translation, extension API |
| [EXTENSIONS.md](EXTENSIONS.md) | Server plugins + frontend extensions, 14 built-in extensions, regex engine, memory/summarization, connection manager |
| [TAGS_STATS_DATA.md](TAGS_STATS_DATA.md) | Tag system with virtual folders, Fuse.js fuzzy search, per-character stats, Data Maid integrity checker |

---

## Source Version

- **SillyTavern:** v1.17.0
- **Analysis date:** 2026-04-07
- **Tool:** Claude Opus 4.6 (1M context)
