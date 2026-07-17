import type { Character } from "@/types/discover";

const MARKDOWN_LINK_RE = /!?\[[^\]]*\]\([^)]*\)/g;
const MARKDOWN_HEADING_RE = /^#{1,6}\s+/gm;
const MARKDOWN_BOLD_RE = /\*\*/g;
const MACRO_RE = /\{\{\s*(\w+)\s*\}\}/g;

/**
 * A one-line teaser for the Discover grid/list cards. Imported cards routinely
 * write description/creator_notes as a markdown-formatted "character sheet"
 * (## headers, **bold**, embedded image links) or leave {{char}}/{{user}}
 * macros unresolved (macro substitution only happens backend-side, at prompt
 * time) — none of that reads well truncated to a few words in a card preview.
 * Display-only: the full text is untouched everywhere else (detail view, edit
 * form), and description is preferred over creator_notes since the latter is
 * author commentary, not a description of the character.
 */
export function previewText(
  character: Pick<Character, "name" | "description" | "creator_notes">,
): string {
  const raw = character.description || character.creator_notes || "";
  if (!raw) return "";

  return raw
    .replace(MACRO_RE, (_match, name: string) =>
      name.toLowerCase() === "char" ? character.name : "",
    )
    .replace(MARKDOWN_LINK_RE, "")
    .replace(MARKDOWN_HEADING_RE, "")
    .replace(MARKDOWN_BOLD_RE, "")
    .replace(/\s+/g, " ")
    .trim();
}
