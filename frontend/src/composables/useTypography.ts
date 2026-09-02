import { ref, watch } from "vue";

export const TYPOGRAPHY_PRESETS = ["storybook", "literary", "modern", "system"] as const;
export type TypographyPreset = (typeof TYPOGRAPHY_PRESETS)[number];

export const CHAT_FONTS = ["match", "newsreader", "literata", "inter", "georgia"] as const;
export type ChatFont = (typeof CHAT_FONTS)[number];

export const DEFAULT_TYPOGRAPHY_PRESET: TypographyPreset = "storybook";
export const DEFAULT_CHAT_FONT: ChatFont = "match";

const TYPOGRAPHY_KEY = "typography-preset";
const CHAT_FONT_KEY = "chat-font";
const NARRATIVE_ITALICS_KEY = "narrative-italics";

const typographyPreset = ref<TypographyPreset>(DEFAULT_TYPOGRAPHY_PRESET);
const chatFont = ref<ChatFont>(DEFAULT_CHAT_FONT);
const narrativeItalics = ref(false);
let initialized = false;

function isTypographyPreset(value: string | null): value is TypographyPreset {
  return TYPOGRAPHY_PRESETS.some((option) => option === value);
}

function isChatFont(value: string | null): value is ChatFont {
  return CHAT_FONTS.some((option) => option === value);
}

function applyToDom() {
  const root = document.documentElement;
  root.dataset.typography = typographyPreset.value;
  root.dataset.chatFont = chatFont.value;
  root.dataset.narrativeItalics = String(narrativeItalics.value);
}

function persist() {
  localStorage.setItem(TYPOGRAPHY_KEY, typographyPreset.value);
  localStorage.setItem(CHAT_FONT_KEY, chatFont.value);
  localStorage.setItem(NARRATIVE_ITALICS_KEY, String(narrativeItalics.value));
}

function init() {
  if (initialized) return;
  initialized = true;

  const storedTypography = localStorage.getItem(TYPOGRAPHY_KEY);
  const storedChatFont = localStorage.getItem(CHAT_FONT_KEY);
  if (isTypographyPreset(storedTypography)) typographyPreset.value = storedTypography;
  if (isChatFont(storedChatFont)) chatFont.value = storedChatFont;
  narrativeItalics.value = localStorage.getItem(NARRATIVE_ITALICS_KEY) === "true";

  applyToDom();
  watch([typographyPreset, chatFont, narrativeItalics], () => {
    applyToDom();
    persist();
  });
}

export function useTypography() {
  init();

  function setTypographyPreset(value: TypographyPreset) {
    typographyPreset.value = value;
  }

  function setChatFont(value: ChatFont) {
    chatFont.value = value;
  }

  function setNarrativeItalics(value: boolean) {
    narrativeItalics.value = value;
  }

  return {
    typographyPreset,
    chatFont,
    narrativeItalics,
    setTypographyPreset,
    setChatFont,
    setNarrativeItalics,
  };
}
