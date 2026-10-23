import { afterEach, beforeEach, describe, expect, it, vi } from "vite-plus/test";
import { effectScope, ref, nextTick, type EffectScope } from "vue";
import { flushPromises } from "@vue/test-utils";
import { useAssetCache } from "@/composables/useAssetCache";
import { deferred } from "@/test/helpers";

const scopes: EffectScope[] = [];
const cacheDescriptor = Object.getOwnPropertyDescriptor(window, "caches");
let sequence = 0;
function consumer(url: ReturnType<typeof ref<string | null>>) {
  const scope = effectScope();
  scopes.push(scope);
  return { scope, api: scope.run(() => useAssetCache(url))! };
}
function cacheSetup() {
  const cache = {
    match: vi.fn(async (_url: string): Promise<Response | undefined> => undefined),
    put: vi.fn(async () => {}),
  };
  const storage = { open: vi.fn(async () => cache) };
  vi.stubGlobal("caches", storage);
  Object.defineProperty(window, "caches", { value: storage, configurable: true });
  const create = vi
    .spyOn(URL, "createObjectURL")
    .mockImplementation(() => `blob:test-${++sequence}`);
  const revoke = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
  const fetch = vi.fn(async () => new Response("image"));
  vi.stubGlobal("fetch", fetch);
  return { cache, storage, create, revoke, fetch };
}
beforeEach(() => vi.spyOn(console, "warn").mockImplementation(() => {}));
afterEach(async () => {
  scopes.splice(0).forEach((s) => s.stop());
  await flushPromises();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  if (cacheDescriptor) Object.defineProperty(window, "caches", cacheDescriptor);
  else Reflect.deleteProperty(window, "caches");
});

describe("asset cache lifecycle", () => {
  it("an absent asset has no source and makes no request", async () => {
    const { fetch } = cacheSetup();
    const { api } = consumer(ref(null));
    await flushPromises();
    expect(api.src.value).toBeUndefined();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("serves a persistent cache hit without fetching and releases the blob on dispose", async () => {
    const { cache, fetch, revoke } = cacheSetup();
    cache.match.mockResolvedValueOnce(new Response("cached image"));
    const { api, scope } = consumer(ref("/cached-avatar"));
    await flushPromises();
    expect(api.src.value).toMatch(/^blob:test-/);
    expect(fetch).not.toHaveBeenCalled();
    const blob = api.src.value;
    scope.stop();
    expect(revoke).toHaveBeenCalledWith(blob);
    expect(revoke).toHaveBeenCalledTimes(1);
  });

  it("shares an in-flight download and keeps the URL alive until the last consumer leaves", async () => {
    const { fetch, create, revoke } = cacheSetup();
    const gate = deferred<Response>();
    fetch.mockReturnValueOnce(gate.promise);
    const a = consumer(ref("/shared-avatar"));
    const b = consumer(ref("/shared-avatar"));
    await flushPromises();
    expect(fetch).toHaveBeenCalledTimes(1);
    gate.resolve(new Response("image"));
    await flushPromises();
    expect(a.api.src.value).toBe(b.api.src.value);
    expect(create).toHaveBeenCalledTimes(1);
    a.scope.stop();
    expect(revoke).not.toHaveBeenCalled();
    b.scope.stop();
    expect(revoke).toHaveBeenCalledTimes(1);
  });

  it("a warm in-memory URL can be shared without reading persistent storage again", async () => {
    const { storage, revoke } = cacheSetup();
    const a = consumer(ref("/warm-avatar"));
    await flushPromises();
    const b = consumer(ref("/warm-avatar"));
    await flushPromises();
    expect(storage.open).toHaveBeenCalledTimes(1);
    a.scope.stop();
    expect(revoke).not.toHaveBeenCalled();
    expect(b.api.src.value).toBe(a.api.src.value);
  });

  it("changing the source releases the old URL and an absent source clears the image", async () => {
    const { revoke } = cacheSetup();
    const source = ref<string | null>("/old-avatar");
    const { api } = consumer(source);
    await flushPromises();
    const old = api.src.value;
    source.value = "/new-avatar";
    await nextTick();
    await flushPromises();
    expect(revoke).toHaveBeenCalledWith(old);
    expect(api.src.value).not.toBe(old);
    source.value = null;
    await nextTick();
    expect(api.src.value).toBeUndefined();
    expect(revoke).toHaveBeenCalledTimes(2);
  });

  it("a late download after disposal does not leak an unowned object URL", async () => {
    const { fetch, create, revoke } = cacheSetup();
    const gate = deferred<Response>();
    fetch.mockReturnValueOnce(gate.promise);
    const { scope } = consumer(ref("/abandoned-avatar"));
    await flushPromises();
    scope.stop();
    gate.resolve(new Response("image"));
    await flushPromises();
    expect(create).toHaveBeenCalledTimes(1);
    expect(revoke).toHaveBeenCalledWith(create.mock.results[0].value);
  });

  it("cancelling one pending consumer does not revoke the URL needed by another", async () => {
    const { fetch, revoke } = cacheSetup();
    const gate = deferred<Response>();
    fetch.mockReturnValueOnce(gate.promise);
    const a = consumer(ref("/pending-shared-avatar"));
    const b = consumer(ref("/pending-shared-avatar"));
    await flushPromises();
    a.scope.stop();
    gate.resolve(new Response("image"));
    await flushPromises();
    expect(b.api.src.value).toMatch(/^blob:test-/);
    expect(revoke).not.toHaveBeenCalled();
    b.scope.stop();
    expect(revoke).toHaveBeenCalledTimes(1);
  });

  it("a quota failure still renders the downloaded asset", async () => {
    const { cache } = cacheSetup();
    cache.put.mockRejectedValueOnce(new Error("quota exceeded"));
    const { api } = consumer(ref("/quota-avatar"));
    await flushPromises();
    expect(api.src.value).toMatch(/^blob:test-/);
    expect(api.error.value).toBeNull();
  });

  it("network failures fall back to the original URL and a later attempt can retry", async () => {
    const { fetch } = cacheSetup();
    fetch.mockRejectedValueOnce(new Error("offline"));
    const source = ref<string | null>("/retry-avatar");
    const { api } = consumer(source);
    await flushPromises();
    expect(api.src.value).toBe("/retry-avatar");
    expect(api.error.value?.message).toBe("offline");
    source.value = null;
    await nextTick();
    source.value = "/retry-avatar";
    await nextTick();
    await flushPromises();
    expect(api.error.value).toBeNull();
    expect(api.src.value).toMatch(/^blob:test-/);
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it("falls back directly to the original URL when CacheStorage is unavailable", async () => {
    const { fetch } = cacheSetup();
    Reflect.deleteProperty(window, "caches");
    const { api } = consumer(ref("/uncached-avatar"));
    await flushPromises();
    expect(api.src.value).toBe("/uncached-avatar");
    expect(fetch).not.toHaveBeenCalled();
  });
});
