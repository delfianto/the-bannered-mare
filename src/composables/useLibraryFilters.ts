import { reactive, computed } from "vue";
import type {
  LibraryCharacter,
  FilterState,
  SortOption,
  SourceFilter,
  ViewMode,
} from "@/types/discover";

export function useLibraryFilters(characters: LibraryCharacter[]) {
  const filters = reactive<FilterState>({
    search: "",
    category: "All",
    source: "all",
    sort: "recent",
    viewMode: "grid",
  });

  const filtered = computed(() => {
    let result = [...characters];

    // Search filter
    if (filters.search) {
      const q = filters.search.toLowerCase();
      result = result.filter(
        (c) =>
          c.name.toLowerCase().includes(q) ||
          c.tags.some((t) => t.toLowerCase().includes(q)) ||
          c.description.toLowerCase().includes(q) ||
          c.species.toLowerCase().includes(q),
      );
    }

    // Category filter
    if (filters.category !== "All") {
      result = result.filter((c) =>
        c.tags.some((t) => t.toLowerCase() === filters.category.toLowerCase()),
      );
    }

    // Source filter
    if (filters.source !== "all") {
      result = result.filter((c) => c.source === filters.source);
    }

    // Sort
    switch (filters.sort) {
      case "name-asc":
        result.sort((a, b) => a.name.localeCompare(b.name));
        break;
      case "name-desc":
        result.sort((a, b) => b.name.localeCompare(a.name));
        break;
      case "sessions":
        result.sort((a, b) => b.sessionCount - a.sessionCount);
        break;
      case "newest":
        result.sort(
          (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
        );
        break;
      // 'recent' keeps the default order
    }

    return result;
  });

  function setSearch(value: string) {
    filters.search = value;
  }

  function setCategory(value: string) {
    filters.category = value;
  }

  function setSource(value: SourceFilter) {
    filters.source = value;
  }

  function setSort(value: SortOption) {
    filters.sort = value;
  }

  function setViewMode(value: ViewMode) {
    filters.viewMode = value;
  }

  return { filters, filtered, setSearch, setCategory, setSource, setSort, setViewMode };
}
