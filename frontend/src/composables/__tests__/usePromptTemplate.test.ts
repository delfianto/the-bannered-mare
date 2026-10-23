import { afterEach, beforeEach, describe, expect, it, vi } from "vite-plus/test";
import { createPinia, setActivePinia } from "pinia";
import { http, HttpResponse } from "msw";
import { usePromptTemplate } from "@/composables/usePromptTemplate";
import { usePromptTemplatesStore } from "@/composables/usePromptTemplates";
import { promptTemplates, templateFragments } from "@/mocks/data/prompt-templates";
import { server } from "@/mocks/server";

beforeEach(() => {
  setActivePinia(createPinia());
  vi.spyOn(console, "error").mockImplementation(() => {});
});
afterEach(() => vi.restoreAllMocks());

describe("prompt template composition", () => {
  it("create, save and delete invalidate the shared template list", async () => {
    const row = structuredClone(promptTemplates[0]);
    let reads = 0;
    server.use(
      http.post("/api/prompt-templates/", () => HttpResponse.json(row)),
      http.put("/api/prompt-templates/:id", () => HttpResponse.json({ ...row, name: "Edited" })),
      http.delete("/api/prompt-templates/:id", () => new HttpResponse(null, { status: 204 })),
      http.get("/api/prompt-templates/", () => {
        reads++;
        return HttpResponse.json({ items: [{ ...row, name: "Snapshot " + reads }] });
      }),
    );
    const api = usePromptTemplate();
    await api.createTemplate(row);
    await api.saveTemplate(row.id, { name: "Edited" });
    expect(api.template.value?.name).toBe("Edited");
    expect(usePromptTemplatesStore().items[0].name).toBe("Snapshot 2");
    await api.deleteTemplate(row.id);
    expect(reads).toBe(3);
  });

  it("preview sends sample data, renders the response and preserves the previous preview after failure", async () => {
    const api = usePromptTemplate();
    server.use(
      http.post("/api/prompt-templates/:id/preview", async ({ request }) => {
        expect(await request.json()).toEqual({ character_name: "Lydia" });
        return HttpResponse.json({ rendered: "You are Lydia" });
      }),
    );
    const pending = api.previewTemplate("tpl", { character_name: "Lydia" });
    expect(api.previewing.value).toBe(true);
    await pending;
    expect(api.preview.value).toMatchObject({ rendered: "You are Lydia" });
    server.use(
      http.post("/api/prompt-templates/:id/preview", () =>
        HttpResponse.json({ detail: "Invalid Jinja" }, { status: 422 }),
      ),
    );
    await expect(api.previewTemplate("tpl", {})).rejects.toThrow("Invalid Jinja");
    expect(api.previewing.value).toBe(false);
    expect(api.preview.value).toMatchObject({ rendered: "You are Lydia" });
  });

  it("loads, attaches and detaches fragments with ordering and insertion position intact", async () => {
    const fragment = structuredClone(templateFragments.get(promptTemplates[0].id)![0]);
    const api = usePromptTemplate();
    server.use(
      http.get("/api/prompt-templates/:id/fragments/", () =>
        HttpResponse.json({ items: [fragment] }),
      ),
      http.post("/api/prompt-templates/:id/fragments/", async ({ request }) => {
        expect(await request.json()).toEqual({
          fragment_id: "new",
          position: "pre_history",
          ordinal: 2,
        });
        return HttpResponse.json({
          ...fragment,
          fragment_id: "new",
          ordinal: 2,
          position: "pre_history",
        });
      }),
      http.delete(
        "/api/prompt-templates/:id/fragments/:fragment",
        () => new HttpResponse(null, { status: 204 }),
      ),
    );
    await api.fetchAttachedFragments("tpl");
    await api.attachFragment("tpl", "new", "pre_history", 2);
    expect(api.attachedFragments.value.map((f) => f.fragment_id)).toEqual([
      fragment.fragment_id,
      "new",
    ]);
    await api.detachFragment("tpl", fragment.fragment_id);
    expect(api.attachedFragments.value).toHaveLength(1);
    expect(api.attachedFragments.value[0].fragment_id).toBe("new");
  });

  it("failed attach/detach preserves attachments and reports the failure", async () => {
    const api = usePromptTemplate();
    api.attachedFragments.value = structuredClone(
      templateFragments.get(promptTemplates[0].id)!.slice(0, 1),
    );
    server.use(
      http.post("/api/prompt-templates/:id/fragments/", () =>
        HttpResponse.json({ detail: "Duplicate" }, { status: 409 }),
      ),
      http.delete("/api/prompt-templates/:id/fragments/:fragment", () =>
        HttpResponse.json({ detail: "In use" }, { status: 409 }),
      ),
    );
    await expect(api.attachFragment("tpl", "new", "pre_history", 1)).rejects.toThrow("Duplicate");
    await expect(
      api.detachFragment("tpl", templateFragments.get(promptTemplates[0].id)![0].fragment_id),
    ).rejects.toThrow("In use");
    expect(api.attachedFragments.value).toHaveLength(1);
  });
});
