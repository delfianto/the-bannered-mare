import { ref, watch } from "vue";

// Chat suggestion preferences, shared between Settings (the toggles) and the
// chat view (the behaviour). Singleton so both stay in sync.
//
// `replySuggestionsEnabled` is the master switch for the whole suggestions bar
// (reply cards + tone chips). `autoGenerateTones` only has any effect while the
// master is on: when set, scene-specific tone chips are generated automatically
// after each reply instead of showing the static defaults until clicked.
const replySuggestionsEnabled = ref(true);
const autoGenerateTones = ref(false);
let initialized = false;

function init() {
  if (initialized) return;
  initialized = true;

  const stored = localStorage.getItem("setting-reply-suggestions");
  if (stored !== null) replySuggestionsEnabled.value = stored === "true";

  const storedAuto = localStorage.getItem("setting-auto-tones");
  if (storedAuto !== null) autoGenerateTones.value = storedAuto === "true";

  watch(replySuggestionsEnabled, (v) =>
    localStorage.setItem("setting-reply-suggestions", String(v)),
  );
  watch(autoGenerateTones, (v) => localStorage.setItem("setting-auto-tones", String(v)));
}

export function useSuggestionSettings() {
  init();
  return { replySuggestionsEnabled, autoGenerateTones };
}
