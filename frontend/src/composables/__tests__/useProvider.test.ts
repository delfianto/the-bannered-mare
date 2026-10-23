import { beforeEach, describe, expect, it } from "vite-plus/test";
import { createPinia, setActivePinia } from "pinia";
import { http, HttpResponse } from "msw";
import { useProvider } from "@/composables/useProvider";
import { useSettingsStore } from "@/stores/settings";
import { server } from "@/mocks/server";
import { providers } from "@/mocks/data/providers";

const provider = providers[0];
const discovered = (id: string) => ({
  identifier: id,
  display_name: id,
  state: "not-loaded" as const,
  size_bytes: null,
  quantization: null,
  max_context_length: 8192,
});
const catalog = {
  models: [discovered("Zebra"), discovered("Alpha")],
  last_synced_at: "2026-10-23T00:00:00Z",
};
beforeEach(() => setActivePinia(createPinia()));
function setup() {
  server.use(http.get("/api/providers/:id", () => HttpResponse.json(provider)));
  return useProvider();
}

describe("provider detail", () => {
  it("saving provider settings refreshes the shared list for other consumers", async () => {
    const api = setup();
    await api.fetchProvider(provider.id);
    let reads = 0;
    const edited = { ...provider, name: "Edited provider" };
    server.use(
      http.put("/api/providers/:id", async ({ request }) => {
        expect(await request.json()).toEqual({ name: edited.name });
        return HttpResponse.json(edited);
      }),
      http.get("/api/providers", () => {
        reads++;
        return HttpResponse.json({ items: [edited] });
      }),
    );
    await api.saveProvider(provider.id, { name: edited.name });
    expect(api.provider.value?.name).toBe(edited.name);
    expect(useSettingsStore().providers[0].name).toBe(edited.name);
    expect(reads).toBe(1);
  });

  it("sorts discovered models and updates the sync timestamp", async () => {
    const api = setup();
    await api.fetchProvider(provider.id);
    server.use(
      http.get("/api/providers/:id/models/available", () => HttpResponse.json(catalog)),
      http.post("/api/providers/:id/models/sync", () => HttpResponse.json(catalog)),
    );
    await api.fetchAvailableModels(provider.id);
    expect(api.availableModels.value.map((m) => m.identifier)).toEqual(["Alpha", "Zebra"]);
    expect(api.provider.value?.last_synced_at).toBe(catalog.last_synced_at);
    await api.syncNow(provider.id);
    expect(api.syncing.value).toBe(false);
    expect(api.modelsError.value).toBeNull();
  });

  it("discovery failures preserve the last good list and record a retryable error", async () => {
    const api = setup();
    api.availableModels.value = [discovered("kept")];
    server.use(
      http.get("/api/providers/:id/models/available", () =>
        HttpResponse.json({ detail: "Offline" }, { status: 503 }),
      ),
    );
    await api.fetchAvailableModels(provider.id);
    expect(api.availableModels.value[0].identifier).toBe("kept");
    expect(api.modelsLoading.value).toBe(false);
    expect(api.modelsError.value).toBeInstanceOf(Error);
  });

  it("searches with encoded query text and clears results", async () => {
    const api = setup();
    server.use(
      http.get("/api/providers/:id/models/search", ({ request }) => {
        expect(new URL(request.url).searchParams.get("q")).toBe("meta/muse & llama");
        return HttpResponse.json(catalog);
      }),
    );
    expect(await api.searchModels(provider.id, "meta/muse & llama")).toEqual(catalog.models);
    expect(api.searchingModels.value).toBe(false);
    api.clearSearch();
    expect(api.searchResults.value).toEqual([]);
  });

  it("persists an allow-list and applies the filtered catalog atomically after success", async () => {
    const api = setup();
    await api.fetchProvider(provider.id);
    server.use(
      http.put("/api/providers/:id/models/filter", async ({ request }) => {
        expect(await request.json()).toEqual({ allowed_models: ["meta/muse-wonder"] });
        return HttpResponse.json(catalog);
      }),
    );
    await api.setModelFilter(provider.id, ["meta/muse-wonder"]);
    expect(api.provider.value?.allowed_models).toEqual(["meta/muse-wonder"]);
    expect(api.savingFilter.value).toBe(false);
    server.use(
      http.put("/api/providers/:id/models/filter", () => HttpResponse.json({}, { status: 500 })),
    );
    await expect(api.setModelFilter(provider.id, [])).rejects.toThrow();
    expect(api.provider.value?.allowed_models).toEqual(["meta/muse-wonder"]);
    expect(api.savingFilter.value).toBe(false);
  });

  it.each(["loadModel", "unloadModel", "deleteModel"] as const)(
    "%s sends the identifier and refreshes runtime state",
    async (action) => {
      const api = setup();
      const identifier = "model:quant/q4";
      let reads = 0;
      const endpoint = action === "loadModel" ? "load" : "unload";
      const handler =
        action === "deleteModel"
          ? http.delete("/api/providers/:id/models", ({ request }) => {
              expect(new URL(request.url).searchParams.get("model_identifier")).toBe(identifier);
              return new HttpResponse(null, { status: 204 });
            })
          : http.post(`/api/providers/:id/models/${endpoint}`, async ({ request }) => {
              expect(await request.json()).toEqual({ model_identifier: identifier });
              return new HttpResponse(null, { status: 204 });
            });
      server.use(
        handler,
        http.get("/api/providers/:id/models/available", () => {
          reads++;
          return HttpResponse.json(catalog);
        }),
      );
      const pending = api[action](provider.id, identifier);
      expect(api.pendingModelAction.value).toBe(identifier);
      await pending;
      expect(api.pendingModelAction.value).toBeNull();
      expect(reads).toBe(1);
    },
  );

  it.each(["loadModel", "unloadModel", "deleteModel", "persistModel"] as const)(
    "%s clears its busy state after failure",
    async (action) => {
      const api = setup();
      server.use(
        http.all("/api/providers/:id/models/*", () =>
          HttpResponse.json({ detail: "Offline" }, { status: 503 }),
        ),
        http.delete("/api/providers/:id/models", () => HttpResponse.json({}, { status: 503 })),
      );
      await expect(api[action](provider.id, "model")).rejects.toThrow();
      expect(api.pendingModelAction.value).toBeNull();
    },
  );
});
