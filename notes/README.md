# MARE — a 2026 character-card spec that isn't held together with tape

> ## ⚠️ DRAFT — WIP — nothing here is final
> This is a **living brainstorm**, not a specification. Everything in these notes is an
> **idea in iteration**: field names, shapes, the codename, the AVIF-only decision, the
> versioning — **all of it is provisional and will change.** It is **not implemented**, **not
> approved**, and **not a commitment to build anything.** Do not cite it as "the spec," don't
> generate code from it, and don't treat any file here as settled. It exists to think out
> loud and pressure-test ideas. Expect contradictions between sessions as we revise. When in
> doubt: *this is a sketch on a napkin, written in pencil.*

> **Status:** brainstorm / design dossier — **DRAFT, actively changing.** Not implemented. Not committed to.
> **Working codename:** **MARE** — *Modular Actor & Roleplay Entity* (placeholder; themed to
> *The Bannered Mare*, rename freely).
> **One-line thesis:** stop welding a JSON blob into a PNG comment field and calling it a
> data format. Separate the **model** from the **container**, make every field **typed and
> validated**, carry the avatar as **AVIF**, and sign the whole thing.

This dossier is the answer to a what-if: *if we threw out the TavernCard V1/V2/V3 lineage
and designed a character-card format from scratch for 2026, what would it be?* It is
deliberately opinionated. It is written as a **middle finger to the incumbent** — but an
*evidence-based* one: almost every design decision here maps to a concrete bug we fixed in
this very repo's importer (`backend/src/character/card_parser.py`) while cleaning up real
cards.

## Why you can trust the diagnosis

We didn't imagine TavernCard's problems. Over the last few sessions we:

- reflowed a `personality` field whose bullet list had been **flattened into runs of
  spaces** because the format stores prose as one untyped string;
- recovered real names (**Elara Voss**, **Hazel Smith**, **Mina Eun-Hee**) that were
  buried in `Name:` / PList `name(...)` lines because the **`name` field does double duty**
  as both the `{{char}}` prompt token *and* the storefront listing title;
- stopped the importer from **assigning `{{user}}`'s name to the character** because names
  live in ungoverned prose and we were grabbing the first `name:` we saw;
- folded **smart quotes** to ASCII because cards mix straight and curled quotes in the same
  field;
- inferred **species / age / gender** from prose because there are no typed fields for them.

Every one of those is a workaround for a **missing or overloaded field**. MARE's job is to
make those workarounds unnecessary.

## Read in this order

| File | What's in it |
|---|---|
| [`00-manifesto.md`](00-manifesto.md) | The full charge sheet against TavernCard, and the 12 design principles that fall out of it. |
| [`01-data-model.md`](01-data-model.md) | The data model, field by field, with the TavernCard sin each field kills. JSON Schema spine. |
| [`02-container-and-avif.md`](02-container-and-avif.md) | The container: **one `.avif` file**, everything (avatar, sprites, voice, JSON) as HEIF items — how you actually embed the payload in ISO-BMFF — plus integrity & signing. Why there's no ZIP. |
| [`03-templating-and-runtime.md`](03-templating-and-runtime.md) | The variable/templating system that replaces `{{char}}` string-substitution, the greeting model, Lorebook v2, and the prompt-assembly contract. |
| [`04-migration-and-mapping.md`](04-migration-and-mapping.md) | Importing TavernCard (reusing our recovery heuristics), the validator/linter, mapping onto the TBM backend, and the versioning/migration policy. |
| [`05-example-elara.md`](05-example-elara.md) | A full worked card — **Elara Voss**, the shy-cousin card redeemed — plus a byte-level AVIF layout and a before/after against the original PNG. |
| [`06-json-schema.md`](06-json-schema.md) | The schema *as a versioned contract*: `$schema` self-reference, immutable published/versioned URLs, `$defs`/`$ref` modularity, schema+linter layers, SchemaStore + type generation, and CI enforcement. The thing that stops it decaying back into vibes. |

## The one-paragraph pitch

A MARE card is a **canonical, strictly-typed JSON document** (RFC 8785 canonicalization for
stable hashing) describing an **actor** — character, user-persona, or narrator. It ships as
**one `.avif` file** — HEIF is natively a multi-item container, so the avatar, every expression
sprite, the background, an optional voice clip, and the zstd-compressed card JSON all live as
items *inside that single image* (drop-one-file-in-Discord portability, no second archive).
While authoring you edit the raw JSON; the build embeds it into the `.avif`. Identity is
**structured** (`display_name` ≠
`reference_token` ≠ `given_name`), attributes are **typed** (age is a plain number, not the
string `"19-ish 😳"`), model-facing prose is **separated from
discovery metadata**, the templating language has a **frozen variable namespace** instead of
whatever-`{{...}}`-the-creator-felt-like, content is **rated and licensed** with SPDX, and
the whole document can be **Ed25519-signed** so "someone re-uploaded my card with a swapped
avatar and a Patreon link" becomes detectable.

## The comparison at a glance

| Dimension | TavernCard V2/V3 | MARE |
|---|---|---|
| Container | JSON, base64'd, in a PNG `tEXt` chunk | **one `.avif`** — avatar + all assets + zstd'd JSON as HEIF items; no second archive |
| Image codec | PNG (+33% base64 bloat on the payload too) | **AVIF** (AV1, royalty-free, alpha, HDR, animation) |
| Identity | one free-string `name` = title = `{{char}}` | `display_name` / `reference_token` / `given_name`+`family_name` / `nickname` / `pronouns`, all distinct |
| Attributes | none — baked into prose | typed `species` / `age{value}` / `gender` / `appearance` |
| Personality | one untyped string (bullets, PList, W++, whatever) | structured facets + typed speech model |
| Macros | `{{char}}` string-substitution, unescaped, undefined namespace | frozen variable schema, sandboxed dialect, no turn-markers-in-prose |
| Examples | `mes_example` string split on `<START>` | typed `dialogue_examples[]` with roles |
| Extensions | `extensions: {}` free-for-all | reverse-DNS namespaced, schema-registered |
| Provenance | `creator` string, maybe | creator object, **SPDX license**, source, tool |
| Lifecycle | none | top-level `created_at` / `updated_at` (ISO 8601 UTC) + `revision` counter |
| Integrity | none (anyone edits/re-hosts silently) | JCS hash + optional **Ed25519 signature** |
| Validation | none; front-ends render whatever | **published, versioned JSON Schema** (draft 2020-12) via `$schema` + a conformance linter; enforced at author/export/import/CI |
| Safety | implicit | explicit `content_rating` (maturity, warnings, `is_fictional`) |
| i18n | V3 bolted on `*_multilingual` | first-class `i18n` locale overrides |

Everything below is the long version.
