import { onMounted, ref, type Ref } from "vue";
import { extractApiError } from "@/api/client";

interface CursorMeta {
  has_more: boolean;
  cursor?: string | null;
}
interface CursorEnvelope<TItem> {
  items: TItem[];
  meta: CursorMeta;
}
type ClientResult<T> = Promise<{ data?: T; error?: unknown }>;

interface CursorListOptions<TItem> {
  /**
   * Fetch one page. Returns `null` when there's no context to fetch for yet
   * (e.g. no chat selected) so `load`/`loadMore` become no-ops rather than
   * hitting the API with a missing path param.
   */
  fetchPage: (
    cursor: string | undefined,
    pageSize: number,
  ) => ClientResult<CursorEnvelope<TItem>> | null;
  /**
   * Merge a freshly-fetched batch into the existing list. `isInitial` is true
   * for the first page (no cursor). This is where the two twins diverge:
   * the chat list appends at the end, messages reverse each batch and prepend
   * older ones on top.
   */
  merge: (existing: TItem[], batch: TItem[], isInitial: boolean) => TItem[];
  pageSize?: number;
  /** Starting value for `hasMore` — chats optimistically assume a page exists. */
  hasMoreInitial?: boolean;
  autoLoad?: boolean;
  errorContext?: string;
}

/**
 * Shared cursor/infinite-scroll list state — the loading/hasMore/cursor + load/
 * loadMore/reset machinery duplicated across the two chat twins. The caller
 * supplies a typed `fetchPage` closure (so per-endpoint contract typing +
 * path/query mapping stay put) and a `merge` strategy; the list ref itself is
 * returned so callers can mutate it in place (the message streaming path writes
 * straight into `items` without going through the loader).
 */
export function useCursorList<TItem>(options: CursorListOptions<TItem>) {
  const {
    fetchPage,
    merge,
    pageSize = 20,
    hasMoreInitial = false,
    autoLoad = false,
    errorContext = "Failed to load",
  } = options;

  const items = ref<TItem[]>([]) as Ref<TItem[]>;
  const loading = ref(false);
  const hasMore = ref(hasMoreInitial);
  const cursor = ref<string | null>(null);
  const error = ref<Error | null>(null);

  async function load(nextCursor?: string) {
    const result = fetchPage(nextCursor, pageSize);
    if (!result) return;

    loading.value = true;
    error.value = null;
    try {
      const { data, error: apiError } = await result;
      if (apiError) throw extractApiError(apiError, errorContext);
      if (data) {
        items.value = merge(items.value, data.items, !nextCursor);
        hasMore.value = data.meta.has_more;
        cursor.value = data.meta.cursor || null;
      }
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error(errorContext, err);
    } finally {
      loading.value = false;
    }
  }

  async function loadMore() {
    if (hasMore.value && !loading.value && cursor.value) {
      await load(cursor.value);
    }
  }

  function reset() {
    items.value = [];
    hasMore.value = hasMoreInitial;
    cursor.value = null;
  }

  onMounted(() => {
    if (autoLoad) load();
  });

  return { items, loading, hasMore, cursor, error, load, loadMore, reset };
}
