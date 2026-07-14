import { client } from "@/api/client";
import { useEntityCrud } from "@/composables/useEntityCrud";
import type { components } from "@/api/schema";

type FragmentResponse = components["schemas"]["FragmentResponse"];
type FragmentCreate = components["schemas"]["FragmentCreate"];
type FragmentUpdate = components["schemas"]["FragmentUpdate"];

export function usePromptFragment() {
  const crud = useEntityCrud<FragmentResponse, FragmentCreate, FragmentUpdate>({
    label: "fragment",
    fetchOne: (id) =>
      client.GET("/api/prompt-fragments/{fragment_id}", { params: { path: { fragment_id: id } } }),
    create: (body) => client.POST("/api/prompt-fragments/", { body }),
    update: (id, body) =>
      client.PUT("/api/prompt-fragments/{fragment_id}", {
        params: { path: { fragment_id: id } },
        body,
      }),
    remove: (id) =>
      client.DELETE("/api/prompt-fragments/{fragment_id}", {
        params: { path: { fragment_id: id } },
      }),
  });

  return {
    fragment: crud.item,
    loading: crud.loading,
    saving: crud.saving,
    deleting: crud.deleting,
    error: crud.error,
    fetchFragment: crud.fetchItem,
    createFragment: crud.createItem,
    saveFragment: crud.updateItem,
    deleteFragment: crud.removeItem,
  };
}
