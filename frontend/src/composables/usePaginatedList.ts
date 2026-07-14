import { computed, onMounted, ref, type Ref } from "vue";
import { extractApiError } from "@/api/client";

interface PageMeta {
  limit: number;
  has_more: boolean;
  cursor?: string | null;
  total?: number | null;
  page?: number | null;
}
interface PageEnvelope<TItem> {
  items: TItem[];
  meta: PageMeta;
}
type ClientResult<T> = Promise<{ data?: T; error?: unknown }>;

interface PaginatedListOptions<TFilters> {
  pageSize?: number;
  initialFilters?: TFilters;
  initialPage?: number;
  autoLoad?: boolean;
  errorContext?: string;
  /** When true, `loadPage(n>1)` appends (infinite scroll) instead of replacing. */
  append?: boolean;
}

/**
 * Shared offset/page-based list state — the page/hasMore/total/totalPages +
 * loadPage/loadMore/refresh machinery duplicated across the list composables.
 * The caller passes a typed `fetchPage` closure (so per-endpoint contract typing
 * + its own filter→query mapping stay in the composable) and gets the state back.
 */
export function usePaginatedList<TItem, TFilters = Record<string, never>>(
  fetchPage: (page: number, pageSize: number, filters: TFilters) => ClientResult<PageEnvelope<TItem>>,
  options: PaginatedListOptions<TFilters> = {},
) {
  const {
    pageSize = 20,
    initialFilters = {} as TFilters,
    initialPage = 1,
    autoLoad = true,
    errorContext = "Failed to load",
    append = false,
  } = options;

  const items = ref<TItem[]>([]) as Ref<TItem[]>;
  const loading = ref(false);
  const error = ref<Error | null>(null);
  const page = ref(initialPage);
  const hasMore = ref(false);
  const total = ref(0);
  const currentFilters = ref<TFilters>(initialFilters) as Ref<TFilters>;

  const totalPages = computed(() => (total.value === 0 ? 1 : Math.ceil(total.value / pageSize)));

  // Monotonic request token: fast filter/search changes fire overlapping loads,
  // and a slower earlier response must not clobber a newer one. Each call captures
  // its token and only applies its result/error/loading if still the latest
  // (last-request-wins, without threading an AbortSignal through every fetchPage).
  let requestSeq = 0;

  async function loadPage(pageNum: number = initialPage, filters?: TFilters) {
    const seq = ++requestSeq;
    loading.value = true;
    error.value = null;
    if (filters !== undefined) currentFilters.value = filters;

    try {
      const { data, error: apiError } = await fetchPage(pageNum, pageSize, currentFilters.value);
      if (seq !== requestSeq) return; // superseded by a newer load — discard
      if (apiError) throw extractApiError(apiError, errorContext);
      if (data) {
        items.value = append && pageNum > 1 ? [...items.value, ...data.items] : data.items;
        page.value = data.meta.page ?? pageNum;
        hasMore.value = data.meta.has_more;
        total.value = data.meta.total ?? 0;
      }
    } catch (err) {
      if (seq !== requestSeq) return;
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error(errorContext, err);
    } finally {
      if (seq === requestSeq) loading.value = false;
    }
  }

  async function loadMore() {
    if (hasMore.value && !loading.value) await loadPage(page.value + 1);
  }

  function refresh() {
    if (append) {
      items.value = [];
      hasMore.value = false;
      page.value = 1;
    }
    loadPage(append ? 1 : page.value);
  }

  onMounted(() => {
    if (autoLoad) loadPage(initialPage);
  });

  return {
    items,
    loading,
    error,
    page,
    hasMore,
    total,
    totalPages,
    currentFilters,
    loadPage,
    loadMore,
    refresh,
  };
}
