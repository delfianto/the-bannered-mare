import { ref, type Ref } from "vue";
import { extractApiError } from "@/api/client";

// openapi-fetch calls resolve to `{ data, error, response }`; accept that
// structural shape so callers can hand us fully-typed `client.*` closures without
// losing per-path typing (a generic `basePath` string would). `response` is kept
// so failures can carry the HTTP status into APIError (see extractApiError).
type ClientResult<T> = Promise<{ data?: T; error?: unknown; response?: Response }>;

interface EntityCrudOps<TDetail, TCreate, TUpdate> {
  /** Lowercase noun for error messages, e.g. "preset". */
  label: string;
  fetchOne: (id: string) => ClientResult<TDetail>;
  create?: (body: TCreate) => ClientResult<TDetail>;
  update?: (id: string, body: TUpdate) => ClientResult<TDetail>;
  remove?: (id: string) => ClientResult<unknown>;
}

/**
 * Shared single-entity CRUD state + flow for the settings detail composables,
 * which otherwise each re-implemented the same loading/saving/deleting/error refs
 * and try/finally blocks. The caller supplies typed `client.*` closures (so the
 * contract types survive) and gets back the standard refs + actions. Errors go
 * through extractApiError so messages stay consistent.
 */
export function useEntityCrud<TDetail, TCreate = never, TUpdate = never>(
  ops: EntityCrudOps<TDetail, TCreate, TUpdate>,
) {
  const item = ref<TDetail | null>(null) as Ref<TDetail | null>;
  const loading = ref(false);
  const saving = ref(false);
  const deleting = ref(false);
  const error = ref<Error | null>(null);

  async function fetchItem(id: string) {
    loading.value = true;
    error.value = null;
    try {
      const { data, error: apiError, response } = await ops.fetchOne(id);
      if (apiError || !data)
        throw extractApiError(apiError, `Failed to load ${ops.label}`, response?.status);
      item.value = data;
    } catch (e) {
      error.value = e instanceof Error ? e : new Error("Unknown error");
    } finally {
      loading.value = false;
    }
  }

  // Mutations rethrow (callers await + toast), but they also record the failure on
  // the shared `error` ref so consumers reading it after a write see the real
  // error, and clear it on a fresh attempt — matching fetchItem's contract.
  function recordError(e: unknown): Error {
    const err = e instanceof Error ? e : new Error("Unknown error");
    error.value = err;
    return err;
  }

  async function createItem(body: TCreate): Promise<TDetail> {
    saving.value = true;
    error.value = null;
    try {
      const { data, error: apiError, response } = await ops.create!(body);
      if (apiError || !data)
        throw extractApiError(apiError, `Failed to create ${ops.label}`, response?.status);
      return data;
    } catch (e) {
      throw recordError(e);
    } finally {
      saving.value = false;
    }
  }

  async function updateItem(id: string, body: TUpdate): Promise<TDetail> {
    saving.value = true;
    error.value = null;
    try {
      const { data, error: apiError, response } = await ops.update!(id, body);
      if (apiError || !data)
        throw extractApiError(apiError, `Failed to save ${ops.label}`, response?.status);
      item.value = data;
      return data;
    } catch (e) {
      throw recordError(e);
    } finally {
      saving.value = false;
    }
  }

  async function removeItem(id: string): Promise<void> {
    deleting.value = true;
    error.value = null;
    try {
      const { error: apiError, response } = await ops.remove!(id);
      if (apiError) throw extractApiError(apiError, `Failed to delete ${ops.label}`, response?.status);
    } catch (e) {
      throw recordError(e);
    } finally {
      deleting.value = false;
    }
  }

  /** Run an entity-specific extra mutation under the shared `saving` flag. */
  async function runSaving<T>(fn: () => ClientResult<T>, context: string): Promise<T> {
    saving.value = true;
    error.value = null;
    try {
      const { data, error: apiError, response } = await fn();
      if (apiError || data == null) throw extractApiError(apiError, context, response?.status);
      return data;
    } catch (e) {
      throw recordError(e);
    } finally {
      saving.value = false;
    }
  }

  return {
    item,
    loading,
    saving,
    deleting,
    error,
    fetchItem,
    createItem,
    updateItem,
    removeItem,
    runSaving,
  };
}
