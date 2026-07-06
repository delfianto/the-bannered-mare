---
title: SillyTavern Study
---

# SillyTavern Study

> Based on SillyTavern v1.17.0 (analysis dated 2026-04-07). Two angles per topic:
> a deep **Analysis** of SillyTavern's own source, and a **Comparison** with how
> The Bannered Mare solves the same problem.

Each of the thirteen topics below is examined through two lenses — first how the incumbent
does it, then how The Bannered Mare diverges:

<Figure tag="Figure 1" title="Two lenses on every topic" id="fig-study-lenses">
<svg viewBox="0 0 720 300" role="img" aria-label="Each topic is examined as an analysis and a comparison" style="font-family:var(--vp-font-family-base)">
  <defs>
    <marker id="tbm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-arrow)"/>
    </marker>
  </defs>
  <rect x="270" y="20" width="180" height="46" rx="23" fill="var(--tbm-dgm-surface-3)" stroke="var(--tbm-dgm-border-strong)"/>
  <text x="360" y="42" text-anchor="middle" font-size="13" font-weight="700" fill="var(--tbm-dgm-ink)">One topic</text>
  <text x="360" y="58" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">e.g. RAG, streaming, world lore</text>
  <rect x="48" y="138" width="290" height="126" rx="12" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/>
  <text x="70" y="166" font-size="13" font-weight="800" fill="var(--tbm-dgm-ink)">Analysis</text>
  <text x="70" y="190" font-size="11.5" fill="var(--tbm-dgm-ink-2)">How SillyTavern v1.17.0 does it,</text>
  <text x="70" y="208" font-size="11.5" fill="var(--tbm-dgm-ink-2)">read from its own source.</text>
  <text x="70" y="240" font-size="10.5" fill="var(--tbm-dgm-faint)">The incumbent's design, on its</text>
  <text x="70" y="255" font-size="10.5" fill="var(--tbm-dgm-faint)">own terms.</text>
  <rect x="382" y="138" width="290" height="126" rx="12" fill="var(--tbm-dgm-provider-soft)" stroke="var(--tbm-dgm-provider)"/>
  <text x="404" y="166" font-size="13" font-weight="800" fill="var(--tbm-dgm-ink)">Comparison</text>
  <text x="404" y="190" font-size="11.5" fill="var(--tbm-dgm-ink-2)">SillyTavern vs The Bannered Mare —</text>
  <text x="404" y="208" font-size="11.5" fill="var(--tbm-dgm-ink-2)">the same problem, two designs.</text>
  <text x="404" y="240" font-size="10.5" fill="var(--tbm-dgm-faint)">What we kept, what we changed,</text>
  <text x="404" y="255" font-size="10.5" fill="var(--tbm-dgm-faint)">and why.</text>
  <g stroke="var(--tbm-dgm-arrow)" stroke-width="1.6" fill="none" marker-end="url(#tbm-ah)">
    <path d="M320 66 L220 136"/>
    <path d="M400 66 L500 136"/>
  </g>
</svg>
<template #caption>

**Read a topic top to bottom.** The *Analysis* page reconstructs SillyTavern's own
implementation from its source; the *Comparison* page then sets it beside The Bannered Mare's
approach to the same problem.

</template>
</Figure>

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
