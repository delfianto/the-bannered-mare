export interface ChatCharacter {
  id: string;
  name: string;
  avatar: string;
  title: string;
  tags: string[];
}

export interface ChatMessage {
  id: string;
  sender: "user" | "character";
  content: string;
  timestamp: string;
  characterName?: string;
  characterAvatar?: string;
}

export interface ChatSession {
  id: string;
  character: ChatCharacter;
  sessionTitle: string;
  lastMessage: string;
  lastActivity: string;
  unread: boolean;
  messageCount: number;
}

export interface MoodChip {
  id: string;
  label: string;
}
