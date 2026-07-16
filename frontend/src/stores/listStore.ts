import { defineStore } from "pinia";
import { ref, type Ref } from "vue";
import { extractApiError } from "@/api/client";

// openapi-fetch calls resolve to `{ data, error, response }`; accept that
// structural shape (mirrors useEntityCrud/useListCrud) so callers hand us
// fully-typed `client.*` closures without losing per-path typing.
type ClientResult<T> = Promise<{ data?: T; error?: unknown; response?: Response }>;

interface ListStoreOps<TItem, TCreate, TUpdate> {
  /** Singular noun for mutation error messages, e.g. "preset". */
  label: string;
  /** Plural noun for the load error message; defaults to `${label}s`. */
  labelPlural?: string;
  list: () => ClientResult<{ items: TItem[] }>;
  /** Read the id off an item (default `item.id`). */
  idOf?: (item: TItem) => string;
  /** Keep a single `is_default` row after create/update/setDefault. */
  singleDefault?: boolean;
  create?: (body: TCreate) => ClientResult<TItem>;
  update?: (id: string, body: TUpdate) => ClientResult<TItem>;
  remove?: (id: string) => ClientResult<unknown>;
  setDefault?: (id: string) => ClientResult<unknown>;
}

/**
 * A Pinia store factory for a shared, cached list resource — the singleton
 * counterpart to the per-instance `useListCrud`. Every consumer of a
 * given resource shares one `items` array and one fetch: `ensureLoaded()`
 * (called on mount) fetches once and caches, like the providers store; mutations
 * keep the cached list coherent in place; `refresh()` force-refetches (for the
 * error-retry and for out-of-band mutators — the single-item detail composables —
 * to invalidate the cache after they write, so no list goes stale).
 *
 * Error contract matches `useListCrud`: operations clear `error` on entry and
 * record failures on the shared `error` ref (never a silent swallow); mutations
 * return `null`/`false` so callers can branch inline.
 */
export function defineListStore<
  TItem extends { id: string; is_default?: boolean },
  TCreate = never,
  TUpdate = never,
>(id: string, ops: ListStoreOps<TItem, TCreate, TUpdate>) {
  const plural = ops.labelPlural ?? `${ops.label}s`;
  const idOf = ops.idOf ?? ((item: TItem) => item.id);

  return defineStore(id, () => {
    const items = ref<TItem[]>([]) as Ref<TItem[]>;
    const loading = ref(false);
    const error = ref<Error | null>(null);
    const hasLoaded = ref(false);

    function clearError(): void {
      error.value = null;
    }

    function recordError(e: unknown): void {
      error.value = e instanceof Error ? e : new Error("Unknown error");
    }

    async function fetchList(): Promise<void> {
      loading.value = true;
      error.value = null;
      try {
        const { data, error: apiError, response } = await ops.list();
        if (apiError) throw extractApiError(apiError, `Failed to load ${plural}`, response?.status);
        if (data) {
          items.value = data.items;
          hasLoaded.value = true;
        }
      } catch (e) {
        recordError(e);
      } finally {
        loading.value = false;
      }
    }

    // Fetch once and cache (mount path); a warm or in-flight cache is a no-op.
    function ensureLoaded(): void {
      if (hasLoaded.value || loading.value) return;
      void fetchList();
    }

    // Force a refetch — error-retry, and cache invalidation from out-of-band
    // mutators (the single-item detail composables).
    function refresh(): Promise<void> {
      return fetchList();
    }

    // Enforce the single-default invariant locally when a saved row becomes default.
    function reconcileDefault(saved: TItem): void {
      if (!ops.singleDefault || !saved.is_default) return;
      for (const item of items.value) {
        if (idOf(item) !== idOf(saved)) (item as { is_default?: boolean }).is_default = false;
      }
    }

    // Replace an existing row or prepend a new one — for out-of-band writers
    // (e.g. the multipart persona save) that own the mutation but want the shared
    // list coherent without a refetch.
    function upsert(item: TItem): void {
      reconcileDefault(item);
      const idx = items.value.findIndex((i) => idOf(i) === idOf(item));
      if (idx !== -1) items.value[idx] = item;
      else items.value.unshift(item);
    }

    async function createItem(body: TCreate): Promise<TItem | null> {
      error.value = null;
      try {
        const { data, error: apiError, response } = await ops.create!(body);
        if (apiError || !data)
          throw extractApiError(apiError, `Failed to create ${ops.label}`, response?.status);
        reconcileDefault(data);
        items.value.unshift(data);
        return data;
      } catch (e) {
        recordError(e);
        return null;
      }
    }

    async function updateItem(id: string, body: TUpdate): Promise<TItem | null> {
      error.value = null;
      try {
        const { data, error: apiError, response } = await ops.update!(id, body);
        if (apiError || !data)
          throw extractApiError(apiError, `Failed to save ${ops.label}`, response?.status);
        reconcileDefault(data);
        const idx = items.value.findIndex((item) => idOf(item) === id);
        if (idx !== -1) items.value[idx] = data;
        return data;
      } catch (e) {
        recordError(e);
        return null;
      }
    }

    async function removeItem(id: string): Promise<boolean> {
      error.value = null;
      try {
        const { error: apiError, response } = await ops.remove!(id);
        if (apiError)
          throw extractApiError(apiError, `Failed to delete ${ops.label}`, response?.status);
        items.value = items.value.filter((item) => idOf(item) !== id);
        return true;
      } catch (e) {
        recordError(e);
        return false;
      }
    }

    async function setDefaultItem(id: string): Promise<boolean> {
      error.value = null;
      try {
        const { error: apiError, response } = await ops.setDefault!(id);
        if (apiError)
          throw extractApiError(apiError, `Failed to set default ${ops.label}`, response?.status);
        for (const item of items.value) {
          (item as { is_default?: boolean }).is_default = idOf(item) === id;
        }
        return true;
      } catch (e) {
        recordError(e);
        return false;
      }
    }

    return {
      items,
      loading,
      error,
      hasLoaded,
      clearError,
      recordError,
      ensureLoaded,
      refresh,
      upsert,
      createItem,
      updateItem,
      removeItem,
      setDefaultItem,
    };
  });
}
