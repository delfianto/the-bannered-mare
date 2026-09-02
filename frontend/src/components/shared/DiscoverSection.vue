<script setup lang="ts">
import { ref, computed } from "vue";
import type { components } from "@/api/schema";
import CharacterCard from "./HomeCharacterCard.vue";

type Character = components["schemas"]["CharacterResponse"];

const props = defineProps<{
  characters: Character[];
  categories: string[];
  loading?: boolean;
  // When set, renders a "Browse all" link to the full library (home preview).
  browseAllTo?: string;
}>();

const activeCategory = ref("All");

const filtered = computed(() => {
  if (activeCategory.value === "All") return props.characters;
  return props.characters.filter((c) =>
    (c.tags ?? []).some((t) => t.toLowerCase().includes(activeCategory.value.toLowerCase())),
  );
});
</script>

<template>
  <section>
    <div class="mb-6 flex flex-col gap-4 border-b pb-4 md:flex-row md:items-end md:justify-between">
      <div>
        <p class="mb-2 text-2xs font-semibold tracking-[0.2em] text-primary uppercase">The cast</p>
        <h2 class="font-story text-2xl font-semibold tracking-wide text-foreground">
          {{ $t("home.discoverCharacters") }}
        </h2>
      </div>
      <div class="flex min-w-0 items-center gap-5">
        <div class="scrollbar-hide flex min-w-0 items-center gap-5 overflow-x-auto">
          <button
            v-for="cat in categories.slice(0, 5)"
            :key="cat"
            class="shrink-0 text-2xs font-semibold tracking-wider uppercase transition-colors"
            :class="
              activeCategory === cat
                ? 'text-primary'
                : 'text-muted-foreground hover:text-foreground'
            "
            @click="activeCategory = cat"
          >
            {{ cat }}
          </button>
        </div>
        <RouterLink
          v-if="browseAllTo"
          :to="browseAllTo"
          class="inline-flex shrink-0 items-center gap-1 text-2xs font-semibold tracking-wider text-muted-foreground uppercase transition-colors hover:text-primary"
        >
          {{ $t("home.browseAll") }}
          <AppIcon name="i-lucide-arrow-right" class="size-3.5" />
        </RouterLink>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-8">
      <AppIcon name="i-lucide-loader-circle" class="size-5 animate-spin text-muted-foreground" />
    </div>

    <!-- Character Grid -->
    <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 lg:grid-rows-2">
      <CharacterCard
        v-for="(character, i) in filtered"
        :key="character.id"
        :character="character"
        :index="i"
        :featured="i === 0"
        :class="i > 4 ? 'lg:hidden' : ''"
      />
    </div>
  </section>
</template>
