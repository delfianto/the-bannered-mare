import type { components } from "@/api/schema";

type PromptTemplate = components["schemas"]["PromptTemplateResponse"];
type TemplateFragment = components["schemas"]["TemplateFragmentResponse"];
const NOW = new Date().toISOString();

export const promptTemplates: PromptTemplate[] = [
  {
    id: "tpl-default",
    name: "Default Template",
    description: "Standard roleplay template with all components enabled. Suitable for most character interactions.",
    is_default: true,
    system_template: "You are {{character_name}}. {{character_description}}",
    component_order: ["persona", "character", "scenario", "examples", "history"],
    components_enabled: {
      persona: true,
      character: true,
      scenario: true,
      examples: true,
      history: true,
    },
    max_history_tokens: 4096,
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "tpl-minimal",
    name: "Minimal Template",
    description: "Lightweight template with only essential components. Faster token usage for simple conversations.",
    is_default: false,
    system_template: "You are {{character_name}}.",
    component_order: ["character", "history"],
    components_enabled: {
      persona: false,
      character: true,
      scenario: false,
      examples: false,
      history: true,
    },
    max_history_tokens: 2048,
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "tpl-advanced-rp",
    name: "Advanced RP Template",
    description: "Extended template with all components, post-history instructions, and higher token limits for deep roleplay.",
    is_default: false,
    system_template: "You are {{character_name}}, {{character_personality}}. {{scenario}}",
    component_order: ["persona", "character", "scenario", "lore", "examples", "history"],
    components_enabled: {
      persona: true,
      character: true,
      scenario: true,
      lore: true,
      examples: true,
      history: true,
    },
    max_history_tokens: 8192,
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "tpl-assistant",
    name: "Assistant Template",
    description: "Optimized for assistant-style interactions without heavy roleplay elements.",
    is_default: false,
    system_template: "You are a helpful assistant named {{character_name}}.",
    component_order: ["character", "history"],
    components_enabled: {
      persona: false,
      character: true,
      scenario: false,
      examples: false,
      history: true,
    },
    max_history_tokens: 4096,
    created_at: NOW,
    updated_at: NOW,
  },
];

// Seeded template-fragment associations (fragments attached to templates)
// Import the fragment data inline to avoid circular deps — we reference by ID
export const templateFragments: Map<string, TemplateFragment[]> = new Map([
  [
    "tpl-default",
    [
      {
        id: "tf-1",
        template_id: "tpl-default",
        fragment_id: "frag-writing-style",
        position: "after_system",
        ordinal: 0,
        created_at: NOW,
        fragment: {
          id: "frag-writing-style",
          name: "Writing Style Guide",
          description: "Enforces a literary prose style with vivid descriptions, sensory details, and varied sentence structure.",
          fragment_type: "instruction",
          content: "Write in a literary prose style. Use vivid sensory details, varied sentence lengths, and show rather than tell. Avoid cliches and purple prose.",
          is_global: true,
          created_at: NOW,
          updated_at: NOW,
        },
      },
      {
        id: "tf-2",
        template_id: "tpl-default",
        fragment_id: "frag-character-depth",
        position: "pre_history",
        ordinal: 1,
        created_at: NOW,
        fragment: {
          id: "frag-character-depth",
          name: "Character Depth Enhancement",
          description: "Adds psychological depth and consistency to character portrayals with internal monologue cues.",
          fragment_type: "system",
          content: "Portray characters with psychological depth. Include subtle body language, internal conflicts, and consistent personality traits. Characters should have believable motivations.",
          is_global: true,
          created_at: NOW,
          updated_at: NOW,
        },
      },
    ],
  ],
]);
