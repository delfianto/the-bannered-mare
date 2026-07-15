import { onMounted, ref, type Ref } from "vue";
import { extractApiError } from "@/api/client";

// openapi-fetch calls resolve to `{ data, error, response }`; accept that
// structural shape (mirrors useEntityCrud) so callers hand us fully-typed
// `client.*` closures without losing per-path typing. `response` carries the
// HTTP status into APIError (see extractApiError).
type ClientResult<T> = Promise<{ data?: T; error?: unknown; response?: Response }>;

interface ListCrudOps<TItem, FetchArgs extends unknown[], TCreate, TUpdate> {
  /** Lowercase plural noun for error messages, e.g. "presets". */
  label: string;
  /** List fetch; its args become `fetchList`/`refresh` args (e.g. a scope filter). */
  list: (...args: FetchArgs) => ClientResult<{ items: TItem[] }>;
  /** Fetch on mount (default true). */
  autoLoad?: boolean;
  /** Read the id off an item (default `item.id`). */
  idOf?: (item: TItem) => string;
  /** Keep a single `is_default` row after create/update. */
  singleDefault?: boolean;
  create?: (body: TCreate) => ClientResult<TItem>;
  update?: (id: string, body: TUpdate) => ClientResult<TItem>;
  remove?: (id: string) => ClientResult<unknown>;
  setDefault?: (id: string) => ClientResult<unknown>;
}

/**
 * Shared list + CRUD state/flow for the feature-list composables, which each
 * re-implemented the same items/loading/error refs, the fetch try/catch/finally,
 * and the local-list reconcile after a mutation. The list-only analog of
 * `useEntityCrud`, and it uses the same error contract: mutations reject on
 * failure **and** record it on `error` (never a silent `return null`), so a
 * caller can `await` + toast while a consumer reading `error` still sees it.
 */
export function useListCrud<
  TItem extends { id: string; is_default?: boolean },
  FetchArgs extends unknown[] = [],
  TCreate = never,
  TUpdate = never,
>(ops: ListCrudOps<TItem, FetchArgs, TCreate, TUpdate>) {
  const items = ref<TItem[]>([]) as Ref<TItem[]>;
  const loading = ref(false);
  const error = ref<Error | null>(null);
  const idOf = ops.idOf ?? ((item: TItem) => item.id);

  async function fetchList(...args: FetchArgs): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      const { data, error: apiError, response } = await ops.list(...args);
      if (apiError)
        throw extractApiError(apiError, `Failed to load ${ops.label}`, response?.status);
      if (data) items.value = data.items;
    } catch (e) {
      error.value = e instanceof Error ? e : new Error("Unknown error");
    } finally {
      loading.value = false;
    }
  }

  function refresh(...args: FetchArgs): void {
    void fetchList(...args);
  }

  function recordError(e: unknown): Error {
    const err = e instanceof Error ? e : new Error("Unknown error");
    error.value = err;
    return err;
  }

  // Enforce the single-default invariant locally when a saved row becomes default.
  function reconcileDefault(saved: TItem): void {
    if (!ops.singleDefault || !saved.is_default) return;
    for (const item of items.value) {
      if (idOf(item) !== idOf(saved)) (item as { is_default?: boolean }).is_default = false;
    }
  }

  async function createItem(body: TCreate): Promise<TItem> {
    error.value = null;
    try {
      const { data, error: apiError, response } = await ops.create!(body);
      if (apiError || !data)
        throw extractApiError(apiError, `Failed to create ${ops.label}`, response?.status);
      reconcileDefault(data);
      items.value.unshift(data);
      return data;
    } catch (e) {
      throw recordError(e);
    }
  }

  async function updateItem(id: string, body: TUpdate): Promise<TItem> {
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
      throw recordError(e);
    }
  }

  async function removeItem(id: string): Promise<void> {
    error.value = null;
    try {
      const { error: apiError, response } = await ops.remove!(id);
      if (apiError)
        throw extractApiError(apiError, `Failed to delete ${ops.label}`, response?.status);
      items.value = items.value.filter((item) => idOf(item) !== id);
    } catch (e) {
      throw recordError(e);
    }
  }

  async function setDefaultItem(id: string): Promise<void> {
    error.value = null;
    try {
      const { error: apiError, response } = await ops.setDefault!(id);
      if (apiError)
        throw extractApiError(apiError, `Failed to set default ${ops.label}`, response?.status);
      for (const item of items.value) {
        (item as { is_default?: boolean }).is_default = idOf(item) === id;
      }
    } catch (e) {
      throw recordError(e);
    }
  }

  onMounted(() => {
    if (ops.autoLoad ?? true) void fetchList(...([] as unknown as FetchArgs));
  });

  return {
    items,
    loading,
    error,
    fetchList,
    refresh,
    createItem,
    updateItem,
    removeItem,
    setDefaultItem,
  };
}
