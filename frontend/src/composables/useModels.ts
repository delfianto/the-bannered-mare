import { ref, computed, onMounted } from "vue";
import type { components } from "@/api/schema";
import { client } from "@/api/client";

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

  const models = ref<ModelListItem[]>([]);
  const loading = ref(false);
  const error = ref<Error | null>(null);
  const page = ref(initialPage);
  const hasMore = ref(false);
  const total = ref(0);
  const currentFilters = ref<ModelFilters>(initialFilters);

  const totalPages = computed(() => {
    if (total.value === 0) return 1;
    return Math.ceil(total.value / pageSize);
  });

  const loadPage = async (pageNum: number = 1, filters?: ModelFilters) => {
    loading.value = true;
    error.value = null;

    if (filters !== undefined) {
      currentFilters.value = filters;
    }

    const f = currentFilters.value;

    try {
      const query: Record<string, unknown> = {
        page: pageNum,
        limit: pageSize,
      };

      if (f.name) query.name__ilike = f.name;
      if (f.provider_id) query.provider_id = f.provider_id;
      if (f.model_family_id) query.model_family_id = f.model_family_id;
      if (f.enabled !== undefined) query.enabled = f.enabled;

      const { data, error: apiError } = await client.GET("/api/models", {
        params: {
          query: query as {
            page?: number;
            limit?: number;
            name__ilike?: string | null;
            provider_id?: string | null;
            model_family_id?: string | null;
            enabled?: boolean | null;
          },
        },
      });

      if (apiError) {
        throw new Error(`Failed to load models: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        models.value = data.items;
        page.value = data.meta.page ?? pageNum;
        hasMore.value = data.meta.has_more;
        total.value = data.meta.total ?? 0;
      }
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error("Error loading models:", err);
    } finally {
      loading.value = false;
    }
  };

  const search = (name: string) => {
    loadPage(1, { ...currentFilters.value, name: name || undefined });
  };

  // `provider_id` now means "has a route on that provider" — the server resolves
  // it against each registry's routes, so the client just forwards the id.
  const filterByProvider = (providerId: string | undefined) => {
    loadPage(1, { ...currentFilters.value, provider_id: providerId });
  };

  const filterByFamily = (familyId: string | undefined) => {
    loadPage(1, { ...currentFilters.value, model_family_id: familyId });
  };

  const filterByStatus = (enabled: boolean | undefined) => {
    loadPage(1, { ...currentFilters.value, enabled });
  };

  onMounted(() => {
    if (autoLoad) loadPage(initialPage);
  });

  return {
    models,
    loading,
    error,
    page,
    hasMore,
    total,
    totalPages,
    loadPage,
    search,
    filterByProvider,
    filterByFamily,
    filterByStatus,
  };
}
