import { ref, computed, onMounted } from "vue";
import type { components } from "@/api/schema";
import { client } from "@/api/client";

export type ModelFamilyListItem = components["schemas"]["ModelFamilyListResponse"];

interface UseModelFamiliesOptions {
  pageSize?: number;
}

export function useModelFamilies(options: UseModelFamiliesOptions = {}) {
  const { pageSize = 10 } = options;

  const families = ref<ModelFamilyListItem[]>([]);
  const loading = ref(false);
  const error = ref<Error | null>(null);
  const page = ref(1);
  const hasMore = ref(false);
  const total = ref(0);

  const totalPages = computed(() => {
    if (total.value === 0) return 1;
    return Math.ceil(total.value / pageSize);
  });

  const loadPage = async (pageNum: number = 1) => {
    loading.value = true;
    error.value = null;

    try {
      const { data, error: apiError } = await client.GET("/api/model-families", {
        params: {
          query: {
            page: pageNum,
            limit: pageSize,
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

  onMounted(() => {
    loadPage(1);
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
  };
}
