import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { client } from "@/api/client";
import type { components } from "@/api/schema";

type CharacterResponse = components["schemas"]["CharacterResponse"];

async function getForm(initial?: any) {
  const { useCharacterForm } = await import("../useCharacterForm");
  return useCharacterForm(initial);
}

describe("useCharacterForm - species and age fields", () => {
  // FE-H5: this suite swaps `global.fetch` / `client.GET` for a couple of cases;
  // capture the pristine references at collection time and restore after each
  // test so nothing leaks into later suites (no unrestored global patching).
  const realFetch = globalThis.fetch;
  const realGet = client.GET;
  afterEach(() => {
    globalThis.fetch = realFetch;
    client.GET = realGet;
  });

  it("should initialize with default species and age values", async () => {
    const { data } = await getForm();
    expect(data.species).toBe("");
    expect(data.age).toBe("");
  });

  it("should append species and age to FormData on save", async () => {
    const form = await getForm();

    form.updateField("name", "Test Name");
    form.updateField("species", "Elf");
    form.updateField("age", "150");

    const emptyLorebooks = {
      items: [],
      meta: { limit: 0, has_more: false, cursor: null, total: 0, page: 1 },
    };

    // openapi-fetch calls fetch with a Request; the raw multipart save calls it
    // with (urlString, { body }). Discriminate by URL so the lorebook-sync GET
    // (added after the character save) returns an empty page instead of choking.
    const mockFetch = (input: any, options?: any) => {
      const url = typeof input === "string" ? input : input.url;
      if (url.includes("/api/lorebooks")) {
        return Promise.resolve(
          new Response(JSON.stringify(emptyLorebooks), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      const fd = options.body as FormData;
      expect(fd.get("name")).toBe("Test Name");
      expect(fd.get("species")).toBe("Elf");
      expect(fd.get("age")).toBe("150");
      return Promise.resolve(
        new Response(JSON.stringify({ id: "123", name: "Test Name", species: "Elf", age: "150" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    };

    // @ts-ignore
    global.fetch = mockFetch;

    await form.saveCharacter();
  });

  it("should map species and age back from CharacterResponse", async () => {
    const form = await getForm();

    const mockResponse: CharacterResponse = {
      id: "ej2Ymmz9-5lO",
      name: "Your Young Homeroom Teacher",
      description: "Strict teacher",
      personality: "Strict",
      first_message: "Hello class",
      tags: ["Teacher"],
      avatar: "/api/characters/ej2Ymmz9-5lO/avatar",
      avatar_large: "/api/characters/ej2Ymmz9-5lO/avatar_large",
      avatar_thumbnail: "/api/characters/ej2Ymmz9-5lO/avatar_thumbnail",
      creator_notes: "Janitor import",
      system_prompt: "Strict prompt",
      species: "Human",
      age: "24",
      gender: "female",
      custom_gender: null,
      creator: "yernox",
      character_version: "main",
      version: 1,
      created_at: "2026-07-14T00:00:00Z",
      updated_at: "2026-07-14T00:00:00Z",
    };

    const { client } = await import("@/api/client");
    // loadFromApi fetches the character, then its lorebooks; return an empty
    // lorebook page so only the character mapping is under test here.
    client.GET = ((path: string) =>
      path === "/api/lorebooks"
        ? Promise.resolve({
            data: {
              items: [],
              meta: { limit: 0, has_more: false, cursor: null, total: 0, page: 1 },
            },
            error: null,
          })
        : Promise.resolve({ data: mockResponse, error: null })) as any;

    await form.loadFromApi("ej2Ymmz9-5lO");

    expect(form.data.species).toBe("Human");
    expect(form.data.age).toBe("24");
    expect(form.data.creatorNotes).toBe("Janitor import");
    expect(form.data.systemPrompt).toBe("Strict prompt");
  });
});

// ---------------------------------------------------------------------------
// FE-M9 — the gnarly paths the original suite skipped: gender→custom_gender
// normalization, the example_dialogues regex round-trip, and the lorebook
// entry-diff in saveCharacter. buildFormData/mapResponseToForm aren't exported,
// so each case drives the public saveCharacter/loadFromApi and mocks the
// fetch/client boundary.
//
// `client` (the openapi-fetch singleton) is captured pristine at module-load
// time and reinstated in beforeEach here as defense-in-depth. The "species and
// age" suite above now restores its own `client.GET`/`fetch` swaps (FE-H5), so
// this is belt-and-suspenders — it keeps these suites order-independent even if
// a future test forgets to clean up.
// ---------------------------------------------------------------------------

const PRISTINE_CLIENT = {
  GET: client.GET,
  POST: client.POST,
  PUT: client.PUT,
  DELETE: client.DELETE,
} as const;

function restoreClient() {
  Object.assign(client, PRISTINE_CLIENT);
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const EMPTY_LOREBOOK_PAGE = {
  items: [],
  meta: { limit: 0, has_more: false, cursor: null, total: 0, page: 1 },
};

function reqInfo(input: unknown, init: RequestInit | undefined): { url: string; method: string } {
  const req = input instanceof Request ? input : null;
  const url = req ? req.url : String(input);
  const method = (init?.method ?? req?.method ?? "GET").toUpperCase();
  return { url, method };
}

// openapi-fetch (0.17) calls fetch(new Request(url, { body: <json string> })) —
// one Request arg, no init; the raw multipartFetch calls fetch(urlString, { body:
// FormData }). Read a JSON body out of whichever shape a request used (a FormData
// body reads back as undefined, which is fine — those assertions read the
// FormData directly).
async function readJsonBody(input: unknown, init: RequestInit | undefined): Promise<any> {
  if (init && typeof init.body === "string") {
    try {
      return JSON.parse(init.body);
    } catch {
      return undefined;
    }
  }
  if (input instanceof Request) {
    return await input
      .clone()
      .json()
      .catch(() => undefined);
  }
  return undefined;
}

describe("useCharacterForm - gender → custom_gender normalization (buildFormData)", () => {
  let realFetch: typeof globalThis.fetch;
  let captured: FormData | undefined;

  beforeEach(() => {
    realFetch = globalThis.fetch;
    restoreClient();
    captured = undefined;
    // Capture the multipart character save's FormData; stub the lorebook-sync GET
    // empty so saveCharacter's diff loop stays a no-op for these cases.
    globalThis.fetch = vi.fn(async (input: unknown, init?: RequestInit) => {
      const { url } = reqInfo(input, init);
      if (url.includes("/api/lorebooks")) return jsonResponse(EMPTY_LOREBOOK_PAGE);
      captured = init!.body as FormData;
      return jsonResponse({ id: "char-gender", name: "Gender Test" });
    }) as typeof globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = realFetch;
    restoreClient();
    vi.restoreAllMocks();
  });

  async function formDataForGender(gender: string): Promise<FormData> {
    const form = await getForm();
    form.updateField("name", "Gender Test");
    form.updateField("gender", gender);
    await form.saveCharacter();
    return captured!;
  }

  it("lowercases a standard gender and appends no custom_gender", async () => {
    const fd = await formDataForGender("Male");
    expect(fd.get("gender")).toBe("male");
    expect(fd.get("custom_gender")).toBeNull();
  });

  it("keeps the hyphenated 'Non-binary' option as canonical 'non-binary'", async () => {
    const fd = await formDataForGender("Non-binary");
    expect(fd.get("gender")).toBe("non-binary");
    expect(fd.get("custom_gender")).toBeNull();
  });

  it("routes a free-text gender to gender=others + custom_gender=<verbatim>", async () => {
    const fd = await formDataForGender("Genderfluid");
    expect(fd.get("gender")).toBe("others");
    expect(fd.get("custom_gender")).toBe("Genderfluid");
  });

  it("omits gender entirely when the field is blank", async () => {
    const fd = await formDataForGender("");
    expect(fd.get("gender")).toBeNull();
    expect(fd.get("custom_gender")).toBeNull();
  });
});

describe("useCharacterForm - example_dialogues regex round-trip", () => {
  let realFetch: typeof globalThis.fetch;
  let captured: FormData | undefined;
  let loadResponse: Partial<CharacterResponse>;

  beforeEach(() => {
    realFetch = globalThis.fetch;
    restoreClient();
    captured = undefined;
    loadResponse = {};
    globalThis.fetch = vi.fn(async (input: unknown, init?: RequestInit) => {
      const { url, method } = reqInfo(input, init);
      if (url.includes("/api/lorebooks")) return jsonResponse(EMPTY_LOREBOOK_PAGE);
      // loadFromApi's character GET → the fixture under test; any other verb is
      // the multipart save, whose serialized FormData we capture.
      if (method === "GET" && url.includes("/api/characters")) return jsonResponse(loadResponse);
      captured = init!.body as FormData;
      return jsonResponse({ id: "dlg-1", name: "Dialogue Test" });
    }) as typeof globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = realFetch;
    restoreClient();
    vi.restoreAllMocks();
  });

  function charWithDialogues(dialogues: string[]): Partial<CharacterResponse> {
    return { id: "dlg-1", name: "Dialogue Test", example_dialogues: dialogues };
  }

  function serializedDialogues(): string[] {
    return JSON.parse(captured!.get("example_dialogues") as string);
  }

  it("parses an explicit User:/Character: exchange into the two fields", async () => {
    loadResponse = charWithDialogues([
      "<START>\nUser: Hail, friend\nCharacter: Well met, traveller",
    ]);
    const form = await getForm();
    await form.loadFromApi("dlg-1");

    expect(form.data.exampleDialogues).toHaveLength(1);
    expect(form.data.exampleDialogues[0].userMessage).toBe("Hail, friend");
    expect(form.data.exampleDialogues[0].characterReply).toBe("Well met, traveller");
  });

  it("preserves a freeform (marker-less) example verbatim in the reply field", async () => {
    loadResponse = charWithDialogues(["She studies you from across the smoky tavern."]);
    const form = await getForm();
    await form.loadFromApi("dlg-1");

    expect(form.data.exampleDialogues[0].userMessage).toBe("");
    expect(form.data.exampleDialogues[0].characterReply).toBe(
      "She studies you from across the smoky tavern.",
    );
  });

  it("strips a bare <START> marker from a freeform example", async () => {
    loadResponse = charWithDialogues(["<START>\nAn ancient tale unfolds by the hearth."]);
    const form = await getForm();
    await form.loadFromApi("dlg-1");

    expect(form.data.exampleDialogues[0].userMessage).toBe("");
    expect(form.data.exampleDialogues[0].characterReply).toBe(
      "An ancient tale unfolds by the hearth.",
    );
  });

  it("handles a User:-only exchange (no Character marker) → empty reply", async () => {
    loadResponse = charWithDialogues(["User: Just the user speaks"]);
    const form = await getForm();
    await form.loadFromApi("dlg-1");

    expect(form.data.exampleDialogues[0].userMessage).toBe("Just the user speaks");
    expect(form.data.exampleDialogues[0].characterReply).toBe("");
  });

  it("serializes each dialogue pair as a <START>/User/Character block", async () => {
    const form = await getForm();
    form.updateField("name", "Dialogue Test");
    form.addDialogue();
    const dlgId = form.data.exampleDialogues[0].id;
    form.updateDialogue(dlgId, "userMessage", "What news?");
    form.updateDialogue(dlgId, "characterReply", "War in the east.");

    await form.saveCharacter();

    expect(serializedDialogues()).toEqual([
      "<START>\nUser: What news?\nCharacter: War in the east.",
    ]);
  });

  it("round-trips a well-formed exchange parse→serialize without drift", async () => {
    loadResponse = charWithDialogues(["<START>\nUser: Hail\nCharacter: Well met"]);
    const form = await getForm();
    await form.loadFromApi("dlg-1");
    await form.saveCharacter();

    expect(serializedDialogues()).toEqual(["<START>\nUser: Hail\nCharacter: Well met"]);
  });

  it("round-trips a freeform example into the Character slot (content survives)", async () => {
    loadResponse = charWithDialogues(["A lone figure warms by the fire."]);
    const form = await getForm();
    await form.loadFromApi("dlg-1");
    await form.saveCharacter();

    // Freeform text has no User half, so it re-emits under Character — lossy in
    // structure but the content is never dropped.
    expect(serializedDialogues()).toEqual([
      "<START>\nUser: \nCharacter: A lone figure warms by the fire.",
    ]);
  });
});

describe("useCharacterForm - lorebook entry diff (saveCharacter)", () => {
  let realFetch: typeof globalThis.fetch;
  let calls: { method: string; url: string; body: any }[];

  beforeEach(() => {
    realFetch = globalThis.fetch;
    restoreClient();
    calls = [];
  });

  afterEach(() => {
    globalThis.fetch = realFetch;
    restoreClient();
    vi.restoreAllMocks();
  });

  // Record every request (method/url/json-body) and delegate the response to
  // `route`. The lorebook-sync calls all flow through the typed client, so
  // routing on url + verb exercises the real delete/update/create branches.
  function install(route: (url: string, method: string) => Response) {
    globalThis.fetch = vi.fn(async (input: unknown, init?: RequestInit) => {
      const { url, method } = reqInfo(input, init);
      const body = await readJsonBody(input, init);
      calls.push({ method, url, body });
      return route(url, method);
    }) as typeof globalThis.fetch;
  }

  it("deletes removed entries, updates kept ones, and creates new ones against the existing book", async () => {
    const existingBook = {
      id: "book-1",
      entries: [
        { id: "entry-keep", name: "Dragon", content: "old", keys: ["Dragon"], enabled: true },
        { id: "entry-drop", name: "Ghost", content: "old", keys: ["Ghost"], enabled: true },
      ],
    };
    install((url, method) => {
      if (url.includes("/api/characters")) return jsonResponse({ id: "char-1", name: "Lore Test" });
      if (url.includes("/entries"))
        return jsonResponse({ id: "srv-entry" }, method === "POST" ? 201 : 200);
      if (/\/api\/lorebooks\/[^/?]+$/.test(url)) return jsonResponse(existingBook);
      return jsonResponse({
        items: [{ id: "book-1", name: "Book" }],
        meta: { limit: 20, has_more: false, cursor: null, total: 1, page: 1 },
      });
    });

    const form = await getForm();
    form.updateField("name", "Lore Test");
    form.updateField("lorebook", [
      { id: "entry-keep", keywords: ["Dragon"], content: "updated lore", enabled: true },
      { id: "lore-new-1", keywords: ["Sword"], content: "new lore", enabled: false },
    ]);

    await form.saveCharacter();

    // DELETE — the existing entry no longer present in the form is removed.
    const deletes = calls.filter((c) => c.method === "DELETE");
    expect(deletes).toHaveLength(1);
    expect(deletes[0].url).toContain("/api/lorebooks/book-1/entries/entry-drop");

    // UPDATE — the kept entry is PUT with the fresh content; no NEW_ENTRY_DEFAULTS.
    const puts = calls.filter((c) => c.method === "PUT" && c.url.includes("/entries/"));
    expect(puts).toHaveLength(1);
    expect(puts[0].url).toContain("/entries/entry-keep");
    expect(puts[0].body).toMatchObject({
      name: "Dragon",
      content: "updated lore",
      keys: ["Dragon"],
      enabled: true,
    });
    expect(puts[0].body.position).toBeUndefined();

    // CREATE — the new (client-id'd) entry is POSTed with NEW_ENTRY_DEFAULTS merged.
    const posts = calls.filter((c) => c.method === "POST" && c.url.includes("/entries"));
    expect(posts).toHaveLength(1);
    expect(posts[0].url).toMatch(/\/api\/lorebooks\/book-1\/entries$/);
    expect(posts[0].body).toMatchObject({
      name: "Sword",
      content: "new lore",
      keys: ["Sword"],
      enabled: false,
      position: "after_character",
      role: "system",
      secondary_logic: "and_any",
    });
  });

  it("creates a fresh lorebook when none exists yet, then creates its entries", async () => {
    install((url, method) => {
      if (url.includes("/api/characters")) return jsonResponse({ id: "char-2", name: "New Lore" });
      if (url.includes("/entries")) return jsonResponse({ id: "srv-entry" }, 201);
      if (/\/api\/lorebooks\/[^/?]+$/.test(url) && method === "GET")
        return jsonResponse({ id: "book-new", entries: [] });
      if (url.includes("/api/lorebooks") && method === "POST")
        return jsonResponse({ id: "book-new", name: "New Lore Lorebook" }, 201);
      return jsonResponse({
        items: [],
        meta: { limit: 20, has_more: false, cursor: null, total: 0, page: 1 },
      });
    });

    const form = await getForm();
    form.updateField("name", "New Lore");
    form.updateField("lorebook", [
      { id: "lore-x", keywords: ["Relic"], content: "a relic", enabled: true },
    ]);

    await form.saveCharacter();

    const createBook = calls.find((c) => c.method === "POST" && c.url.endsWith("/api/lorebooks"));
    expect(createBook).toBeDefined();
    expect(createBook!.body).toMatchObject({
      name: "New Lore Lorebook",
      character_id: "char-2",
      is_global: false,
    });

    const entryPosts = calls.filter((c) => c.method === "POST" && c.url.includes("/entries"));
    expect(entryPosts).toHaveLength(1);
    expect(entryPosts[0].url).toMatch(/\/api\/lorebooks\/book-new\/entries$/);
    expect(entryPosts[0].body).toMatchObject({
      name: "Relic",
      content: "a relic",
      keys: ["Relic"],
    });
  });
});
