<script setup lang="ts">
import { onUnmounted, ref, watch } from "vue";

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

// Removal is driven by a plain timer, not a Vue <Transition> leave callback.
// Nested transitions + teleports can drop the leave hook (the modal opens but
// never unmounts); a setTimeout always fires. `visible` gates mounting;
// `entered` drives the enter/leave CSS so the animation still plays.
const DURATION = 200;
const visible = ref(props.show);
const entered = ref(props.show);
let closeTimer: ReturnType<typeof setTimeout> | undefined;

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === "Escape" && props.show) emit("close");
};

watch(
  () => props.show,
  (show) => {
    if (closeTimer) clearTimeout(closeTimer);
    if (show) {
      visible.value = true;
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
      // Mount at the "from" state, then flip on the next frame so the CSS transition runs.
      entered.value = false;
      requestAnimationFrame(() => requestAnimationFrame(() => (entered.value = true)));
    } else {
      entered.value = false;
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
      closeTimer = setTimeout(() => (visible.value = false), DURATION);
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
    >
      <!-- Backdrop -->
      <div
        class="fixed inset-0 bg-black/60 backdrop-blur-[4px] transition-opacity duration-200"
        :class="entered ? 'opacity-100' : 'opacity-0'"
        @click="closeOnBackdrop && emit('close')"
      />

      <!-- Panel -->
      <div
        :class="[
          'relative z-10 max-h-[90vh] w-full overflow-y-auto rounded-2xl border border-white/10 bg-base-200/95 p-6 shadow-2xl backdrop-blur-md transition-all duration-200 ease-out',
          entered ? 'scale-100 opacity-100' : 'scale-95 opacity-0',
          maxWidthClass,
        ]"
      >
        <!-- Header -->
        <div class="mb-4 flex items-start justify-between gap-4">
          <slot name="header">
            <h2 v-if="title" class="font-cinzel text-lg font-bold tracking-wide text-foreground">
              {{ title }}
            </h2>
          </slot>
          <button
            class="flex size-8 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-all hover:bg-white/10 hover:text-foreground active:scale-95"
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
