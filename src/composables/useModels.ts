import { ref, computed, onMounted } from "vue";
import type { components } from "@/api/schema";
import { client } from "@/api/client";

export type ModelListItem = components["schemas"]["ModelListResponse"];

interface UseModelsOptions {
  pageSize?: number;
}

interface ModelFilters {
  name?: string;
  provider_id?: string;
}

export function useModels(options: UseModelsOptions = {}) {
  const { pageSize = 12 } = options;

  const models = ref<ModelListItem[]>([]);
  const loading = ref(false);
  const error = ref<Error | null>(null);
  const page = ref(1);
  const hasMore = ref(false);
  const total = ref(0);
  const currentFilters = ref<ModelFilters>({});

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

      const { data, error: apiError } = await client.GET("/api/models", {
        params: {
          query: query as {
            page?: number;
            limit?: number;
            name__ilike?: string | null;
            provider_id?: string | null;
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

  const filterByProvider = (providerId: string | undefined) => {
    loadPage(1, { ...currentFilters.value, provider_id: providerId });
  };

  onMounted(() => {
    loadPage(1);
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
  };
}
