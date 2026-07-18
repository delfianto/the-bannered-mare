# 04 — Migration from TavernCard, validation, and the TBM backend mapping

← [`03-templating-and-runtime.md`](03-templating-and-runtime.md) · next: [`05-example-elara.md`](05-example-elara.md)

A spec that can't import the existing world is a museum piece. The good news: **we already
built the importer.** Everything in `backend/src/character/card_parser.py` that recovers
names, attributes, and clean prose from messy TavernCard PNGs *is* the TavernCard→MARE
migration engine. This file wires it together, defines the validator, maps MARE onto the TBM
tables, and states the versioning policy.

---

## Part A — TavernCard (V1/V2/V3 PNG) → MARE

The importer is a pipeline. Each stage already exists in our codebase or is a thin wrapper on
what does.

```
PNG bytes
  │  _read_png_text_chunks + base64 decode           (card_parser.py — done)
  ▼
raw TavernCard JSON (V1 flat | V2/V3 under "data")
  │  parse_card_json / _parse_v2_data                (card_parser.py — done)
  ▼
ParsedCard  ──────────────────────────────────────────────────────────────┐
  │  normalize_card_quotes    (smart quotes → ASCII)                        │  all four
  │  normalize_card_bullets   (reflow flattened bullet lists)               │  already
  │  fill_canonical_name      (recover real/fullest name, drop title)       │  shipped
  │  fill_baked_in_attributes + fill_prose_inferred_attributes (species/age/gender)  │
  ▼                                                                          ┘
clean ParsedCard  →  MARE mapper (new, small)  →  MARE character.json  →  validate  →  emit
```

### Field mapping, TavernCard → MARE

| TavernCard | MARE | Transform (mostly done) |
|---|---|---|
| `name` | `identity.display_name` (verbatim) **and** `identity.reference_token` (cleaned) | `fill_canonical_name` splits title/role from the real name; `reference_token` = recovered given name |
| `Name:` / `name(...)` in prose | `identity.given_name` / `family_name` | `_labeled_name_candidates` (fullest-wins, user/handle-skip, salvage) |
| — (pronoun tally) | `identity.pronouns` | from `_infer_gender_from_prose`, upgraded to explicit pronouns |
| `**Age:** 19` etc. | `attributes.age.{value,descriptor}` | `_AGE_PROSE_PATTERN` + label extractor → integer `value`; a non-numeric age ("ancient") lands in `descriptor` |
| `Khajiit dancer` | `attributes.species.{value,canonical}` | `_SPECIES_VOCAB` → controlled `canonical`, prose → `value` |
| `Ethnicity: Korean` | `attributes.nationality` | the fix we made so this stops becoming `species` |
| `description` | `profile.description` | `normalize_card_bullets` + quote fold |
| `personality` (bullet blob) | `profile.personality[]` if parseable, else `profile.personality_text` | reflow → split facets on `Trait: detail`; fall back to text |
| `first_mes` | `scene.greetings[0]` (`id:"g_default"`) | wrap in greeting object |
| `alternate_greetings[]` | `scene.greetings[1..]` | id/label auto-assigned |
| `mes_example` (`<START>`) | `dialogue_examples[]` | `split_example_dialogues` → parse `{{char}}:`/`{{user}}:` lines into typed `turns[]` |
| `scenario` | `scene.scenario` | verbatim (quote fold) |
| `system_prompt` | `prompt.system` | verbatim; `{{char}}`→`{char.reference_token}` rewrite |
| `post_history_instructions` | `prompt.post_history` | verbatim (de-"jailbreak"ed in name only) |
| `character_book` | `lore` (Lorebook v2) | ST world-info → the [`03`](03-templating-and-runtime.md) shape |
| `tags` | **routed** into `taxonomy.{tags,genres,themes,franchise,language}`, `content_rating.{maturity,warnings}`, or `attributes.*` | slugify (split comma-phrases first), then facet-route each tag; drop typed-fact duplicates and meta-noise (see below) |
| `creator` | `provenance.creator.name` | verbatim |
| `creator_notes` | `provenance` note / `extensions` | not model-facing |
| `character_version` | `provenance.version` | verbatim |
| `extensions.*` | `extensions["com.sillytavern.*"]` | **preserved verbatim**, namespaced |
| the PNG pixels | `assets[avatar]` re-encoded to **AVIF** | transcode PNG→AVIF; keep PNG hash in provenance |
| — | `id` (new UUIDv7), `spec`, `spec_version`, `revision:1` | minted at import |
| — | `created_at` / `updated_at` | both set to import time (ISO 8601, UTC, `Z`); a legacy PNG carries no timestamp to recover |
| — | `integrity.hash` | computed over JCS canonical form |

### Tag routing, worked on `shy_cousin`'s real bag

The importer slugifies every legacy tag (splitting comma-phrases), then facet-routes it:

```
raw: ["can be wholesome", "can be wholesome, can be sexy", "cousin", "cute", "english",
      "female", "human", "love", "oc", "original character", "roleplay", "romance",
      "sexy", "shy", "sister", "wholesome", "young"]

→ taxonomy.language      : "en"                         (from "english")
→ taxonomy.genres        : ["romance"]
→ content_rating.maturity: "mature"                     (from "sexy")
→ attributes.gender      : female                        (from "female" — fills if blank, else dropped)
→ attributes.species     : Human                         (from "human")
→ attributes.age         : {descriptor:"young"}          (from "young")
→ attributes.relationship_to_user: "cousin"              ("sister" conflicts → linter WARNING, not silently kept)
→ taxonomy.tags          : ["wholesome", "cute", "love", "oc", "shy"]   (slugified, de-duped)
                            # "original character" → canonical "oc" (synonym); the two
                            # "can be wholesome…" phrases collapse into "wholesome"; "roleplay" dropped as meta-noise
```

Nothing is silently mangled: a comma-phrase is *split* (not slugified into one giant slug), a
typed-fact tag *fills its field or is dropped* (never duplicated), and a genuine contradiction
(`cousin` vs `sister`) is surfaced as a **linter warning** for a human to resolve.

Two migration stances:

- **`{{char}}` / `{{user}}` rewrite.** Legacy strings use `{{char}}`; MARE uses
  `{char.reference_token}`. The importer rewrites the *known* macros and leaves unknown
  `{{...}}` as literals flagged by the linter (a human decides). This is safe because we now
  have a *real* `reference_token` to point at.
- **Lossy is labeled, not hidden.** If `personality` can't be split into clean facets, it
  lands in `personality_text` with a linter **warning** — never silently dropped, never
  fake-structured.

### MARE → TavernCard (export for back-compat)

The reverse exists too (people still use ST): flatten `identity.reference_token` →
`name` (**not** the marketing title — this is the *improvement* the round-trip preserves),
re-join `personality[]` into a bullet string, collapse greetings, re-emit `character_book`,
re-embed as base64 in a PNG `tEXt`. Downgrading loses structure but produces a *cleaner*
TavernCard than most native ones (because the name is finally just the name).

---

## Part B — The validator / linter

Two levels (Principle 10):

- **`error`** (reject): missing required field, `additionalProperties` at top level,
  malformed `id`, `reference_token` empty, `spec_version` unparseable, `created_at`/`updated_at`
  not ISO 8601 UTC (`Z`-suffixed), `updated_at` earlier than `created_at`, an asset hash that
  doesn't match its bytes, a signature that doesn't verify.
- **`warning`** (accept + flag): `reference_token` > 60 chars, `personality_text` used
  instead of structured facets, unknown `{{...}}` macros left after import, `content_rating`
  absent on an adult-tagged card, an extension namespace with no `schema` URL, both `age.value`
  and `age.descriptor` empty on a card that clearly stated an age in prose.

CLI shape (a natural sibling to our existing `scripts/`):

```
mare lint elara.avif          # errors + warnings
mare fmt  elara.mare.json     # canonicalize the authoring source (JCS) in place
mare hash elara.avif          # print integrity hash
mare sign elara.avif --key ~/.mare/key.ed25519
mare convert mina.png -o mina.avif        # TavernCard → MARE (runs the pipeline above)
mare convert elara.avif --to tavern -o elara.png   # downgrade
```

These map onto what `scripts/import_card.py` / `export_card.py` already do — `mare convert`
*is* `import_card.py` with a MARE emitter bolted on the end.

---

## Part C — Mapping onto the TBM backend

MARE is a better *interchange* format; the DB schema barely has to change to consume it. The
mapping onto existing tables:

| MARE | TBM model (`core/persistence/models/`) | Notes |
|---|---|---|
| `actor_kind: character` | `Character` | the main table |
| `actor_kind: persona` | `Persona` | **same importer, one flag** — solves the "personas are a second-class system" problem (Principle 11) |
| `actor_kind: narrator` | (new, tiny) or a `Character` variant | future |
| `identity.reference_token` | `Character.name` | ← the value we now compute in `fill_canonical_name` |
| `identity.display_name` | **new column** `display_name` | the marketing title, kept but not used as `{{char}}` (the "preserve the title" option from our earlier chat — now it has a home) |
| `identity.given_name/family_name/nickname` | new nullable columns *or* a `identity` JSONB | structured name, finally stored |
| `identity.pronouns` | new `pronouns` JSONB | replaces gender-from-prose guessing |
| `attributes.age` | `Character.age` (widen `str`→JSONB `{value,descriptor}`) | `value` is a filterable integer instead of today's unqueryable free string |
| `attributes.species/gender/nationality` | `species` / `gender` (+`custom_gender`) / **new** `nationality` | we already fought to keep nationality ≠ species |
| `profile.description` | `Character.description` | |
| `profile.personality[]` | `Character.personality` (widen to JSONB) or a child table | structured facets |
| `scene.greetings[]` | `Character.first_message` + `alternate_greetings` **or** a `greetings` child table | child table unlocks labels/tags |
| `dialogue_examples[]` | `Character.example_dialogues` (widen to structured) | roles become data |
| `prompt.system/post_history` | `Character.system_prompt` / `post_history_instructions` | 1:1 |
| `lore` | `Lorebook` + `LoreEntry` | **near-verbatim** — TBM's lore model already matches |
| `lore.entries[].vectorized` | ties into `rag` slice + pgvector | keyword ∪ embedding retrieval |
| `assets[]` | `avatar` / `avatar_large` / `avatar_thumbnail` (+ new `assets` child table for sprites/voice) | AVIF files under `$STORAGE_PATH` |
| `created_at` / `updated_at` | `BaseModel.created_at` / `updated_at` | **already exist** — timezone-aware UTC columns on every row, with `onupdate=utc_now`; serialize to ISO 8601 `Z`. Zero new columns |
| `provenance.*` | `creator`, `character_version` (+ new `license`, `source`) | attribution only — timestamps handled by the row above |
| `integrity.hash` | new `content_hash` column | dedupe + tamper-evidence; kills the "two Mina rows" ambiguity by identity, not name |
| `extensions.*` | new `extensions` JSONB | the disciplined home for our old `bannered_mare` blob |

Migration reality check, honoring `backend/CLAUDE.md`: these are **additive Alembic
migrations** (new nullable columns / JSONB / child tables), single-user local Postgres, small
data — exactly the low-risk shape the project's tradeoffs doc favors. Nothing here forces a
rewrite; the importer keeps writing `Character.name` = the clean token as it does today, and
the new columns fill in progressively.

---

## Part D — Versioning & compatibility policy (Principle 12)

- **`spec_version` is SemVer.** *Minor* bumps are additive and backward-compatible (new
  optional fields, new open-enum values); *major* bumps may remove/rename/retype.
- **Consumers declare a range** they accept (`>=1.0 <2.0`). A `1.4` card opened by a `1.1`
  reader: unknown minor fields are **preserved on round-trip**, not dropped — so a
  down-level editor can't silently strip a newer card's data (the failure mode where an old
  ST client nukes a V3-only field).
- **`extensions` never affects version negotiation.** Unknown namespaces are always carried
  through untouched.
- **Migrations are declared, not implied.** A `1.x → 2.0` bump ships a written field-by-field
  transform (the same discipline as this whole document), and `mare convert --to 2.0` runs
  it. No "does a `data` key exist?" sniffing to tell versions apart.

Next: see it all on one real card — [`05-example-elara.md`](05-example-elara.md).
