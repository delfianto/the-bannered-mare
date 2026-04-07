export interface Character {
  id: string;
  name: string;
  imageUrl: string;
  tags: string[];
  chatCount: number;
  creator: string;
}

export interface RecentSession {
  id: string;
  characterName: string;
  characterAvatar: string;
  lastMessage: string;
  timestamp: string;
}

export interface ContinueSession {
  id: string;
  title: string;
  characterName: string;
  imageUrl: string;
  lastActivity: string;
  messageCount: number;
}
