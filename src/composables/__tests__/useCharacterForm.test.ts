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

    const mockFetch = (url: string, options: any) => {
      const fd = options.body as FormData;
      expect(fd.get("name")).toBe("Test Name");
      expect(fd.get("species")).toBe("Elf");
      expect(fd.get("age")).toBe("150");
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            id: "123",
            name: "Test Name",
            species: "Elf",
            age: "150",
          }),
      });
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
    };

    const { client } = await import("@/api/client");
    client.GET = () => Promise.resolve({ data: mockResponse, error: null }) as any;

    await form.loadFromApi("ej2Ymmz9-5lO");

    expect(form.data.species).toBe("Human");
    expect(form.data.age).toBe("24");
    expect(form.data.creatorNotes).toBe("Janitor import");
    expect(form.data.systemPrompt).toBe("Strict prompt");
  });
});
