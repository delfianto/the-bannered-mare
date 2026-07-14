import type { components } from "@/api/schema";
import { client } from "@/api/client";
import { usePaginatedList } from "@/composables/usePaginatedList";

export type PromptFragment = components["schemas"]["FragmentResponse"];

interface UseFragmentsOptions {
  pageSize?: number;
}

interface FragmentFilters {
  fragment_type?: string;
  is_global?: boolean;
  unused_only?: boolean;
}

export function usePromptFragments(options: UseFragmentsOptions = {}) {
  const { pageSize = 20 } = options;

  const list = usePaginatedList<PromptFragment, FragmentFilters>(
    (page, limit, f) =>
      client.GET("/api/prompt-fragments/", {
        params: {
          query: {
            page,
            limit,
            fragment_type: f.fragment_type,
            is_global: f.is_global,
            unused_only: f.unused_only,
          },
        },
      }),
    { pageSize, errorContext: "Failed to load prompt fragments" },
  );

  return {
    fragments: list.items,
    loading: list.loading,
    error: list.error,
    page: list.page,
    hasMore: list.hasMore,
    total: list.total,
    totalPages: list.totalPages,
    loadPage: list.loadPage,
    filterByType: (fragmentType: string | undefined) =>
      list.loadPage(1, { ...list.currentFilters.value, fragment_type: fragmentType }),
    filterByUnusedOnly: (unusedOnly: boolean) =>
      list.loadPage(1, { ...list.currentFilters.value, unused_only: unusedOnly || undefined }),
    refresh: list.refresh,
  };
}
