<script setup lang="ts">
import type { LibraryCharacter } from "@/types/discover";
import CharacterContextMenu from "./CharacterContextMenu.vue";

const props = defineProps<{
  character: LibraryCharacter;
  index: number;
  selectMode: boolean;
  selected: boolean;
}>();

defineEmits<{
  select: [id: string];
  contextAction: [action: string, id: string];
}>();

function formatCount(count: number): string {
  return count >= 1000 ? `${(count / 1000).toFixed(1)}k` : String(count);
}
</script>

<template>
  <div
    class="group flex items-center gap-4 rounded-xl border border-border bg-card/50 px-4 py-3 transition-all duration-200 animate-fade-in-up hover:bg-muted/40 hover:shadow-[0_4px_16px_var(--color-primary)/0.08]"
    :style="{ animationDelay: `${index * 40}ms` }"
    @click="selectMode ? $emit('select', character.id) : undefined"
  >
    <!-- Checkbox -->
    <div v-if="selectMode" class="shrink-0">
      <div
        class="flex h-5 w-5 items-center justify-center rounded border-2 transition-colors"
        :class="
          selected
            ? 'border-primary bg-primary'
            : 'border-border bg-muted/40'
        "
      >
        <UIcon
          v-if="selected"
          name="i-lucide-check"
          class="h-3.5 w-3.5 text-primary-foreground"
        />
      </div>
    </div>

    <!-- Thumbnail -->
    <div class="h-20 w-[60px] shrink-0 overflow-hidden rounded-lg">
      <img
        :src="character.imageUrl"
        :alt="character.name"
        class="h-full w-full object-cover"
      />
    </div>

    <!-- Info -->
    <div class="min-w-0 flex-1">
      <h3
        class="truncate font-cinzel text-sm font-semibold text-foreground"
        style="letter-spacing: 0.02em"
      >
        {{ character.name }}
      </h3>
      <p class="truncate text-xs text-muted-foreground">{{ character.title }}</p>
      <p class="mt-1 line-clamp-1 text-xs text-muted-foreground/70">
        {{ character.description }}
      </p>
      <div class="mt-1.5 flex flex-wrap items-center gap-1.5">
        <span
          v-for="tag in character.tags.slice(0, 3)"
          :key="tag"
          class="rounded-full bg-accent px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide text-foreground"
        >
          {{ tag }}
        </span>
        <span class="text-[10px] text-muted-foreground">
          {{ character.species }} &middot; {{ formatCount(character.chatCount) }} chats
          &middot; {{ character.sessionCount }} sessions
        </span>
      </div>
    </div>

    <!-- Source badge -->
    <div class="hidden shrink-0 sm:block">
      <span
        class="rounded-full px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide"
        :class="
          character.source === 'created'
            ? 'bg-primary/15 text-primary'
            : 'bg-accent text-muted-foreground'
        "
      >
        {{ character.source === "created" ? "Created" : "Imported" }}
      </span>
    </div>

    <!-- Last used -->
    <div class="hidden shrink-0 text-right sm:block">
      <p class="text-xs text-muted-foreground">{{ character.lastUsed }}</p>
    </div>

    <!-- Context menu -->
    <div class="shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100">
      <CharacterContextMenu
        @action="$emit('contextAction', $event, character.id)"
      />
    </div>
  </div>
</template>
