import { afterEach, beforeEach, describe, expect, it, vi } from "vite-plus/test";
import { createPinia, setActivePinia } from "pinia";
import { http, HttpResponse } from "msw";
import { server } from "@/mocks/server";
import { useSettingsStore } from "@/stores/settings";
import { providers } from "@/mocks/data/providers";
import { deferred } from "@/test/helpers";

beforeEach(() => {
  setActivePinia(createPinia());
  vi.spyOn(console, "error").mockImplementation(() => {});
});
afterEach(() => vi.restoreAllMocks());

describe("settings cache", () => {
  it("deduplicates concurrent provider loads, sorts names, and caches the response", async () => {
    const gate = deferred<void>();
    let reads = 0;
    server.use(
      http.get("/api/providers", async () => {
        reads++;
        await gate.promise;
        return HttpResponse.json({
          items: [
            { ...providers[0], name: "Zebra" },
            { ...providers[1], name: "Alpha" },
          ],
        });
      }),
    );
    const store = useSettingsStore();
    const pending = store.fetchProviders();
    await store.fetchProviders();
    expect(store.isLoadingProviders).toBe(true);
    gate.resolve();
    await pending;
    expect(store.providers.map((p) => p.name)).toEqual(["Alpha", "Zebra"]);
    await store.fetchProviders();
    expect(reads).toBe(1);
    await store.fetchProviders(true);
    expect(reads).toBe(2);
  });

  it("keeps cached providers after a failed forced refresh and supports retry", async () => {
    const store = useSettingsStore();
    server.use(http.get("/api/providers", () => HttpResponse.json({ items: [providers[0]] })));
    await store.fetchProviders();
    server.use(
      http.get("/api/providers", () =>
        HttpResponse.json({ detail: "Unavailable" }, { status: 503 }),
      ),
    );
    await store.fetchProviders(true);
    expect(store.providers).toHaveLength(1);
    expect(store.providersError?.message).toBe("Unavailable");
    expect(store.isLoadingProviders).toBe(false);
    server.use(http.get("/api/providers", () => HttpResponse.json({ items: [] })));
    await store.fetchProviders(true);
    expect(store.providersError).toBeNull();
    expect(store.providers).toEqual([]);
  });

  it("caches parameter documentation once and allows retry after failure", async () => {
    let reads = 0;
    server.use(
      http.get("/api/model-families/parameter-docs", () => {
        reads++;
        return HttpResponse.json({ detail: "Oops" }, { status: 500 });
      }),
    );
    const store = useSettingsStore();
    await store.fetchParameterDocs();
    expect(store.hasLoadedDocs).toBe(false);
    expect(store.isLoadingDocs).toBe(false);
    server.use(
      http.get("/api/model-families/parameter-docs", () => {
        reads++;
        return HttpResponse.json({
          temperature: { label: "Temperature", short_info: "Sampling", detailed_info: "Details" },
        });
      }),
    );
    await store.fetchParameterDocs();
    await store.fetchParameterDocs();
    expect(store.parameterDocs.temperature.label).toBe("Temperature");
    expect(reads).toBe(2);
  });
});
