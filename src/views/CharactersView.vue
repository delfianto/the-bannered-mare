<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useCharacters } from "@/composables/useCharacters";
import { useLibraryFilters } from "@/composables/useLibraryFilters";
import { CATEGORIES } from "@/constants/discoverData";
import DiscoverHeader from "@/components/discover/DiscoverHeader.vue";
import FilterBar from "@/components/discover/FilterBar.vue";
import CategoryPills from "@/components/discover/CategoryPills.vue";
import BulkActionBar from "@/components/discover/BulkActionBar.vue";
import CharacterCard from "@/components/discover/CharacterCard.vue";
import CharacterListRow from "@/components/discover/CharacterListRow.vue";
import EmptyState from "@/components/discover/EmptyState.vue";

const router = useRouter();

// Fetch characters from API
const { characters, loading } = useCharacters({ pageSize: 50 });

// Filter the API data locally
const { filters, filtered, setSearch, setCategory, setSort, setViewMode } =
  useLibraryFilters(characters);

const selectMode = ref(false);
const selected = ref(new Set<string>());

const hasFilters = computed(
  () => filters.search !== "" || filters.category !== "All",
);

function toggleSelect(id: string) {
  const next = new Set(selected.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  selected.value = next;
}

function cancelSelect() {
  selectMode.value = false;
  selected.value = new Set();
}

function handleBulkExport() {
  console.log("Exporting:", [...selected.value]);
}

function handleBulkDelete() {
  console.log("Deleting:", [...selected.value]);
}

function handleContextAction(action: string, id: string) {
  if (action === "edit") router.push(`/characters/${id}/edit`);
  else console.log("Context action:", action, id);
}

function navigateToCreate() {
  router.push("/characters/create");
}
</script>

<template>
  <div class="space-y-8 px-12 py-8">
    <!-- Header -->
    <div class="animate-fade-in-up">
      <DiscoverHeader
        :character-count="filtered.length"
        @import="() => {}"
        @create-new="navigateToCreate"
      />
    </div>

    <!-- Filters -->
    <div class="animate-fade-in-up" style="animation-delay: 60ms">
      <FilterBar
        :search="filters.search"
        :sort="filters.sort"
        :view-mode="filters.viewMode"
        :select-mode="selectMode"
        @update:search="setSearch"
        @update:sort="setSort"
        @update:view-mode="setViewMode"
        @update:select-mode="(v: boolean) => (v ? (selectMode = true) : cancelSelect())"
      />
    </div>

    <!-- Category pills -->
    <div class="animate-fade-in-up" style="animation-delay: 120ms">
      <CategoryPills
        :active="filters.category"
        :categories="CATEGORIES"
        @change="setCategory"
      />
    </div>

    <!-- Bulk action bar -->
    <BulkActionBar
      :selected-count="selected.size"
      :visible="selectMode"
      @export="handleBulkExport"
      @delete="handleBulkDelete"
      @cancel="cancelSelect"
    />

    <!-- Loading -->
    <div v-if="loading && characters.length === 0" class="flex justify-center py-16">
      <UIcon name="i-lucide-loader-circle" class="h-6 w-6 animate-spin text-muted-foreground" />
    </div>

    <!-- Grid view -->
    <div
      v-else-if="filtered.length > 0 && filters.viewMode === 'grid'"
      class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4"
    >
      <CharacterCard
        v-for="(character, i) in filtered"
        :key="character.id"
        :character="character"
        :index="i"
        :select-mode="selectMode"
        :selected="selected.has(character.id)"
        @select="toggleSelect"
        @context-action="handleContextAction"
      />
    </div>

    <!-- List view -->
    <div
      v-else-if="filtered.length > 0 && filters.viewMode === 'list'"
      class="grid grid-cols-1 gap-3 lg:grid-cols-2"
    >
      <CharacterListRow
        v-for="(character, i) in filtered"
        :key="character.id"
        :character="character"
        :index="i"
        :select-mode="selectMode"
        :selected="selected.has(character.id)"
        @select="toggleSelect"
        @context-action="handleContextAction"
      />
    </div>

    <!-- Empty state -->
    <EmptyState
      v-if="!loading && filtered.length === 0"
      :has-filters="hasFilters"
      @create-new="navigateToCreate"
    />
  </div>
</template>
