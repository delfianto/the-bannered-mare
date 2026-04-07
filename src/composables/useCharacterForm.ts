import { reactive, computed } from "vue";
import type { CharacterData, LorebookEntry } from "@/types/creator";
import { INITIAL_CHARACTER } from "@/types/creator";

export function useCharacterForm(initial?: Partial<CharacterData>) {
  const data = reactive<CharacterData>({ ...INITIAL_CHARACTER, ...initial });

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
    completeness,
  };
}
