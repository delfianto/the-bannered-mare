import { ref, computed, onMounted } from "vue";
import type { components } from "@/api/schema";
import { client, extractApiError } from "@/api/client";

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

  const fragments = ref<PromptFragment[]>([]);
  const loading = ref(false);
  const error = ref<Error | null>(null);
  const page = ref(1);
  const hasMore = ref(false);
  const total = ref(0);
  const currentFilters = ref<FragmentFilters>({});

  const totalPages = computed(() => {
    if (total.value === 0) return 1;
    return Math.ceil(total.value / pageSize);
  });

  const loadPage = async (pageNum: number = 1, filters?: FragmentFilters) => {
    loading.value = true;
    error.value = null;

    if (filters !== undefined) {
      currentFilters.value = filters;
    }
    const f = currentFilters.value;

    try {
      const { data, error: apiError } = await client.GET("/api/prompt-fragments/", {
        params: {
          query: {
            page: pageNum,
            limit: pageSize,
            fragment_type: f.fragment_type,
            is_global: f.is_global,
            unused_only: f.unused_only,
          },
        },
      });

      if (apiError) {
        throw extractApiError(apiError, "Failed to load prompt fragments");
      }

      if (data) {
        fragments.value = data.items;
        page.value = data.meta.page ?? pageNum;
        hasMore.value = data.meta.has_more;
        total.value = data.meta.total ?? 0;
      }
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error("Error loading prompt fragments:", err);
    } finally {
      loading.value = false;
    }
  };

  const filterByType = (fragmentType: string | undefined) => {
    loadPage(1, { ...currentFilters.value, fragment_type: fragmentType });
  };

  const filterByUnusedOnly = (unusedOnly: boolean) => {
    loadPage(1, { ...currentFilters.value, unused_only: unusedOnly || undefined });
  };

  const refresh = () => {
    loadPage(page.value);
  };

  onMounted(() => {
    loadPage(1);
  });

  return {
    fragments,
    loading,
    error,
    page,
    hasMore,
    total,
    totalPages,
    loadPage,
    filterByType,
    filterByUnusedOnly,
    refresh,
  };
}
