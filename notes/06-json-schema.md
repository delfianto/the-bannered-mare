# 06 — The schema *is* the contract (versioned, published, enforced)

← [`05-example-elara.md`](05-example-elara.md) · complements [`01-data-model.md`](01-data-model.md) · back to [`README.md`](README.md)

[`01`](01-data-model.md) defined the *shape*. This file is about making that shape **binding**
— a published, versioned **JSON Schema** that documents self-reference via `$schema`, that
editors validate against automatically, that CI can reject a bad card with, and that we
generate types from. This is the machinery every serious modern JSON format ships:
`package.json`, `tsconfig.json`, `renovate.json`, `.eslintrc`, `composer.json`, GitHub
Actions workflows, OpenAPI/AsyncAPI documents — none of them rely on "please be tidy." They
rely on a schema. So does MARE.

Principle 10 said *validate hard at the boundary*. This is the how.

---

## Part A — The document points at its schema (`$schema`)

Every MARE document carries a top-level `$schema` (recommended, and emitted by any conformant
writer):

```jsonc
{
  "$schema": "https://mare.spec/schema/1.0/character.schema.json",
  "spec": "mare",
  "spec_version": "1.0.0",
  ...
}
```

This one line is what gives you the **modern config experience** for free:

- Open `elara.mare.json` in VS Code / JetBrains → red squiggles on a wrong type, autocomplete
  on field names, hover docs from the schema's `description`s, enum dropdowns for
  `actor_kind` / `maturity`. Zero setup, because the editor follows `$schema`.
- It's **self-describing**: the artifact declares the exact contract it claims to satisfy. A
  validator doesn't guess which rules apply; the document says so.

**`$schema` vs `spec_version` — why both.** They're not redundant:

| Field | Answers | Machine-actionable for |
|---|---|---|
| `spec_version: "1.4.0"` | "which version of the *format* is this?" | SemVer compatibility negotiation (Principle 12) |
| `$schema: ".../1.4/character.schema.json"` | "which concrete *document* validates me?" | fetch-and-validate, editor tooling |

`$schema` is derivable from `spec_version` (they must agree — the linter checks it), but making
it explicit is what plugs into the existing schema-tooling ecosystem, which keys off `$schema`,
not off a custom `spec_version` field it's never heard of.

---

## Part B — How the schema itself is versioned and published

The schema is not a file that drifts. It's a set of **immutable, versioned artifacts** at
stable URLs — the same discipline as the JSON Schema drafts themselves, or a pinned OpenAPI
doc.

```
https://mare.spec/schema/1.0/character.schema.json     # frozen forever once 1.0 ships
https://mare.spec/schema/1.1/character.schema.json     # 1.1 adds optional fields; 1.0 untouched
https://mare.spec/schema/1/character.schema.json        # floating alias → latest 1.x (dev convenience)
https://mare.spec/schema/latest/character.schema.json   # floating alias → newest (never pin to this)
```

Rules of the road (mirrors how modern specs handle it):

- **Published = immutable.** `1.0/character.schema.json` never changes after release. A bug in
  the schema means `1.0.1`, not an edit-in-place — otherwise a document that validated
  yesterday fails today, which is the "vibes" failure we're eliminating.
- **The schema version tracks `spec_version` (major.minor).** *Minor* bumps are **additive and
  backward-compatible**: new **optional** properties, new values in **open** enums. A `1.0`
  document still validates against `1.1`. *Major* bumps may remove/retype/rename and ship a
  written migration (see [`04`](04-migration-and-mapping.md) Part D).
- **The `$id` inside the schema is its canonical URL**; the schema's own `$schema` points at
  the **JSON Schema dialect** it's written in — **draft 2020-12** (the current, widely-tooled
  dialect: `ajv`, Python `jsonschema`, VS Code, JetBrains all speak it).

```jsonc
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",   // the DIALECT this schema is written in
  "$id": "https://mare.spec/schema/1.0/character.schema.json", // the canonical id of THIS schema
  "title": "MARE Character Card 1.0",
  "type": "object",
  ...
}
```

- **The schema ships *in the repo too*.** The URL is canonical, but the exact bytes are vendored
  (e.g. `spec/schema/1.0/…`) so validation works offline and in CI without a network call. URL
  for tooling discovery; local copy for hermetic builds.

### Forward-compatibility, resolved (the strict-vs-future tension)

`additionalProperties: false` at the top level (which we want, to force deliberate growth)
seems to fight forward-compat: how does a `1.1` field not break a `1.0` validator? The modern
answer, and MARE's rule:

> **Validate a document against the schema *it declares*, not against whatever local copy you
> happen to have.** A `1.4` card is validated with the `1.4` schema (fetched or vendored).

So there's no contradiction: the `1.4` schema knows the `1.4` fields. A `1.0`-only tool that
receives a `1.4` card either fetches the `1.4` schema, or — if it refuses to — treats the card
as "newer than I speak" and round-trips unknown fields untouched (Principle 12) rather than
failing or silently dropping them. And anything genuinely *outside* the versioned schema goes
in **`extensions`**, which is `additionalProperties: true` by design — the one sanctioned open
region.

---

## Part C — Modular schema with `$defs` + `$ref` (so it stays maintainable)

A 1,500-line monolithic schema rots. MARE's schema is **decomposed into reusable definitions**
and split across files with `$ref` — exactly how OpenAPI, AsyncAPI, and the GitHub-workflow
schema stay sane.

```
spec/schema/1.0/
├─ character.schema.json      # top-level: $refs into the others
├─ common.schema.json         # $defs: pronouns, timestamp, uuid, spdxLicense, referenceToken
├─ identity.schema.json
├─ attributes.schema.json     # $defs: age, species, gender
├─ lore.schema.json           # $defs: loreEntry, placement, matchRules
├─ asset.schema.json
├─ provenance.schema.json
└─ integrity.schema.json
```

```jsonc
// character.schema.json (excerpt)
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://mare.spec/schema/1.0/character.schema.json",
  "type": "object",
  "required": ["spec", "spec_version", "id", "actor_kind", "revision",
               "created_at", "updated_at", "identity", "profile", "provenance"],
  "additionalProperties": false,
  "properties": {
    "$schema":      { "type": "string", "format": "uri" },
    "spec":         { "const": "mare" },
    "spec_version": { "$ref": "common.schema.json#/$defs/semver" },
    "id":           { "$ref": "common.schema.json#/$defs/uuid" },
    "created_at":   { "$ref": "common.schema.json#/$defs/utcTimestamp" },
    "updated_at":   { "$ref": "common.schema.json#/$defs/utcTimestamp" },
    "identity":     { "$ref": "identity.schema.json" },
    "attributes":   { "$ref": "attributes.schema.json" },
    "lore":         { "$ref": "lore.schema.json" },
    "provenance":   { "$ref": "provenance.schema.json" }
  }
}
```

```jsonc
// common.schema.json (excerpt) — the reusable building blocks
{
  "$id": "https://mare.spec/schema/1.0/common.schema.json",
  "$defs": {
    "semver":       { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
    "uuid":         { "type": "string", "format": "uuid" },
    "utcTimestamp": { "type": "string", "format": "date-time",
                      "pattern": "Z$", "description": "ISO 8601, UTC, Z-suffixed" },
    "referenceToken": { "type": "string", "minLength": 1, "maxLength": 60 },
    "spdxLicense":  { "type": "string",
                      "description": "SPDX license id or LicenseRef-*",
                      "examples": ["CC-BY-4.0", "CC-BY-NC-4.0", "LicenseRef-custom"] },
    "slug":         { "type": "string", "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$", "maxLength": 40,
                      "description": "lowercase kebab; the canonical machine form of a tag/genre/franchise" },
    "slugArray":    { "type": "array", "items": { "$ref": "#/$defs/slug" },
                      "uniqueItems": true, "maxItems": 32 },
    "bcp47":        { "type": "string", "pattern": "^[a-z]{2,3}(-[A-Za-z0-9]+)*$",
                      "description": "BCP-47 language tag", "examples": ["en", "ja", "pt-BR"] }
  }
}
```

The `pattern: "Z$"` on `utcTimestamp` is a nice example: it lets the *schema itself* enforce
the UTC-`Z` rule we described for `created_at`/`updated_at`, instead of leaving it to the
linter. **The same trick governs tags:** `taxonomy.tags` (and `genres`, `themes`, `franchise`)
are just `$ref: "#/$defs/slug(Array)"`, so the casing/whitespace/comma chaos from real cards
([`01`](01-data-model.md) §10) is **structurally impossible** — `"can be wholesome, can be
sexy"` fails the `slug` pattern at validation time; it can't be stored. Define a constraint
once, reuse it everywhere via `$ref`.

---

## Part D — Two layers: schema (structural) + linter (semantic)

JSON Schema is powerful but not omniscient. `format: uuid` / `date-time` are, by spec,
**annotations** — many validators don't *enforce* them unless told to, and some rules simply
can't be expressed structurally. So MARE validates in **two layers**, and says which is which:

| Rule | Enforced by |
|---|---|
| required fields, types, enums, `additionalProperties`, string patterns, array bounds | **JSON Schema** (draft 2020-12) |
| `$schema` URL agrees with `spec_version` | linter |
| `updated_at >= created_at` | linter (cross-field; schema can't compare two values) |
| `reference_token` is actually short & token-like (warn) | linter |
| `license` is a *real* SPDX id | linter (against the SPDX list) |
| `integrity.hash` matches the canonical bytes; signature verifies | linter (needs the bytes + crypto) |
| unknown `{{...}}` macros survived import | linter |

The schema is the **floor** anyone can check with an off-the-shelf validator; the linter adds
the **semantic** checks that need context. `mare lint` runs both (structural failures =
`error`, most semantic issues = `error` or `warning` per [`04`](04-migration-and-mapping.md)
Part B).

---

## Part E — The schema drives tooling (the real payoff)

Because the schema is machine-readable and annotated (`title`, `description`, `examples`,
`default`, `deprecated`), it's not just a gate — it's a **source of truth** everything else is
generated from:

- **Editor UX:** validation + autocomplete + hover docs, via `$schema` (Part A) or a
  **SchemaStore** catalog entry that maps `*.mare.json` → the schema, so it works even without
  the `$schema` line. (Getting listed in [schemastore.org](https://www.schemastore.org)'s
  catalog is *the* distribution channel for "my JSON format is now understood by every editor.")
- **Type generation — single source of truth:**
  - TypeScript: `json-schema-to-typescript` → `MareCharacter` interfaces for a web editor.
  - Python: `datamodel-code-generator` → **Pydantic** models for the backend. The importer's
    `ParsedCard` stops being hand-maintained and becomes *generated from the schema*.
- **Form generation:** a card editor ("mare-studio") renders its UI **from the schema** —
  `enum` → dropdown, `maxLength` → input limit, `description` → field help. New optional field
  in `1.1`? The editor grows a control for free.
- **`deprecated: true`** lets a field be sunset with warnings before a major bump removes it —
  graceful evolution instead of breakage.

### You already do exactly this here

This isn't exotic — it's the pattern **this repo already uses for its API contract**. Per the
root `CLAUDE.md`: the backend emits `openapi.json`, and the frontend runs `bun run api:gen` to
generate `frontend/src/api/schema.d.ts` from it. Schema → generated types → both sides can't
drift. MARE applies the identical discipline to *character cards*: one canonical
`character.schema.json`, from which the TS editor types and the Python Pydantic models are
generated, so `ParsedCard`, the frontend, and the on-disk card can never disagree about what a
field means.

---

## Part F — Validation in the pipeline / CI

Where validation actually runs, end to end:

1. **Authoring:** the editor validates live via `$schema` (Part A). Bad card, red squiggle,
   immediately.
2. **On save / export:** the writer canonicalizes (JCS), then `mare lint` runs schema + linter
   before it will embed the JSON into the `.avif`. A card that doesn't validate **cannot be
   exported** — clean-in, clean-out (Principle 10).
3. **On import (TavernCard → MARE):** the pipeline in [`04`](04-migration-and-mapping.md)
   produces MARE, then validates it. Import may be *lenient reading* legacy junk, but it only
   *emits* schema-valid MARE.
4. **CI / registry:** a card registry validates on upload against the pinned schema version;
   a git repo of cards runs `mare lint` in CI — the same way this repo could lint its
   `characters/` fixtures. A malformed card never lands.

The through-line: **the JSON is never trusted to be tidy — it is *proven* tidy at every
boundary, against a versioned, published schema.** That's the difference between a format and a
convention, and it's the specific thing that stops MARE from decaying into the TavernCard
prose-swamp we spent all week cleaning up.

---

## TL;DR

- Documents carry **`$schema`** → free IDE validation/autocomplete, self-describing.
- The schema is **published at immutable, versioned URLs** and **vendored in-repo**; version
  tracks `spec_version` (major.minor), additive-only within a major line.
- **Validate against the schema the document declares**, which dissolves the strict-vs-forward-
  compat tension; `extensions` is the one open region.
- Schema is **modular** (`$defs` + `$ref` across files), dialect **draft 2020-12**.
- **Two layers:** JSON Schema (structural) + linter (semantic cross-field/crypto/SPDX checks).
- The schema **generates** TS types and Pydantic models and drives editor forms — the same
  `openapi.json → schema.d.ts` discipline this repo already runs, applied to cards.
- Validation is enforced at **author, export, import, and CI** — proven tidy, not asked nicely.
