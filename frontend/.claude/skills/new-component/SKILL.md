---
name: new-component
description: Scaffold a Vue 3 SFC that follows Candlekeep UI conventions — script setup + TypeScript, Nuxt UI primitives, and the project's design-system classes. Use when creating a new component under src/components/ or a routed view under src/views/.
---

Create a component that matches the house style so it looks and behaves like the rest of the app.

## Conventions (non-negotiable)

- `<script setup lang="ts">`, PascalCase filename, under `src/components/<area>/` (or `src/views/` if routed).
- Use **Nuxt UI** primitives (`UButton`, `UBadge`, `UIcon`, `USelectMenu`, …) — they auto-import. **Always** `<UIcon name="i-lucide-*" />`, never a bare `<span class="i-lucide-*">`. (Use the `nuxt-ui` MCP to check component props/slots/examples.)
- API types come from `components["schemas"][...]` (`@/api/schema`) — no parallel interfaces. Data fetching lives in a `use*` composable (see `/new-composable`), not inline in the component.
- Keep it presentational: typed `props`/`emits`, events up; lift API calls and global state to a composable or Pinia store.

## Design-system classes

- **Card:** `rounded-xl border bg-card/50 p-4`
- **Input:** `h-11 w-full rounded-lg border bg-muted/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40`
- **Section heading:** `font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground`
- **Entry animation:** `animate-fade-in-up` (stagger with `animation-delay`)
- Use `border` alone for borders (the base layer sets the color). `font-cinzel` for display headings.

## USelectMenu (custom-styled trigger)

Use the warm-bordered dropdown pattern from CLAUDE.md §6.2 — a custom `<button>` trigger plus `:ui` overrides (`base`, `content`, `item`), not the default trigger.

## Finish

Run `bun run typecheck` (vue-tsc validates template bindings too). For visible UI, sanity-check in `VITE_USE_MOCKS=true vp dev`.
