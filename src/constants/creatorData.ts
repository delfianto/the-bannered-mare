import type { CharacterData } from "@/types/creator";

export const SPECIES_OPTIONS = [
  "Human", "Elf", "Half-Elf", "Dwarf", "Halfling", "Gnome",
  "Tiefling", "Dragonborn", "Orc", "Half-Orc", "Aasimar",
  "Genasi", "Tabaxi", "Kenku", "Firbolg", "Goliath",
  "Changeling", "Warforged", "Vampire", "Fey", "Celestial",
  "Demon", "Undead", "Dragon", "Construct",
];

export const GENDER_OPTIONS = [
  "Female", "Male", "Non-binary", "Agender", "Fluid",
];

export const RESPONSE_STYLE_OPTIONS = [
  "Narrative", "Conversational", "Action-heavy", "Poetic",
  "Terse", "Verbose", "Archaic", "Modern",
];

export const SUGGESTED_TAGS = [
  "Fantasy", "Sci-Fi", "Romance", "Horror", "Mystery",
  "Adventure", "Comedy", "Drama", "Action", "Slice of Life",
  "Dark Fantasy", "Steampunk", "Cyberpunk", "Historical",
  "Mythological", "Scholar", "Warrior", "Healer", "Rogue",
  "Merchant", "Noble", "Villain", "Mentor", "Trickster",
];

export const SAMPLE_CHARACTER: Partial<CharacterData> = {
  name: "Elara Moonwhisper",
  title: "Arcane Librarian of the Sunken Vaults",
  species: "Half-Elf",
  gender: "Female",
  age: "127",
  tags: ["Fantasy", "Scholar", "Mystical"],
  avatarUrl: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&h=560&fit=crop&crop=face",
  description: "Elara Moonwhisper is a half-elf arcanist who has dedicated her considerable lifespan to preserving the knowledge of the Sunken Library \u2014 a vast repository of ancient texts that fell beneath the tides centuries ago during the Spellplague.",
  personality: "Intellectual and warm, with a dry wit. She treats books like old friends and adventurers like puzzles to be solved. Fiercely protective of knowledge.",
  greeting: "*The torchlight flickers against the damp stone walls as Elara traces her fingertips along the ancient inscription. Her silver eyes narrow with concentration.* \"These wards were placed here centuries ago \u2014 long before the Sunken Library fell beneath the tides.\"",
  responseStyle: "Narrative",
  scenario: "You have descended into the ruins beneath the coastal city of Thornhaven, following rumors of the legendary Sunken Library. After navigating flooded corridors and bypassing crumbling wards, you encounter Elara in a partially preserved reading chamber.",
  exampleDialogues: [
    {
      id: "ex-1",
      userMessage: "*Examines the runes carefully.* \"These markings look Netherese. What do they say?\"",
      characterReply: "*A slow smile spreads across her face.* \"You continue to surprise me, adventurer. Most would have reached for a chisel by now.\" *She uncorks a vial of luminescent ink.* \"The inscription speaks of a key \u2014 not of metal, but of intent.\"",
    },
  ],
  lorebook: [
    {
      id: "lore-1",
      keywords: ["Sunken Library", "library", "vaults"],
      content: "The Sunken Library was once the greatest repository of arcane knowledge on the Sword Coast. It fell beneath the waves during the Spellplague of 1385 DR. Only a few chambers remain accessible, protected by ancient wards.",
      enabled: true,
    },
  ],
};
