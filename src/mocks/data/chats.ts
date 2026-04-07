import type { components } from "@/api/schema";
import { dateMock } from "@/mocks/utils";

type Chat = components["schemas"]["ChatResponse"];

export const chats: Chat[] = [
  // Aranwen the Banished - Clockwork theology crisis
  {
    id: "chat-aranwen-01",
    character: {
      id: "7384-aranwen-the-banished",
      name: "Aranwen the Banished",
      avatar: "https://images.unsplash.com/?w=400&h=560&fit=crop&crop=face",
      avatar_thumbnail: "https://images.unsplash.com/?w=200&h=200&fit=crop&crop=face",
    },
    model: {
      id: "gpt-4o",
      name: "GPT-4o",
    },
    preview:
      "The divine mechanism is failing, and I fear the gears of the world are grinding to a halt...",
    title: "Divine Mechanism and Doubt",
    ...dateMock.datePair(12, 1),
  },

  // Lynara Frost-Scholar - Ancient ruin expedition
  {
    id: "chat-lynara-01",
    character: {
      id: "2910-lynara-frost-scholar",
      name: "Lynara Frost-Scholar",
      avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&h=560&fit=crop&crop=face",
      avatar_thumbnail: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&h=200&fit=crop&crop=face",
    },
    model: {
      id: "claude-3-5-sonnet",
      name: "Claude 3.5 Sonnet",
    },
    preview: "The ice here is ancient, humming with a resonance that shouldn't exist.",
    title: "Secrets of Saarthal's Ice",
    ...dateMock.datePair(8, 2),
  },

  // Zahrasha the Death-Singer - Necromantic philosophy
  {
    id: "chat-zahrasha-01",
    character: {
      id: "5621-zahrasha-death-singer",
      name: "Zahrasha the Death-Singer",
      avatar: "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=400&h=560&fit=crop&crop=face",
      avatar_thumbnail: "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=200&h=200&fit=crop&crop=face",
    },
    model: {
      id: "gpt-4o-mini",
      name: "GPT-4o Mini",
    },
    preview:
      "Bones do not lie, traveler. They only sing the songs of those who can no longer speak.",
    title: "Desert Bones and Moon Sugar",
    ...dateMock.datePair(15, 3),
  },

  // Eloise Montclair - Poison commission for guild
  {
    id: "chat-eloise-01",
    character: {
      id: "8492-eloise-montclair",
      name: "Eloise Montclair",
      avatar: "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=400&h=560&fit=crop&crop=face",
      avatar_thumbnail: "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=200&h=200&fit=crop&crop=face",
    },
    model: {
      id: "gpt-4o",
      name: "GPT-4o",
    },
    preview: "A discreet transaction is a successful one. What exactly are you looking for?",
    title: "A Most Discreet Transaction",
    ...dateMock.datePair(5, 1),
  },

  // Beeps-With-The-Hist - Hist tree communion
  {
    id: "chat-beeps-01",
    character: {
      id: "1847-beeps-with-the-hist",
      name: "Beeps-With-The-Hist",
      avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400&h=560&fit=crop&crop=face",
      avatar_thumbnail: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&h=200&fit=crop&crop=face",
    },
    model: {
      id: "claude-3-5-opus",
      name: "Claude 3.5 Opus",
    },
    preview: "The sap flows, and with it, the memories of a thousand generations.",
    title: "The Hist Remembers All",
    ...dateMock.datePair(22, 4),
  },

  // Hildra Stormcloak - Companion trials and beast blood
  {
    id: "chat-hildra-01",
    character: {
      id: "3956-hildra-stormcloak",
      name: "Hildra Stormcloak",
      avatar: "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=400&h=560&fit=crop&crop=face",
      avatar_thumbnail: "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=200&h=200&fit=crop&crop=face",
    },
    model: {
      id: "gpt-4o",
      name: "GPT-4o",
    },
    preview: "Honor is earned in blood and sweat. Are you ready for the trial?",
    title: "Blood and Honor at Jorrvaskr",
    ...dateMock.datePair(7, 1),
  },

  // Calanwe Sun-Blessed - Moral crisis over Thalmor orders
  {
    id: "chat-calanwe-01",
    character: {
      id: "6273-calanwe-sun-blessed",
      name: "Calanwe Sun-Blessed",
      avatar: "https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=400&h=560&fit=crop&crop=face",
      avatar_thumbnail: "https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=200&h=200&fit=crop&crop=face",
    },
    model: {
      id: "gpt-4o",
      name: "GPT-4o",
    },
    preview:
      "The Concordat is the law, but sometimes the law feels like a heavy burden on the soul.",
    title: "The Weight of the Concordat",
    ...dateMock.datePair(18, 5),
  },

  // Octavia Maro - Civil war reconnaissance
  {
    id: "chat-octavia-01",
    character: {
      id: "9104-octavia-maro",
      name: "Octavia Maro",
      avatar: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=400&h=560&fit=crop&crop=face",
      avatar_thumbnail: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=200&h=200&fit=crop&crop=face",
    },
    model: {
      id: "claude-3-5-sonnet",
      name: "Claude 3.5 Sonnet",
    },
    preview: "The Empire has eyes everywhere. Even here, in the heart of the rebellion.",
    title: "Empire's Eyes in Skyrim",
    ...dateMock.datePair(10, 2),
  },

  // Finedrin Treemother - Wild Hunt nightmares
  {
    id: "chat-finedrin-01",
    character: {
      id: "4738-finedrin-treemother",
      name: "Finedrin Treemother",
      avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=560&fit=crop&crop=face",
      avatar_thumbnail: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=crop&crop=face",
    },
    model: {
      id: "gpt-4o",
      name: "GPT-4o",
    },
    preview: "The Green Pact is not just a promise; it's a part of our very being.",
    title: "When the Green Pact Screams",
    ...dateMock.datePair(25, 7),
  },

  // Taneth at-Sentinel - Alik'r fugitive hunt
  {
    id: "chat-taneth-01",
    character: {
      id: "7825-taneth-at-sentinel",
      name: "Taneth at-Sentinel",
      avatar: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=400&h=560&fit=crop&crop=face",
      avatar_thumbnail: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=200&h=200&fit=crop&crop=face",
    },
    model: {
      id: "gpt-4o-mini",
      name: "GPT-4o Mini",
    },
    preview: "The sands of the Alik'r are harsh, but they never forget a face.",
    title: "Honor and Sand, Far from Home",
    ...dateMock.datePair(14, 3),
  },

  // Yargol gra-Dushnikh - Stronghold leadership challenge
  {
    id: "chat-yargol-01",
    character: {
      id: "2469-yargol-gra-dushnikh",
      name: "Yargol gra-Dushnikh",
      avatar: "https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?w=400&h=560&fit=crop&crop=face",
      avatar_thumbnail: "https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?w=200&h=200&fit=crop&crop=face",
    },
    model: {
      id: "gpt-4o",
      name: "GPT-4o",
    },
    preview: "Only the strong survive in the stronghold. Do you have what it takes?",
    title: "Steel and Strength Prevail",
    ...dateMock.datePair(9, 2),
  },

  // Nerise Sarethi - House Telvanni power games
  {
    id: "chat-nerise-01",
    character: {
      id: "8156-nerise-sarethi",
      name: "Nerise Sarethi",
      avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&h=560&fit=crop&crop=face",
      avatar_thumbnail: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200&h=200&fit=crop&crop=face",
    },
    model: {
      id: "claude-3-5-opus",
      name: "Claude 3.5 Opus",
    },
    preview: "Power in House Telvanni is not given; it's taken through intellect and magic.",
    title: "Climbing the Mushroom Tower",
    ...dateMock.datePair(11, 1),
  },

  // Elara Montclair - Meridia's Light Against the Abyss
  {
    id: "chat-elara-01",
    character: {
      id: "5309-elara-mavine",
      name: "Elara Mavine",
      avatar: "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=400&h=560&fit=crop&crop=face",
      avatar_thumbnail: "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=200&h=200&fit=crop&crop=face",
    },
    model: {
      id: "gpt-4o",
      name: "GPT-4o",
    },
    preview:
      "In Meridia's light, you are safe. Not from the sound of war, but from corruption itself.",
    title: "Light in the Depths",
    ...dateMock.datePair(28, 8),
  },

  // Valerica's Heir - Adjusting to modern Tamriel
  {
    id: "chat-valerica-01",
    character: {
      id: "6941-valerica-heir",
      name: "Valerica's Heir",
      avatar: "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=400&h=560&fit=crop&crop=face",
      avatar_thumbnail: "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=200&h=200&fit=crop&crop=face",
    },
    model: {
      id: "gpt-4o",
      name: "GPT-4o",
    },
    preview: "The Soul Cairn was a prison, but sometimes the world outside feels just as cold.",
    title: "Memories of the Soul Cairn",
    ...dateMock.datePair(33, 6),
  },

  // Lilatha of Artaeum - Temporal crisis intervention
  {
    id: "chat-lilatha-01",
    character: {
      id: "3582-lilatha-of-artaeum",
      name: "Lilatha of Artaeum",
      avatar: "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?w=400&h=560&fit=crop&crop=face",
      avatar_thumbnail: "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?w=200&h=200&fit=crop&crop=face",
    },
    model: {
      id: "claude-3-5-sonnet",
      name: "Claude 3.5 Sonnet",
    },
    preview: "Time is a fragile thing, and the threads are beginning to fray.",
    title: "Threads Across Time",
    ...dateMock.datePair(20, 4),
  },

  // Mirelle Shadowfoot - Thieves Guild fencing operation
  {
    id: "chat-mirelle-01",
    character: {
      id: "9217-mirelle-shadowfoot",
      name: "Mirelle Shadowfoot",
      avatar: "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=400&h=560&fit=crop&crop=face",
      avatar_thumbnail: "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=200&h=200&fit=crop&crop=face",
    },
    model: {
      id: "gpt-4o-mini",
      name: "GPT-4o Mini",
    },
    preview: "Riften has its own rules. If you want to trade, you'd better learn them fast.",
    title: "The Riften Gray Market",
    ...dateMock.datePair(6, 1),
  },

  // Helga Sky-Voice - Way of the Voice meditation
  {
    id: "chat-helga-01",
    character: {
      id: "4893-helga-sky-voice",
      name: "Helga Sky-Voice",
      avatar: "https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453?w=400&h=560&fit=crop&crop=face",
      avatar_thumbnail: "https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453?w=200&h=200&fit=crop&crop=face",
    },
    model: {
      id: "gpt-4o",
      name: "GPT-4o",
    },
    preview: "The Voice is a gift from Kyne. Use it with wisdom and reverence.",
    title: "The Seven Thousand Steps",
    ...dateMock.datePair(16, 5),
  },

  // Drenlyn Uvirith - Morag Tong writ execution
  {
    id: "chat-drenlyn-01",
    character: {
      id: "7604-drenlyn-uvirith",
      name: "Drenlyn Uvirith",
      avatar: "https://images.unsplash.com/photo-1554151228-14d9def656e4?w=400&h=560&fit=crop&crop=face",
      avatar_thumbnail: "https://images.unsplash.com/photo-1554151228-14d9def656e4?w=200&h=200&fit=crop&crop=face",
    },
    model: {
      id: "claude-3-5-opus",
      name: "Claude 3.5 Opus",
    },
    preview: "Mephala's web is intricate, and every thread has its purpose in the execution.",
    title: "In Mephala's Web",
    ...dateMock.datePair(19, 7),
  },

  // Aetheris Moravayn - Hermaeus Mora's servant seeks knowledge
  {
    id: "chat-aetheris-01",
    character: {
      id: "2135-aetheris-moravayn",
      name: "Aetheris Moravayn",
      avatar: "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=400&h=560&fit=crop&crop=face",
      avatar_thumbnail: "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=200&h=200&fit=crop&crop=face",
    },
    model: {
      id: "gpt-4o",
      name: "GPT-4o",
    },
    preview: "Knowledge is the only true currency in Apocrypha. What are you willing to pay?",
    title: "Apocrypha's Whispers",
    ...dateMock.datePair(30, 9),
  },

  // Nerys Dren - First Week at the College of Winterhold
  {
    id: "chat-nerys-01",
    character: {
      id: "5770-nerys-dren",
      name: "Nerys Dren",
      avatar: "https://images.unsplash.com/photo-1557862921-37829c790f19?w=400&h=560&fit=crop&crop=face",
      avatar_thumbnail: "https://images.unsplash.com/photo-1557862921-37829c790f19?w=200&h=200&fit=crop&crop=face",
    },
    model: {
      id: "gpt-4o",
      name: "GPT-4o",
    },
    preview:
      "A Dunmer apprentice, a refugee from Morrowind, meets the Dragonborn senior fellow. What begins as helping with scattered books becomes something deeper—a mentorship, a friendship, and the beginning of healing.",
    title: "First Week at the College",
    ...dateMock.datePair(6, 0),
  },
];
