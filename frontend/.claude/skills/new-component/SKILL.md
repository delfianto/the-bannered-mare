---
name: new-component
description: Scaffold a Vue 3 SFC that follows The Bannered Mare's frontend conventions — script setup + TypeScript, DaisyUI classes + shared primitives, and the project's design-system classes. Use when creating a new component under src/components/ or a routed view under src/views/.
---

Create a component that matches the house style so it looks and behaves like the rest of the app.

## Conventions (non-negotiable)

- `<script setup lang="ts">`, PascalCase filename, under `src/components/<area>/` (or `src/views/` if routed).
- Use **DaisyUI** classes (`btn`, `badge`, `toggle`, `tabs`, `card`, …) on hand-rolled markup, plus the globally-registered shared primitives — `<AppIcon>`, `<SelectMenu>`, `<AppToggle>` (no import needed). Other shared primitives (e.g. `<AppTooltip>`) are **not** global — `import` them per-component from `@/components/shared/`. **Always** `<AppIcon name="i-lucide-*" />`, never a bare `<span class="i-lucide-*">`; add new icons to `src/components/shared/icons.ts`.
- API types come from `components["schemas"][...]` (`@/api/schema`) — no parallel interfaces. Data fetching lives in a `use*` composable (see `/new-composable`), not inline in the component.
- Keep it presentational: typed `props`/`emits`, events up; lift API calls and global state to a composable or Pinia store.

## Design-system classes

- **Card:** `rounded-xl border bg-base-200/50 p-4`
- **Input:** `h-11 w-full rounded-lg border bg-base-300/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40`
- **Section heading:** `font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground`
- **Entry animation:** `animate-fade-in-up` (stagger with `animation-delay`)
- Surfaces are `bg-base-100/200/300`; text is `text-base-content` / `text-muted-foreground`; brand is `bg-primary` / `text-primary-content`; errors `text-error`. Use `border` alone for borders (the base layer sets the color). `font-cinzel` for display headings.

## SelectMenu (searchable dropdown)

Use `<SelectMenu v-model="v" :items="items" value-key="value" :search-input="false">` with a custom `<button>` trigger in the default slot (see CLAUDE.md §6.2). The listbox styling, width, and teleport are handled internally — no `:ui` overrides.

## Finish

Run `bun run typecheck` (vue-tsc validates template bindings too). For visible UI, sanity-check in `VITE_USE_MOCKS=true vp dev`.
