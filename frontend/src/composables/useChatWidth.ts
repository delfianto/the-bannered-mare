import { ref, watch } from "vue";

// Chat conversation column width. Applied as the `--chat-max-width` CSS var on
// <html>; the message list and the input both cap at it. Values are rem so they
// scale with the Text Size setting; "full" uses the whole pane.
export type ChatWidth = "narrow" | "cozy" | "wide" | "full";

export const CHAT_WIDTHS: Record<ChatWidth, string> = {
  narrow: "56rem",
  cozy: "72rem",
  wide: "88rem",
  full: "100%",
};

export const CHAT_WIDTH_ORDER: ChatWidth[] = ["narrow", "cozy", "wide", "full"];
const DEFAULT_CHAT_WIDTH: ChatWidth = "cozy";
const STORAGE_KEY = "chat-width";

const chatWidth = ref<ChatWidth>(DEFAULT_CHAT_WIDTH);
let initialized = false;

function apply() {
  document.documentElement.style.setProperty("--chat-max-width", CHAT_WIDTHS[chatWidth.value]);
}

function init() {
  if (initialized) return;
  initialized = true;

  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored && stored in CHAT_WIDTHS) chatWidth.value = stored as ChatWidth;

  apply();

  watch(chatWidth, () => {
    apply();
    localStorage.setItem(STORAGE_KEY, chatWidth.value);
  });
}

export function useChatWidth() {
  init();

  function setChatWidth(w: ChatWidth) {
    chatWidth.value = w;
  }

  return { chatWidth, setChatWidth };
}
