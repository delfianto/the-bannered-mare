# 02 — The container: one AVIF file, everything inside

← [`01-data-model.md`](01-data-model.md) · next: [`03-templating-and-runtime.md`](03-templating-and-runtime.md)

**A MARE card is one `.avif` file. That's the whole answer.** No second container, no ZIP, no
"it depends." HEIF — the box format AVIF already lives in — is *natively a multi-item
container*, so a single `.avif` holds everything a card needs: the avatar, every expression
sprite, the background, an optional voice clip, and the card's JSON data, each as an **item**
inside the same file. There is nothing a ZIP would add, so there is no ZIP.

The one thing that isn't the AVIF is the **authoring source**. While you write a card you edit
raw JSON (`elara.mare.json`) — that's just the card's *source text*, the way you edit `.ts`
before it builds to `.js`. The build step embeds that JSON (and the images) into the `.avif`.
**The thing you share is always the `.avif`.** Source vs. built artifact — not two formats.

> **Why not a ZIP (killing the question for good):** a ZIP would be a *second* archive wrapped
> around files that are *already* individually compressed images plus one small JSON — it saves
> nothing, and HEIF already gives us a manifest of items with offsets, types, and references.
> Adding a ZIP would be inventing a container to sit next to a container. We don't.

---

## Part A — Why AVIF

AVIF = the **AV1 Image File Format**: an AV1 intra-frame wrapped in the ISO Base Media File
Format (ISO/IEC 14496-12), specifically its HEIF profile (ISO/IEC 23008-12). Two independent
facts make it the right pick:

1. **AV1 is a great still-image codec.** Royalty-free (AOMedia), alpha channel, 10/12-bit HDR,
   wide gamut (BT.2020), film-grain synthesis, animated avatars via image sequences.
2. **HEIF is a real container** — a box structure holding *multiple images and arbitrary
   metadata/data items*. This is the part that matters for us: it means the card's data (and
   every extra asset) rides *natively* as items, not smuggled into a text comment, and not
   needing a ZIP wrapped around it.

### AVIF vs PNG for an avatar

| | PNG | AVIF |
|---|---|---|
| Painted 1024² portrait | ~1.8 MB lossless | ~150–300 KB visually-lossless, ~60 KB good-enough |
| Alpha | yes (verbose) | yes (efficient) |
| HDR / 10-bit / BT.2020 | no | yes |
| Animation | APNG (bolt-on) | native image sequence |
| Royalty | free | free (AV1/AOMedia) |
| Carries extra data | ancillary chunks (`tEXt`/`zTXt`/`iTXt`), one asset | **HEIF items** — many images + arbitrary MIME payloads in one file |

**Honest caveats** (so nobody says we oversold it):

- **Lossless AVIF isn't always smaller than PNG** for *tiny palettized pixel-art*. Character
  portraits are never that case; non-issue.
- **Encode is CPU-heavier** than PNG. Irrelevant — encode once, read forever.
- **Old tooling** may not decode AVIF. In 2026 browsers/OSes do; and the card's *data* is
  readable by anything that can parse HEIF boxes even if it can't decode the AV1 pixels.
- **Naive metadata stripping exists** (same risk PNG's `tEXt` had). Mitigated by: the payload
  is (a) content-**hashed** so tampering/loss is detectable, and (b) optionally mirrored as a
  breadcrumb in an **XMP** item that mainstream tools preserve (see Part B).

---

## Part B — How everything lives inside the one AVIF

HEIF's `meta` box is a table of **items**. Some items are coded images (`av01`); some are
data (`mime`). A MARE card just populates that table: one primary image (the avatar), any
number of extra image items (sprites, background), optional data items (voice, the card JSON).
`pitm` marks the avatar as the primary/visible image, so a dumb viewer shows a portrait while
a MARE reader pulls the rest.

### The box tree of a full MARE card

```
ftyp   major_brand="avif", compatible=["avif","mif1","miaf",...]
meta
├─ hdlr  handler = "pict"
├─ pitm  primary_item_ID = 1                        # avatar is what a plain viewer renders
├─ iinf  item_info:
│    ├─ infe 1  "av01"                               # avatar image
│    ├─ infe 2  "av01"                               # thumbnail (native HEIF thumb)
│    ├─ infe 3  "av01"  name="expr:happy"            # expression sprite
│    ├─ infe 4  "av01"  name="expr:shy"              # expression sprite
│    ├─ infe 5  "av01"  name="bg:kitchen"            # background image
│    ├─ infe 6  "mime"  content_type="audio/opus"    name="voice:sample"   # a voice clip, as data
│    └─ infe 7  "mime"  content_type="application/vnd.mare.character+json"
│                        content_encoding="zstd"      # ← THE CARD DATA
├─ iref
│    ├─ 2 "thmb" 1                                    # item 2 is the thumbnail OF item 1
│    └─ 7 "cdsc" 1                                    # the card data DESCRIBES the avatar
├─ iprp  item properties (colr, pixi, ispe, ...)     # per image item
└─ iloc  offsets/lengths for items 1..7 → mdat
mdat
├─ [AV1 avatar]  [AV1 thumb]  [AV1 happy]  [AV1 shy]  [AV1 kitchen]
├─ [opus voice bytes]
└─ [zstd( JCS( character.json ) )]
```

How the model points at these:

- **`assets[].path` is a fragment reference into the same file** — `"#item=3"` for the happy
  sprite, `"#item=6"` for the voice clip. No external files, no ZIP paths. One `.avif`,
  self-contained.
- **The card data is item #7, a `mime` item** with `content_type =
  application/vnd.mare.character+json`. Any HEIF reader can enumerate items and pull it out by
  content-type; it doesn't need to understand MARE to *preserve* it.
- **`content_encoding = "zstd"`** — the JSON is **zstd-compressed** (RFC 8878), stored raw in
  `mdat`. No base64 anywhere. Compare TavernCard: JSON → base64 (+33%) → uncompressed `tEXt`.
  A 40 KB lorebook-heavy card is ~9–12 KB here vs. ~55 KB there.
- **Thumbnails and derivations are native.** The thumbnail is an image item linked by an
  `iref` of type `thmb` — HEIF's built-in mechanism, not a bolt-on.

### Reading and writing, in words

**Read:** parse `ftyp`/`meta`, find the `infe` whose `item_type=="mime"` and
`content_type==application/vnd.mare.character+json`, resolve its bytes via `iloc` from `mdat`,
`zstd`-decompress, parse JSON, verify `integrity.hash`, then resolve `assets[].path` fragments
to their image/data items as needed. **Write:** encode the images, zstd the canonical JSON,
lay them into `mdat`, build the `iinf`/`iloc`/`iref` tables. Editing only the card data
rewrites item #7 — the image bytes are untouched, so re-saving a card never re-encodes the
avatar.

### The XMP breadcrumb (interop insurance, optional)

Because some pipelines strip unknown items but carry Exif/XMP, a writer **may** also drop a
tiny copy — or just `id` + `integrity.hash` + a fetch URL — into an **XMP** item under a
`mare:` namespace. Belt-and-suspenders: full fidelity in the MIME item, a survivable
breadcrumb in XMP. Never the *only* copy.

---

## Part C — Canonicalization, hashing, signing

Integrity (Principle 8) only works if the document has **one** byte form — which TavernCard
never had (smart quotes, whitespace, key order all drift), and why you can't hash or dedupe
those cards.

1. **Canonicalize** the JSON with **RFC 8785 (JCS)**: UTF-8, sorted keys, minimal number
   formatting, NFC strings. Remove `integrity.hash`/`integrity.signature` first (a field can't
   contain its own hash).
2. **Hash**: `sha256` over the canonical bytes → `integrity.hash = "sha256:…"`.
3. **Sign** (optional): **Ed25519** (RFC 8032) over the same canonical bytes →
   `integrity.signature`. Key identified by a `did:key`, raw public key, or fingerprint.
4. **The assets are covered for free.** Every image/data item's `sha256` lives in `assets[]`
   *inside* the JSON, so signing the JSON transitively fixes the assets: swap the avatar bytes
   in a signed `.avif` and its hash no longer matches `assets[avatar].hash`, and that mismatch
   (or the broken signature) is detectable. One signature, whole card — no separate manifest to
   sign, because there's no separate archive.

### The trust model, stated plainly

A signature answers **"has this changed since key K signed it?"** and **"does K vouch for
it?"** — nothing more. It does not manufacture trust: a client trusts a signature *iff* it
already trusts K (a creator you follow, a curator/registry, your own key). Unsigned cards are
fine and common; they just get no tamper-evidence beyond the bare `hash`. The opposite of
TavernCard, where a re-hosted card with an injected system prompt is **indistinguishable** from
the original.

---

## Part D — Media types (for registries and OSes)

| Thing | Media type | Extension |
|---|---|---|
| The card (what you share) | `image/avif` (with MARE items inside) | `.avif` |
| Authoring source (the raw JSON) | `application/vnd.mare.character+json` | `.mare.json` |

That's the whole surface — two things, and one of them is just the editable source. Registering
`application/vnd.mare.character+json` (IANA) lets tooling recognize the payload; the shared
artifact is a plain `image/avif` that happens to carry MARE items, so it routes and previews as
an image everywhere with zero special support.

---

## The payoff, in one diff

TavernCard, conceptually:

```
avatar.png
  └─ tEXt "chara" = base64( json )     # +33%, uncompressed, ONE asset, no integrity, weldable-only
```

MARE — one AVIF, everything inside:

```
elara.avif
  ├─ image item 1  = AV1(avatar)                 # 5–10× smaller than PNG; what a plain viewer shows
  ├─ image item 2  = AV1(thumbnail)              # native HEIF thumb
  ├─ image items 3..N = AV1(sprites, background) # extra visuals, same file
  ├─ mime  item    = audio/opus (voice)          # optional, same file
  └─ mime  item    = zstd( JCS( character.json ) ) # compressed, typed, hashable, signable
```

Source you edit: `elara.mare.json` → **builds to** `elara.avif`. That's the only "two things,"
and it's source-vs-artifact, not two container formats.

Next: the runtime side — templating, greetings, lore, and prompt assembly —
[`03-templating-and-runtime.md`](03-templating-and-runtime.md).
