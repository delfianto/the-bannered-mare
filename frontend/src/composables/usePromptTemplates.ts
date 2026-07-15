import type { components } from "@/api/schema";
import { client } from "@/api/client";
import { useListCrud } from "@/composables/useListCrud";

export type PromptTemplate = components["schemas"]["PromptTemplateResponse"];

export function usePromptTemplates() {
  const {
    items: templates,
    loading,
    error,
    refresh,
  } = useListCrud<PromptTemplate>({
    label: "prompt templates",
    list: () => client.GET("/api/prompt-templates/", { params: { query: { limit: 50 } } }),
  });

  return { templates, loading, error, refresh };
}
