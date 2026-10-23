import { afterEach, describe, expect, it } from "vite-plus/test";
import { http, HttpResponse } from "msw";
import { useServerStatus } from "@/composables/useServerStatus";
import { server } from "@/mocks/server";
import { deferred } from "@/test/helpers";

afterEach(() => useServerStatus().reportResponse(200));
describe("backend status retry", () => {
  it.each([200, 500, 502, 503, 504])(
    "reports HTTP %s and releases the checking flag",
    async (status) => {
      server.use(http.get("/api/providers", () => HttpResponse.json({}, { status })));
      const api = useServerStatus();
      api.reportNetworkError();
      const pending = api.checkNow();
      expect(api.checking.value).toBe(true);
      expect(await pending).toBe(![502, 503, 504].includes(status));
      expect(api.checking.value).toBe(false);
    },
  );

  it("network failure is retryable and status is shared between banner consumers", async () => {
    const api = useServerStatus();
    server.use(http.get("/api/providers", () => HttpResponse.error()));
    expect(await api.checkNow()).toBe(false);
    expect(useServerStatus().reachable.value).toBe(false);
    const gate = deferred<void>();
    server.use(
      http.get("/api/providers", async () => {
        await gate.promise;
        return HttpResponse.json({ items: [] });
      }),
    );
    const pending = api.checkNow();
    expect(useServerStatus().checking.value).toBe(true);
    gate.resolve();
    expect(await pending).toBe(true);
    expect(api.checking.value).toBe(false);
  });
});
