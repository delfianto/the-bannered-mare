# Characters, Personas & Assets

Roleplay needs cast and crew. The Bannered Mare models three things: **Character cards** (the
non-player characters the LLM performs), **User Personas** (who the user is within the scene),
and the **local media assets** (avatars and thumbnails) attached to both.

## 1. Character Cards (V2-Spec Compatible)

The `Character` entity is a fully loaded character profile, compatible with the SillyTavern V2
character-card specification.

### Core Data Structure

- **System prompt override (`system_prompt`)** — a per-character instruction block that
  replaces the global template's system prompt when active.
- **Alternate greetings (`alternate_greetings`)** — a list of alternative opening messages;
  the system can pick one at random or let the user choose when launching a chat.
- **Example dialogues (`example_dialogues`)** — structured exchanges that illustrate the
  character's speech patterns and behavior, injected into the prompt context dynamically.
- **Tags & classification** — string arrays for tags, species, age, and gender (with custom
  text mappings for non-binary classifications), plus creator-attribution metadata.

## 2. User Personas

The `Persona` model defines the profile of the user taking part in the chat session.

- **Name & description** — the name and details of the user's roleplay alias.
- **Prompt integration** — when a persona is active, its details are injected into the
  compiled prompt under the `persona` component, telling the LLM who it is interacting with.

## 3. Storage & Asset Directory Layout

Media assets such as custom avatars and profile images are saved to a local disk path set by
the `STORAGE_PATH` configuration value. The layout is:

```text
storage/
├── characters/
│   └── {character_id}/
│       ├── avatar.png
│       └── avatar_thumbnail.png
├── personas/
│   └── {persona_id}/
│       ├── avatar.png
│       └── avatar_thumbnail.png
└── temp/                      # Temp folder for file processing and uploads
```

Startup directories are verified and created by `ensure_storage_directories` in
[storage.py](https://github.com/delfianto/the-bannered-mare/blob/main/backend/src/core/utils/storage.py).

## 4. Image Processing & Thumbnail Generation

An uploaded avatar is never written straight to its final home. It lands in `temp/` first,
gets validated and thumbnailed by Pillow, is written to the entity's folder, and only then is
the temp copy removed — so a failed upload can't leave a half-written avatar in place:

<Figure tag="Figure 1" title="The avatar upload pipeline" id="fig-asset-pipeline">
<svg viewBox="0 0 820 250" role="img" aria-label="Avatar image processing pipeline" style="font-family:var(--vp-font-family-base)">
  <defs>
    <marker id="tbm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-arrow)"/>
    </marker>
  </defs>
  <g font-size="12" text-anchor="middle">
    <!-- Row 1 -->
    <rect x="30" y="44" width="230" height="64" rx="10" fill="var(--tbm-dgm-surface-3)" stroke="var(--tbm-dgm-border-strong)"/>
    <text x="145" y="72" font-weight="700" fill="var(--tbm-dgm-ink)">1 · User uploads image</text>
    <text x="145" y="90" font-size="10.5" fill="var(--tbm-dgm-ink-2)">multipart form upload</text>

    <rect x="295" y="44" width="230" height="64" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <text x="410" y="72" font-weight="700" fill="var(--tbm-dgm-ink)">2 · Write to storage/temp</text>
    <text x="410" y="90" font-size="10.5" fill="var(--tbm-dgm-ink-2)">staging area</text>

    <rect x="560" y="44" width="230" height="64" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <text x="675" y="72" font-weight="700" fill="var(--tbm-dgm-ink)">3 · Verify / format</text>
    <text x="675" y="90" font-size="10.5" fill="var(--tbm-dgm-ink-2)">Pillow → PNG / JPEG</text>

    <!-- Row 2 -->
    <rect x="560" y="160" width="230" height="64" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <text x="675" y="188" font-weight="700" fill="var(--tbm-dgm-ink)">4 · Generate thumbnail</text>
    <text x="675" y="206" font-size="10.5" fill="var(--tbm-dgm-ink-2)">Pillow · max 150×150</text>

    <rect x="295" y="160" width="230" height="64" rx="10" fill="var(--tbm-dgm-data-soft)" stroke="var(--tbm-dgm-data)"/>
    <text x="410" y="185" font-weight="700" fill="var(--tbm-dgm-ink)">5 · Save both</text>
    <text x="410" y="203" font-size="10.5" fill="var(--tbm-dgm-ink-2)">storage/characters/{id}/</text>

    <rect x="30" y="160" width="230" height="64" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border)" stroke-dasharray="5 4"/>
    <text x="145" y="188" font-weight="700" fill="var(--tbm-dgm-ink)">6 · Delete temp files</text>
    <text x="145" y="206" font-size="10.5" fill="var(--tbm-dgm-ink-2)">cleanup</text>
  </g>
  <g stroke="var(--tbm-dgm-arrow)" stroke-width="1.6" fill="none" marker-end="url(#tbm-ah)">
    <path d="M260 76 L292 76"/>
    <path d="M525 76 L557 76"/>
    <path d="M675 108 L675 158"/>
    <path d="M558 192 L527 192"/>
    <path d="M293 192 L262 192"/>
  </g>
</svg>
<template #caption>

**Temp-first, cleanup-last.** Because the original and the thumbnail are both produced from a
staged copy and written together, an interrupted upload leaves nothing partial behind — the
final avatar folder is only touched once both images exist.

</template>
</Figure>

### Pillow Image Transformation

The **Pillow** library handles formatting and resizing:

1. **Format validation** — converts images to compatible PNG/JPEG formats.
2. **Thumbnail scaling** — scales to a standard thumbnail size (max width/height of 150px)
   while preserving aspect ratio.
3. **Storage paths** — returns the relative paths (e.g.,
   `characters/ch_1234567890/avatar_thumbnail.png`) stored in the `avatar` and
   `avatar_thumbnail` database columns.

### Asset Deletion & Cleanup

To prevent disk-space leaks:

- When a character or persona gets a new avatar, the old avatar and thumbnail files are
  deleted.
- When a character or persona is deleted, the service calls `delete_character_files()` or
  `delete_persona_files()`, which recursively removes the entity's storage folder
  (`storage/characters/{id}/`).
