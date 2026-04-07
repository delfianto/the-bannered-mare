<script setup lang="ts">
import { ref, computed } from "vue";
import type { Character } from "@/types/home";
import CharacterCard from "./CharacterCard.vue";

const props = defineProps<{
  characters: Character[];
  categories: string[];
}>();

const activeCategory = ref("All");

const filtered = computed(() => {
  if (activeCategory.value === "All") return props.characters;
  return props.characters.filter((c) =>
    c.tags.some((t) => t.toLowerCase().includes(activeCategory.value.toLowerCase())),
  );
});
</script>

<template>
  <section>
    <div class="mb-4 flex items-center justify-between">
      <h2 class="font-cinzel text-lg font-semibold tracking-wide text-foreground">
        Discover Characters
      </h2>
    </div>

    <!-- Category pills -->
    <div class="scrollbar-hide mb-5 flex items-center gap-2 overflow-x-auto pb-1">
      <button
        v-for="cat in categories"
        :key="cat"
        class="relative whitespace-nowrap rounded-full px-3.5 py-1.5 text-xs font-medium tracking-wide transition-colors duration-200"
        :class="
          activeCategory === cat
            ? 'bg-primary text-primary-foreground'
            : 'border border-border text-muted-foreground hover:border-muted-foreground/40 hover:text-foreground'
        "
        @click="activeCategory = cat"
      >
        {{ cat }}
      </button>
    </div>

    <!-- Character Grid -->
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <CharacterCard
        v-for="(character, i) in filtered"
        :key="character.id"
        :character="character"
        :index="i"
      />
    </div>
  </section>
</template>
