import { ref } from "vue";

export interface ConfirmOptions {
  title?: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  /** Style the confirm button as destructive (error tone). */
  danger?: boolean;
}

interface ConfirmState extends ConfirmOptions {
  open: boolean;
}

// Module-level singleton — one dialog, rendered once by <ConfirmDialog> (mounted
// in App.vue), like the toast store. `confirm()` opens it and resolves the
// returned promise when the user answers. Replaces blocking native `confirm()`
// with a themed, async dialog that also works inside a router leave-guard.
const state = ref<ConfirmState>({ open: false, message: "" });
let resolver: ((confirmed: boolean) => void) | null = null;

function settle(confirmed: boolean) {
  if (!resolver) return;
  const resolve = resolver;
  resolver = null;
  state.value = { ...state.value, open: false };
  resolve(confirmed);
}

export function useConfirm() {
  function confirm(options: ConfirmOptions): Promise<boolean> {
    settle(false); // a new prompt supersedes any still-open one
    state.value = { open: true, ...options };
    return new Promise<boolean>((resolve) => {
      resolver = resolve;
    });
  }

  return { confirm };
}

/** For the single <ConfirmDialog> renderer only. */
export function useConfirmState() {
  return {
    state,
    onConfirm: () => settle(true),
    onCancel: () => settle(false),
  };
}
