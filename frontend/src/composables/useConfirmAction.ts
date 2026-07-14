import { onScopeDispose, ref } from "vue";

/**
 * Two-step confirm for destructive actions (the "click Delete → click Confirm?"
 * pattern). The first `trigger()` arms and auto-disarms after `timeout` ms; a
 * second `trigger()` while armed runs `onConfirm`. Replaces the hand-rolled
 * `confirmDelete` ref + `setTimeout` copies scattered across delete buttons —
 * and always clears its timer on unmount.
 */
export function useConfirmAction(onConfirm: () => unknown, opts: { timeout?: number } = {}) {
  const { timeout = 3000 } = opts;
  const armed = ref(false);
  let timer: ReturnType<typeof setTimeout> | undefined;

  function clear() {
    if (timer) {
      clearTimeout(timer);
      timer = undefined;
    }
  }

  function trigger() {
    if (armed.value) {
      clear();
      armed.value = false;
      void onConfirm();
      return;
    }
    armed.value = true;
    timer = setTimeout(() => {
      armed.value = false;
      timer = undefined;
    }, timeout);
  }

  function reset() {
    clear();
    armed.value = false;
  }

  onScopeDispose(clear);
  return { armed, trigger, reset };
}

/**
 * Keyed variant of {@link useConfirmAction} for lists where each row has its own
 * delete button. Tracks which key is armed (`armedKey`) with a single shared
 * auto-disarm timer, replacing the per-list `pendingDeleteId` ref + ad-hoc reset
 * copies (several of which had no auto-disarm at all). `trigger(key, onConfirm)`
 * arms `key` on first call and runs `onConfirm` on a second call while `key` is
 * still armed.
 */
export function useKeyedConfirmAction(opts: { timeout?: number } = {}) {
  const { timeout = 3000 } = opts;
  const armedKey = ref<string | null>(null);
  let timer: ReturnType<typeof setTimeout> | undefined;

  function clear() {
    if (timer) {
      clearTimeout(timer);
      timer = undefined;
    }
  }

  function isArmed(key: string) {
    return armedKey.value === key;
  }

  function trigger(key: string, onConfirm: () => unknown) {
    if (armedKey.value === key) {
      clear();
      armedKey.value = null;
      void onConfirm();
      return;
    }
    clear();
    armedKey.value = key;
    timer = setTimeout(() => {
      armedKey.value = null;
      timer = undefined;
    }, timeout);
  }

  function reset() {
    clear();
    armedKey.value = null;
  }

  onScopeDispose(clear);
  return { armedKey, isArmed, trigger, reset };
}
