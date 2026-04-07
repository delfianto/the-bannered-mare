import type { Character, RecentSession, ContinueSession } from "@/types/home";

export const RECENT_SESSIONS: RecentSession[] = [
  {
    id: "rs1",
    characterName: "Elara Moonwhisper",
    characterAvatar:
      "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=80&h=80&fit=crop&crop=face",
    lastMessage:
      '"The ancient runes shimmer beneath your touch, revealing a passage that leads deeper into the catacombs..."',
    timestamp: "2m ago",
  },
  {
    id: "rs2",
    characterName: "Captain Thorne",
    characterAvatar:
      "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=80&h=80&fit=crop&crop=face",
    lastMessage:
      '"Set course for the Shattered Isles. We sail at dawn, and may the winds favor the bold."',
    timestamp: "1h ago",
  },
  {
    id: "rs3",
    characterName: "Professor Grimshaw",
    characterAvatar:
      "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=80&h=80&fit=crop&crop=face",
    lastMessage:
      '"Fascinating specimen! This alchemical compound could change everything we know about transmutation..."',
    timestamp: "3h ago",
  },
  {
    id: "rs4",
    characterName: "Lyra the Bard",
    characterAvatar:
      "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=80&h=80&fit=crop&crop=face",
    lastMessage:
      '"Every song holds a secret, traveler. Shall I play you one from the age of forgotten kings?"',
    timestamp: "5h ago",
  },
];

export const CONTINUE_SESSIONS: ContinueSession[] = [
  {
    id: "cs1",
    title: "The Sunken Library",
    characterName: "Elara Moonwhisper",
    imageUrl:
      "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=600&h=340&fit=crop",
    lastActivity: "2 min ago",
    messageCount: 47,
  },
  {
    id: "cs2",
    title: "Voyage of the Iron Gale",
    characterName: "Captain Thorne",
    imageUrl:
      "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=600&h=340&fit=crop",
    lastActivity: "1 hour ago",
    messageCount: 112,
  },
  {
    id: "cs3",
    title: "The Alchemist's Gambit",
    characterName: "Professor Grimshaw",
    imageUrl:
      "https://images.unsplash.com/photo-1532012197267-da84d127e765?w=600&h=340&fit=crop",
    lastActivity: "3 hours ago",
    messageCount: 23,
  },
  {
    id: "cs4",
    title: "Ballad of the Lost Crown",
    characterName: "Lyra the Bard",
    imageUrl:
      "https://images.unsplash.com/photo-1507924538820-ede94a04019d?w=600&h=340&fit=crop",
    lastActivity: "5 hours ago",
    messageCount: 89,
  },
];

export const DISCOVER_CHARACTERS: Character[] = [
  {
    id: "c1",
    name: "Seraphina Vale",
    imageUrl:
      "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=400&h=560&fit=crop&crop=face",
    tags: ["Fantasy", "Healer", "Mystical"],
    chatCount: 2340,
    creator: "TaleWeaver",
  },
  {
    id: "c2",
    name: "Kael Stormrider",
    imageUrl:
      "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=400&h=560&fit=crop&crop=face",
    tags: ["Adventure", "Warrior", "Epic"],
    chatCount: 5120,
    creator: "MythForge",
  },
  {
    id: "c3",
    name: "Morgana Ashwood",
    imageUrl:
      "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=400&h=560&fit=crop&crop=face",
    tags: ["Dark Fantasy", "Witch", "Gothic"],
    chatCount: 3890,
    creator: "ShadowScribe",
  },
  {
    id: "c4",
    name: "Dorian Blackthorn",
    imageUrl:
      "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&h=560&fit=crop&crop=face",
    tags: ["Romance", "Nobility", "Intrigue"],
    chatCount: 7560,
    creator: "QuillMaster",
  },
  {
    id: "c5",
    name: "Zara Nightbloom",
    imageUrl:
      "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=400&h=560&fit=crop&crop=face",
    tags: ["Sci-Fantasy", "Rogue", "Cyberpunk"],
    chatCount: 4210,
    creator: "NeonTale",
  },
  {
    id: "c6",
    name: "Aldric the Sage",
    imageUrl:
      "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=400&h=560&fit=crop&crop=face",
    tags: ["Wisdom", "Mentor", "Ancient"],
    chatCount: 1890,
    creator: "LoreKeeper",
  },
];

export const CATEGORIES = [
  "All",
  "Fantasy",
  "Adventure",
  "Romance",
  "Sci-Fantasy",
  "Dark Fantasy",
];
