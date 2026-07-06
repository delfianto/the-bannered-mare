import type { components } from "@/api/schema";

/** API response types — use these throughout chat components */
export type Chat = components["schemas"]["ChatResponse"];
export type Message = components["schemas"]["MessageResponse"];
export type ChatCharacterInfo = components["schemas"]["ChatCharacterResponse"];

/** UI-only types (not from API) */
export interface MoodChip {
  id: string;
  label: string;
}
