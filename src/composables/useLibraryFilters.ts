import { reactive, computed, type Ref } from "vue";
import type { Character, FilterState, SortOption, ViewMode } from "@/types/discover";

export function useLibraryFilters(characters: Ref<Character[]>) {
  const filters = reactive<FilterState>({
    search: "",
    category: "All",
    sort: "recent",
    viewMode: "grid",
  });

  const filtered = computed(() => {
    let result = [...characters.value];

    // Search filter
    if (filters.search) {
      const q = filters.search.toLowerCase();
      result = result.filter(
        (c) =>
          c.name.toLowerCase().includes(q) ||
          (c.tags ?? []).some((t) => t.toLowerCase().includes(q)) ||
          (c.description ?? "").toLowerCase().includes(q) ||
          (c.gender ?? "").toLowerCase().includes(q),
      );
    }

    // Category filter (by tags)
    if (filters.category !== "All") {
      result = result.filter((c) =>
        (c.tags ?? []).some((t) => t.toLowerCase() === filters.category.toLowerCase()),
      );
    }

    // Sort
    switch (filters.sort) {
      case "name-asc":
        result.sort((a, b) => a.name.localeCompare(b.name));
        break;
      case "name-desc":
        result.sort((a, b) => b.name.localeCompare(a.name));
        break;
      case "newest":
        result.sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        );
        break;
      // 'recent' keeps the default order (updated_at desc from API)
    }

    return result;
  });

  function setSearch(value: string) {
    filters.search = value;
  }

  function setCategory(value: string) {
    filters.category = value;
  }

  function setSort(value: SortOption) {
    filters.sort = value;
  }

  function setViewMode(value: ViewMode) {
    filters.viewMode = value;
  }

  return { filters, filtered, setSearch, setCategory, setSort, setViewMode };
}
