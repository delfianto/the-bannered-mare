import type { components } from "@/api/schema";

type Profile = components["schemas"]["ProfileResponse"];
const NOW = new Date().toISOString();

// IDs reference existing template/preset/persona/model fixtures so the
// loadout dropdowns and card summaries resolve to real names in mock mode.
export const profiles: Profile[] = [
  {
    id: "profile-grimdark-gm",
    name: "Grimdark GM",
    description: "Harsh, unforgiving game master for dark fantasy campaigns.",
    is_default: true,
    prompt_template_id: "tpl-default",
    preset_id: "preset-creative-writing",
    persona_id: "persona-3",
    model_id: "mdl-openai-gpt54",
    source: "manual",
    source_filename: null,
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "profile-cozy-tavern",
    name: "Cozy Tavern Chat",
    description: "Warm, lighthearted roleplay for relaxed tavern encounters.",
    is_default: false,
    prompt_template_id: "tpl-default",
    preset_id: "preset-default-rp",
    persona_id: "persona-1",
    model_id: "mdl-openai-gpt4o",
    source: "manual",
    source_filename: null,
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "profile-lorekeeper",
    name: "Lorekeeper",
    description: "Detail-obsessed narrator that keeps continuity across long sagas.",
    is_default: false,
    prompt_template_id: "tpl-default",
    preset_id: "preset-precise",
    persona_id: "persona-2",
    model_id: "mdl-openai-gpt53-chat",
    source: "sillytavern",
    source_filename: "lorekeeper_preset.json",
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: "profile-quick-banter",
    name: "Quick Banter",
    description: "Snappy, low-token loadout for fast back-and-forth.",
    is_default: false,
    prompt_template_id: "tpl-minimal",
    preset_id: "preset-default-rp",
    persona_id: null,
    model_id: "mdl-openai-gpt4o-mini",
    source: "manual",
    source_filename: null,
    created_at: NOW,
    updated_at: NOW,
  },
];
