<script setup lang="ts">
import { useRouter } from "vue-router";
import type { Character } from "@/types/discover";
import CharacterContextMenu from "./CharacterContextMenu.vue";

const props = defineProps<{
  character: Character;
  index: number;
  selectMode: boolean;
  selected: boolean;
}>();

const emit = defineEmits<{
  select: [id: string];
  contextAction: [action: string, id: string];
}>();

const router = useRouter();

function handleClick() {
  if (props.selectMode) {
    emit("select", props.character.id);
  } else {
    router.push(`/characters/${props.character.id}`);
  }
}

function avatarSrc(): string {
  // Large tier: full 3:4 portrait shown at ~card width. The large avatar keeps
  // it sharp while being far lighter than serving the original to a whole grid.
  return (
    props.character.avatar_large ||
    props.character.avatar ||
    `https://ui-avatars.com/api/?name=${encodeURIComponent(props.character.name)}&background=C9922E&color=fff&size=400`
  );
}
</script>

<template>
  <div
    class="group relative aspect-3/4 animate-fade-in-up cursor-pointer overflow-hidden rounded-xl shadow-[0_2px_12px_var(--color-foreground)/0.06] transition-all duration-300 hover:scale-[1.02] hover:shadow-[0_8px_32px_var(--color-primary)/0.18]"
    :style="{ animationDelay: `${index * 40}ms` }"
    @click="handleClick"
  >
    <!-- Character portrait -->
    <img
      :src="avatarSrc()"
      :alt="character.name"
      class="absolute inset-0 size-full object-cover transition-transform duration-700 group-hover:scale-[1.04]"
    />

    <!-- Gradient overlay -->
    <div class="absolute inset-0 bg-linear-to-t from-black/85 via-black/20 to-transparent" />

    <!-- Select checkbox (top-left) -->
    <div v-if="selectMode" class="absolute top-3 left-3 z-10">
      <div
        class="flex size-5 items-center justify-center rounded border-2 transition-colors"
        :class="
          selected ? 'border-primary bg-primary' : 'border-white/60 bg-black/30 backdrop-blur-sm'
        "
      >
        <AppIcon v-if="selected" name="i-lucide-check" class="size-3.5 text-primary-content" />
      </div>
    </div>

    <!-- Context menu (bottom-right, on hover) -->
    <div
      class="absolute right-3 bottom-3 z-10 text-white/80 opacity-0 transition-opacity duration-200 group-hover:opacity-100"
    >
      <CharacterContextMenu @action="$emit('contextAction', $event, character.id)" />
    </div>

    <!-- Bottom info overlay -->
    <div class="absolute inset-x-0 bottom-0 p-4">
      <h3
        class="mb-0.5 font-cinzel text-base font-semibold text-white drop-shadow-lg"
        style="letter-spacing: 0.02em"
      >
        {{ character.name }}
      </h3>
      <p
        v-if="character.creator_notes || character.description"
        class="mb-2 line-clamp-3 text-[11px] leading-relaxed text-white/60"
      >
        {{ character.creator_notes || character.description }}
      </p>
      <div v-if="character.tags?.length" class="flex flex-wrap gap-1.5">
        <span
          v-for="tag in character.tags.slice(0, 3)"
          :key="tag"
          class="rounded-full border border-white/10 bg-white/15 px-2 py-0.5 text-[9px] font-medium tracking-wide text-white/80 uppercase backdrop-blur-sm"
        >
          {{ tag }}
        </span>
      </div>
    </div>
  </div>
</template>
