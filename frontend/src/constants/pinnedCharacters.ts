export interface PinnedCharacter {
  id: string;
  name: string;
  avatar: string;
  chatPath: string;
}

export const PINNED_CHARACTERS: PinnedCharacter[] = [
  {
    id: "char-1",
    name: "Elara Moonwhisper",
    avatar:
      "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=80&h=80&fit=crop&crop=face",
    chatPath: "/chats/session-1",
  },
  {
    id: "char-2",
    name: "Captain Thorne",
    avatar:
      "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=80&h=80&fit=crop&crop=face",
    chatPath: "/chats/session-2",
  },
  {
    id: "char-4",
    name: "Lyra the Bard",
    avatar:
      "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=80&h=80&fit=crop&crop=face",
    chatPath: "/chats/session-4",
  },
];
