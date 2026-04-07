<script setup lang="ts">
import type { Character } from "@/types/discover";
import CharacterContextMenu from "./CharacterContextMenu.vue";

const props = defineProps<{
  character: Character;
  index: number;
  selectMode: boolean;
  selected: boolean;
}>();

defineEmits<{
  select: [id: string];
  contextAction: [action: string, id: string];
}>();

function avatarSrc(): string {
  return props.character.avatar_thumbnail
    || props.character.avatar
    || `https://ui-avatars.com/api/?name=${encodeURIComponent(props.character.name)}&background=C9922E&color=fff&size=400`;
}
</script>

<template>
  <div
    class="group relative aspect-[3/4] cursor-pointer overflow-hidden rounded-xl shadow-[0_2px_12px_var(--color-foreground)/0.06] transition-all duration-300 animate-fade-in-up hover:scale-[1.02] hover:shadow-[0_8px_32px_var(--color-primary)/0.18]"
    :style="{ animationDelay: `${index * 40}ms` }"
    @click="selectMode ? $emit('select', character.id) : undefined"
  >
    <!-- Character portrait -->
    <img
      :src="avatarSrc()"
      :alt="character.name"
      class="absolute inset-0 h-full w-full object-cover transition-transform duration-700 group-hover:scale-[1.04]"
    />

    <!-- Gradient overlay -->
    <div class="absolute inset-0 bg-gradient-to-t from-black/85 via-black/20 to-transparent" />

    <!-- Select checkbox (top-left) -->
    <div v-if="selectMode" class="absolute left-3 top-3 z-10">
      <div
        class="flex h-5 w-5 items-center justify-center rounded border-2 transition-colors"
        :class="selected ? 'border-primary bg-primary' : 'border-white/60 bg-black/30 backdrop-blur-sm'"
      >
        <UIcon v-if="selected" name="i-lucide-check" class="h-3.5 w-3.5 text-primary-foreground" />
      </div>
    </div>

    <!-- Context menu (bottom-right, on hover) -->
    <div
      class="absolute bottom-3 right-3 z-10 text-white/80 opacity-0 transition-opacity duration-200 group-hover:opacity-100"
    >
      <CharacterContextMenu @action="$emit('contextAction', $event, character.id)" />
    </div>

    <!-- Bottom info overlay -->
    <div class="absolute bottom-0 left-0 right-0 p-4">
      <h3
        class="mb-0.5 font-cinzel text-base font-semibold text-white drop-shadow-lg"
        style="letter-spacing: 0.02em"
      >
        {{ character.name }}
      </h3>
      <p v-if="character.description" class="mb-2 line-clamp-3 text-[11px] leading-relaxed text-white/60">
        {{ character.description }}
      </p>
      <div v-if="character.tags?.length" class="flex flex-wrap gap-1.5">
        <span
          v-for="tag in character.tags.slice(0, 3)"
          :key="tag"
          class="rounded-full border border-white/10 bg-white/15 px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide text-white/80 backdrop-blur-sm"
        >
          {{ tag }}
        </span>
      </div>
    </div>
  </div>
</template>
