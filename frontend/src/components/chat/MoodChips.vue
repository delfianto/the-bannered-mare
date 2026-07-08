<script setup lang="ts">
import type { MoodChip } from "@/types/chat";

defineProps<{
  chips: MoodChip[];
  disabled?: boolean;
}>();

const emit = defineEmits<{
  select: [chip: MoodChip];
}>();
</script>

<template>
  <div class="flex flex-wrap items-center justify-center gap-2 py-2">
    <button
      v-for="(chip, i) in chips"
      :key="chip.id"
      :disabled="disabled"
      class="animate-fade-in-up rounded-full border bg-base-300 px-4 py-1.5 text-xs font-medium tracking-wide text-base-content transition-all duration-200 hover:border-primary/40 hover:shadow-[0_0_12px_var(--color-primary)/0.15] disabled:cursor-not-allowed disabled:opacity-50"
      :style="{ animationDelay: `${i * 60}ms` }"
      @click="emit('select', chip)"
    >
      {{ chip.label }}
    </button>
  </div>
</template>
