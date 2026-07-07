# Characters, Personas & Assets

Roleplay needs cast and crew. The Bannered Mare models three things: **Character cards** (the
non-player characters the LLM performs), **User Personas** (who the user is within the scene),
and the **local media assets** (avatars and thumbnails) attached to both.

## 1. Character Cards (V2-Spec Compatible)

The `Character` entity is a fully loaded character profile, compatible with the TavernCard V2
character-card specification. Cards can be imported from either a PNG (with the base64 JSON
embedded in a `chara` `tEXt` chunk) or plain JSON, and both the V2 format and the older V1
(flat, Pygmalion-style `char_name` / `char_persona` / `char_greeting`) format are parsed;
export always produces V2 JSON or a V2-embedded PNG.

### Core Data Structure

- **System prompt override (`system_prompt`)** — a per-character instruction block that
  replaces the global template's system prompt when active.
- **Alternate greetings (`alternate_greetings`)** — a list of alternative opening messages;
  the system can pick one at random or let the user choose when launching a chat.
- **Example dialogues (`example_dialogues`)** — structured exchanges that illustrate the
  character's speech patterns and behavior, injected into the prompt context dynamically.
- **Classification** — `tags`, `species`, `age`, and a `gender` enum (`male`, `female`,
  `non-binary`, `others`); when gender is `others`, a free-text `custom_gender` holds the
  actual value. Species/gender/age are read from card extensions (the `bannered_mare`
  extension namespace, with `chara_personal_details` and top-level fallbacks) on import.
- **Attribution** — `creator`, `creator_notes` (not sent to the LLM), and
  `character_version`.

## 2. User Personas

The `Persona` model defines the profile of the user taking part in the chat session.

- **Name & description** — the name and details of the user's roleplay alias.
- **Prompt integration** — when a persona is active, its details are injected into the
  compiled prompt under the `persona` component, telling the LLM who it is interacting with.

## 3. Storage & Asset Directory Layout

Media assets such as custom avatars and profile images are saved to a local disk path set by
the `STORAGE_PATH` configuration value (default `./storage`). The layout is:

```text
storage/
├── characters/
│   └── {character_id}/
│       ├── avatar_original.{ext}    # Original upload, extension preserved
│       └── avatar_thumbnail.jpg     # Generated thumbnail (always JPEG)
├── personas/
│   └── {persona_id}/
│       ├── avatar_original.{ext}
│       └── avatar_thumbnail.jpg
└── temp/                            # Created at startup; reserved for file processing
```

The original keeps its uploaded extension (one of `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`);
the thumbnail is always re-encoded to JPEG regardless of the source format. The relative
paths (e.g. `characters/{id}/avatar_original.png` and `characters/{id}/avatar_thumbnail.jpg`)
are stored in the entity's `avatar` and `avatar_thumbnail` columns.

Startup directories are verified and created by `ensure_storage_directories` in
[storage.py](https://github.com/delfianto/the-bannered-mare/blob/main/backend/src/core/utils/storage.py).

## 4. Image Processing & Thumbnail Generation

An uploaded avatar is validated up front, then written to the entity's folder and thumbnailed
in place. Validation is strict — extension, size, Pillow integrity, and dimensions are all
checked before anything is written — so a malformed upload is rejected before it touches disk:

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
    <text x="410" y="72" font-weight="700" fill="var(--tbm-dgm-ink)">2 · Validate</text>
    <text x="410" y="90" font-size="10.5" fill="var(--tbm-dgm-ink-2)">ext · ≤20MB · Pillow · ≤4096²</text>
    <rect x="560" y="44" width="230" height="64" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <text x="675" y="72" font-weight="700" fill="var(--tbm-dgm-ink)">3 · Write original</text>
    <text x="675" y="90" font-size="10.5" fill="var(--tbm-dgm-ink-2)">avatar_original.{ext}</text>
    <!-- Row 2 -->
    <rect x="560" y="160" width="230" height="64" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
    <text x="675" y="188" font-weight="700" fill="var(--tbm-dgm-ink)">4 · Generate thumbnail</text>
    <text x="675" y="206" font-size="10.5" fill="var(--tbm-dgm-ink-2)">Pillow · max 128×128 · JPEG</text>
    <rect x="295" y="160" width="230" height="64" rx="10" fill="var(--tbm-dgm-data-soft)" stroke="var(--tbm-dgm-data)"/>
    <text x="410" y="185" font-weight="700" fill="var(--tbm-dgm-ink)">5 · Return paths</text>
    <text x="410" y="203" font-size="10.5" fill="var(--tbm-dgm-ink-2)">stored in avatar columns</text>
    <rect x="30" y="160" width="230" height="64" rx="10" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border)" stroke-dasharray="5 4"/>
    <text x="145" y="188" font-weight="700" fill="var(--tbm-dgm-ink)">DB update</text>
    <text x="145" y="206" font-size="10.5" fill="var(--tbm-dgm-ink-2)">service persists paths</text>
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

**Validate first, then write.** The upload is fully validated before any file is created;
the original is saved with its uploaded extension, and the thumbnail is derived from it and
re-encoded to JPEG. The service then persists the two relative paths on the entity row.

</template>
</Figure>

### Pillow Image Transformation

The **Pillow** library handles validation and resizing:

1. **Validation** — checks the extension against an allow-list (`.png`, `.jpg`, `.jpeg`,
   `.gif`, `.webp`), enforces a 20MB size cap, verifies image integrity, and rejects images
   larger than 4096×4096.
2. **Original** — written verbatim (extension preserved) as `avatar_original.{ext}`; no EXIF
   stripping is applied to the original.
3. **Thumbnail** — the saved original is reopened, converted to RGB if needed (RGBA/palette),
   scaled with `Image.thumbnail((128, 128))` preserving aspect ratio, and saved as an
   optimized JPEG (quality 85) named `avatar_thumbnail.jpg`.
4. **Storage paths** — returns the relative paths (e.g.,
   `characters/{id}/avatar_original.png` and `characters/{id}/avatar_thumbnail.jpg`) stored
   in the `avatar` and `avatar_thumbnail` database columns.

### Asset Deletion & Cleanup

When a character or persona is deleted, the service calls `delete_character_files()` or
`delete_persona_files()`, which recursively removes the entity's storage folder
(`storage/characters/{id}/` or `storage/personas/{id}/`).

Note that replacing an avatar overwrites the files with matching names but does **not**
explicitly delete a prior original whose extension differed (e.g. an old `.png` left behind
when a new `.jpg` is uploaded) — the folder is only fully cleaned on entity deletion.
