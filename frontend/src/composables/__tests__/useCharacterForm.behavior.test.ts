import { describe, expect, it, vi, afterEach } from "vite-plus/test";
import { http, HttpResponse } from "msw";
import { useCharacterForm } from "@/composables/useCharacterForm";
import { characters } from "@/mocks/data/characters";
import { server } from "@/mocks/server";

afterEach(() => vi.restoreAllMocks());

describe("character creator state", () => {
  it("keeps tags, dialogues and lore independent between new forms", () => {
    const a = useCharacterForm(),
      b = useCharacterForm();
    a.addTag("Dragon");
    a.addDialogue();
    a.addLorebook();
    expect(b.data.tags).toEqual([]);
    expect(b.data.exampleDialogues).toEqual([]);
    expect(b.data.lorebook).toEqual([]);
  });

  it("caps tags at ten, ignores duplicates, and removes a tag", () => {
    const form = useCharacterForm({ tags: [] });
    for (let i = 0; i < 12; i++) form.addTag(`tag-${i}`);
    form.addTag("tag-0");
    expect(form.data.tags).toHaveLength(10);
    form.removeTag("tag-0");
    expect(form.data.tags).not.toContain("tag-0");
  });

  it("dialogue IDs remain unique for rapid edits in the same millisecond", () => {
    vi.spyOn(Date, "now").mockReturnValue(100);
    const form = useCharacterForm({ exampleDialogues: [] });
    form.addDialogue();
    form.addDialogue();
    const [a, b] = form.data.exampleDialogues;
    expect(a.id).not.toBe(b.id);
    form.updateDialogue(a.id, "characterReply", "First reply");
    expect(b.characterReply).toBe("");
    form.removeDialogue(a.id);
    expect(form.data.exampleDialogues.map((d) => d.id)).toEqual([b.id]);
  });

  it("lore IDs remain unique and editing one entry preserves the other", () => {
    vi.spyOn(Date, "now").mockReturnValue(100);
    const form = useCharacterForm({ lorebook: [] });
    form.addLorebook();
    form.addLorebook();
    const [a, b] = form.data.lorebook;
    expect(a.id).not.toBe(b.id);
    form.updateLorebook(a.id, { content: "Dragon lore", keywords: ["dragon"] });
    expect(b.content).toBe("");
    form.removeLorebook(a.id);
    expect(form.data.lorebook.map((e) => e.id)).toEqual([b.id]);
  });

  it("completion tracks nonblank fields and dialogue/lore sections", () => {
    const form = useCharacterForm();
    expect(form.completeness.value).toEqual({ filled: 0, total: 12 });
    form.updateField("name", "  ");
    expect(form.completeness.value.filled).toBe(0);
    form.updateField("name", "Lydia");
    form.addDialogue();
    form.addLorebook();
    expect(form.completeness.value.filled).toBe(3);
  });
});

describe("character persistence over HTTP", () => {
  it("failed saves retain the draft and reset the busy flag", async () => {
    server.use(
      http.post("/api/characters", () =>
        HttpResponse.json({ detail: "Invalid portrait" }, { status: 422 }),
      ),
    );
    const form = useCharacterForm({ name: "Draft", tags: ["warrior"] });
    const pending = form.saveCharacter();
    expect(form.saving.value).toBe(true);
    await expect(pending).rejects.toThrow("Invalid portrait");
    expect(form.saving.value).toBe(false);
    expect(form.data.name).toBe("Draft");
    expect(form.data.tags).toEqual(["warrior"]);
    expect(form.id.value).toBeUndefined();
  });

  it("a create followed by another save uses PUT against the persisted ID", async () => {
    const writes: string[] = [];
    server.use(
      http.post("/api/characters", () => {
        writes.push("POST");
        return HttpResponse.json({ ...characters[0], id: "saved" });
      }),
      http.put("/api/characters/saved", () => {
        writes.push("PUT");
        return HttpResponse.json({ ...characters[0], id: "saved" });
      }),
      http.get("/api/lorebooks", () => HttpResponse.json({ items: [] })),
    );
    const form = useCharacterForm({ name: "Saved" });
    await form.saveCharacter();
    await form.saveCharacter();
    expect(writes).toEqual(["POST", "PUT"]);
    expect(form.id.value).toBe("saved");
  });

  it("loads custom gender, preferred portrait and server lore into the editor", async () => {
    server.use(
      http.get("/api/characters/c", () =>
        HttpResponse.json({
          ...characters[0],
          id: "c",
          gender: "others",
          custom_gender: "Spirit",
          avatar_large: "/large.webp",
          avatar: "/original.png",
        }),
      ),
      http.get("/api/lorebooks", () => HttpResponse.json({ items: [{ id: "book" }] })),
      http.get("/api/lorebooks/book", () =>
        HttpResponse.json({
          entries: [{ id: "entry", keys: ["dragon"], content: "Lore", enabled: false }],
        }),
      ),
    );
    const form = useCharacterForm();
    await form.loadFromApi("c");
    expect(form.data.gender).toBe("Spirit");
    expect(form.data.avatarUrl).toBe("/large.webp");
    expect(form.data.avatarFile).toBeNull();
    expect(form.loading.value).toBe(false);
    expect(form.data.lorebook).toEqual([
      { id: "entry", keywords: ["dragon"], content: "Lore", enabled: false },
    ]);
  });

  it("load and delete failures release their busy flags", async () => {
    server.use(
      http.get("/api/characters/missing", () => new HttpResponse(null, { status: 404 })),
      http.delete("/api/characters/missing", () =>
        HttpResponse.json({ detail: "Character is in use" }, { status: 409 }),
      ),
    );
    const form = useCharacterForm();
    await expect(form.loadFromApi("missing")).rejects.toThrow();
    expect(form.loading.value).toBe(false);
    await expect(form.deleteCharacter("missing")).rejects.toThrow();
    expect(form.deleting.value).toBe(false);
  });

  it.each(["create-book", "create-entry", "update-entry", "delete-entry"])(
    "reports a failed lore %s instead of showing a successful save",
    async (action) => {
      server.use(
        http.post("/api/characters", () => HttpResponse.json({ ...characters[0], id: "saved" })),
        http.get("/api/lorebooks", () =>
          HttpResponse.json({ items: action === "create-book" ? [] : [{ id: "book" }] }),
        ),
        http.get("/api/lorebooks/book", () =>
          HttpResponse.json({
            entries:
              action === "update-entry" || action === "delete-entry"
                ? [{ id: "existing", keys: ["dragon"], content: "Old", enabled: true }]
                : [],
          }),
        ),
        http.post("/api/lorebooks", () =>
          HttpResponse.json({ detail: "Lore write rejected" }, { status: 422 }),
        ),
        http.all("/api/lorebooks/book/entries/*", () =>
          HttpResponse.json({ detail: "Lore write rejected" }, { status: 422 }),
        ),
        http.post("/api/lorebooks/book/entries", () =>
          HttpResponse.json({ detail: "Lore write rejected" }, { status: 422 }),
        ),
      );
      const form = useCharacterForm({
        name: "Draft",
        lorebook:
          action === "delete-entry"
            ? []
            : [
                {
                  id: action === "update-entry" ? "existing" : "lore-new",
                  keywords: ["dragon"],
                  content: "Draft lore",
                  enabled: true,
                },
              ],
      });
      await expect(form.saveCharacter()).rejects.toThrow("Lore write rejected");
      expect(form.saving.value).toBe(false);
      expect(form.id.value).toBe("saved");
      expect(form.data.name).toBe("Draft");
    },
  );
});
