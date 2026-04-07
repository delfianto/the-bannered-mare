<script setup lang="ts">
import type { components } from "@/api/schema";

type Character = components["schemas"]["CharacterResponse"];

const props = defineProps<{
  character: Character;
  index: number;
}>();

function avatarSrc(): string {
  return props.character.avatar
    || `https://ui-avatars.com/api/?name=${encodeURIComponent(props.character.name)}&background=C9922E&color=fff&size=400`;
}
</script>

<template>
  <RouterLink
    :to="{ name: 'character-detail', params: { id: character.id } }"
    class="group relative aspect-[3/4] cursor-pointer overflow-hidden rounded-xl shadow-[0_2px_12px_var(--color-foreground)/0.06] transition-all duration-300 animate-fade-in-up hover:scale-[1.02] hover:shadow-[0_8px_32px_var(--color-primary)/0.18]"
    :style="{ animationDelay: `${index * 60}ms` }"
  >
    <!-- Character portrait -->
    <img
      :src="avatarSrc()"
      :alt="character.name"
      class="absolute inset-0 h-full w-full object-cover transition-transform duration-700 group-hover:scale-[1.04]"
    />

    <!-- Gradient overlay -->
    <div class="absolute inset-0 bg-gradient-to-t from-black/85 via-black/20 to-transparent" />

    <!-- Bottom info overlay -->
    <div class="absolute bottom-0 left-0 right-0 p-4">
      <h3
        class="mb-1.5 font-cinzel text-base font-semibold text-white drop-shadow-lg"
        style="letter-spacing: 0.02em"
      >
        {{ character.name }}
      </h3>
      <div v-if="character.tags?.length" class="flex flex-wrap gap-1.5">
        <span
          v-for="tag in character.tags.slice(0, 3)"
          :key="tag"
          class="rounded-full border border-white/10 bg-white/15 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-white/80 backdrop-blur-sm"
        >
          {{ tag }}
        </span>
      </div>
      <p v-if="character.creator" class="mt-2 text-[11px] text-white/50">
        by {{ character.creator }}
      </p>
    </div>
  </RouterLink>
</template>
