<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useLibraryFilters } from "@/composables/useLibraryFilters";
import { LIBRARY_CHARACTERS, CATEGORIES } from "@/constants/discoverData";
import DiscoverHeader from "@/components/discover/DiscoverHeader.vue";
import FilterBar from "@/components/discover/FilterBar.vue";
import CategoryPills from "@/components/discover/CategoryPills.vue";
import BulkActionBar from "@/components/discover/BulkActionBar.vue";
import CharacterCard from "@/components/discover/CharacterCard.vue";
import CharacterListRow from "@/components/discover/CharacterListRow.vue";
import EmptyState from "@/components/discover/EmptyState.vue";

const router = useRouter();
const { filters, filtered, setSearch, setCategory, setSource, setSort, setViewMode } =
  useLibraryFilters(LIBRARY_CHARACTERS);

const selectMode = ref(false);
const selected = ref(new Set<string>());

const hasFilters = computed(
  () =>
    filters.search !== "" ||
    filters.category !== "All" ||
    filters.source !== "all",
);

function toggleSelect(id: string) {
  const next = new Set(selected.value);
  if (next.has(id)) {
    next.delete(id);
  } else {
    next.add(id);
  }
  selected.value = next;
}

function cancelSelect() {
  selectMode.value = false;
  selected.value = new Set();
}

function handleBulkExport() {
  // TODO: implement export
  console.log("Exporting:", [...selected.value]);
}

function handleBulkDelete() {
  // TODO: implement delete
  console.log("Deleting:", [...selected.value]);
}

function handleContextAction(action: string, id: string) {
  console.log("Context action:", action, id);
}

function navigateToCreate() {
  router.push("/characters/create");
}
</script>

<template>
  <div class="space-y-8 px-8 py-8">
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
        :source="filters.source"
        :sort="filters.sort"
        :view-mode="filters.viewMode"
        :select-mode="selectMode"
        @update:search="setSearch"
        @update:source="setSource"
        @update:sort="setSort"
        @update:view-mode="setViewMode"
        @update:select-mode="(v) => (v ? (selectMode = true) : cancelSelect())"
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

    <!-- Grid view -->
    <div
      v-if="filtered.length > 0 && filters.viewMode === 'grid'"
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
      class="space-y-2"
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
      v-if="filtered.length === 0"
      :has-filters="hasFilters"
      @create-new="navigateToCreate"
    />
  </div>
</template>
