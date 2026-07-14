import { reactive, computed, ref } from "vue";
import type { CharacterData, LorebookEntry } from "@/types/creator";
import { INITIAL_CHARACTER } from "@/types/creator";
import { client, extractApiError, multipartFetch } from "@/api/client";
import type { components } from "@/api/schema";

type CharacterResponse = components["schemas"]["CharacterResponse"];

// openapi-typescript types LoreEntryCreate's defaulted fields (secondary_logic,
// position, role, etc.) as required even though the backend supplies them — only
// name + content are truly required. Send the schema defaults so a new-entry body
// type-checks without an `as any`.
const NEW_ENTRY_DEFAULTS = {
  secondary_logic: "and_any",
  case_sensitive: false,
  match_whole_words: false,
  use_regex: false,
  constant: false,
  position: "after_character",
  depth: 4,
  role: "system",
  priority: 100,
  ignore_budget: false,
  order: 0,
} as const satisfies Partial<components["schemas"]["LoreEntryCreate"]>;

export function useCharacterForm(initial?: Partial<CharacterData>) {
  const data = reactive<CharacterData>({ ...INITIAL_CHARACTER, ...initial });
  const id = ref<string | undefined>(initial?.id);
  const saving = ref(false);
  const deleting = ref(false);
  const loading = ref(false);

  function updateField<K extends keyof CharacterData>(field: K, value: CharacterData[K]) {
    (data as any)[field] = value;
  }

  function addTag(tag: string) {
    if (data.tags.includes(tag) || data.tags.length >= 10) return;
    data.tags.push(tag);
  }

  function removeTag(tag: string) {
    data.tags = data.tags.filter((t) => t !== tag);
  }

  function addDialogue() {
    data.exampleDialogues.push({
      id: `dlg-${Date.now()}`,
      userMessage: "",
      characterReply: "",
    });
  }

  function updateDialogue(id: string, field: "userMessage" | "characterReply", value: string) {
    const d = data.exampleDialogues.find((p) => p.id === id);
    if (d) d[field] = value;
  }

  function removeDialogue(id: string) {
    data.exampleDialogues = data.exampleDialogues.filter((d) => d.id !== id);
  }

  function addLorebook() {
    data.lorebook.push({
      id: `lore-${Date.now()}`,
      keywords: [],
      content: "",
      enabled: true,
    });
  }

  function updateLorebook(id: string, updates: Partial<LorebookEntry>) {
    const e = data.lorebook.find((l) => l.id === id);
    if (e) Object.assign(e, updates);
  }

  function removeLorebook(id: string) {
    data.lorebook = data.lorebook.filter((e) => e.id !== id);
  }

  function loadCharacter(char: CharacterData) {
    Object.assign(data, char);
  }

  /** Build a FormData object from the reactive form state. */
  function buildFormData(): FormData {
    const fd = new FormData();
    fd.append("name", data.name);

    if (data.description) fd.append("description", data.description);
    if (data.personality) fd.append("personality", data.personality);
    if (data.greeting) fd.append("first_message", data.greeting);
    if (data.scenario) fd.append("scenario", data.scenario);
    if (data.creatorNotes) fd.append("creator_notes", data.creatorNotes);
    if (data.systemPrompt) fd.append("system_prompt", data.systemPrompt);
    if (data.species) fd.append("species", data.species);
    if (data.age) fd.append("age", data.age);

    // Always send tags and example_dialogues (even when empty) so that clearing
    // them on edit actually persists — the backend only updates a field when it
    // receives one, so omitting the field left the old value in place.
    fd.append("tags", JSON.stringify(data.tags));

    const dialogueStrings = data.exampleDialogues.map(
      (d) => `<START>\nUser: ${d.userMessage}\nCharacter: ${d.characterReply}`,
    );
    fd.append("example_dialogues", JSON.stringify(dialogueStrings));

    if (data.gender) {
      const genderLower = data.gender.toLowerCase();
      const validGenders = ["male", "female", "non-binary", "others"];
      if (validGenders.includes(genderLower)) {
        fd.append("gender", genderLower);
      } else {
        fd.append("gender", "others");
        fd.append("custom_gender", data.gender);
      }
    }

    if (data.avatarFile) {
      fd.append("avatar", data.avatarFile);
    }

    fd.append("version", "1");

    return fd;
  }

  /** Map an API CharacterResponse back to the reactive form data. */
  function mapResponseToForm(res: CharacterResponse) {
    data.id = res.id;
    id.value = res.id;
    data.name = res.name;
    data.description = res.description || "";
    data.personality = res.personality || "";
    data.greeting = res.first_message || "";
    data.scenario = res.scenario || "";
    data.tags = res.tags || [];
    // Prefer the large tier so the creator preview matches the detail view's
    // portrait (same asset), not the heavy full-size original.
    data.avatarUrl = res.avatar_large || res.avatar || "";
    data.avatarFile = null;
    data.creatorNotes = res.creator_notes || "";
    data.systemPrompt = res.system_prompt || "";
    data.species = res.species || "";
    data.age = res.age || "";

    // Map gender back
    if (res.gender === "others" && res.custom_gender) {
      data.gender = res.custom_gender;
    } else if (res.gender) {
      // Capitalize first letter to match UI options
      data.gender = res.gender.charAt(0).toUpperCase() + res.gender.slice(1);
      if (data.gender === "Non-binary") data.gender = "Non-binary";
    } else {
      data.gender = "";
    }

    // Map example_dialogues back to DialoguePair[]. A well-formed exchange has
    // explicit User:/Character: markers; anything else (freeform mes_example
    // imported from a card) is preserved verbatim in the reply field so an
    // edit + save round-trip never silently destroys it.
    if (res.example_dialogues && res.example_dialogues.length > 0) {
      data.exampleDialogues = res.example_dialogues.map((text, idx) => {
        const id = `dlg-${Date.now()}-${idx}`;
        const hasMarkers = /(^|\n)\s*(user|char(acter)?)\s*:/i.test(text);
        if (hasMarkers) {
          const userMatch = text.match(/User:\s*([\s\S]*?)(?:\nCharacter:|$)/i);
          const charMatch = text.match(/Character:\s*([\s\S]*?)$/i);
          return {
            id,
            userMessage: userMatch ? userMatch[1].trim() : "",
            characterReply: charMatch ? charMatch[1].trim() : "",
          };
        }
        return {
          id,
          userMessage: "",
          characterReply: text.replace(/^\s*<START>\s*/i, "").trim(),
        };
      });
    } else {
      data.exampleDialogues = [];
    }

    // Reset fields not in API
    data.title = "";
    data.responseStyle = "";
    data.lorebook = [];
  }

  /** Save (create or update) the character via the API. */
  async function saveCharacter(): Promise<CharacterResponse> {
    saving.value = true;
    try {
      const fd = buildFormData();
      const isEdit = !!id.value;
      const url = isEdit ? `/api/characters/${id.value}` : "/api/characters";
      const method = isEdit ? "PUT" : "POST";

      const { data: result, error: apiError } = await multipartFetch<CharacterResponse>(url, {
        method,
        body: fd,
      });
      if (apiError || !result) throw apiError ?? new Error("Failed to save character");

      id.value = result.id;
      data.id = result.id;

      // Sync lorebook entries
      const { data: lorebooks, error: lbErr } = await client.GET("/api/lorebooks", {
        params: { query: { character_id: result.id } },
      });
      if (lbErr) throw extractApiError(lbErr, "Failed to load lorebooks");

      let lorebookId = "";
      if (lorebooks && lorebooks.items.length > 0) {
        lorebookId = lorebooks.items[0].id;
      } else if (data.lorebook.length > 0) {
        // Create new lorebook
        const newBook = await client.POST("/api/lorebooks", {
          body: {
            name: `${data.name} Lorebook`,
            description: `Lorebook for ${data.name}`,
            is_global: false,
            character_id: result.id,
          },
        });
        if (newBook.data) {
          lorebookId = newBook.data.id;
        }
      }

      if (lorebookId) {
        // Fetch existing entries to know what to delete/update
        const { data: bookDetails, error: bdErr } = await client.GET(
          "/api/lorebooks/{lorebook_id}",
          { params: { path: { lorebook_id: lorebookId } } },
        );
        if (bdErr) throw extractApiError(bdErr, "Failed to load lorebook entries");
        const existingEntries = bookDetails?.entries ?? [];

        // Determine entries to delete
        const currentIds = new Set(data.lorebook.map((e) => e.id));
        for (const entry of existingEntries) {
          if (!currentIds.has(entry.id)) {
            await client.DELETE("/api/lorebooks/{lorebook_id}/entries/{entry_id}", {
              params: { path: { lorebook_id: lorebookId, entry_id: entry.id } },
            });
          }
        }

        // Create or update current entries
        for (const entry of data.lorebook) {
          const isNew = !existingEntries.some((e) => e.id === entry.id);
          const payload = {
            name: entry.keywords[0] || "Untitled",
            content: entry.content,
            keys: entry.keywords,
            enabled: entry.enabled,
          };

          if (isNew) {
            await client.POST("/api/lorebooks/{lorebook_id}/entries", {
              params: { path: { lorebook_id: lorebookId } },
              body: { ...payload, ...NEW_ENTRY_DEFAULTS },
            });
          } else {
            await client.PUT("/api/lorebooks/{lorebook_id}/entries/{entry_id}", {
              params: { path: { lorebook_id: lorebookId, entry_id: entry.id } },
              body: payload,
            });
          }
        }
      }

      return result;
    } finally {
      saving.value = false;
    }
  }

  /** Load a character from the API by ID and populate the form. */
  async function loadFromApi(characterId: string) {
    loading.value = true;
    try {
      const { data: res, error } = await client.GET("/api/characters/{character_id}", {
        params: { path: { character_id: characterId } },
      });

      if (error || !res) {
        throw new Error(`Failed to load character ${characterId}`);
      }

      mapResponseToForm(res);

      // Load lorebook if it exists
      const { data: lorebooks, error: lbErr } = await client.GET("/api/lorebooks", {
        params: { query: { character_id: characterId } },
      });
      if (lbErr) throw extractApiError(lbErr, "Failed to load lorebook");

      if (lorebooks && lorebooks.items.length > 0) {
        const lorebookId = lorebooks.items[0].id;
        const { data: bookDetails, error: bdErr } = await client.GET(
          "/api/lorebooks/{lorebook_id}",
          { params: { path: { lorebook_id: lorebookId } } },
        );
        if (bdErr) throw extractApiError(bdErr, "Failed to load lorebook entries");
        if (bookDetails?.entries) {
          data.lorebook = bookDetails.entries.map((entry) => ({
            id: entry.id,
            keywords: entry.keys ?? [],
            content: entry.content,
            enabled: entry.enabled,
          }));
        }
      } else {
        data.lorebook = [];
      }
    } finally {
      loading.value = false;
    }
  }

  /** Delete a character via the API. */
  async function deleteCharacter(characterId: string) {
    deleting.value = true;
    try {
      const { error: apiError } = await client.DELETE("/api/characters/{character_id}", {
        params: { path: { character_id: characterId } },
      });
      if (apiError) throw new Error("Failed to delete character");
    } finally {
      deleting.value = false;
    }
  }

  const completeness = computed(() => {
    const fields = [
      data.name,
      data.title,
      data.species,
      data.gender,
      data.avatarUrl,
      data.description,
      data.personality,
      data.greeting,
      data.responseStyle,
      data.scenario,
    ];
    const filled = fields.filter((f) => f.trim().length > 0).length;
    const hasDialogues = data.exampleDialogues.length > 0 ? 1 : 0;
    const hasLorebook = data.lorebook.length > 0 ? 1 : 0;
    return { filled: filled + hasDialogues + hasLorebook, total: 12 };
  });

  return {
    data,
    id,
    saving,
    deleting,
    loading,
    updateField,
    addTag,
    removeTag,
    addDialogue,
    updateDialogue,
    removeDialogue,
    addLorebook,
    updateLorebook,
    removeLorebook,
    loadCharacter,
    saveCharacter,
    loadFromApi,
    deleteCharacter,
    completeness,
  };
}
