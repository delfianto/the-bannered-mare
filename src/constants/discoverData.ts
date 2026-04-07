import type { LibraryCharacter } from "@/types/discover";

export const CATEGORIES = [
  "All",
  "Fantasy",
  "Adventure",
  "Romance",
  "Sci-Fantasy",
  "Dark Fantasy",
  "Horror",
  "Comedy",
  "Slice of Life",
];

export const SORT_OPTIONS = [
  { value: "recent", label: "Recently Used" },
  { value: "name-asc", label: "Name A\u2013Z" },
  { value: "name-desc", label: "Name Z\u2013A" },
  { value: "sessions", label: "Most Sessions" },
  { value: "newest", label: "Newest Created" },
] as const;

export const SOURCE_OPTIONS = [
  { value: "all", label: "All Sources" },
  { value: "created", label: "My Creations" },
  { value: "imported", label: "Imported" },
] as const;

export const LIBRARY_CHARACTERS: LibraryCharacter[] = [
  {
    id: "lc1",
    name: "Elara Moonwhisper",
    title: "Arcane Librarian of the Sunken Vaults",
    imageUrl:
      "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&h=560&fit=crop&crop=face",
    tags: ["Fantasy", "Scholar", "Mystical"],
    species: "Half-Elf",
    gender: "Female",
    description:
      "A devoted keeper of forbidden knowledge who guards the drowned archives beneath the Moonlit Sea.",
    chatCount: 2340,
    creator: "You",
    source: "created",
    lastUsed: "2 min ago",
    sessionCount: 47,
    createdAt: "2025-06-01",
  },
  {
    id: "lc2",
    name: "Captain Thorne",
    title: "Corsair of the Shattered Isles",
    imageUrl:
      "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=560&fit=crop&crop=face",
    tags: ["Adventure", "Pirate", "Epic"],
    species: "Human",
    gender: "Male",
    description:
      "A cunning sea captain whose iron will and quick blade have carved legends across every port.",
    chatCount: 5120,
    creator: "You",
    source: "created",
    lastUsed: "1 hour ago",
    sessionCount: 112,
    createdAt: "2025-05-15",
  },
  {
    id: "lc3",
    name: "Morgana Ashwood",
    title: "Witch of the Thornveil Forest",
    imageUrl:
      "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=400&h=560&fit=crop&crop=face",
    tags: ["Dark Fantasy", "Witch", "Gothic"],
    species: "Human",
    gender: "Female",
    description:
      "A reclusive herbalist whose dark bargains with the forest spirits exact a terrible price.",
    chatCount: 3890,
    creator: "ShadowScribe",
    source: "imported",
    lastUsed: "3 hours ago",
    sessionCount: 34,
    createdAt: "2025-05-20",
  },
  {
    id: "lc4",
    name: "Dorian Blackthorn",
    title: "Duke of Midnight Court",
    imageUrl:
      "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&h=560&fit=crop&crop=face",
    tags: ["Romance", "Nobility", "Intrigue"],
    species: "Vampire",
    gender: "Male",
    description:
      "An immortal aristocrat navigating centuries of courtly schemes and forbidden desire.",
    chatCount: 7560,
    creator: "QuillMaster",
    source: "imported",
    lastUsed: "6 hours ago",
    sessionCount: 89,
    createdAt: "2025-04-10",
  },
  {
    id: "lc5",
    name: "Zara Nightbloom",
    title: "Neon Runner of Sector 7",
    imageUrl:
      "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=400&h=560&fit=crop&crop=face",
    tags: ["Sci-Fantasy", "Rogue", "Cyberpunk"],
    species: "Genasi",
    gender: "Female",
    description:
      "A street-smart data courier who outruns corporate enforcers through neon-lit back alleys.",
    chatCount: 4210,
    creator: "NeonTale",
    source: "imported",
    lastUsed: "1 day ago",
    sessionCount: 56,
    createdAt: "2025-04-25",
  },
  {
    id: "lc6",
    name: "Aldric the Sage",
    title: "Keeper of the First Flame",
    imageUrl:
      "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=400&h=560&fit=crop&crop=face",
    tags: ["Fantasy", "Mentor", "Ancient"],
    species: "Human",
    gender: "Male",
    description:
      "The last living guardian of an ancient fire whose light holds back an encroaching darkness.",
    chatCount: 1890,
    creator: "You",
    source: "created",
    lastUsed: "2 days ago",
    sessionCount: 23,
    createdAt: "2025-06-05",
  },
  {
    id: "lc7",
    name: "Seraphina Vale",
    title: "Lightbearer of the Silver Dawn",
    imageUrl:
      "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=400&h=560&fit=crop&crop=face",
    tags: ["Fantasy", "Healer", "Celestial"],
    species: "Aasimar",
    gender: "Female",
    description:
      "A celestial-touched healer whose radiant touch mends wounds and inspires hope in the darkest hours.",
    chatCount: 3450,
    creator: "You",
    source: "created",
    lastUsed: "4 hours ago",
    sessionCount: 67,
    createdAt: "2025-05-28",
  },
  {
    id: "lc8",
    name: "Kael Stormrider",
    title: "Champion of the Broken Oath",
    imageUrl:
      "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=400&h=560&fit=crop&crop=face",
    tags: ["Adventure", "Warrior", "Epic"],
    species: "Goliath",
    gender: "Male",
    description:
      "A battle-scarred warrior seeking redemption for a vow shattered on the field of glory.",
    chatCount: 6200,
    creator: "MythForge",
    source: "imported",
    lastUsed: "12 hours ago",
    sessionCount: 94,
    createdAt: "2025-03-12",
  },
  {
    id: "lc9",
    name: "Lyra the Bard",
    title: "Voice of Forgotten Kings",
    imageUrl:
      "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400&h=560&fit=crop&crop=face",
    tags: ["Fantasy", "Comedy", "Wanderer"],
    species: "Halfling",
    gender: "Female",
    description:
      "A silver-tongued storyteller whose songs can charm crowns from kings and secrets from shadows.",
    chatCount: 4800,
    creator: "You",
    source: "created",
    lastUsed: "5 hours ago",
    sessionCount: 89,
    createdAt: "2025-05-10",
  },
  {
    id: "lc10",
    name: "Professor Grimshaw",
    title: "Master Alchemist of Ironhold",
    imageUrl:
      "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=400&h=560&fit=crop&crop=face",
    tags: ["Fantasy", "Scholar", "Alchemy"],
    species: "Gnome",
    gender: "Male",
    description:
      "An eccentric genius whose volatile experiments blur the line between brilliance and catastrophe.",
    chatCount: 2100,
    creator: "You",
    source: "created",
    lastUsed: "3 hours ago",
    sessionCount: 23,
    createdAt: "2025-06-02",
  },
  {
    id: "lc11",
    name: "Vex Shadowmere",
    title: "The Whispering Blade",
    imageUrl:
      "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=400&h=560&fit=crop&crop=face",
    tags: ["Dark Fantasy", "Rogue", "Intrigue"],
    species: "Tiefling",
    gender: "Male",
    description:
      "A lethal assassin whose whispered contracts shape the fates of empires from the shadows.",
    chatCount: 3340,
    creator: "ShadowScribe",
    source: "imported",
    lastUsed: "1 day ago",
    sessionCount: 41,
    createdAt: "2025-04-18",
  },
  {
    id: "lc12",
    name: "Aria Frostweave",
    title: "Daughter of the Eternal Winter",
    imageUrl:
      "https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=400&h=560&fit=crop&crop=face",
    tags: ["Romance", "Fantasy", "Nobility"],
    species: "Elf",
    gender: "Female",
    description:
      "An elven princess bound by duty to a frozen realm, yearning for warmth beyond its borders.",
    chatCount: 5670,
    creator: "QuillMaster",
    source: "imported",
    lastUsed: "8 hours ago",
    sessionCount: 78,
    createdAt: "2025-03-30",
  },
];
