<script setup lang="ts">
import { onUnmounted, watch } from "vue";

const props = withDefaults(
  defineProps<{
    show: boolean;
    title?: string;
    maxWidth?: "sm" | "md" | "lg" | "xl" | "2xl";
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

// Close on escape key
const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === "Escape" && props.show) {
    emit("close");
  }
};

watch(
  () => props.show,
  (show) => {
    if (show) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    } else {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
    }
  },
  { immediate: true },
);

onUnmounted(() => {
  document.body.style.overflow = "";
  window.removeEventListener("keydown", handleKeyDown);
});

const maxWidthClass = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-xl",
  "2xl": "max-w-2xl",
}[props.maxWidth];
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <!-- Backdrop -->
        <div
          class="fixed inset-0 bg-black/60 backdrop-blur-[4px] transition-opacity"
          @click="closeOnBackdrop && emit('close')"
        />

        <!-- Dialog Wrapper -->
        <Transition
          enter-active-class="transition duration-300 ease-out transform"
          enter-from-class="scale-95 opacity-0 translate-y-4 sm:translate-y-0"
          enter-to-class="scale-100 opacity-100 translate-y-0"
          leave-active-class="transition duration-200 ease-in transform"
          leave-from-class="scale-100 opacity-100 translate-y-0"
          leave-to-class="scale-95 opacity-0 translate-y-4 sm:translate-y-0"
        >
          <!-- Panel -->
          <div
            v-if="show"
            :class="[
              'relative z-10 w-full rounded-2xl border border-white/10 bg-card/95 p-6 shadow-2xl backdrop-blur-md',
              maxWidthClass,
            ]"
            role="dialog"
            aria-modal="true"
          >
            <!-- Header -->
            <div class="mb-4 flex items-start justify-between gap-4">
              <slot name="header">
                <h2
                  v-if="title"
                  class="font-cinzel text-lg font-bold tracking-wide text-foreground"
                >
                  {{ title }}
                </h2>
              </slot>
              <button
                class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-all hover:bg-white/10 hover:text-foreground active:scale-95"
                @click="emit('close')"
              >
                <UIcon name="i-lucide-x" class="h-4 w-4" />
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
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
