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

/**
 * SSE stream events from the send/regenerate pipeline. Not in the OpenAPI schema
 * (SSE bodies aren't modeled there), so this mirrors the backend `StreamEvent`
 * (backend/src/chat_message/schemas.py) — keep the two in sync.
 */
export type StreamEvent =
  | { type: "start"; message_id?: string }
  | { type: "text"; content: string }
  | { type: "reasoning"; content: string }
  | { type: "usage"; input_tokens?: number; output_tokens?: number; total_tokens?: number }
  | { type: "done"; finish_reason?: string }
  | { type: "error"; message?: string; code?: string };
