# 03 — Templating, greetings, lore, and prompt assembly

← [`02-container-and-avif.md`](02-container-and-avif.md) · next: [`04-migration-and-mapping.md`](04-migration-and-mapping.md)

Data at rest is half the problem; the other half is what a runtime *does* with it. TavernCard's
runtime story is `{{char}}` string-substitution plus a lorebook, both under-specified, which
is why every client renders cards slightly differently and why our `prompt_builder.py` has
defensive regexes. MARE specifies the runtime contract.

---

## Part A — The templating dialect: `mare-tmpl@1`

The rule that prevents the whole `{{char}}`-is-a-sentence disaster: **variables reference a
frozen namespace of typed fields, and prose never contains turn markers.**

### The variable namespace (frozen per spec_version)

```
char.id                     char.display_name        char.reference_token
char.given_name             char.family_name         char.nickname
char.pronoun.subject        char.pronoun.object      char.pronoun.possessive_det
char.pronoun.possessive     char.pronoun.reflexive
char.attributes.age.value   char.attributes.species.value   char.attributes.gender.value

user.display_name           user.reference_token     user.pronoun.*        # the persona (actor_kind=persona)
scene.scenario
sys.date  sys.time  sys.datetime  sys.weekday                              # host-provided, defined tz policy
```

- **`{char}` alone is an alias for `char.reference_token`** — *not* `display_name`. This one
  aliasing decision is the entire fix for "the model thinks its name is the marketplace
  title." The token is short by construction (validator warns >60 chars).
- Unknown variables are a **render error surfaced to the author** at validation time — not a
  silently-empty string (TavernCard) and not a literal `{{char}}` leaking into the model.
- Whitespace inside braces is insignificant; braces are `{ }` (single). A literal brace is
  `{{` → `{` (doubling escapes, like `str.format`).

### The mini-grammar (deliberately small)

```jinja
{char.display_name}                                   # substitution
{if char.nickname}{char.nickname}{else}{char.reference_token}{endif}   # one conditional
{for q in voice.quirks}- {q}\n{endfor}                # one loop
{pick scene.greetings where tag="cozy"}               # tag-filtered selection (returns .content)
{char.pronoun.subject|capitalize}                     # a closed set of filters
```

- **Sandboxed.** No arbitrary expressions, no attribute access outside the namespace, no
  function calls beyond a **closed filter set** (`capitalize`, `upper`, `lower`, `trim`,
  `default:"x"`). This is a *card*, not a program — it should never be able to loop forever
  or read the host.
- **One dialect id, pinned in `prompt.template_dialect`.** A renderer that only knows
  `mare-tmpl@1` refuses `@2` loudly instead of mis-parsing. Compare: TavernCard strings might
  be ST macros, RisuAI's CBS, Agnai's syntax, or raw text, with no marker at all.
- **Reference implementation** target: a MiniJinja/Jinja *subset* with the namespace injected
  and everything else stripped. (This maps onto TBM's existing `template_service.render`,
  which already does Jinja-style rendering — see [`04`](04-migration-and-mapping.md).)

### Why prose has no turn markers

Dialogue and greetings are **structured** (`turns[]` with explicit `role`, [`01`](01-data-model.md)
§7). A renderer emits role-tagged messages directly. Nothing ever writes `{{char}}: hi` into a
prose blob for a downstream regex to unscramble. The `\{{0,2}...` "zero-to-two-braces"
tolerance in our current builder becomes unnecessary because malformed turn markers cannot
exist.

---

## Part B — Greetings, resolved

```jsonc
"scene": {
  "greetings": [
    { "id": "g_default", "label": "Default",     "tags": ["sfw"],         "content": "..." },
    { "id": "g_rainy",   "label": "Rainy night",  "tags": ["sfw","cozy"],  "content": "..." },
    { "id": "g_spicy",   "label": "Late & alone", "tags": ["explicit"],    "content": "...",
      "requires": { "content_rating.maturity": "explicit" } }
  ],
  "default_greeting": "g_default"
}
```

Runtime rules:

- A client picks `default_greeting`, lets the user choose by `label`, filters by `tags`, or
  rolls a random one within a tag — all from **data**, versus TavernCard's `first_mes` +
  parallel `alternate_greetings[]` string array with no labels or tags.
- A greeting may declare `requires` (e.g. an explicit greeting only offered when the client's
  maturity gate allows it). Honest gating, as data.
- Greeting `content` is `mare-tmpl@1` — so `{char.pronoun.subject|capitalize}` works, but no
  turn markers.

---

## Part C — Lorebook v2 (world info that isn't a footgun)

TBM's existing `LoreEntry` model is already **good** — keys, secondary keys with
AND/OR/NOT logic, insertion position, depth, priority, regex, budgets. MARE adopts it almost
verbatim (credit where due — this part of the ecosystem got it mostly right) and tightens the
edges:

```jsonc
"lore": {
  "scan_depth_default": 4,
  "token_budget": 1024,
  "recursion": { "enabled": true, "max_depth": 3 },     // declared, bounded (ST's recursion is infamous)
  "entries": [
    {
      "id": "le_house",
      "name": "The house",                               // memo, not injected
      "content": "A narrow two-story near the university; {char.given_name}'s room is the attic.",
      "keys": ["house", "home", "attic"],
      "secondary_keys": ["night"],
      "secondary_logic": "and_any",                      // and_any|and_all|not_any|not_all (TBM's enum)
      "match": { "case_sensitive": false, "whole_words": true, "regex": false },
      "activation": { "constant": false, "enabled": true, "probability": 100 },
      "placement": { "position": "after_character", "depth": 4, "role": "system" },
      "priority": 100,
      "vectorized": true                                  // eligible for embedding retrieval, not just keyword
    }
  ]
}
```

Improvements over the incumbent:

- **Bounded recursion.** SillyTavern's recursive lore activation is a well-known way to blow
  your context budget; here `recursion.max_depth` is **required if recursion is enabled**.
- **`vectorized` flag** bridges keyword lore and **embedding retrieval** — which is exactly
  what TBM's `rag` slice + pgvector already do. A MARE lore entry can be keyword-triggered,
  embedding-retrieved, or both, declared per entry.
- **Placement is a sub-object**, mapping 1:1 to TBM's `InsertionPosition` / `depth` /
  `MessageRole`. No new concepts to learn — this is the model you already have, serialized
  cleanly.

---

## Part D — The prompt-assembly contract

The spec defines the **order and roles** a conformant runtime uses, so the same card produces
the same prompt shape everywhere (a client may re-skin wording, but not silently reorder).
Assembly, top to bottom:

```
1. system            ← prompt.system (rendered)  OR  host default template
2. persona block     ← the actor_kind=persona card (user)               role=system
3. character block   ← profile.description + personality + appearance    role=system
4. scenario          ← scene.scenario (rendered)                          role=system
5. lore (before_examples / before_character / after_character)  ← activated entries by placement
6. dialogue_examples ← rendered as real role-tagged turns                 role=user/assistant
7. chat history      ← the actual conversation
8. lore (at_depth)   ← entries injected N turns from the end
9. post_history      ← prompt.post_history (rendered)                     role=system
```

- Every card field lands at a **defined** position and **role**. TBM's `prompt_builder`
  already assembles Description/Personality/Scenario system blocks and splices lore by
  position — MARE just makes that order part of the *spec* instead of one app's convention.
- **`post_history` is last and neutral** (not blessed as a "jailbreak"), matching its purpose
  as final steering.
- Because everything is typed, the builder never guesses. No `\{{0,2}` regex, no `<START>`
  splitting, no smart-quote folding at read time — the card is *already* clean.

---

## Part E — Determinism & safety at runtime

- **Deterministic rendering.** Given `(card, persona, host_vars, seed)`, `{pick ... random}`
  is seeded so a session is reproducible. No hidden nondeterminism in prompt construction.
- **No card-driven code.** The dialect can't call out, fetch, or recurse unbounded. A card is
  data the host *interprets*, never code the host *runs*.
- **Injection posture.** `post_history` and lore `content` are clearly *card-authored* text;
  a host that wants to sandbox untrusted cards knows exactly which spans came from the card
  versus the user versus the system, because they're separate typed fields with roles — not a
  concatenated string.

Next: how we get from a pile of legacy TavernCard PNGs to this, and how it lands on the TBM
backend — [`04-migration-and-mapping.md`](04-migration-and-mapping.md).
