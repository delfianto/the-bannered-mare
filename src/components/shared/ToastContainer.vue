<script setup lang="ts">
import { useAppToast } from "@/composables/useToast";

const { toasts, removeToast } = useAppToast();

const getIcon = (type: string) => {
  switch (type) {
    case "success":
      return "i-lucide-circle-check";
    case "error":
      return "i-lucide-circle-alert";
    case "warning":
      return "i-lucide-triangle-alert";
    default:
      return "i-lucide-info";
  }
};

const getTypeClasses = (type: string) => {
  switch (type) {
    case "success":
      return {
        border: "border-emerald-500/25 bg-emerald-950/90 text-emerald-100",
        icon: "text-emerald-400",
      };
    case "error":
      return {
        border: "border-destructive/25 bg-red-950/90 text-red-100",
        icon: "text-red-400",
      };
    case "warning":
      return {
        border: "border-amber-500/25 bg-amber-950/90 text-amber-100",
        icon: "text-amber-400",
      };
    default:
      return {
        border: "border-white/10 bg-stone-900/90 text-stone-100",
        icon: "text-primary",
      };
  }
};
</script>

<template>
  <Teleport to="body">
    <div
      class="pointer-events-none fixed right-0 top-0 z-[100] flex w-full max-w-sm flex-col gap-3 p-4 sm:p-6"
    >
      <TransitionGroup
        enter-active-class="transform ease-out duration-300 transition"
        enter-from-class="translate-y-2 opacity-0 sm:translate-y-0 sm:translate-x-2"
        enter-to-class="translate-y-0 opacity-100 sm:translate-x-0"
        leave-active-class="transition ease-in duration-100"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0 font-medium"
      >
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="pointer-events-auto flex w-full overflow-hidden rounded-xl border p-4 shadow-2xl backdrop-blur-md"
          :class="getTypeClasses(toast.type).border"
        >
          <div class="flex w-full items-start gap-3">
            <UIcon
              :name="getIcon(toast.type)"
              class="mt-0.5 h-5 w-5 shrink-0"
              :class="getTypeClasses(toast.type).icon"
            />
            <div class="min-w-0 flex-1">
              <h4
                class="font-cinzel text-xs font-semibold uppercase tracking-wider text-foreground"
              >
                {{ toast.title }}
              </h4>
              <p
                v-if="toast.description"
                class="mt-1 text-xs text-muted-foreground leading-relaxed"
              >
                {{ toast.description }}
              </p>
            </div>
            <button
              class="flex h-5 w-5 shrink-0 items-center justify-center rounded text-muted-foreground/60 transition-colors hover:bg-white/10 hover:text-foreground active:scale-95"
              @click="removeToast(toast.id)"
            >
              <UIcon name="i-lucide-x" class="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
