import { characters } from "./characters";
import { chats } from "./chats";
import { daysAgo } from "@/mocks/utils";

// Pick 6 characters as favorites
export const bookmarkedCharacters = characters.slice(0, 6).map((c, i) => ({
  ...c,
  bookmarked_at: daysAgo(i * 2 + 1),
}));

// Pick 4 chats as bookmarked sessions
export const bookmarkedSessions = chats.slice(0, 4).map((c, i) => ({
  ...c,
  bookmarked_at: daysAgo(i * 3 + 1),
}));

// Mock bookmarked messages with NarrativeText content
export const bookmarkedMessages = [
  {
    id: "bmsg-001",
    role: "assistant" as const,
    content:
      '*Thalric sighs, his breath clouding in the freezing air of the sanctum as he adjusts the weight of his staff. He looks toward the heavy stone doors...*\n\n"If the prophecy holds, the sun will not rise over Candlekeep tomorrow. We must finish the ritual before the clock strikes twelve."',
    character: {
      id: characters[0].id,
      name: characters[0].name,
      avatar: characters[0].avatar,
    },
    chat: {
      id: chats[0].id,
      title: chats[0].title,
    },
    bookmarked_at: daysAgo(2),
    created_at: daysAgo(12),
  },
  {
    id: "bmsg-002",
    role: "assistant" as const,
    content:
      '*She lets out a short, melodic laugh that startles a murder of crows nearby. Her eyes sparkle with a dangerous mischief.*\n\n"Danger is just a fancy word for an interesting Tuesday. Now, are you coming? Or do you prefer the safety of your dusty library?"',
    character: {
      id: characters[1].id,
      name: characters[1].name,
      avatar: characters[1].avatar,
    },
    chat: {
      id: chats[1].id,
      title: chats[1].title,
    },
    bookmarked_at: daysAgo(5),
    created_at: daysAgo(18),
  },
  {
    id: "bmsg-003",
    role: "assistant" as const,
    content:
      '*The ancient tome crackles as its pages turn on their own, revealing script that glows with a faint amber light. The scholar adjusts her spectacles, leaning closer.*\n\n"This... this changes everything. The Founding Texts speak of a gate beneath the mountain — sealed not by magic, but by a riddle spoken in the tongue of dragons."',
    character: {
      id: characters[2].id,
      name: characters[2].name,
      avatar: characters[2].avatar,
    },
    chat: {
      id: chats[2].id,
      title: chats[2].title,
    },
    bookmarked_at: daysAgo(8),
    created_at: daysAgo(25),
  },
];
