import type { components } from "@/api/schema";
import { client } from "@/api/client";
import { usePaginatedList } from "@/composables/usePaginatedList";

export type ModelListItem = components["schemas"]["ModelListResponse"];

interface ModelFilters {
  name?: string;
  provider_id?: string;
  model_family_id?: string;
  enabled?: boolean;
}

interface UseModelsOptions {
  pageSize?: number;
  // Seed the first load from restored state (e.g. URL query on remount) so the
  // list comes back filtered/paged instead of resetting to page 1, no filters.
  initialFilters?: ModelFilters;
  initialPage?: number;
  autoLoad?: boolean;
}

export function useModels(options: UseModelsOptions = {}) {
  const { pageSize = 12, initialFilters = {}, initialPage = 1, autoLoad = true } = options;

  const list = usePaginatedList<ModelListItem, ModelFilters>(
    (page, limit, f) =>
      client.GET("/api/models", {
        params: {
          query: {
            page,
            limit,
            name__ilike: f.name || undefined,
            provider_id: f.provider_id || undefined,
            model_family_id: f.model_family_id || undefined,
            enabled: f.enabled,
          },
        },
      }),
    { pageSize, initialFilters, initialPage, autoLoad, errorContext: "Failed to load models" },
  );

  const filter = (patch: Partial<ModelFilters>) =>
    list.loadPage(1, { ...list.currentFilters.value, ...patch });

  return {
    models: list.items,
    loading: list.loading,
    error: list.error,
    page: list.page,
    hasMore: list.hasMore,
    total: list.total,
    totalPages: list.totalPages,
    loadPage: list.loadPage,
    search: (name: string) => filter({ name: name || undefined }),
    // `provider_id` now means "has a route on that provider" — the server resolves
    // it against each registry's routes, so the client just forwards the id.
    filterByProvider: (providerId: string | undefined) => filter({ provider_id: providerId }),
    filterByFamily: (familyId: string | undefined) => filter({ model_family_id: familyId }),
    filterByStatus: (enabled: boolean | undefined) => filter({ enabled }),
  };
}
