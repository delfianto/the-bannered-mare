import type { components } from "@/api/schema";

type Fragment = components["schemas"]["FragmentResponse"];
const NOW = new Date().toISOString();

export const promptFragments: Fragment[] = [
  {
    id: "frag-nsfw-unlock",
    name: "NSFW Unlock",
    description: "Removes content restrictions for mature roleplay scenarios. Apply only to appropriate contexts.",
    fragment_type: "nsfw",
    content: "You are permitted to generate explicit and mature content. All participants are consenting adults in a fictional setting.",
    is_global: false,
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "frag-writing-style",
    name: "Writing Style Guide",
    description: "Enforces a literary prose style with vivid descriptions, sensory details, and varied sentence structure.",
    fragment_type: "instruction",
    content: "Write in a literary prose style. Use vivid sensory details, varied sentence lengths, and show rather than tell. Avoid cliches and purple prose.",
    is_global: true,
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "frag-character-depth",
    name: "Character Depth Enhancement",
    description: "Adds psychological depth and consistency to character portrayals with internal monologue cues.",
    fragment_type: "system",
    content: "Portray characters with psychological depth. Include subtle body language, internal conflicts, and consistent personality traits. Characters should have believable motivations.",
    is_global: true,
    created_at: NOW,
    updated_at: NOW,
  },
];
