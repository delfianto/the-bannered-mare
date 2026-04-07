<script setup lang="ts">
import type { Character } from "@/types/home";

const props = defineProps<{
  character: Character;
  index: number;
}>();

function formatCount(count: number): string {
  return count >= 1000 ? `${(count / 1000).toFixed(1)}k` : String(count);
}
</script>

<template>
  <div
    class="group relative aspect-[3/4] cursor-pointer overflow-hidden rounded-xl shadow-[0_2px_12px_var(--color-foreground)/0.06] transition-all duration-300 animate-fade-in-up hover:scale-[1.02] hover:shadow-[0_8px_32px_var(--color-primary)/0.18]"
    :style="{ animationDelay: `${index * 60}ms` }"
  >
    <!-- Character portrait -->
    <img
      :src="character.imageUrl"
      :alt="character.name"
      class="absolute inset-0 h-full w-full object-cover transition-transform duration-700 group-hover:scale-[1.04]"
    />

    <!-- Gradient overlay -->
    <div class="absolute inset-0 bg-gradient-to-t from-black/85 via-black/20 to-transparent" />

    <!-- Top badge — chat count -->
    <div
      class="absolute right-3 top-3 flex items-center gap-1 rounded-full bg-black/50 px-2 py-1 text-[11px] text-white/80 backdrop-blur-sm"
    >
      <span class="i-lucide-message-circle h-3 w-3" />
      {{ formatCount(character.chatCount) }}
    </div>

    <!-- Bottom info overlay -->
    <div class="absolute bottom-0 left-0 right-0 p-4">
      <h3
        class="mb-1.5 text-base font-semibold text-white drop-shadow-lg font-cinzel"
        style="letter-spacing: 0.02em"
      >
        {{ character.name }}
      </h3>
      <div class="flex flex-wrap gap-1.5">
        <span
          v-for="tag in character.tags"
          :key="tag"
          class="rounded-full border border-white/10 bg-white/15 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-white/80 backdrop-blur-sm"
        >
          {{ tag }}
        </span>
      </div>
      <p class="mt-2 text-[11px] text-white/50">by {{ character.creator }}</p>
    </div>
  </div>
</template>
