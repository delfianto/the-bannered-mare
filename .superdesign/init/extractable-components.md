# Extractable Superdesign Components

## AppSidebar

- Source: `frontend/src/components/layout/AppSidebar.vue`
- Category: layout
- Description: Persistent desktop rail/sidebar with brand trigger, two-column navigation, favorite-character shortcuts, settings, and theme control.
- Extractable props: `collapsed`, `activePath`, `favorites`
- Hardcoded: route labels, Lucide icon names, grid/list structure, theme-toggle placement, semantic token classes

## PageContainer

- Source: `frontend/src/components/layout/PageContainer.vue`
- Category: layout
- Description: Routed-page frame with optional title/subtitle/header actions and consistent responsive padding.
- Extractable props: `title`, `subtitle`, `spacingClass`, `animate`
- Hardcoded: responsive page padding and heading typography

## ContinueTaleSection

- Source: `frontend/src/components/shared/ContinueTaleSection.vue`
- Category: basic
- Description: Horizontal carousel of image-led recent story cards.
- Extractable props: `sessions`, `loading`
- Hardcoded: card dimensions, gradients, hover treatment, scroll controls

## DiscoverSection

- Source: `frontend/src/components/shared/DiscoverSection.vue`
- Category: basic
- Description: Category-filtered character preview grid with browse-all affordance.
- Extractable props: `characters`, `categories`, `loading`, `browseAllTo`
- Hardcoded: grid breakpoints, category-pill structure, section heading treatment

## HomeCharacterCard

- Source: `frontend/src/components/shared/HomeCharacterCard.vue`
- Category: basic
- Description: Full-bleed portrait card with gradient metadata overlay.
- Extractable props: `character`, `index`
- Hardcoded: aspect ratio, hover zoom, tag-pill treatment

## SearchBar

- Source: `frontend/src/components/shared/SearchBar.vue`
- Category: basic
- Description: Wide library search with authored focus state.
- Extractable props: none in current source
- Hardcoded: icon, translated placeholder, focus behavior

## Modal

- Source: `frontend/src/components/shared/Modal.vue`
- Category: basic
- Description: Teleported accessible modal shell with configurable sizing and slots.
- Extractable props: `open`, `title`, `description`, `size`, `closeOnBackdrop`
- Hardcoded: overlay, focus/escape behavior, panel construction

## Tabs

- Source: `frontend/src/components/shared/Tabs.vue`
- Category: basic
- Description: Reusable tab navigation row.
- Extractable props: `items`, `modelValue`
- Hardcoded: active underline and semantic color treatment

## EmptyState

- Source: `frontend/src/components/shared/EmptyState.vue`
- Category: basic
- Description: Centered no-content state with glowing icon and optional action.
- Extractable props: `icon`, `title`, `description`, `actionLabel`, `hasFilters`
- Hardcoded: entry animation, glow construction, primary action style

