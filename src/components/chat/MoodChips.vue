<script setup lang="ts">
import type { MoodChip } from "@/types/chat";

defineProps<{
  chips: MoodChip[];
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
      class="rounded-full border border-border bg-accent px-4 py-1.5 text-xs font-medium tracking-wide text-accent-foreground transition-all duration-200 animate-fade-in-up hover:border-primary/40 hover:shadow-[0_0_12px_var(--color-primary)/0.15]"
      :style="{ animationDelay: `${i * 60}ms` }"
      @click="emit('select', chip)"
    >
      {{ chip.label }}
    </button>
  </div>
</template>
