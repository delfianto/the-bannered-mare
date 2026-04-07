<script setup lang="ts">
import { ref, computed } from "vue";
import type { SortOption, SourceFilter, ViewMode } from "@/types/discover";
import { SORT_OPTIONS, SOURCE_OPTIONS } from "@/constants/discoverData";

const props = defineProps<{
  search: string;
  source: SourceFilter;
  sort: SortOption;
  viewMode: ViewMode;
  selectMode: boolean;
}>();

const emit = defineEmits<{
  "update:search": [value: string];
  "update:source": [value: SourceFilter];
  "update:sort": [value: SortOption];
  "update:viewMode": [value: ViewMode];
  "update:selectMode": [value: boolean];
}>();

const searchFocused = ref(false);

const sourceItems = SOURCE_OPTIONS.map((o) => ({ label: o.label, value: o.value }));
const sortItems = SORT_OPTIONS.map((o) => ({ label: o.label, value: o.value }));

const selectedSource = computed({
  get: () => props.source,
  set: (v: SourceFilter) => emit("update:source", v),
});

const selectedSort = computed({
  get: () => props.sort,
  set: (v: SortOption) => emit("update:sort", v),
});

function sourceLabel(value: SourceFilter): string {
  return SOURCE_OPTIONS.find((o) => o.value === value)?.label ?? "All Sources";
}

function sortLabel(value: SortOption): string {
  return SORT_OPTIONS.find((o) => o.value === value)?.label ?? "Recently Used";
}
</script>

<template>
  <div class="relative z-30 flex flex-wrap items-center gap-2">
    <!-- Search -->
    <div class="relative min-w-[200px] flex-1">
      <div
        class="flex items-center gap-2 rounded-lg border px-3 transition-all duration-200"
        :class="
          searchFocused
            ? 'border-primary/40 bg-background shadow-[0_0_0_3px_var(--color-primary)/0.08]'
            : 'border-border bg-muted/40 hover:border-muted-foreground/30'
        "
      >
        <UIcon
          name="i-lucide-search"
          class="h-4 w-4 shrink-0 transition-colors"
          :class="searchFocused ? 'text-primary' : 'text-muted-foreground'"
        />
        <input
          type="text"
          :value="search"
          placeholder="Search characters..."
          class="h-9 flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
          @input="emit('update:search', ($event.target as HTMLInputElement).value)"
          @focus="searchFocused = true"
          @blur="searchFocused = false"
        />
      </div>
    </div>

    <!-- Source dropdown -->
    <USelectMenu
      v-model="selectedSource"
      :items="sourceItems"
      value-key="value"
      :search-input="false"
      :ui="{
        base: 'border-none shadow-none ring-0 outline-none p-0 bg-transparent',
        content: 'border border-[var(--border)] bg-[var(--card)] ring-0 outline-none shadow-lg',
        item: 'text-muted-foreground data-highlighted:text-foreground data-highlighted:bg-[var(--accent)]',
      }"
    >
      <button
        class="flex h-9 items-center gap-1.5 rounded-lg border border-[var(--border)] bg-muted/40 px-3 text-sm text-muted-foreground transition-all hover:border-muted-foreground/30 outline-none"
      >
        <UIcon name="i-lucide-filter" class="h-3.5 w-3.5 text-muted-foreground" />
        {{ sourceLabel(source) }}
        <UIcon name="i-lucide-chevron-down" class="h-3.5 w-3.5 text-muted-foreground" />
      </button>
    </USelectMenu>

    <!-- Sort dropdown -->
    <USelectMenu
      v-model="selectedSort"
      :items="sortItems"
      value-key="value"
      :search-input="false"
      :ui="{
        base: 'border-none shadow-none ring-0 outline-none p-0 bg-transparent',
        content: 'border border-[var(--border)] bg-[var(--card)] ring-0 outline-none shadow-lg',
        item: 'text-muted-foreground data-highlighted:text-foreground data-highlighted:bg-[var(--accent)]',
      }"
    >
      <button
        class="flex h-9 items-center gap-1.5 rounded-lg border border-[var(--border)] bg-muted/40 px-3 text-sm text-muted-foreground transition-all hover:border-muted-foreground/30 outline-none"
      >
        <UIcon name="i-lucide-arrow-up-down" class="h-3.5 w-3.5 text-muted-foreground" />
        {{ sortLabel(sort) }}
        <UIcon name="i-lucide-chevron-down" class="h-3.5 w-3.5 text-muted-foreground" />
      </button>
    </USelectMenu>

    <!-- View mode toggle -->
    <div class="flex h-9 items-center rounded-lg border border-border bg-muted/40">
      <button
        class="flex h-full items-center px-2.5 transition-colors"
        :class="viewMode === 'grid' ? 'text-primary' : 'text-muted-foreground hover:text-foreground'"
        @click="emit('update:viewMode', 'grid')"
      >
        <UIcon name="i-lucide-layout-grid" class="h-4 w-4" />
      </button>
      <div class="h-4 w-px bg-border" />
      <button
        class="flex h-full items-center px-2.5 transition-colors"
        :class="viewMode === 'list' ? 'text-primary' : 'text-muted-foreground hover:text-foreground'"
        @click="emit('update:viewMode', 'list')"
      >
        <UIcon name="i-lucide-list" class="h-4 w-4" />
      </button>
    </div>

    <!-- Select mode toggle -->
    <button
      class="flex h-9 items-center gap-1.5 rounded-lg border px-3 text-sm transition-colors"
      :class="
        selectMode
          ? 'border-primary/40 bg-primary/10 text-primary'
          : 'border-border bg-muted/40 text-muted-foreground hover:text-foreground'
      "
      @click="emit('update:selectMode', !selectMode)"
    >
      <UIcon name="i-lucide-check-square" class="h-4 w-4" />
      Select
    </button>
  </div>
</template>
