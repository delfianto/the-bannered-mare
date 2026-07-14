import { onScopeDispose, ref } from "vue";

/**
 * Two-step confirm for destructive actions (the "click Delete → click Confirm?"
 * pattern). The first `trigger()` arms and auto-disarms after `timeout` ms; a
 * second `trigger()` while armed runs `onConfirm`. Replaces the hand-rolled
 * `confirmDelete` ref + `setTimeout` copies scattered across delete buttons —
 * and always clears its timer on unmount.
 */
export function useConfirmAction(
  onConfirm: () => void | Promise<void>,
  opts: { timeout?: number } = {},
) {
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
