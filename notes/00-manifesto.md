# 00 — The charge sheet, and the principles that fall out of it

← back to [`README.md`](README.md) · next: [`01-data-model.md`](01-data-model.md)

TavernCard (the SillyTavern "V2" spec, `chara_card_v2`, and its "V3" successor
`chara_card_v3`) won by being *good enough* in 2023 and by network effects. It is not evil.
It is just a **1990s idea** — "stash a config blob in an image comment" — wearing a 2023
hoodie, and the entire ecosystem's messiness is downstream of a handful of structural
mistakes. Here is the charge sheet. Each count ends with the principle it forces.

---

## Count 1 — The container is an image comment

A TavernCard is a JSON object, serialized, **base64-encoded**, and stuffed into a PNG
`tEXt` chunk under the keyword `chara` (V3 adds a second `ccv3` chunk). That's the whole
"format."

Consequences we have personally hit:

- **Base64 is a 33% tax** on every byte of the payload, *inside* an already-uncompressed
  text chunk. For a card with a big lorebook that's real bloat.
- **Naive tools destroy it.** Resize the avatar in an editor that doesn't preserve ancillary
  chunks and the character is *gone*. The data's survival depends on image tools being
  polite about metadata they don't understand.
- **One image, one asset.** Want expression sprites, a background, a voice sample? There's
  nowhere to put them. People ship ZIPs of PNGs held together by naming conventions.
- **The image and the data are welded.** You cannot update the portrait without rewriting
  the data payload, and you cannot diff two versions of the character without diffing a
  binary.

> **Principle 1 — Separate the *model* from the *container*.** The character is a document.
> An image is an *asset the document references*, not the filing cabinet the document lives
> inside. Define one canonical model and several container *bindings*.

---

## Count 2 — PNG in 2026

PNG is 30 years old. It is lossless, universal, and — for this job — the wrong tool. Avatar
portraits are photographic or painted; PNG stores them enormously. PNG has no HDR, no wide
gamut, weak alpha ergonomics, and its only "animation" (APNG) is a bolt-on.

> **Principle 2 — Use AVIF.** AV1-based, **royalty-free** (AOMedia), alpha, 10/12-bit HDR,
> wide gamut, film-grain synthesis, and **animation** in one codec. A painted portrait is
> typically **5–10× smaller** than the PNG at visually-lossless quality. (Honest caveat:
> for *tiny pixel-art* palettized images PNG can still win, and encoder CPU cost is higher —
> see [`02`](02-container-and-avif.md). Neither matters for character portraits.)

---

## Count 3 — `name` does three jobs and botches all three

This is the big one, and it's the bug we spent the most time on. TavernCard's `name` is a
single free-text string with **no validation**, and it is simultaneously:

1. the **display title** shown in the UI and the marketplace listing,
2. the **`{{char}}` token** substituted into every prompt, and
3. the **character's actual name**.

These have *opposite* incentives. The storefront wants a long keyword-stuffed headline; the
prompt wants a short token. So creators optimize for the store and the junk leaks into the
model:

```
name = "Mina — Your Mean and Bratty Stepsister Catches you Sleeping in her Bed"
```

…and now the model believes its name is that entire sentence. Meanwhile the *real* name is
hidden in the description as `Name: Elara Voss` or the PList form `[{{char}} name(Mina
Eun-Hee)]`, because there was nowhere structured to put it. We wrote **three commits** of
heuristics to claw names back out of prose, and even added a guard so we'd stop assigning
`{{user}}`'s name to the character.

> **Principle 3 — Split identity into distinct, typed fields.** `display_name` (free,
> for humans) ≠ `reference_token` (what `{{char}}` resolves to) ≠ `given_name` /
> `family_name` (structured) ≠ `nickname` ≠ `aliases[]`. No field ever does two jobs.

---

## Count 4 — Everything interesting is unstructured prose

There is no field for species, age, gender, pronouns, body, or appearance. Creators bake
them into `description`/`personality` as ad-hoc "character sheets" in a dozen mutually
incompatible mini-dialects:

- Markdown bold: `**Age:** 19`
- Emoji labels: `🎂 Age: 20`
- **PList**: `[Elara: shy, kind; age(19); body(petite)]`
- **W++ / Boostyle**: `[ character("Elara") { Age("19") Body("petite") } ]`
- Just… sentences: `a mesmerizing 19-year-old Khajiit dancer`

We built a *two-pass extractor* (labeled fields, then a prose fallback with a curated
species vocabulary and a gender-pronoun tally) to recover this. It works, but it's
**archaeology** — reconstructing structured data a saner format would have stored directly.

> **Principle 4 — Typed fields for structured facts.** `age` is `{value: 19}` — a number, not
> the string `"19-ish 😳"` (and no `unit`/`is_adult` ceremony: years is implicit, adulthood is
> `value >= 18` or a `content_rating` concern). `species` is a controlled value with a
> free-text escape hatch. `gender`/`pronouns` are structured. Prose is for *prose*.

---

## Count 5 — Prose is a swamp of encoding and whitespace bugs

Because the "sheet" is one big string, it accumulates every text sin:

- **Smart-quote soup** — straight and curled quotes mixed in one field (Word/Docs vs. plain
  editors), which breaks exact-match lore-key triggers. We fold them to ASCII on import.
- **Whitespace mangling** — a bullet list whose newlines got replaced by runs of spaces,
  producing one unreadable blob. We literally wrote a reflow pass for this.
- **No canonical form** — two "identical" cards can differ by invisible bytes, so you can't
  hash or dedupe them.

> **Principle 5 — One canonical text encoding.** UTF-8, Unicode **NFC**, `\n` newlines, a
> declared Markdown flavor for prose fields, and **RFC 8785 (JCS)** canonical JSON so the
> document has *exactly one* byte representation for hashing and signing.

---

## Count 6 — `{{char}}`/`{{user}}` is string-substitution with no grammar

The macro system is "find `{{char}}`, replace with a string." There is no defined variable
namespace, no escaping, no types. Cards embed **turn markers inside prose** (`{{char}}:
hello`) and front-ends parse them back out with tolerant regexes — this repo's
`prompt_builder.py` matches `\{{0,2}\s*(user|char(?:acter)?)\s*\}{0,2}` (**zero to two
braces**!) precisely because malformed cards are the norm. Nested macros, conditionals, and
"random" tricks got layered on with no spec.

> **Principle 6 — A real templating contract.** A *frozen* variable namespace
> (`char.name`, `char.pronoun.subject`, `user.name`, …), a small sandboxed dialect for
> conditionals/lists, defined escaping, and **structured** dialogue examples so turn roles
> are data, never regex-scraped from prose.

---

## Count 7 — `extensions: {}` is a junk drawer

V2's escape hatch is an untyped free-form object. Every client invented incompatible keys
(`depth_prompt`, `talkativeness`, `fav`, `world`, a dozen `risuai`/`agnai` blobs). There's
no namespacing, no schema, no discovery. Reading another client's card is guesswork. (We
invented our *own* `bannered_mare` extension for species/gender/age — guilty as charged.)

> **Principle 7 — Namespaced, schema'd extensions.** Reverse-DNS keys
> (`ai.risu.emotion_pack`), each pointing at a declared (ideally URL-addressable) schema.
> Unknown namespaces are preserved verbatim on round-trip and never block validation.

---

## Count 8 — No provenance, no license, no integrity

A card says `creator: "someone"` at best. There is no license, no source URL, no
created/modified time, and **no integrity**. Cards are copied, edited, monetized, and
re-hosted with swapped avatars and injected "join my Patreon" system prompts — and none of
it is detectable. The `post_history_instructions` field is even *documented* as the place to
put a "jailbreak," blessing prompt-injection as a first-class feature.

> **Principle 8 — Provenance and integrity are first-class.** A creator object, an **SPDX
> license id**, a source URI, timestamps, the authoring tool, a content hash over the
> canonical bytes, and an **optional Ed25519 signature**. Trust is "self-asserted unless a
> key you already trust signed it" — not "trust the internet."

---

## Count 9 — Card definition is tangled with runtime state

`scenario` is described as the "*current* scenario/situation." `first_mes` is baked in. The
card conflates the **immutable definition** of a character with the **mutable state** of one
play session. You can't cache/dedupe the definition, and re-sharing a card leaks whatever
session drift got saved into it.

> **Principle 9 — The card is immutable definition; session state lives elsewhere.** A card
> describes *who the actor is and how a scene may open*. Where the scene has *gone* is chat
> state, not card data.

---

## Count 10 — There is no validation, so there is no floor

Nothing rejects a malformed card. `name` can be empty, `age` can be `"immortal ancient (looks
18)"`, `tags` can be a string instead of a list. Front-ends cope by being infinitely
lenient, which means the *data* is never forced to be clean, which is the root cause of
every other count on this sheet.

> **Principle 10 — Validate hard at the boundary.** A published JSON Schema + a conformance
> linter with **errors** (reject) and **warnings** (accept-but-flag). A conformant importer
> may still be lenient reading legacy TavernCard, but it *emits* only clean MARE.

---

## Count 11 — Only one kind of actor exists

TavernCard describes an NPC "character." The **user persona** (`{{user}}`) is a separate,
poorer concept in each client, and "narrator"/"scene" actors aren't modeled at all. The same
data — a name, pronouns, appearance, a description — gets re-specified three times.

> **Principle 11 — One actor model, several kinds.** `actor_kind: character | persona |
> narrator`. A persona is just a card whose kind is `persona`. One schema, one importer, one
> asset pipeline. (This maps directly onto TBM's split `Character` vs `Persona` tables —
> see [`04`](04-migration-and-mapping.md).)

---

## Count 12 — Versioning is vibes

"V2" and "V3" are wire-format nicknames, not a policy. There's no semantic-version field
with defined compatibility rules, no migration contract, no way for a tool to say "I speak
1.x but not 2.x." Detection is "does a `data` key exist?" (which is how *our* parser tells
V1 from V2).

> **Principle 12 — SemVer with a compatibility contract.** `spec_version: "1.2.0"`. Minor =
> additive/back-compatible, major = breaking, and every consumer declares the range it
> supports. Unknown minor fields are preserved, not dropped.

---

## The twelve principles, condensed

1. Separate model from container.
2. AVIF, not PNG.
3. Identity is several distinct typed fields, never one.
4. Typed fields for structured facts; prose only for prose.
5. One canonical text/JSON encoding (NFC + JCS).
6. A real templating contract with a frozen variable namespace.
7. Namespaced, schema'd extensions.
8. First-class provenance, licensing, and integrity/signing.
9. Immutable definition; session state lives elsewhere.
10. Hard validation at the boundary.
11. One actor model, several kinds.
12. SemVer with a compatibility contract.

The rest of this dossier turns these into an actual schema, an actual container, and an
actual migration path. Onward to [`01-data-model.md`](01-data-model.md).
