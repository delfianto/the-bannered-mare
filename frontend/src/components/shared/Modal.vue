<script setup lang="ts">
import { nextTick, onUnmounted, ref, useId, watch } from "vue";

const props = withDefaults(
  defineProps<{
    show: boolean;
    title?: string;
    maxWidth?: "sm" | "md" | "lg" | "xl" | "2xl" | "3xl" | "4xl";
    closeOnBackdrop?: boolean;
  }>(),
  {
    maxWidth: "md",
    closeOnBackdrop: true,
  },
);

const emit = defineEmits<{
  close: [];
}>();

const titleId = useId();
const panelRef = ref<HTMLElement | null>(null);
// The element focused before the dialog opened, so focus can return to it on close.
let previouslyFocused: HTMLElement | null = null;

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

function focusableEls(): HTMLElement[] {
  if (!panelRef.value) return [];
  return Array.from(panelRef.value.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
    (el) => el.offsetParent !== null,
  );
}

// Removal is driven by a plain timer, not a Vue <Transition> leave callback.
// Nested transitions + teleports can drop the leave hook (the modal opens but
// never unmounts); a setTimeout always fires. `visible` gates mounting;
// `entered` drives the enter/leave CSS so the animation still plays.
const DURATION = 200;
const visible = ref(props.show);
const entered = ref(props.show);
let closeTimer: ReturnType<typeof setTimeout> | undefined;

const handleKeyDown = (e: KeyboardEvent) => {
  if (!props.show) return;
  if (e.key === "Escape") {
    emit("close");
    return;
  }
  // Trap Tab within the panel so focus can't escape to the obscured page behind
  // the backdrop; wrap around at both ends.
  if (e.key === "Tab") {
    const els = focusableEls();
    const active = document.activeElement as HTMLElement | null;
    if (els.length === 0) {
      e.preventDefault();
      panelRef.value?.focus();
      return;
    }
    const first = els[0];
    const last = els[els.length - 1];
    // Recapture to the far end whenever focus is on a boundary element, on the
    // bare panel container, or has escaped the panel entirely — so Tab/Shift+Tab
    // wrap inside the dialog instead of leaking to the page behind the backdrop.
    const onTabbable = !!active && els.includes(active);
    if (e.shiftKey && (active === first || !onTabbable)) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && (active === last || !onTabbable)) {
      e.preventDefault();
      first.focus();
    }
  }
};

watch(
  () => props.show,
  (show) => {
    if (closeTimer) clearTimeout(closeTimer);
    if (show) {
      previouslyFocused = document.activeElement as HTMLElement | null;
      visible.value = true;
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
      // Mount at the "from" state, then flip on the next frame so the CSS transition runs.
      entered.value = false;
      requestAnimationFrame(() => requestAnimationFrame(() => (entered.value = true)));
      // Focus the first focusable control (not the bare panel) once rendered, so
      // the tab trap has a real anchor — otherwise the first Shift+Tab, from the
      // untabbable panel, escapes to the page behind the backdrop. Fall back to
      // the panel only when the dialog has no focusable children.
      void nextTick(() => {
        const els = focusableEls();
        (els[0] ?? panelRef.value)?.focus();
      });
    } else {
      entered.value = false;
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
      closeTimer = setTimeout(() => (visible.value = false), DURATION);
      // Return focus to whatever launched the dialog (only when we were open).
      if (previouslyFocused) {
        previouslyFocused.focus();
        previouslyFocused = null;
      }
    }
  },
  { immediate: true },
);

onUnmounted(() => {
  if (closeTimer) clearTimeout(closeTimer);
  document.body.style.overflow = "";
  window.removeEventListener("keydown", handleKeyDown);
});

const maxWidthClass = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-xl",
  "2xl": "max-w-2xl",
  "3xl": "max-w-3xl",
  "4xl": "max-w-4xl",
}[props.maxWidth];
</script>

<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="title ? titleId : undefined"
    >
      <!-- Backdrop -->
      <div
        class="fixed inset-0 bg-black/60 backdrop-blur-[4px] transition-opacity duration-200"
        :class="entered ? 'opacity-100' : 'opacity-0'"
        @click="closeOnBackdrop && emit('close')"
      />

      <!-- Panel -->
      <div
        ref="panelRef"
        tabindex="-1"
        :class="[
          'relative z-10 max-h-[90vh] w-full overflow-y-auto rounded-2xl border border-base-content/10 bg-base-200/95 p-6 shadow-2xl backdrop-blur-md transition-all duration-200 ease-out outline-none',
          entered ? 'scale-100 opacity-100' : 'scale-95 opacity-0',
          maxWidthClass,
        ]"
      >
        <!-- Header -->
        <div class="mb-4 flex items-start justify-between gap-4">
          <slot name="header">
            <h2
              v-if="title"
              :id="titleId"
              class="font-cinzel text-lg font-bold tracking-wide text-foreground"
            >
              {{ title }}
            </h2>
          </slot>
          <button
            class="flex size-8 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-all hover:bg-base-content/10 hover:text-foreground active:scale-95"
            :aria-label="$t('common.close')"
            @click="emit('close')"
          >
            <AppIcon name="i-lucide-x" class="size-4" />
          </button>
        </div>

        <!-- Content -->
        <div class="text-sm text-muted-foreground">
          <slot />
        </div>

        <!-- Footer -->
        <div v-if="$slots.footer" class="mt-6 flex items-center justify-end gap-3">
          <slot name="footer" />
        </div>
      </div>
    </div>
  </Teleport>
</template>
