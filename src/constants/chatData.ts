import type { ChatCharacter, ChatMessage, ChatSession, MoodChip } from "@/types/chat";

export const ACTIVE_CHARACTER: ChatCharacter = {
  id: "char-1",
  name: "Elara Moonwhisper",
  avatar:
    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=120&h=120&fit=crop&crop=face",
  title: "Arcane Librarian of the Sunken Vaults",
  tags: ["Fantasy", "Mystical", "Scholar"],
};

export const CHAT_SESSIONS: ChatSession[] = [
  {
    id: "session-1",
    character: ACTIVE_CHARACTER,
    sessionTitle: "The Sunken Library",
    lastMessage:
      '"The ancient runes shimmer beneath your touch, revealing a passage that leads deeper into the catacombs..."',
    lastActivity: "2m ago",
    unread: true,
    messageCount: 47,
  },
  {
    id: "session-2",
    character: {
      id: "char-2",
      name: "Captain Thorne",
      avatar:
        "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=120&h=120&fit=crop&crop=face",
      title: "Corsair of the Shattered Isles",
      tags: ["Adventure", "Pirate"],
    },
    sessionTitle: "Voyage of the Iron Gale",
    lastMessage:
      '"Set course for the Shattered Isles. We sail at dawn, and may the winds favor the bold."',
    lastActivity: "1h ago",
    unread: false,
    messageCount: 112,
  },
  {
    id: "session-3",
    character: {
      id: "char-3",
      name: "Professor Grimshaw",
      avatar:
        "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=120&h=120&fit=crop&crop=face",
      title: "Master Alchemist, Ravencrest Academy",
      tags: ["Alchemy", "Mystery"],
    },
    sessionTitle: "The Alchemist's Gambit",
    lastMessage:
      '"Fascinating specimen! This compound could change everything we know about transmutation..."',
    lastActivity: "3h ago",
    unread: false,
    messageCount: 23,
  },
  {
    id: "session-4",
    character: {
      id: "char-4",
      name: "Lyra the Bard",
      avatar:
        "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=120&h=120&fit=crop&crop=face",
      title: "Wandering Songstress of the Silver Road",
      tags: ["Romance", "Music"],
    },
    sessionTitle: "Ballad of the Lost Crown",
    lastMessage:
      '"Every song holds a secret, traveler. Shall I play you one from the age of forgotten kings?"',
    lastActivity: "5h ago",
    unread: false,
    messageCount: 89,
  },
  {
    id: "session-5",
    character: {
      id: "char-5",
      name: "Seraphina Vale",
      avatar:
        "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=120&h=120&fit=crop&crop=face",
      title: "High Priestess of the Dawn Temple",
      tags: ["Fantasy", "Healer"],
    },
    sessionTitle: "The Shattered Covenant",
    lastMessage:
      '"The wards are failing. Whatever lies beyond that door, we face it together or not at all."',
    lastActivity: "1d ago",
    unread: false,
    messageCount: 34,
  },
];

export const MOCK_MESSAGES: ChatMessage[] = [
  {
    id: "msg-1",
    sender: "character",
    content:
      '*The torchlight flickers against the damp stone walls as Elara traces her fingertips along the ancient inscription. Her silver eyes narrow with concentration, and a faint glow begins to pulse from the carved symbols.* "These wards were placed here centuries ago \u2014 long before the Sunken Library fell beneath the tides." *She pauses, turning to face you with an expression caught between scholarly excitement and genuine concern.* "The script is Old Netherese. Whoever sealed this passage did not intend for it to be opened lightly."',
    timestamp: "10:42 AM",
    characterName: "Elara Moonwhisper",
    characterAvatar: ACTIVE_CHARACTER.avatar,
  },
  {
    id: "msg-2",
    sender: "user",
    content:
      '*Steps closer to the wall, examining the runes with a careful eye.* "I have seen markings like these before \u2014 in the ruins beneath Neverwinter. They responded to intent, not force." *Places a hand flat against the cool stone.* "Perhaps it requires a specific phrase, or a demonstration of purpose."',
    timestamp: "10:44 AM",
  },
  {
    id: "msg-3",
    sender: "character",
    content:
      '*A slow smile spreads across her face, warm despite the cold air of the underground chamber. She reaches into the leather satchel at her hip and produces a small crystal vial filled with luminescent ink.* "You continue to surprise me, adventurer. Most would have reached for a chisel by now." *She uncorks the vial, and the ink rises of its own accord, hovering in the air like a living constellation.* "If intent is the key, then let us declare ours. Speak your purpose to the ward \u2014 honestly, from the heart. These old enchantments can sense deception as surely as a hound scents fear."',
    timestamp: "10:46 AM",
    characterName: "Elara Moonwhisper",
    characterAvatar: ACTIVE_CHARACTER.avatar,
  },
  {
    id: "msg-4",
    sender: "user",
    content:
      '*Takes a steadying breath and faces the sealed door. The luminescent ink casts shifting patterns of light across the stone.* "I seek the knowledge buried here \u2014 not for power or conquest, but to preserve what was nearly lost. The scholars who built this place trusted that the right seeker would come." *The words echo in the chamber, and for a moment, the runes pulse brighter.*',
    timestamp: "10:48 AM",
  },
  {
    id: "msg-5",
    sender: "character",
    content:
      '*The chamber trembles. Dust cascades from the ceiling as the ancient mechanism groans to life. One by one, the runes along the doorframe ignite \u2014 not with the cold blue of arcane force, but with a warm, amber glow that reminds you of candlelight in a quiet study.*\n\n"It worked." *Elara whispers, her voice thick with wonder. She has studied these vaults for years, pored over fragmentary maps and half-translated texts, and yet \u2014 this moment still catches her breath.*\n\n*The stone door splits down its center and slides apart with a sound like a long-held sigh. Beyond it lies a vast chamber: shelves upon shelves of books and scrolls stretching into darkness, their spines glinting with gilt lettering. The air smells of old paper, dried lavender, and something faintly electric \u2014 preserved magic, perhaps.*\n\n"Welcome to the Heart of the Sunken Library." *She steps forward, and her voice drops to something almost reverent.* "No living soul has stood in this room for over four hundred years."',
    timestamp: "10:51 AM",
    characterName: "Elara Moonwhisper",
    characterAvatar: ACTIVE_CHARACTER.avatar,
  },
];

export const MOOD_CHIPS: MoodChip[] = [
  { id: "mood-1", label: "Boldly" },
  { id: "mood-2", label: "With caution" },
  { id: "mood-3", label: "Whisper" },
  { id: "mood-4", label: "Defiantly" },
  { id: "mood-5", label: "Tenderly" },
];
