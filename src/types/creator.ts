export type CreatorTab = "character" | "behavior" | "world";

export interface DialoguePair {
  id: string;
  userMessage: string;
  characterReply: string;
}

export interface LorebookEntry {
  id: string;
  keywords: string[];
  content: string;
  enabled: boolean;
}

export interface CharacterData {
  id?: string;
  name: string;
  title: string;
  species: string;
  gender: string;
  age: string;
  tags: string[];
  avatarUrl: string;
  avatarFile?: File | null;
  description: string;
  personality: string;
  greeting: string;
  responseStyle: string;
  scenario: string;
  exampleDialogues: DialoguePair[];
  lorebook: LorebookEntry[];
  creatorNotes?: string;
  systemPrompt?: string;
}

export const INITIAL_CHARACTER: CharacterData = {
  name: "",
  title: "",
  species: "",
  gender: "",
  age: "",
  tags: [],
  avatarUrl: "",
  avatarFile: null,
  description: "",
  personality: "",
  greeting: "",
  responseStyle: "",
  scenario: "",
  exampleDialogues: [],
  lorebook: [],
  creatorNotes: "",
  systemPrompt: "",
};
