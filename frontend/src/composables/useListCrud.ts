import { onMounted, ref, type Ref } from "vue";
import { extractApiError } from "@/api/client";

// openapi-fetch calls resolve to `{ data, error, response }`; accept that
// structural shape (mirrors useEntityCrud) so callers hand us fully-typed
// `client.*` closures without losing per-path typing. `response` carries the
// HTTP status into APIError (see extractApiError).
type ClientResult<T> = Promise<{ data?: T; error?: unknown; response?: Response }>;

interface ListCrudOps<TItem, FetchArgs extends unknown[], TCreate, TUpdate> {
  /** Singular noun for mutation error messages, e.g. "profile". */
  label: string;
  /** Plural noun for the load error message; defaults to `${label}s`. */
  labelPlural?: string;
  /** List fetch; its args become `fetchList`/`refresh` args (e.g. a scope filter). */
  list: (...args: FetchArgs) => ClientResult<{ items: TItem[] }>;
  /** Fetch on mount (default true). */
  autoLoad?: boolean;
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
 * Shared list + CRUD state/flow for the feature-list composables, which each
 * re-implemented the same items/loading/error refs, the fetch try/catch/finally,
 * and the local-list reconcile after a mutation.
 *
 * Error contract: every operation clears `error` on entry and **records** the
 * failure on the shared `error` ref (never a silent `console.error` swallow);
 * mutations then return `null`/`false` so their callers can branch inline. This
 * differs from the single-item `useEntityCrud`, which *rethrows* for a detail
 * page's one-shot save — here the list callers already switch on the result
 * (e.g. `if (res) toast.success else toast.error`).
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
  const plural = ops.labelPlural ?? `${ops.label}s`;

  function recordError(e: unknown): void {
    error.value = e instanceof Error ? e : new Error("Unknown error");
  }

  async function fetchList(...args: FetchArgs): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      const { data, error: apiError, response } = await ops.list(...args);
      if (apiError) throw extractApiError(apiError, `Failed to load ${plural}`, response?.status);
      if (data) items.value = data.items;
    } catch (e) {
      recordError(e);
    } finally {
      loading.value = false;
    }
  }

  function refresh(...args: FetchArgs): void {
    void fetchList(...args);
  }

  // Enforce the single-default invariant locally when a saved row becomes default.
  function reconcileDefault(saved: TItem): void {
    if (!ops.singleDefault || !saved.is_default) return;
    for (const item of items.value) {
      if (idOf(item) !== idOf(saved)) (item as { is_default?: boolean }).is_default = false;
    }
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
