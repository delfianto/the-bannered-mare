import type { components } from "@/api/schema";
import { client } from "@/api/client";
import { usePaginatedList } from "@/composables/usePaginatedList";

export type ModelFamilyListItem = components["schemas"]["ModelFamilyListResponse"];

interface ModelFamilyFilters {
  name?: string;
  provider_type?: string;
}

interface UseModelFamiliesOptions {
  pageSize?: number;
  // Seed the first load from restored state (e.g. URL query on remount) so the
  // list comes back filtered/paged instead of resetting to page 1, no filters.
  initialFilters?: ModelFamilyFilters;
  initialPage?: number;
  autoLoad?: boolean;
}

export function useModelFamilies(options: UseModelFamiliesOptions = {}) {
  const { pageSize = 12, initialFilters = {}, initialPage = 1, autoLoad = true } = options;

  const list = usePaginatedList<ModelFamilyListItem, ModelFamilyFilters>(
    (page, limit, f) =>
      client.GET("/api/model-families", {
        params: {
          query: {
            page,
            limit,
            name__ilike: f.name || undefined,
            provider_type: f.provider_type || undefined,
          },
        },
      }),
    {
      pageSize,
      initialFilters,
      initialPage,
      autoLoad,
      errorContext: "Failed to load model families",
    },
  );

  return {
    families: list.items,
    loading: list.loading,
    error: list.error,
    page: list.page,
    hasMore: list.hasMore,
    total: list.total,
    totalPages: list.totalPages,
    loadPage: list.loadPage,
    search: (name: string) =>
      list.loadPage(1, { ...list.currentFilters.value, name: name || undefined }),
    filterByProviderType: (providerType: string | undefined) =>
      list.loadPage(1, { ...list.currentFilters.value, provider_type: providerType }),
  };
}
