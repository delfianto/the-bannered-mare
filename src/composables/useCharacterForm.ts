import { reactive, computed, ref } from "vue";
import type { CharacterData, LorebookEntry } from "@/types/creator";
import { INITIAL_CHARACTER } from "@/types/creator";
import { client } from "@/api/client";
import type { components } from "@/api/schema";

type CharacterResponse = components["schemas"]["CharacterResponse"];

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

    if (data.tags.length > 0) {
      fd.append("tags", JSON.stringify(data.tags));
    }

    if (data.exampleDialogues.length > 0) {
      const dialogueStrings = data.exampleDialogues.map(
        (d) => `<START>\nUser: ${d.userMessage}\nCharacter: ${d.characterReply}`,
      );
      fd.append("example_dialogues", JSON.stringify(dialogueStrings));
    }

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

    if (data.avatarUrl) fd.append("avatar", data.avatarUrl);

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
    data.avatarUrl = res.avatar || "";

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

    // Map example_dialogues back to DialoguePair[]
    if (res.example_dialogues && res.example_dialogues.length > 0) {
      data.exampleDialogues = res.example_dialogues.map((text, idx) => {
        // Parse "<START>\nUser: ...\nCharacter: ..." format
        const userMatch = text.match(/User:\s*([\s\S]*?)(?:\nCharacter:|$)/);
        const charMatch = text.match(/Character:\s*([\s\S]*?)$/);
        return {
          id: `dlg-${Date.now()}-${idx}`,
          userMessage: userMatch ? userMatch[1].trim() : "",
          characterReply: charMatch ? charMatch[1].trim() : "",
        };
      });
    } else {
      data.exampleDialogues = [];
    }

    // Reset fields not in API
    data.title = "";
    data.species = "";
    data.age = "";
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

      const response = await fetch(url, { method, body: fd });

      if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(`API Error ${response.status}: ${errorBody}`);
      }

      const result: CharacterResponse = await response.json();
      id.value = result.id;
      data.id = result.id;
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
    } finally {
      loading.value = false;
    }
  }

  /** Delete a character via the API. */
  async function deleteCharacter(characterId: string) {
    deleting.value = true;
    try {
      const response = await fetch(`/api/characters/${characterId}`, { method: "DELETE" });
      if (!response.ok && response.status !== 204) {
        throw new Error(`Failed to delete character: ${response.status}`);
      }
    } finally {
      deleting.value = false;
    }
  }

  const completeness = computed(() => {
    const fields = [
      data.name, data.title, data.species, data.gender,
      data.avatarUrl, data.description, data.personality,
      data.greeting, data.responseStyle, data.scenario,
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
