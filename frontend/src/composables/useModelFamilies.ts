import { ref, computed, onMounted } from "vue";
import type { components } from "@/api/schema";
import { client } from "@/api/client";

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

  const families = ref<ModelFamilyListItem[]>([]);
  const loading = ref(false);
  const error = ref<Error | null>(null);
  const page = ref(initialPage);
  const hasMore = ref(false);
  const total = ref(0);

  const totalPages = computed(() => {
    if (total.value === 0) return 1;
    return Math.ceil(total.value / pageSize);
  });

  const currentFilters = ref<ModelFamilyFilters>(initialFilters);

  const loadPage = async (pageNum: number = 1, filters?: ModelFamilyFilters) => {
    loading.value = true;
    error.value = null;

    if (filters !== undefined) {
      currentFilters.value = filters;
    }
    const f = currentFilters.value;

    try {
      const query: Record<string, unknown> = { page: pageNum, limit: pageSize };
      if (f.name) query.name__ilike = f.name;
      if (f.provider_type) query.provider_type = f.provider_type;

      const { data, error: apiError } = await client.GET("/api/model-families", {
        params: {
          query: query as {
            page?: number;
            limit?: number;
            name__ilike?: string | null;
            provider_type?: string | null;
          },
        },
      });

      if (apiError) {
        throw new Error(`Failed to load model families: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        families.value = data.items;
        page.value = data.meta.page ?? pageNum;
        hasMore.value = data.meta.has_more;
        total.value = data.meta.total ?? 0;
      }
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error("Error loading model families:", err);
    } finally {
      loading.value = false;
    }
  };

  const search = (name: string) => {
    loadPage(1, { ...currentFilters.value, name: name || undefined });
  };

  const filterByProviderType = (providerType: string | undefined) => {
    loadPage(1, { ...currentFilters.value, provider_type: providerType });
  };

  onMounted(() => {
    if (autoLoad) loadPage(initialPage);
  });

  return {
    families,
    loading,
    error,
    page,
    hasMore,
    total,
    totalPages,
    loadPage,
    search,
    filterByProviderType,
  };
}
