# The Bannered Mare — Visual Refresh Design System

## Product and experience

The Bannered Mare is a self-hosted, local-first LLM roleplay application. Its central jobs are discovering characters, resuming ongoing tales, reading/writing long-form roleplay, and managing the models, lore, personas, and loadouts beneath those stories.

The interface should feel like entering an authored world, not administering a generic dashboard. It must remain highly legible, fast, keyboard-friendly, and credible as a daily-use tool. Atmosphere should come from composition, typography, imagery, depth, and quiet motion—not decorative clutter.

## Creative thesis

“An illuminated archive after dusk.”

Combine the calm editorial confidence of a beautifully typeset storybook with the warmth and mystery of a fantasy tavern/library. The Otaku reference is inspiration for restraint, strong typographic hierarchy, spacious reading surfaces, and authored navigation—not a layout or branding template to copy.

Core principles:

1. One unmistakable focal point per viewport. Avoid grids where every module has equal weight.
2. Let story and character imagery establish mood through purposeful crops, layered gradients, and overlap.
3. Use asymmetric editorial composition while preserving obvious scan paths.
4. Treat metadata like colophons, chapter markers, marginalia, and library catalog notation.
5. Keep control density quiet until needed; primary actions remain clear.
6. Use whitespace as structure, not leftover space.
7. Preserve the application's semantic color system and all six palette families.

## Existing brand constraints

- Brand name: The Bannered Mare.
- Body/UI typeface: Inter.
- Display/headline typeface: Cinzel.
- BlackChancery is reserved for the brand wordmark only.
- Icons: Lucide through the existing AppIcon system.
- Colors must use DaisyUI semantic tokens so all built-in and custom themes continue to work.
- Default light palette: parchment white, walnut text, aged-gold primary.
- Default dark palette: deep walnut, warm cream, brighter amber.
- Status uses success/error/warning/info tokens.
- No neon cyberpunk colors, glassmorphism soup, purple SaaS gradients, or generic bento-dashboard treatment.

## Color and surface language

Use the existing semantic token ladder:

- base-100: environmental backdrop / page field.
- base-200: raised paper, panels, and navigation planes.
- base-300: recessed controls, hover states, secondary bands.
- base-content / foreground: primary text and linework.
- muted-foreground: metadata and secondary labels.
- primary / primary-content: active chapter markers, key action, focus, fine accents.
- border: hairlines and page edges.

Atmospheric additions must be derived from these tokens using opacity, color-mix, masks, or gradients. Do not add fixed colors that break palette switching. Black/white overlays are acceptable on photographic content for readable text.

## Typography

- Cinzel: page titles, chapter markers, story titles, character names, section headings.
- Inter: navigation, controls, metadata, summaries, form labels.
- BlackChancery: brand wordmark only.
- Editorial contrast is encouraged: large display titles paired with tiny uppercase catalog labels.
- Long prose must use comfortable measure (roughly 60–78 characters), generous line-height, and stable rhythm.
- Never use all caps for paragraph-length text.

## Layout and hierarchy

Desktop:

- A persistent left navigation remains, but may become a more authored “contents rail” rather than a button grid.
- Main content should use a centered or intentionally offset stage with a strong image/story feature.
- Home should privilege “continue your tale” as the emotional entry point, then character discovery.
- Use layered or overlapping cards sparingly to create depth; avoid endless uniform tiles.
- Keep utility actions accessible without competing with narrative content.

Responsive:

- At small widths the sidebar becomes a compact navigation solution.
- Editorial asymmetry collapses into a clear single column.
- No content is hidden solely for visual drama.
- Tap targets stay at least 44px where practical; focus states remain explicit.

## Home page content hierarchy

1. Warm greeting and a concise invitation into the user's worlds.
2. Featured/current tale with a dominant cinematic image, title, character, recency, and obvious Resume action.
3. Remaining recent tales as a smaller supporting rail/list.
4. Search/discovery as a secondary “browse the archive” action.
5. Character discovery with one featured portrait and a varied but orderly supporting collection.
6. First-run setup banner when required.

All current routes and primary capabilities remain recognizable.

## Components

- Navigation: quiet editorial rail with a strong active marker; collapsed and expanded modes remain.
- Cards: image-forward, restrained radii, subtle borders; use composition and crop instead of heavy chrome.
- Buttons: one primary filled action per region; secondary actions are bordered or text.
- Search: can be integrated as a library/catalog control instead of a generic full-width field.
- Tags: small catalog labels, not colorful novelty pills.
- Empty states: atmospheric but simple, with a clear next action.
- Modals/forms/settings: stay utilitarian and calm; the expressive visual language should not reduce task clarity.

## Motion

- 180–400ms transitions.
- Gentle reveal, crossfade, image scale (1.02–1.05), and small parallax-like shifts are welcome.
- No constant ambient motion that distracts from reading.
- Respect prefers-reduced-motion and preserve functionality without animation.

## Accessibility and implementation constraints

- WCAG-conscious contrast across every theme.
- Visible keyboard focus.
- Semantic headings and controls.
- Do not rely on color alone for selection or status.
- Preserve Vue 3.5, Tailwind CSS v4, DaisyUI 5, existing semantic tokens, localization, and root-font-size scaling.
- Prefer canonical Tailwind utilities and rem-based sizing.
- The visual refresh must be implementable without backend/API contract changes.

