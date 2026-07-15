import { onMounted } from "vue";
import { storeToRefs } from "pinia";
import type { components } from "@/api/schema";
import { client } from "@/api/client";
import { defineListStore } from "@/stores/listStore";

export type PromptTemplate = components["schemas"]["PromptTemplateResponse"];

/**
 * Prompt-templates list, backed by a shared cached store singleton (FE-M2). The
 * single-item `usePromptTemplate` mutators call `refresh()` to invalidate this
 * cache after they create/save/delete.
 */
export const usePromptTemplatesStore = defineListStore<PromptTemplate>("prompt-templates", {
  label: "prompt template",
  list: () => client.GET("/api/prompt-templates/", { params: { query: { limit: 50 } } }),
});

export function usePromptTemplates() {
  const store = usePromptTemplatesStore();
  const { items: templates, loading, error } = storeToRefs(store);
  onMounted(() => store.ensureLoaded());
  return { templates, loading, error, refresh: store.refresh };
}
