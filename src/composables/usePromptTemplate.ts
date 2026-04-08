import { ref } from "vue";
import type { components } from "@/api/schema";

type PromptTemplateResponse = components["schemas"]["PromptTemplateResponse"];
type TemplateFragmentResponse = components["schemas"]["TemplateFragmentResponse"];
type TemplatePreviewResponse = components["schemas"]["TemplatePreviewResponse"];

export function usePromptTemplate() {
  const template = ref<PromptTemplateResponse | null>(null);
  const attachedFragments = ref<TemplateFragmentResponse[]>([]);
  const preview = ref<TemplatePreviewResponse | null>(null);
  const loading = ref(false);
  const saving = ref(false);
  const deleting = ref(false);
  const previewing = ref(false);
  const error = ref<Error | null>(null);

  async function fetchTemplate(id: string) {
    loading.value = true;
    error.value = null;
    try {
      const response = await fetch(`/api/prompt-templates/${id}`);
      if (!response.ok) throw new Error(`Failed to load template: ${response.status}`);
      template.value = await response.json();
    } catch (e) {
      error.value = e instanceof Error ? e : new Error("Unknown error");
    } finally {
      loading.value = false;
    }
  }

  async function saveTemplate(id: string, updates: Record<string, unknown>) {
    saving.value = true;
    try {
      const response = await fetch(`/api/prompt-templates/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });
      if (!response.ok) throw new Error(`Save failed: ${response.status}`);
      const data = await response.json();
      template.value = data;
      return data;
    } finally {
      saving.value = false;
    }
  }

  async function deleteTemplate(id: string) {
    deleting.value = true;
    try {
      const response = await fetch(`/api/prompt-templates/${id}`, {
        method: "DELETE",
      });
      if (!response.ok && response.status !== 204) throw new Error(`Delete failed: ${response.status}`);
    } finally {
      deleting.value = false;
    }
  }

  async function previewTemplate(id: string, sampleData: Record<string, string>) {
    previewing.value = true;
    try {
      const response = await fetch(`/api/prompt-templates/${id}/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(sampleData),
      });
      if (!response.ok) throw new Error(`Preview failed: ${response.status}`);
      preview.value = await response.json();
      return preview.value;
    } finally {
      previewing.value = false;
    }
  }

  async function fetchAttachedFragments(id: string) {
    try {
      const response = await fetch(`/api/prompt-templates/${id}/fragments/`);
      if (!response.ok) throw new Error(`Failed to load fragments: ${response.status}`);
      attachedFragments.value = await response.json();
    } catch (e) {
      console.error("Error loading attached fragments:", e);
    }
  }

  async function attachFragment(templateId: string, fragmentId: string, position: string, ordinal: number) {
    const response = await fetch(`/api/prompt-templates/${templateId}/fragments/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fragment_id: fragmentId, position, ordinal }),
    });
    if (!response.ok) throw new Error(`Attach failed: ${response.status}`);
    const data: TemplateFragmentResponse = await response.json();
    attachedFragments.value.push(data);
    return data;
  }

  async function detachFragment(templateId: string, fragmentId: string) {
    const response = await fetch(`/api/prompt-templates/${templateId}/fragments/${fragmentId}`, {
      method: "DELETE",
    });
    if (!response.ok && response.status !== 204) throw new Error(`Detach failed: ${response.status}`);
    attachedFragments.value = attachedFragments.value.filter((f) => f.fragment_id !== fragmentId);
  }

  return {
    template,
    attachedFragments,
    preview,
    loading,
    saving,
    deleting,
    previewing,
    error,
    fetchTemplate,
    saveTemplate,
    deleteTemplate,
    previewTemplate,
    fetchAttachedFragments,
    attachFragment,
    detachFragment,
  };
}
