import { onMounted } from "vue";
import { storeToRefs } from "pinia";
import type { components } from "@/api/schema";
import { useSettingsStore } from "@/stores/settings";

export type Provider = components["schemas"]["ProviderResponse"];

/**
 * Provider list, backed by the settings store's cached singleton so every
 * consumer (Providers/Models/Families tabs, model-create modal, setup wizard)
 * shares one fetch instead of each hitting `/api/providers` on mount. Mutations
 * (create/edit) call `refresh()` to force the shared cache to refetch.
 */
export function useProviders() {
  const store = useSettingsStore();
  const { providers, isLoadingProviders: loading, providersError: error } = storeToRefs(store);

  // Force so both the error-state retry and post-mutation refreshes actually
  // re-hit the endpoint (a plain fetch is a no-op once the cache is warm).
  const refresh = () => store.fetchProviders(true);

  onMounted(() => {
    store.fetchProviders();
  });

  return { providers, loading, error, refresh };
}
