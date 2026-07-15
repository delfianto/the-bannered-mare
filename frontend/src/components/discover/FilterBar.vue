<script setup lang="ts">
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import type { SortOption, ViewMode } from "@/types/discover";

const { t } = useI18n();

const props = defineProps<{
  search: string;
  sort: SortOption;
  viewMode: ViewMode;
  selectMode: boolean;
}>();

const emit = defineEmits<{
  "update:search": [value: string];
  "update:sort": [value: SortOption];
  "update:viewMode": [value: ViewMode];
  "update:selectMode": [value: boolean];
}>();

const searchFocused = ref(false);

const sortKeyMap: Record<string, string> = {
  recent: "characters.sort.recent",
  "name-asc": "characters.sort.nameAsc",
  "name-desc": "characters.sort.nameDesc",
  newest: "characters.sort.newest",
};

const sortItems = computed(() => [
  { label: t("characters.sort.recent"), value: "recent" as const },
  { label: t("characters.sort.nameAsc"), value: "name-asc" as const },
  { label: t("characters.sort.nameDesc"), value: "name-desc" as const },
  { label: t("characters.sort.newest"), value: "newest" as const },
]);

const selectedSort = computed({
  get: () => props.sort,
  set: (v: SortOption) => emit("update:sort", v),
});

function sortLabel(value: SortOption): string {
  return t(sortKeyMap[value] ?? "characters.sort.recent");
}
</script>

<template>
  <div class="relative z-30 flex flex-wrap items-center gap-2">
    <!-- Search -->
    <div class="relative min-w-50 flex-1">
      <div
        class="flex items-center gap-2 rounded-lg border px-3 transition-all duration-200"
        :class="
          searchFocused
            ? 'border-primary/40 bg-base-100 focus-ring'
            : 'border-border bg-base-300/40 hover:border-muted-foreground/30'
        "
      >
        <AppIcon
          name="i-lucide-search"
          class="size-4 shrink-0 transition-colors"
          :class="searchFocused ? 'text-primary' : 'text-muted-foreground'"
        />
        <input
          type="text"
          :value="search"
          :placeholder="$t('characters.searchPlaceholder')"
          aria-label="Search characters"
          autocomplete="off"
          class="h-9 flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
          @input="emit('update:search', ($event.target as HTMLInputElement).value)"
          @focus="searchFocused = true"
          @blur="searchFocused = false"
        />
      </div>
    </div>

    <!-- Sort dropdown -->
    <SelectMenu v-model="selectedSort" :items="sortItems" value-key="value" :search-input="false">
      <button
        class="flex h-9 items-center gap-1.5 rounded-lg border bg-base-300/40 px-3 text-sm text-muted-foreground transition-all outline-none hover:border-muted-foreground/30"
      >
        <AppIcon name="i-lucide-arrow-up-down" class="size-3.5" />
        {{ sortLabel(sort) }}
        <AppIcon name="i-lucide-chevron-down" class="size-3.5" />
      </button>
    </SelectMenu>

    <!-- View mode toggle -->
    <div class="flex h-9 items-center rounded-lg border bg-base-300/40">
      <button
        :aria-label="$t('characters.view.grid')"
        class="flex h-full items-center px-2.5 transition-colors"
        :class="
          viewMode === 'grid' ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
        "
        @click="emit('update:viewMode', 'grid')"
      >
        <AppIcon name="i-lucide-layout-grid" class="size-4" />
      </button>
      <div class="h-4 w-px bg-border" />
      <button
        :aria-label="$t('characters.view.list')"
        class="flex h-full items-center px-2.5 transition-colors"
        :class="
          viewMode === 'list' ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
        "
        @click="emit('update:viewMode', 'list')"
      >
        <AppIcon name="i-lucide-list" class="size-4" />
      </button>
    </div>

    <!-- Select mode toggle -->
    <button
      class="flex h-9 items-center gap-1.5 rounded-lg border px-3 text-sm transition-colors"
      :class="
        selectMode
          ? 'border-primary/40 bg-primary/10 text-primary'
          : 'border-border bg-base-300/40 text-muted-foreground hover:text-foreground'
      "
      @click="emit('update:selectMode', !selectMode)"
    >
      <AppIcon name="i-lucide-check-square" class="size-4" />
      {{ $t("characters.view.select") }}
    </button>
  </div>
</template>
