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
        border: "border-emerald-500/20 bg-emerald-50 dark:bg-emerald-950/85",
        text: "text-emerald-900 dark:text-emerald-100",
        desc: "text-emerald-700 dark:text-emerald-300",
        icon: "text-emerald-600/90 dark:text-emerald-400",
      };
    case "error":
      return {
        border: "border-destructive/20 bg-red-50 dark:bg-red-950/85",
        text: "text-red-900 dark:text-red-100",
        desc: "text-red-700 dark:text-red-300",
        icon: "text-red-600/90 dark:text-red-400",
      };
    case "warning":
      return {
        border: "border-amber-500/20 bg-amber-50 dark:bg-amber-950/85",
        text: "text-amber-900 dark:text-amber-100",
        desc: "text-amber-700 dark:text-amber-300",
        icon: "text-amber-600/90 dark:text-amber-400",
      };
    default:
      return {
        border: "border-stone-200 dark:border-white/10 bg-white dark:bg-stone-900/85",
        text: "text-stone-900 dark:text-stone-100",
        desc: "text-stone-600 dark:text-stone-400",
        icon: "text-primary",
      };
  }
};
</script>

<template>
  <Teleport to="body">
    <div
      class="pointer-events-none fixed top-0 right-0 z-[100] flex w-full max-w-sm flex-col gap-3 p-4 sm:p-6"
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
          :class="[getTypeClasses(toast.type).border, getTypeClasses(toast.type).text]"
        >
          <div class="flex w-full items-start gap-3">
            <UIcon
              :name="getIcon(toast.type)"
              class="mt-0.5 size-5 shrink-0"
              :class="getTypeClasses(toast.type).icon"
            />
            <div class="min-w-0 flex-1">
              <h4 class="font-cinzel text-xs font-semibold tracking-wider text-current uppercase">
                {{ toast.title }}
              </h4>
              <p
                v-if="toast.description"
                class="mt-1 text-xs leading-relaxed"
                :class="getTypeClasses(toast.type).desc"
              >
                {{ toast.description }}
              </p>
            </div>
            <button
              class="flex size-5 shrink-0 items-center justify-center rounded text-current/60 transition-colors hover:bg-current/10 hover:text-current active:scale-95"
              @click="removeToast(toast.id)"
            >
              <UIcon name="i-lucide-x" class="size-3.5" />
            </button>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
