import { ref, watchEffect, onScopeDispose, toValue, type MaybeRefOrGetter } from "vue";

const CACHE_NAME = "candlekeep-assets-v1";

interface RegistryEntry {
  blobUrl: string;
  refCount: number;
}

const blobUrlRegistry = new Map<string, RegistryEntry>();
const inFlightRequests = new Map<string, Promise<string>>();

export function useAssetCache(urlSource: MaybeRefOrGetter<string | undefined | null>) {
  const cachedSrc = ref<string | undefined>(undefined);
  const error = ref<Error | null>(null);

  let currentRegisteredUrl: string | undefined;

  const releaseUrl = (url: string) => {
    const entry = blobUrlRegistry.get(url);
    if (entry) {
      entry.refCount--;
      if (entry.refCount <= 0) {
        URL.revokeObjectURL(entry.blobUrl);
        blobUrlRegistry.delete(url);
      }
    }
  };

  onScopeDispose(() => {
    if (currentRegisteredUrl) {
      releaseUrl(currentRegisteredUrl);
    }
  });

  watchEffect(async (onCleanup) => {
    const url = toValue(urlSource);
    let isCancelled = false;

    onCleanup(() => {
      isCancelled = true;
      if (currentRegisteredUrl) {
        releaseUrl(currentRegisteredUrl);
        currentRegisteredUrl = undefined;
      }
    });

    error.value = null;

    if (!url) {
      cachedSrc.value = undefined;
      return;
    }

    const existing = blobUrlRegistry.get(url);
    if (existing) {
      existing.refCount++;
      currentRegisteredUrl = url;
      cachedSrc.value = existing.blobUrl;
      return;
    }

    let requestPromise = inFlightRequests.get(url);

    if (!requestPromise) {
      requestPromise = (async () => {
        try {
          if (typeof window === "undefined" || !("caches" in window)) {
            return url;
          }

          const cache = await caches.open(CACHE_NAME);
          const cachedResponse = await cache.match(url);

          let blob: Blob;
          if (cachedResponse) {
            blob = await cachedResponse.blob();
          } else {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`Failed to fetch: ${response.statusText}`);
            try {
              await cache.put(url, response.clone());
            } catch (err) {
              console.warn("Cache put failed:", err);
            }
            blob = await response.blob();
          }

          const blobUrl = URL.createObjectURL(blob);

          blobUrlRegistry.set(url, {
            blobUrl,
            refCount: 0,
          });

          return blobUrl;
        } catch (e) {
          inFlightRequests.delete(url);
          throw e;
        } finally {
          inFlightRequests.delete(url);
        }
      })();

      inFlightRequests.set(url, requestPromise);
    }

    try {
      const blobUrl = await requestPromise;
      if (isCancelled) return;

      const entry = blobUrlRegistry.get(url);
      if (entry) {
        entry.refCount++;
        currentRegisteredUrl = url;
        cachedSrc.value = blobUrl;
      } else {
        cachedSrc.value = blobUrl;
      }
    } catch (e) {
      if (isCancelled) return;
      console.warn("Asset cache failed:", e);
      error.value = e as Error;
      cachedSrc.value = url;
    }
  });

  return {
    src: cachedSrc,
    error,
  };
}
