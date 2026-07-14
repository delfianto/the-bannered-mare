import { onUnmounted, ref, watch } from "vue";

/**
 * Timer-driven open/close transition for teleported overlays (drawers, sheets):
 * `visible` gates mounting and `entered` drives the enter/leave CSS. Removal runs
 * on a `setTimeout` rather than a `<Transition>` leave hook because nested
 * transitions + teleports can drop the hook (the overlay opens but never unmounts).
 * Also owns body-scroll-lock and, when `onEscape` is given, an Escape-to-close
 * key listener.
 *
 * Note: `Modal.vue` deliberately keeps its own copy — its transition is coupled to
 * a focus trap and the stacked-modal scroll-lock (see V2-A3/V2-D7), which this
 * intentionally-simple composable does not model.
 */
export function useOverlayTransition(
  isOpen: () => boolean,
  opts: { duration?: number; onEscape?: () => void } = {},
) {
  const { duration = 200, onEscape } = opts;
  const visible = ref(isOpen());
  const entered = ref(isOpen());
  let closeTimer: ReturnType<typeof setTimeout> | undefined;

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === "Escape" && isOpen()) onEscape?.();
  }

  watch(
    isOpen,
    (open) => {
      if (closeTimer) clearTimeout(closeTimer);
      if (open) {
        visible.value = true;
        document.body.style.overflow = "hidden";
        if (onEscape) window.addEventListener("keydown", handleKeyDown);
        // Mount at the "from" state, then flip on the next frame so the CSS runs.
        entered.value = false;
        requestAnimationFrame(() => requestAnimationFrame(() => (entered.value = true)));
      } else {
        entered.value = false;
        document.body.style.overflow = "";
        if (onEscape) window.removeEventListener("keydown", handleKeyDown);
        closeTimer = setTimeout(() => (visible.value = false), duration);
      }
    },
    { immediate: true },
  );

  onUnmounted(() => {
    if (closeTimer) clearTimeout(closeTimer);
    document.body.style.overflow = "";
    if (onEscape) window.removeEventListener("keydown", handleKeyDown);
  });

  return { visible, entered };
}
