process.env.VITE_API_URL = "http://localhost:8000";

import { describe, it, expect } from "bun:test";
import type { components } from "@/api/schema";

type CharacterResponse = components["schemas"]["CharacterResponse"];

async function getForm(initial?: any) {
  const { useCharacterForm } = await import("../useCharacterForm");
  return useCharacterForm(initial);
}

describe("useCharacterForm - species and age fields", () => {
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
            data: { items: [], meta: { limit: 0, has_more: false, cursor: null, total: 0, page: 1 } },
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
