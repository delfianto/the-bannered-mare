import { ref } from "vue";

// Module-level singleton (same pattern as useTheme/useSidebar): a monotonic
// tick bumped whenever an LLM call for a chat settles — completion,
// regeneration, or suggestions, success or error (failed calls write audit
// rows too). Consumers watch `tick` to refresh state derived from a call's
// server-side effects (e.g. the drawer's Logs tab) without polling or a full
// page reload.
const tick = ref(0);
const chatId = ref<string | null>(null);

export function useCompletionSignal() {
  const notify = (id: string) => {
    chatId.value = id;
    tick.value++;
  };
  return { tick, chatId, notify };
}
