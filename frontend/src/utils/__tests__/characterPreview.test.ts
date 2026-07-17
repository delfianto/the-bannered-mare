import { describe, it, expect } from "vitest";
import { previewText } from "../characterPreview";

describe("previewText", () => {
  it("prefers description over creator_notes", () => {
    expect(
      previewText({ name: "Alice", description: "A brave knight.", creator_notes: "notes" }),
    ).toBe("A brave knight.");
  });

  it("falls back to creator_notes when description is empty", () => {
    expect(
      previewText({ name: "Alice", description: null, creator_notes: "Author's notes." }),
    ).toBe("Author's notes.");
  });

  it("returns empty string when both are empty", () => {
    expect(previewText({ name: "Alice", description: null, creator_notes: null })).toBe("");
  });

  it("resolves {{char}} to the character's name and drops {{user}}", () => {
    expect(
      previewText({
        name: "Kalina",
        description: "{{char}} is stuck in a hospital, waiting for {{user}} to visit.",
        creator_notes: null,
      }),
    ).toBe("Kalina is stuck in a hospital, waiting for to visit.");
  });

  // Real card text (kalina.png's description) -- a bracket-attribute-list format,
  // not markdown, but it's how the description-first fallback was verified not
  // to just swap one kind of noise (markdown in creator_notes) for another
  // (unresolved macros) when a real problem card was checked against this fix.
  it("cleans real card description text (kalina.png)", () => {
    const result = previewText({
      name: "Kalina",
      description: "[{{char}} name(Kalina Potocka);\n{{char}} sex(Female);\n{{char}} age(19);",
      creator_notes: null,
    });
    expect(result).not.toContain("{{char}}");
    expect(result).toContain("Kalina name(Kalina Potocka)");
  });

  // Real card text (kalina.png's creator_notes) -- the motivating case: markdown
  // headers/bold and an embedded image link must not leak into the teaser.
  it("strips markdown noise from real card creator_notes (kalina.png)", () => {
    const raw = [
      "**Description:**",
      "*****Meet Kalina — a track-and-field prodigy.*****",
      "",
      "**Scenarios:**",
      '**Scenario 1 (Default) — "A rare visit"**',
      "![](https://i.ibb.co/PsrjsRMG/Kalina-Chibi2.png)",
    ].join("\n");

    const result = previewText({ name: "Kalina", description: null, creator_notes: raw });

    expect(result).not.toContain("**");
    expect(result).not.toContain("![");
    expect(result).not.toContain("https://i.ibb.co");
    expect(result).toContain("Meet Kalina");
  });
});
