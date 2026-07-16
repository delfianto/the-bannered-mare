import { ref } from "vue";
import { client, extractApiError } from "@/api/client";
import { useEntityCrud } from "@/composables/useEntityCrud";
import { usePromptTemplatesStore } from "@/composables/usePromptTemplates";
import type { components } from "@/api/schema";

type PromptTemplateResponse = components["schemas"]["PromptTemplateResponse"];
type PromptTemplateCreate = components["schemas"]["PromptTemplateCreate"];
type PromptTemplateUpdate = components["schemas"]["PromptTemplateUpdate"];
type TemplateFragmentResponse = components["schemas"]["TemplateFragmentResponse"];
type TemplatePreviewResponse = components["schemas"]["TemplatePreviewResponse"];
type TemplatePreviewRequest = components["schemas"]["TemplatePreviewRequest"];

export function usePromptTemplate() {
  const crud = useEntityCrud<PromptTemplateResponse, PromptTemplateCreate, PromptTemplateUpdate>({
    label: "template",
    fetchOne: (id) =>
      client.GET("/api/prompt-templates/{template_id}", { params: { path: { template_id: id } } }),
    create: (body) => client.POST("/api/prompt-templates/", { body }),
    update: (id, body) =>
      client.PUT("/api/prompt-templates/{template_id}", {
        params: { path: { template_id: id } },
        body,
      }),
    remove: (id) =>
      client.DELETE("/api/prompt-templates/{template_id}", {
        params: { path: { template_id: id } },
      }),
  });

  // Invalidate the shared templates list after a create/save/delete, so
  // the cached singleton every list consumer reads stays in sync.
  const store = usePromptTemplatesStore();

  async function createTemplate(body: PromptTemplateCreate) {
    const created = await crud.createItem(body);
    await store.refresh();
    return created;
  }

  async function saveTemplate(id: string, body: PromptTemplateUpdate) {
    const saved = await crud.updateItem(id, body);
    await store.refresh();
    return saved;
  }

  async function deleteTemplate(id: string) {
    await crud.removeItem(id);
    await store.refresh();
  }

  const attachedFragments = ref<TemplateFragmentResponse[]>([]);
  const preview = ref<TemplatePreviewResponse | null>(null);
  const previewing = ref(false);

  async function previewTemplate(id: string, sampleData: Partial<TemplatePreviewRequest>) {
    previewing.value = true;
    try {
      const { data, error: apiError } = await client.POST(
        "/api/prompt-templates/{template_id}/preview",
        {
          params: { path: { template_id: id } },
          // The backend supplies defaults for the mock fields; openapi-typescript
          // still marks them required, so a partial sample is valid at runtime.
          body: sampleData as TemplatePreviewRequest,
        },
      );
      if (apiError || !data) throw extractApiError(apiError, "Failed to preview template");
      preview.value = data;
      return data;
    } finally {
      previewing.value = false;
    }
  }

  async function fetchAttachedFragments(id: string) {
    try {
      const { data, error: apiError } = await client.GET(
        "/api/prompt-templates/{template_id}/fragments/",
        { params: { path: { template_id: id } } },
      );
      if (apiError || !data) throw extractApiError(apiError, "Failed to load fragments");
      attachedFragments.value = data.items;
    } catch (e) {
      console.error("Error loading attached fragments:", e);
    }
  }

  async function attachFragment(
    templateId: string,
    fragmentId: string,
    position: string,
    ordinal: number,
  ) {
    const { data, error: apiError } = await client.POST(
      "/api/prompt-templates/{template_id}/fragments/",
      {
        params: { path: { template_id: templateId } },
        body: { fragment_id: fragmentId, position, ordinal },
      },
    );
    if (apiError || !data) throw extractApiError(apiError, "Failed to attach fragment");
    attachedFragments.value.push(data);
    return data;
  }

  async function detachFragment(templateId: string, fragmentId: string) {
    const { error: apiError } = await client.DELETE(
      "/api/prompt-templates/{template_id}/fragments/{fragment_id}",
      { params: { path: { template_id: templateId, fragment_id: fragmentId } } },
    );
    if (apiError) throw extractApiError(apiError, "Failed to detach fragment");
    attachedFragments.value = attachedFragments.value.filter((f) => f.fragment_id !== fragmentId);
  }

  return {
    template: crud.item,
    attachedFragments,
    preview,
    loading: crud.loading,
    saving: crud.saving,
    deleting: crud.deleting,
    previewing,
    error: crud.error,
    fetchTemplate: crud.fetchItem,
    createTemplate,
    saveTemplate,
    deleteTemplate,
    previewTemplate,
    fetchAttachedFragments,
    attachFragment,
    detachFragment,
  };
}
