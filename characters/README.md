# Character Cards (test data)

Sample character cards used as **test / seed fixtures** for The Bannered Mare — they exercise
the card importer, the avatar/thumbnail pipeline, and the chat + RAG flows. They are **not**
part of the application code; they live at the repo root because they belong to no single half.

A character card is a PNG image with the character definition embedded as base64 JSON in a
`tEXt` chunk (`chara` for the V2 spec, `ccv3` for V3). See
[Characters, Personas & Assets](../docs/architecture/backend/characters-and-personas.md) for how
the backend parses them.

## Sources & credits

Every card except `daro_soraya.png` was obtained from **[Character Tavern](https://character-tavern.com)**
and remains the work of its original creator (credited below). They are included here purely as
import fixtures; all rights stay with their authors. A couple were themselves mirrored onto
Character Tavern from other communities (noted in the table).

**`daro_soraya.png` is an original creation for this project** — authored with Claude Opus to
test deep, lore-accurate roleplay in the *Elder Scrolls* universe (Daro-Soraya, a Khajiit
spy/dancer).

## Cards

| File | Character | Creator | Spec | Source |
|------|-----------|---------|------|--------|
| `daro_soraya.png` | Daro-Soraya | this project | V2 | **Original** — Claude Opus, Elder Scrolls deep-RP test |
| `bestfriend_roommate.png` | Bestfriend / roommate | izuki0009 | V3 | Character Tavern |
| `emily.png` | Emily | zaurabh | V3 | Character Tavern |
| `homeroom_teacher.png` | Your Young Homeroom Teacher | yernox | V3 | Character Tavern (transported from Janitor AI) |
| `kalina.png` | Kalina | paradigme | V3 | Character Tavern |
| `mina.png` | Mina | paradigme | V3 | Character Tavern |
| `mina_stepsister.png` | Mina (bratty-stepsister scenario) | logosy | V3 | Character Tavern (originally Janitor AI, @Iancaesrr) |
| `shy_cousin.png` | Shy Cousin | zaurabh | V3 | Character Tavern |

Files are named after the embedded character name (snake_case); the two distinct "Mina" cards
are disambiguated by scenario.
