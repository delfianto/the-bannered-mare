import { afterEach, beforeEach, describe, expect, it, vi } from "vite-plus/test";
import { createPinia, setActivePinia } from "pinia";
import { http, HttpResponse } from "msw";
import { usePreset } from "@/composables/usePreset";
import { usePresetsStore } from "@/composables/usePresets";
import { usePresetImport } from "@/composables/usePresetImport";
import { presets } from "@/mocks/data/presets";
import { server } from "@/mocks/server";

beforeEach(() => {
  setActivePinia(createPinia());
  vi.spyOn(console, "error").mockImplementation(() => {});
});
afterEach(() => vi.restoreAllMocks());

describe("preset writes invalidate shared dropdown data", () => {
  it("save and default selection refresh the shared cache", async () => {
    const saved = { ...presets[0], name: "Edited" };
    let reads = 0;
    server.use(
      http.put("/api/presets/:id", () => HttpResponse.json(saved)),
      http.post("/api/presets/:id/default", () =>
        HttpResponse.json({ ...saved, is_default: true }),
      ),
      http.get("/api/presets/", () => {
        reads++;
        return HttpResponse.json({ items: [saved] });
      }),
    );
    const api = usePreset();
    await api.savePreset(saved.id, { name: "Edited" });
    expect(usePresetsStore().items[0].name).toBe("Edited");
    expect(api.preset.value?.name).toBe("Edited");
    await api.setDefault(saved.id);
    expect(api.preset.value?.is_default).toBe(true);
    expect(reads).toBe(2);
  });

  it("delete refreshes only after a successful write", async () => {
    let reads = 0;
    server.use(
      http.delete("/api/presets/:id", () =>
        HttpResponse.json({ detail: "In use" }, { status: 409 }),
      ),
      http.get("/api/presets/", () => {
        reads++;
        return HttpResponse.json({ items: [] });
      }),
    );
    const api = usePreset();
    await expect(api.deletePreset("p")).rejects.toThrow("In use");
    expect(reads).toBe(0);
    server.use(http.delete("/api/presets/:id", () => new HttpResponse(null, { status: 204 })));
    await api.deletePreset("p");
    expect(reads).toBe(1);
  });

  it("uploads a preset file, exposes warnings, and refreshes cached presets", async () => {
    let reads = 0;
    const result = {
      template_id: "tpl",
      template_name: "Imported",
      preset_id: "new",
      warnings: ["Unknown sampler ignored"],
    };
    server.use(
      http.post("/api/presets/import", async ({ request }) => {
        const body = await request.formData();
        const file = body.get("file") as File;
        expect(file.name).toBe("preset.json");
        expect(await file.text()).toBe('{"temperature":0.8}');
        return HttpResponse.json(result);
      }),
      http.get("/api/presets/", () => {
        reads++;
        return HttpResponse.json({ items: [{ ...presets[0], id: "new" }] });
      }),
    );
    const api = usePresetImport();
    const pending = api.importPreset(new File(['{"temperature":0.8}'], "preset.json"));
    expect(api.importing.value).toBe(true);
    expect(await pending).toEqual(result);
    expect(api.result.value?.warnings).toEqual(result.warnings);
    expect(api.importing.value).toBe(false);
    expect(reads).toBe(1);
    api.reset();
    expect(api.result.value).toBeNull();
    expect(api.error.value).toBeNull();
  });

  it("failed import retains cached presets, records validation errors, and resets its busy flag", async () => {
    const store = usePresetsStore();
    store.upsert(presets[0]);
    server.use(
      http.post("/api/presets/import", () =>
        HttpResponse.json({ detail: "Invalid preset JSON" }, { status: 422 }),
      ),
    );
    const api = usePresetImport();
    expect(await api.importPreset(new File(["{"], "bad.json"))).toBeNull();
    expect(api.error.value?.message).toBe("Invalid preset JSON");
    expect(api.importing.value).toBe(false);
    expect(store.items).toHaveLength(1);
    api.reset();
    expect(api.error.value).toBeNull();
  });
});
