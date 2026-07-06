import type { components } from "@/api/schema";

type DataBankEntry = components["schemas"]["DataBankResponse"];
const NOW = new Date().toISOString();

export const dataBankEntries: DataBankEntry[] = [
  {
    id: "db-entry-1",
    name: "World Lore Overview",
    content:
      "The world of Aetheris is divided into five great kingdoms, each governed by ancient pacts forged during the Age of Binding. Magic flows through ley lines that converge at the capital cities, and the balance of power depends on controlling these nexus points.",
    scope: "global",
    character_id: null,
    chat_id: null,
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "db-entry-2",
    name: "Common Phrases & Greetings",
    content:
      'Standard greetings in Aetheris include "Stars guide you" (formal) and "Winds at your back" (casual). Farewells use "Until the moons align" among nobility.',
    scope: "global",
    character_id: null,
    chat_id: null,
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "db-entry-3",
    name: "Elara's Backstory Notes",
    content:
      "Elara was raised in the Thornwood Monastery after her parents vanished during the Rift Collapse. She discovered her affinity for shadow magic at age twelve and was subsequently exiled by the Elder Circle who feared her power.",
    scope: "character",
    character_id: "char-elara-001",
    chat_id: null,
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "db-entry-4",
    name: "Session Context: The Heist",
    content:
      "The party has agreed to infiltrate Lord Varen's estate during the Solstice Gala. Key details: the vault is in the east wing, guards rotate every 15 minutes, and the party has a forged invitation under the name 'House Driftmere'.",
    scope: "chat",
    character_id: null,
    chat_id: "chat-session-042",
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "db-entry-5",
    name: "Kael's Personality Anchors",
    content:
      "Kael always speaks in short, clipped sentences. He avoids eye contact with strangers. He has a nervous habit of tapping his left thumb against his thigh when lying. His loyalty to the party is absolute but he never says it outright.",
    scope: "character",
    character_id: "char-kael-002",
    chat_id: null,
    created_at: NOW,
    updated_at: NOW,
  },
];
