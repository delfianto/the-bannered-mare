import { ref, onMounted } from "vue";
import type { components } from "@/api/schema";
import { client, extractApiError } from "@/api/client";

export type Provider = components["schemas"]["ProviderResponse"];

export function useProviders() {
  const providers = ref<Provider[]>([]);
  const loading = ref(false);
  const error = ref<Error | null>(null);

  const fetchProviders = async () => {
    loading.value = true;
    error.value = null;

    try {
      const { data, error: apiError } = await client.GET("/api/providers");

      if (apiError) {
        throw extractApiError(apiError, "Failed to load providers");
      }

      if (data) {
        providers.value = data;
      }
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error("Error loading providers:", err);
    } finally {
      loading.value = false;
    }
  };

  const refresh = () => {
    fetchProviders();
  };

  onMounted(() => {
    fetchProviders();
  });

  return {
    providers,
    loading,
    error,
    refresh,
  };
}
