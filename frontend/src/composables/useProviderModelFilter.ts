import { computed, ref, type Ref } from "vue";
import { useDebounceFn } from "@vueuse/core";
import { useI18n } from "vue-i18n";
import { useAppToast } from "@/composables/useToast";
import type { components } from "@/api/schema";

type ProviderResponse = components["schemas"]["ProviderResponse"];

/** The provider model-search/filter methods this composable drives (from `useProvider`). */
interface ModelFilterApi {
  searchModels: (id: string, query: string) => Promise<unknown>;
  clearSearch: () => void;
  setModelFilter: (id: string, allowedModels: string[]) => Promise<unknown>;
}

/**
 * The provider "curated model allow-list" UI logic — debounced search + add/remove
 * chips — extracted out of ProviderView. Operates on the view's single
 * `useProvider` instance (passed in, since `useProvider` isn't a singleton).
 */
export function useProviderModelFilter(
  provider: Ref<ProviderResponse | null>,
  api: ModelFilterApi,
) {
  const { t } = useI18n();
  const toast = useAppToast();

  const modelSearchQuery = ref("");
  const showSearchResults = ref(false);
  const allowedModels = computed(() => provider.value?.allowed_models ?? []);

  const isFiltered = (identifier: string): boolean => allowedModels.value.includes(identifier);

  const debouncedSearch = useDebounceFn(async (q: string) => {
    if (!provider.value || !q.trim()) {
      api.clearSearch();
      return;
    }
    try {
      await api.searchModels(provider.value.id, q.trim());
      showSearchResults.value = true;
    } catch {
      // Search is advisory — a failure just leaves the dropdown empty.
    }
  }, 250);

  function onSearchInput() {
    if (modelSearchQuery.value.trim()) {
      showSearchResults.value = true;
      void debouncedSearch(modelSearchQuery.value);
    } else {
      showSearchResults.value = false;
      api.clearSearch();
    }
  }

  async function persistFilter(next: string[]) {
    if (!provider.value) return;
    try {
      await api.setModelFilter(provider.value.id, next);
    } catch {
      toast.error(t("connections.provider.toast.filterFailed"));
    }
  }

  async function addToFilter(identifier: string) {
    if (isFiltered(identifier)) return;
    await persistFilter([...allowedModels.value, identifier]);
    modelSearchQuery.value = "";
    showSearchResults.value = false;
    api.clearSearch();
  }

  async function removeFromFilter(identifier: string) {
    await persistFilter(allowedModels.value.filter((m) => m !== identifier));
  }

  async function clearFilter() {
    await persistFilter([]);
  }

  return {
    modelSearchQuery,
    showSearchResults,
    allowedModels,
    isFiltered,
    onSearchInput,
    addToFilter,
    removeFromFilter,
    clearFilter,
  };
}
