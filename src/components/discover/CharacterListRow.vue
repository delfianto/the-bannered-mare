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
    router.push(`/characters/${props.character.id}/edit`);
  }
}

function avatarSrc(): string {
  return (
    props.character.avatar_thumbnail ||
    props.character.avatar ||
    `https://ui-avatars.com/api/?name=${encodeURIComponent(props.character.name)}&background=C9922E&color=fff&size=200`
  );
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
</script>

<template>
  <div
    class="group flex animate-fade-in-up items-center gap-4 rounded-xl border bg-card/50 px-4 py-3 transition-all duration-200 hover:bg-muted/40 hover:shadow-[0_4px_16px_var(--color-primary)/0.08]"
    :style="{ animationDelay: `${index * 40}ms` }"
    @click="handleClick"
  >
    <!-- Checkbox -->
    <div v-if="selectMode" class="shrink-0">
      <div
        class="flex size-5 items-center justify-center rounded border-2 transition-colors"
        :class="selected ? 'border-primary bg-primary' : 'border-border bg-muted/40'"
      >
        <UIcon v-if="selected" name="i-lucide-check" class="size-3.5 text-primary-foreground" />
      </div>
    </div>

    <!-- Thumbnail -->
    <div class="h-20 w-[60px] shrink-0 overflow-hidden rounded-lg">
      <img :src="avatarSrc()" :alt="character.name" class="size-full object-cover" />
    </div>

    <!-- Info -->
    <div class="min-w-0 flex-1">
      <h3
        class="truncate font-cinzel text-sm font-semibold text-foreground"
        style="letter-spacing: 0.02em"
      >
        {{ character.name }}
      </h3>
      <p
        v-if="character.creator_notes || character.description"
        class="mt-1 line-clamp-3 text-xs leading-relaxed text-muted-foreground/70"
      >
        {{ character.creator_notes || character.description }}
      </p>
      <div class="mt-1.5 flex flex-wrap items-center gap-1.5">
        <span
          v-for="tag in (character.tags ?? []).slice(0, 3)"
          :key="tag"
          class="rounded-full bg-accent px-2 py-0.5 text-[9px] font-medium tracking-wide text-foreground uppercase"
        >
          {{ tag }}
        </span>
        <span v-if="character.gender" class="text-[10px] text-muted-foreground">
          {{ character.gender }}
        </span>
      </div>
    </div>

    <!-- Last updated -->
    <div class="hidden shrink-0 text-right sm:block">
      <p class="text-xs text-muted-foreground">{{ timeAgo(character.updated_at) }}</p>
    </div>

    <!-- Context menu -->
    <div
      class="shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
    >
      <CharacterContextMenu @action="$emit('contextAction', $event, character.id)" />
    </div>
  </div>
</template>
