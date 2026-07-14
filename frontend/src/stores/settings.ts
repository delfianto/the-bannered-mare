import { defineStore } from "pinia";
import { ref } from "vue";
import { client, extractApiError } from "@/api/client";
import type { components } from "@/api/schema";

export type ParameterDoc = {
  label: string;
  short_info: string;
  detailed_info: string;
};

type ProviderResponse = components["schemas"]["ProviderResponse"];

export const useSettingsStore = defineStore("settings", () => {
  const parameterDocs = ref<Record<string, ParameterDoc>>({});
  const isLoadingDocs = ref(false);
  const hasLoadedDocs = ref(false);

  const providers = ref<ProviderResponse[]>([]);
  const isLoadingProviders = ref(false);
  const hasLoadedProviders = ref(false);
  const providersError = ref<Error | null>(null);

  const fetchParameterDocs = async () => {
    if (hasLoadedDocs.value || isLoadingDocs.value) return;

    isLoadingDocs.value = true;
    try {
      const { data, error } = await client.GET("/api/model-families/parameter-docs");
      if (error) throw error;

      if (data) {
        parameterDocs.value = data as Record<string, ParameterDoc>;
        hasLoadedDocs.value = true;
      }
    } catch (error) {
      console.error("Failed to load parameter docs", error);
    } finally {
      isLoadingDocs.value = false;
    }
  };

  const fetchProviders = async (force = false) => {
    if ((hasLoadedProviders.value || isLoadingProviders.value) && !force) return;

    isLoadingProviders.value = true;
    providersError.value = null;
    try {
      const { data, error } = await client.GET("/api/providers");
      if (error) throw extractApiError(error, "Failed to load providers");

      if (data) {
        providers.value = [...data.items].sort((a, b) => a.name.localeCompare(b.name));
        hasLoadedProviders.value = true;
      }
    } catch (error) {
      providersError.value = error instanceof Error ? error : new Error("Failed to load providers");
      console.error("Failed to load providers", error);
    } finally {
      isLoadingProviders.value = false;
    }
  };

  return {
    parameterDocs,
    isLoadingDocs,
    hasLoadedDocs,
    fetchParameterDocs,
    providers,
    isLoadingProviders,
    hasLoadedProviders,
    providersError,
    fetchProviders,
  };
});
