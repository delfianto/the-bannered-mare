import type { components } from "@/api/schema";

type Persona = components["schemas"]["PersonaResponse"];

export const personas: Persona[] = [
  {
    id: "persona-1",
    name: "Default User",
    description: "A curious adventurer seeking knowledge and stories.",
    avatar: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=400&h=560&fit=crop&crop=face",
    avatar_thumbnail: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=200&h=200&fit=crop&crop=face",
    is_default: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "persona-2",
    name: "The Scholar",
    description: "An academic researcher with a thirst for ancient lore and forgotten histories.",
    avatar: "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=400&h=560&fit=crop&crop=face",
    avatar_thumbnail: "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=200&h=200&fit=crop&crop=face",
    is_default: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "persona-3",
    name: "The Wanderer",
    description: "A mysterious traveler from distant lands, carrying tales of far-off places.",
    avatar: "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=400&h=560&fit=crop&crop=face",
    avatar_thumbnail: "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=200&h=200&fit=crop&crop=face",
    is_default: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];
