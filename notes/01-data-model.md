# 01 — The data model

← [`00-manifesto.md`](00-manifesto.md) · next: [`02-container-and-avif.md`](02-container-and-avif.md)

This is the canonical model — one JSON document per actor. Everything here is the *logical*
schema; how it's packed into the single `.avif` is [`02`](02-container-and-avif.md).

Conventions used below:

- **R** = required, **O** = optional. Absent ≠ `null`; only R fields may not be absent.
- Every value is UTF-8 / Unicode **NFC**. Prose fields are **CommonMark** (declared flavor).
- Enums are marked **closed** (only listed values) or **open** (listed values + a
  `custom`/free string escape hatch, so we never repeat the smart-quote-style dead-end of a
  field that can't express reality).

---

## 0. The top-level shape

```jsonc
{
  "$schema": "https://mare.spec/schema/1.0/character.schema.json",  // O(recommended) self-describes → IDE validation
  "spec": "mare",                    // R  literal discriminator
  "spec_version": "1.0.0",           // R  SemVer of THIS spec (Principle 12)
  "id": "0193f0a2-...-uuid7",        // R  stable identity, UUIDv7 (time-ordered)
  "actor_kind": "character",         // R  character | persona | narrator (Principle 11)
  "revision": 7,                     // R  monotonic int, bumped on every edit
  "created_at": "2026-02-11T09:00:00Z",  // R  ISO 8601, UTC, Z-suffixed — set once
  "updated_at": "2026-07-18T14:00:00Z",  // R  ISO 8601, UTC, Z-suffixed — set on every revision bump

  "identity":      { ... },          // R  who they are (Principle 3)
  "attributes":    { ... },          // O  typed facts (Principle 4)
  "appearance":    { ... },          // O  typed physical description
  "profile":       { ... },          // R  model-facing prose (description/personality/...)
  "voice":         { ... },          // O  speech style + TTS binding
  "scene":         { ... },          // O  opening scenario + greetings (Principle 9)
  "dialogue_examples": [ ... ],      // O  typed few-shot (Principle 6)
  "prompt":        { ... },          // O  engine-facing overrides
  "lore":          { ... },          // O  Lorebook v2 (see 03)
  "assets":        [ ... ],          // O  avatar/sprites/bg/voice, AVIF-first
  "taxonomy":      { ... },          // O  faceted tags/genres/themes/franchise/language for discovery
  "content_rating":{ ... },          // O  maturity + warnings (Principle 8/10)
  "provenance":    { ... },          // R  creator/license/source/time (Principle 8)
  "i18n":          { ... },          // O  locale overrides (Principle 7-adjacent)
  "extensions":    { ... },          // O  reverse-DNS namespaced (Principle 7)
  "integrity":     { ... }           // O  hash + signature (Principle 8)
}
```

Three deliberate choices up top:

- **`id` is a UUIDv7**, not the name. A card can be renamed, retitled, translated, and
  re-avatared and still be *the same actor*. (TavernCard has no identity at all — it dedupes
  on `name`, which is why our DB briefly had two rows both called `Mina`.)
- **`revision` is a plain counter.** This is edit lineage, distinct from `spec_version`
  (which format) and from `provenance.version` (creator's own "v3 of my character" label).
  Three different "versions" that TavernCard smears into one `character_version` string.
- **`created_at` / `updated_at` sit *with* `revision`**, because the document's lifecycle is
  one concept — when it was born, when it last changed, and how many times. All three are
  top-level, not scattered into `provenance`. Both are **ISO 8601, UTC, `Z`-suffixed** (never
  a local offset — one timezone policy, so timestamps sort and compare without normalization).
  `created_at` is written once and never changes; `updated_at` is rewritten on **every**
  `revision` bump and must always be `>= created_at`. TavernCard has neither, so "which copy
  is newer?" is unanswerable — you can't even tell an edited re-share from the original.
- **`actor_kind`** makes personas and narrators first-class instead of second systems.

---

## 1. `identity` — the field that kills the `name` bug

```jsonc
"identity": {
  "display_name": "Elara Voss",            // R  human/UI/marketplace title, free text
  "reference_token": "Elara",              // R  what {{char}} resolves to (short!)
  "given_name": "Elara",                   // O  structured
  "family_name": "Voss",                   // O  structured
  "additional_names": ["Marie"],           // O  middle/other
  "name_order": "given-family",            // O  given-family | family-given (i18n)
  "nickname": "Ellie",                     // O
  "aliases": ["The Shy Cousin"],           // O  in-fiction epithets / former titles
  "sort_key": "voss elara",                // O  for stable listing
  "pronouns": {                            // O  structured, not a guessed string
    "subject": "she", "object": "her",
    "possessive_det": "her", "possessive": "hers", "reflexive": "herself"
  }
}
```

**Why this shape.** The single hardest lesson from the importer: *display*, *token*, and
*name* are three things. Here they are three fields:

| Concern | Field | TavernCard did |
|---|---|---|
| Storefront headline | `display_name` | crammed into `name` |
| Prompt substitution | `reference_token` | *also* `name` → whole title leaked into `{{char}}` |
| Real, structured name | `given_name`/`family_name` | hidden in `Name:` prose |
| Handle / pet name | `nickname` | V3 `nickname`, ~never used |
| In-fiction epithet | `aliases` | nowhere |

`reference_token` is what solves *"the model thinks its name is a sentence."* It's required,
short (validator warns above ~40 chars), and defaults to `given_name` or the first word of
`display_name`. `pronouns` being structured kills the gender-pronoun-tally heuristic we
wrote — a card can just *say* `she/her` instead of us counting tokens.

---

## 2. `attributes` — typed facts, not archaeology

```jsonc
"attributes": {
  "age": { "value": 19, "descriptor": null },              // years (implicit); descriptor only when no clean number
  "species": { "value": "Human", "canonical": "human" },   // OPEN vocab: canonical is a slug, extensible
  "gender": { "value": "female", "custom": null },          // CLOSED enum: male|female|non-binary|other (+custom iff "other")
  "occupation": ["university student"],
  "nationality": "Korean",                                  // NOT species (a real bug we hit)
  "orientation": null,
  "relationship_to_user": "cousin"                          // the "cousin"/"stepsister" hook, as data
}
```

- **`age`** is deliberately tiny: `value` is an **integer number of years** (or `null`), and
  `descriptor` is the escape hatch for when there *is* no clean number — `"immortal"`,
  `"ancient"`, `"early 20s"`. That's it. Two things it does **not** carry, on purpose:
  - **no `unit`** — years is the only unit a character is ever measured in (a 300-year-old
    vampire is `value: 300`); a `unit` field would be pure ceremony.
  - **no `is_adult`** — when `value` is known it's just `value >= 18` (storing a derived flag
    invites it to *disagree* with `value`), and the one case it can't be derived (unknown
    number) is a **safety** question, which lives in `content_rating` (§10), not smeared across
    every attribute. `age` describes the character; "is this card adult content" is rating.

    This ends `age = "19-ish 😳"` while staying a two-field object, not a five-field one.
- **`species` is *open*** — and it has to be: you cannot enumerate every fantasy/sci-fi race.
  So `canonical` is a **slug** (same `slug` `$def` as tags — `human`, `elf`, `khajiit`, …)
  drawn from a controlled-but-**extensible** vocabulary, plus a free `value` for display. The
  slug keeps `Khajiit`/`khajiit` from fragmenting; the open vocabulary lets a new race exist
  without a spec bump. Our importer's curated `_SPECIES_VOCAB` seeds the vocabulary, but now
  the creator picks the slug instead of us guessing from "a mesmerizing Khajiit dancer."
- **`gender` is *closed*** — because a small fixed set genuinely covers it, and the free-text
  door is the *escape*, not the main field. The enum is **`male | female | non-binary |
  other`**, and `custom` is a free string used **only when `value == "other"`**. This is
  exactly TBM's model (`Gender` enum + `custom_gender`) — a 1:1 map, no translation needed.
  Making the *primary* value closed is the whole point: it stops `female`/`F`/`woman`/`Female`
  from fragmenting the filterable field (the tag lesson), while `other`+`custom` still
  expresses anything under the sun. (The importer's `_map_card_gender` already produces exactly
  this shape.)
- **`nationality` is separate from `species`.** We explicitly fixed a bug where
  `Ethnicity: Korean` landed in a species column. Different fields, permanently.
- **`relationship_to_user`** captures the "stepsister / cousin / roommate" hook as *data*
  instead of as words smuggled into `name`.

---

## 3. `appearance` — optional, typed, and honestly kind of great for sprites

```jsonc
"appearance": {
  "summary": "Petite, freckled, chestnut hair usually half-hiding her face.",  // prose ok here
  "height_cm": 158,
  "build": "petite",
  "hair": { "color": "chestnut", "length": "shoulder", "style": "loose waves" },
  "eyes": { "color": "hazel" },
  "distinguishing_marks": ["freckles across the nose", "small scar, left eyebrow"],
  "wardrobe_default": "oversized cardigan over a turtleneck",
  "expression_set": "shy-cousin-v1"   // links to expression sprites in assets[] (see 02)
}
```

This is *optional* — a card can put appearance entirely in `profile.description`. But
structuring it enables real features TavernCard can't: driving **expression sprites**,
consistent **image-gen** conditioning, and searchable filters ("brown-haired elves"). Free
prose stays available in `summary`.

---

## 4. `profile` — the model-facing prose, separated from everything else

```jsonc
"profile": {
  "tagline": "Your bookish cousin who blushes when you look at her too long.",  // 1 line, discovery
  "description": "Elara is ...",           // R  the main character sheet (markdown)
  "personality": [                          // O  STRUCTURED facets, not a bullet-blob
    { "trait": "Nervously Charming", "detail": "Earnest to a fault; her nerves ..." },
    { "trait": "Daydreamer",         "detail": "Retreats into idealized versions ..." }
  ],
  "personality_text": null,                 // O  fallback single-string form (import target)
  "backstory": "..."                        // O  markdown, long-form
}
```

**The `personality` split is the direct fix for the bullet-flatten bug.** Instead of one
string that a creator formats as a bullet list — which some exporter then flattens into
`"...her.       - Daydreamer: ..."` — each facet is an object. There's *nothing to flatten*;
rendering to bullets or prose is the client's choice. `personality_text` exists only as the
lossy target for importing a legacy blob (see [`04`](04-migration-and-mapping.md)); a
native card uses the array.

**`tagline` vs `description`.** `tagline` is the one-liner for a browse grid — the legitimate
home for the "hook" text creators currently smuggle into `name`. Give SEO a real field and it
stops poisoning the prompt.

---

## 5. `voice` — speech model + optional TTS

```jsonc
"voice": {
  "style": "soft, hesitant, trails off mid-sentence",
  "quirks": ["apologizes reflexively", "uses 'um' when flustered"],
  "verbosity": "medium",             // terse | medium | verbose (closed)
  "accent": "faint regional",
  "tts": {                            // O  binding to a synth voice, engine-agnostic
    "sample_asset": "voice/elara_sample.opus",
    "provider_hints": { "elevenlabs": { "voice_id": "..." } }  // namespaced, optional
  }
}
```

Separating *speech style* (which the LLM reads) from *TTS binding* (which a synth reads)
means a text-only client ignores `tts` cleanly and a voice client has a real place to look —
instead of both fighting over one prose field.

---

## 6. `scene` — how a session may *open*, kept out of the definition

```jsonc
"scene": {
  "scenario": "It's late; the house is asleep; you find Elara reading in the kitchen.",
  "greetings": [
    { "id": "g_default", "label": "Default", "tags": ["sfw"], "content": "Elara looks up, startled ..." },
    { "id": "g_rainy",   "label": "Rainy night", "tags": ["sfw","cozy"], "content": "..." }
  ],
  "default_greeting": "g_default"
}
```

- **Greetings are objects with ids, labels, and tags** — not `first_mes` + a parallel
  `alternate_greetings[]` string array. A client can offer "pick a cozy opener," a tag
  filter, or a random-by-tag roll, all as data. (This subsumes TBM's
  `first_message` + `alternate_greetings`.)
- **`scenario` describes the *opening*, not the "current" state** (Principle 9). Where the
  scene has *drifted to* is chat-session state and never mutates the card.

---

## 7. `dialogue_examples` — few-shot as data, not a `<START>`-delimited string

```jsonc
"dialogue_examples": [
  {
    "id": "ex1",
    "tags": ["flustered"],
    "turns": [
      { "role": "user", "name": "{user}", "text": "You look nice today." },
      { "role": "actor", "name": "{char}", "text": "O-oh — um. Thank you. I ... didn't think you'd notice." }
    ]
  }
]
```

TavernCard stores examples as one `mes_example` string with `<START>` separators and
`{{char}}:`/`{{user}}:` line prefixes — which is *exactly* why `prompt_builder.py` has a
tolerant regex to scrape turn roles back out (and why we wrote `split_example_dialogues`).
Here **roles are structured**; there is nothing to scrape. `name` uses the templating
namespace (see [`03`](03-templating-and-runtime.md)), never a raw literal.

---

## 8. `prompt` — engine overrides, honestly named

```jsonc
"prompt": {
  "system": "You are roleplaying as {char.display_name}. ...",   // O  per-card system override
  "post_history": "Stay in character; describe only Elara's actions.",  // O  (was 'jailbreak')
  "template_dialect": "mare-tmpl@1",       // R-if-present  which templating grammar the strings use
  "wrap_user_as": "narrator"               // O  engine hint
}
```

Deliberately renamed `post_history_instructions` → `post_history`, and the spec **does not
describe it as a "jailbreak."** It's neutral engine instruction. `template_dialect` pins the
grammar so a renderer knows how to parse `{...}` (Principle 6) — no more guessing whether a
string uses `{{char}}`, `{char}`, `<char>`, or `%char%`.

---

## 9. `assets` — AVIF-first, hashed, role-tagged

```jsonc
"assets": [
  { "id": "avatar", "role": "avatar", "path": "#item=1", "mime": "image/avif",
    "width": 1024, "height": 1024, "hash": "sha256:9f2c...", "bytes": 148213 },
  { "id": "thumb",  "role": "thumbnail", "path": "#item=2", "mime": "image/avif",
    "width": 256, "height": 256, "hash": "sha256:...", "derived_from": "avatar" },
  { "id": "sprite_happy", "role": "expression", "expression": "happy",
    "set": "shy-cousin-v1", "path": "#item=3", "mime": "image/avif" },
  { "id": "bg_kitchen", "role": "background", "path": "#item=5", "mime": "image/avif" },
  { "id": "vo", "role": "voice_sample", "path": "#item=6", "mime": "audio/opus" }
]
```

Every `path` is a **fragment reference into the same `.avif`** (`#item=N`) — the card is one
self-contained file, not a folder of assets.

- **Roles are an open enum:** `avatar`, `thumbnail`, `full_portrait`, `expression`,
  `background`, `voice_sample`, `icon`, `card_frame`, …
- Every asset carries a **hash** so the container is verifiable and assets are
  content-addressable (dedupe, CDN, integrity).
- The `avatar` is the AVIF's primary image; every other asset — sprites, background, voice,
  thumbnail — is another **item in the same `.avif`**, and `path` is a fragment reference like
  `#item=3` into that one file. No external asset dir, no second container — [`02`](02-container-and-avif.md).
- Maps cleanly onto TBM's existing `avatar` / `avatar_large` / `avatar_thumbnail` columns,
  but now extensible to sprites and voice.

---

## 10. `taxonomy` — how tags are stored (the un-messable way)

A flat `tags: string[]` is TavernCard's design, and it's the **same "one bag does five jobs"
disaster as the `name` field**. The real cards prove it — `shy_cousin`'s actual tag list:

```
["can be wholesome", "can be wholesome, can be sexy", "cousin", "cute", "english",
 "female", "human", "love", "oc", "original character", "roleplay", "romance", ...]
```

That single list smuggles in: a **language** (`english`), **typed facts** (`female`, `human`
— which are already `attributes.gender`/`species`), a **relationship** (`cousin`, plus a
contradictory `sister`), an **age** (`young`), **unmerged synonyms** (`oc` + `original
character`), a **comma-phrase as one tag** (`"can be wholesome, can be sexy"`, with `"can be
wholesome"` *also* present separately), and **maturity** (`sexy`). And across cards the casing
is chaos (`stepcest` / `Brat` / `NSFW`). We already shipped a "Title-Case tags" commit to
paper over one slice of this. MARE fixes it structurally with three rules.

### Rule 1 — a tag is a **normalized slug**, not free text

```jsonc
"taxonomy": {
  "tags": ["shy", "childhood-friends", "cozy", "slow-burn"],   // slugs only — the open long tail
  "genres": ["romance", "slice-of-life"],       // controlled-ish vocabulary (open enum)
  "themes": ["forbidden-romance", "coming-of-age"],
  "franchise": null,                            // "elder-scrolls" slug for fandom; null for OC
  "language": "en",                             // BCP-47 — a language is NOT a tag
  "labels": { "slice-of-life": "Slice of Life" }// O  display overrides; else Title-Case the slug
}
```

Every tag matches `^[a-z0-9]+(?:-[a-z0-9]+)*$` — lowercase, hyphen-separated, ASCII. The slug
is the **canonical machine form** (for search, filter, dedupe); the human label is *derived*
by Title-Casing unless overridden in `labels`. The normalization is a **spec-defined
algorithm**, not a per-client afterthought:

1. Unicode **NFC** → 2. trim + collapse internal whitespace → 3. lowercase → 4. spaces /
`_` / `/` → `-` → 5. drop everything outside `[a-z0-9-]` → 6. collapse repeated `-`, strip
leading/trailing `-` → 7. drop empties, **de-dupe order-preserving**.

This alone kills the casing drift *and* the comma-phrase: `"can be wholesome, can be sexy"`
contains a comma, so a native card **rejects it** (schema `pattern` fails); an importer
**splits on `,`/`;`** first, yielding `can-be-wholesome` + `can-be-sexy`, then de-dupes so the
standalone `"can be wholesome"` collapses into the same slug.

### Rule 2 — **facets have real homes**; `tags` is only the leftover long tail

The bag gets split into typed buckets, so search can facet and creators can't dump everything
in one place:

| Was a "tag" | Now lives in | Why |
|---|---|---|
| `english` | `taxonomy.language` (BCP-47) | it's a language, not a descriptor |
| `romance`, `slice-of-life` | `taxonomy.genres` | genre is a controlled facet |
| `forbidden-romance` | `taxonomy.themes` | theme ≠ genre |
| `elder-scrolls` | `taxonomy.franchise` | fandom is its own axis |
| `nsfw`, `mature`, `sexy` | `content_rating.maturity` | rating is safety data, not a tag |
| `stepcest`, `humiliation`, `noncon` | `content_rating.warnings` | warnings are a controlled vocabulary |
| `female`, `human`, `teenager`, `young` | `attributes.gender` / `species` / `age` | **typed facts — never duplicated as tags** |
| `cousin`, `sister` | `attributes.relationship_to_user` | relationship is a typed field |
| `roleplay`, `scenario`, `malepov` | *dropped* | meta-noise, describes nothing about the actor |
| `shy`, `cozy`, `slow-burn` | `taxonomy.tags` | the genuine long tail — open |

### Rule 3 — **`synonyms` canonicalize** so search doesn't fragment

An optional alias table (shipped with the spec, extensible) maps variants to one slug so
`original-character` → `oc`, `non-con` → `noncon`, `slice-of-life`/`sol` → `slice-of-life`.
The card stores only the canonical slug; the registry/editor resolves aliases on input.

### Why not `{tag, source, weight}` objects?

Considered and rejected for the *card*: tag provenance ("creator-added" vs "community-voted")
and weights are a **registry/search-index** concern, not part of the portable document — they
change per host and would bloat every card. The card stores canonical slugs + optional display
labels; anything richer belongs in the index that points *at* the card. (If a use case ever
demands it, it goes in `extensions`, not the core `tags`.)

---

## `content_rating` — the safety facet, split out on purpose

```jsonc
"content_rating": {
  "maturity": "explicit",                   // everyone | teen | mature | explicit (closed enum)
  "warnings": ["noncon", "incest-roleplay"],// controlled vocabulary, honest labels
  "is_fictional": true,                     // asserted
  "min_age_years": 18
}
```

`content_rating` is the reason `nsfw`/`sexy`/`stepcest` must **leave** the tag bag: rating and
warnings are *safety data a client gates on*, and they need a **closed, honest vocabulary**,
not free slugs a creator can spell fifteen ways. Structured here, a client can filter or gate
truthfully; `is_fictional` is asserted, not assumed.

---

## 11. `provenance` — where it came from, who may use it

```jsonc
"provenance": {
  "creator": { "name": "someauthor", "url": "https://...", "contact": null },
  "license": "CC-BY-NC-4.0",                // SPDX identifier (or "LicenseRef-custom")
  "license_url": null,
  "source": "https://chub.ai/characters/...",   // where THIS card came from
  "authoring_tool": "mare-studio/0.9.1",
  "version": "3",                            // the CREATOR's own label (was character_version)
  "based_on": "0193...-uuid7"                // O  lineage: forked from another card's id
}
```

`license` as an **SPDX id** makes "can I remix this?" a machine question. `based_on` records
forks (the ecosystem's real behavior — everyone reskins everyone). `source` records
retrieval origin, which — combined with `integrity` — is how you detect "someone grabbed my
card, swapped the avatar, and injected a Patreon plug."

> **Note — no timestamps here.** The document's `created_at` / `updated_at` live at the **top
> level** with `revision` (§0), not in `provenance`. One authoritative lifecycle pair, not two
> competing ones — carrying both would recreate exactly the kind of "which field is the real
> one?" ambiguity this spec exists to kill. `provenance` is *attribution* (who/where/under what
> license); *when* is a top-level lifecycle fact.

---

## 12. `extensions` & `i18n`

```jsonc
"extensions": {
  "ai.risu.emotion_pack": { "schema": "https://risu.ai/schemas/emotion/1.json", "data": { ... } },
  "com.sillytavern.depth_prompt": { "prompt": "...", "depth": 4 }   // legacy, preserved verbatim
},
"i18n": {
  "ja": { "identity.display_name": "エララ・ヴォス", "profile.tagline": "..." },
  "ko": { "identity.display_name": "엘라라 보스" }
}
```

- **Extensions are reverse-DNS namespaced** and each *should* carry a `schema` URL.
  Unknown namespaces are **preserved on round-trip** and never fail validation (Principle 7).
  This is the disciplined version of TavernCard's `extensions: {}` junk drawer — and the
  home our `bannered_mare` species/gender/age blob *should* have had.
- **`i18n`** is a flat map of `locale → { json_pointer_ish_key: translated_value }`, so any
  displayable field can be localized without duplicating the whole document (the sane version
  of V3's `*_multilingual` bolt-ons).

---

## 13. `integrity` — hash and optional signature

```jsonc
"integrity": {
  "canonicalization": "jcs",                       // RFC 8785
  "hash": "sha256:1a2b...",                          // over the canonical doc WITH integrity.hash/signature removed
  "signature": {
    "alg": "ed25519",
    "key_id": "did:key:z6Mk...",                     // or a bare public key / fingerprint
    "sig": "base64url-...",
    "signed_at": "2026-07-18T14:00:01Z"
  }
}
```

Signing is **optional** and the trust model is deliberately modest: a signature proves *this
document hasn't changed since a given key signed it* and *that key vouches for it*. It does
**not** mint authority from nowhere — a client trusts a signature only if it already trusts
the key (a creator you follow, a curator, your own key). But even unsigned, the `hash` gives
dedupe and tamper-evidence across a re-share. See [`02`](02-container-and-avif.md) for how
the hash is computed over canonical bytes.

---

## The JSON Schema spine (excerpt)

Full schema would live at `https://mare.spec/1.0/character.schema.json`. The spine:

```jsonc
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://mare.spec/1.0/character.schema.json",
  "type": "object",
  "required": ["spec", "spec_version", "id", "actor_kind", "revision",
               "created_at", "updated_at", "identity", "profile", "provenance"],
  "additionalProperties": false,
  "properties": {
    "$schema": { "type": "string", "format": "uri" },
    "spec": { "const": "mare" },
    "spec_version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
    "id": { "type": "string", "format": "uuid" },
    "actor_kind": { "enum": ["character", "persona", "narrator"] },
    "revision": { "type": "integer", "minimum": 1 },
    "created_at": { "type": "string", "format": "date-time" },
    "updated_at": { "type": "string", "format": "date-time" },
    "identity": {
      "type": "object",
      "required": ["display_name", "reference_token"],
      "properties": {
        "display_name": { "type": "string", "minLength": 1, "maxLength": 200 },
        "reference_token": { "type": "string", "minLength": 1, "maxLength": 60 },
        "given_name": { "type": "string" },
        "family_name": { "type": "string" },
        "pronouns": {
          "type": "object",
          "properties": {
            "subject": { "type": "string" }, "object": { "type": "string" },
            "possessive_det": { "type": "string" }, "possessive": { "type": "string" },
            "reflexive": { "type": "string" }
          }
        }
      }
    },
    "attributes": {
      "type": "object",
      "properties": {
        "age": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "value": { "type": ["integer", "null"], "minimum": 0, "description": "age in years" },
            "descriptor": { "type": ["string", "null"],
                            "description": "non-numeric age when value can't capture it: immortal / ancient / early-20s" }
          }
        },
        "gender": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "value":  { "enum": ["male", "female", "non-binary", "other"] },   // CLOSED
            "custom": { "type": ["string", "null"] }
          },
          "required": ["value"],
          // custom is only meaningful for "other"; empty otherwise
          "if":   { "properties": { "value": { "const": "other" } } },
          "then": { "required": ["custom"], "properties": { "custom": { "type": "string", "minLength": 1 } } }
        },
        "species": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "value":     { "type": "string" },                          // display, free
            "canonical": { "$ref": "common.schema.json#/$defs/slug" }   // OPEN vocab, slug-formatted
          }
        }
      }
    }
    // ... profile, scene, assets, provenance, integrity ...
  }
}
```

Two schema stances worth calling out:

- **`additionalProperties: false` at the top level** — unknown *top-level* keys are an error
  (forces the spec to grow deliberately), but the **`extensions`** object is the sanctioned,
  open place for anything unforeseen. Discipline plus an escape hatch.
- **Closed vs. open enums are explicit** in the schema, so tooling knows which fields it may
  extend — **open**: `species.canonical`, asset `role`, `tags`, `genres` — and which it may
  not — **closed**: `actor_kind`, `gender.value`, `maturity`. A closed enum with a designated
  `other`/`custom` escape (gender) is still closed: the *primary* value is fixed; the escape is
  a separate field. That's stricter (and cleaner) than an open enum, and it's why gender isn't
  one.

This is only the spine. How the schema is **published, versioned, `$ref`-modularized, wired
into editors/CI, and used to generate types** — i.e. how it stays a real contract and not
vibes — is its own deep dive: [`06-json-schema.md`](06-json-schema.md).

Next: how these bytes actually travel — [`02-container-and-avif.md`](02-container-and-avif.md).
