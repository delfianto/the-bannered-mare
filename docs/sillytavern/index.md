---
title: SillyTavern Study
---

# SillyTavern Study

> Based on SillyTavern v1.17.0 (source study dated 2026-04-07).

Each topic below is a **comparison** of how SillyTavern and The Bannered Mare solve the same
problem. Every comparison drills into a deep **analysis** of SillyTavern's own implementation
— reconstructed from its source — which is kept as a reference and linked inline wherever the
detail matters.

<Figure tag="Figure 1" title="Read the comparison; drill into the analysis" id="fig-study-lenses">
<svg viewBox="0 0 720 200" role="img" aria-label="Each topic is a comparison that drills into a deep analysis" style="font-family:var(--vp-font-family-base)">
  <defs>
    <marker id="tbm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-arrow)"/>
    </marker>
  </defs>
  <rect x="48" y="44" width="288" height="120" rx="12" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)"/>
  <text x="192" y="76" text-anchor="middle" font-size="14" font-weight="800" fill="var(--tbm-dgm-ink)">Comparison</text>
  <text x="192" y="100" text-anchor="middle" font-size="11.5" fill="var(--tbm-dgm-ink-2)">SillyTavern vs The Bannered Mare —</text>
  <text x="192" y="118" text-anchor="middle" font-size="11.5" fill="var(--tbm-dgm-ink-2)">the same problem, two designs</text>
  <text x="192" y="146" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-faint)">— what you read —</text>
  <rect x="384" y="44" width="288" height="120" rx="12" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border-strong)"/>
  <text x="528" y="76" text-anchor="middle" font-size="14" font-weight="800" fill="var(--tbm-dgm-ink)">Analysis</text>
  <text x="528" y="100" text-anchor="middle" font-size="11.5" fill="var(--tbm-dgm-ink-2)">SillyTavern's implementation, in depth,</text>
  <text x="528" y="118" text-anchor="middle" font-size="11.5" fill="var(--tbm-dgm-ink-2)">reconstructed from its source</text>
  <text x="528" y="146" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-faint)">— reference, linked inline —</text>
  <line x1="336" y1="104" x2="382" y2="104" stroke="var(--tbm-dgm-arrow)" stroke-width="1.6" marker-end="url(#tbm-ah)"/>
  <text x="359" y="96" text-anchor="middle" font-size="10" fill="var(--tbm-dgm-ink-2)">drills into</text>
</svg>
<template #caption>

**Comparison first, analysis on demand.** Each topic's comparison page sets SillyTavern's
approach beside The Bannered Mare's; where you want the incumbent's implementation in full, it
links into the matching analysis page — kept as a reference archive rather than a separate
reading track.

</template>
</Figure>

The thirteen topics:

- [Code Structure](/sillytavern/comparison/code-structure)
- [Prompting](/sillytavern/comparison/prompting)
- [Providers](/sillytavern/comparison/providers)
- [Streaming](/sillytavern/comparison/streaming)
- [Character Cards](/sillytavern/comparison/character-cards)
- [World / Lore](/sillytavern/comparison/world-lore)
- [Chat System](/sillytavern/comparison/chat-system)
- [RAG](/sillytavern/comparison/rag)
- [Slash Commands](/sillytavern/comparison/slash-commands)
- [Tool Calling](/sillytavern/comparison/tool-calling)
- [Extensions](/sillytavern/comparison/extensions)
- [Tags / Stats / Data](/sillytavern/comparison/tags-stats-data)
- [Presets](/sillytavern/comparison/presets)
