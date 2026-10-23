import { afterEach, describe, expect, it, vi } from "vite-plus/test";
import { flushPromises } from "@vue/test-utils";
import { usePaginatedList } from "@/composables/usePaginatedList";
import { deferred, mountComposable } from "@/test/helpers";

type Result = {
  data?: {
    items: string[];
    meta: { page?: number | null; total?: number | null; has_more: boolean; limit: number };
  };
  error?: unknown;
};
const page = (items: string[], n = 1, total = 25): Result => ({
  data: { items, meta: { page: n, total, has_more: n < 3, limit: 10 } },
});
afterEach(() => vi.restoreAllMocks());

describe("page-based lists", () => {
  it("restores initial page, filters and totals through the mount lifecycle", async () => {
    const fetch = vi.fn(async () => page(["saved result"], 2));
    const { api } = mountComposable(() =>
      usePaginatedList(fetch, { pageSize: 10, initialPage: 2, initialFilters: { name: "dragon" } }),
    );
    await flushPromises();
    expect(fetch).toHaveBeenCalledWith(2, 10, { name: "dragon" });
    expect(api.page.value).toBe(2);
    expect(api.totalPages.value).toBe(3);
    expect(api.items.value).toEqual(["saved result"]);
  });

  it("disabled auto-load makes no request and an empty collection still has page one", () => {
    const fetch = vi.fn(async () => page([]));
    const { api } = mountComposable(() => usePaginatedList(fetch, { autoLoad: false }));
    expect(fetch).not.toHaveBeenCalled();
    expect(api.totalPages.value).toBe(1);
  });

  it("keeps only the newest filter result when requests settle out of order", async () => {
    const old = deferred<Result>(),
      fresh = deferred<Result>();
    const fetch = vi.fn().mockReturnValueOnce(old.promise).mockReturnValueOnce(fresh.promise);
    const { api } = mountComposable(() =>
      usePaginatedList<string, { q: string }>(fetch, { autoLoad: false }),
    );
    const p1 = api.loadPage(1, { q: "a" });
    const p2 = api.loadPage(1, { q: "ab" });
    old.resolve(page(["stale"]));
    await p1;
    expect(api.loading.value).toBe(true);
    expect(api.items.value).toEqual([]);
    fresh.resolve(page(["current"]));
    await p2;
    expect(api.items.value).toEqual(["current"]);
    expect(api.currentFilters.value).toEqual({ q: "ab" });
    expect(api.loading.value).toBe(false);
  });

  it("a superseded failure cannot overwrite a successful newer search", async () => {
    const old = deferred<Result>();
    const fetch = vi
      .fn()
      .mockReturnValueOnce(old.promise)
      .mockResolvedValueOnce(page(["winner"]));
    const { api } = mountComposable(() => usePaginatedList<string>(fetch, { autoLoad: false }));
    const pending = api.loadPage();
    await api.loadPage();
    old.reject(new Error("old failure"));
    await pending;
    expect(api.error.value).toBeNull();
    expect(api.items.value).toEqual(["winner"]);
  });

  it("appends infinite-scroll pages, gates duplicate loads and refreshes from page one", async () => {
    const gate = deferred<Result>();
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(page(["a"]))
      .mockReturnValueOnce(gate.promise)
      .mockResolvedValueOnce(page(["updated"]));
    const { api } = mountComposable(() =>
      usePaginatedList<string>(fetch, { append: true, autoLoad: false }),
    );
    await api.loadMore();
    expect(fetch).not.toHaveBeenCalled();
    await api.loadPage();
    const pending = api.loadMore();
    await api.loadMore();
    expect(fetch).toHaveBeenCalledTimes(2);
    gate.resolve(page(["b"], 2));
    await pending;
    expect(api.items.value).toEqual(["a", "b"]);
    api.refresh();
    expect(api.items.value).toEqual([]);
    await flushPromises();
    expect(api.items.value).toEqual(["updated"]);
    expect(api.page.value).toBe(1);
  });

  it("regular pagination replaces rows and refreshes the current page", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(page(["a"]))
      .mockResolvedValue(page(["b"], 2));
    const { api } = mountComposable(() => usePaginatedList<string>(fetch, { autoLoad: false }));
    await api.loadPage(1);
    await api.loadMore();
    expect(api.items.value).toEqual(["b"]);
    api.refresh();
    await flushPromises();
    expect(fetch).toHaveBeenLastCalledWith(2, 20, {});
  });

  it("shows validation errors, preserves displayed data and clears the error on retry", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(page(["kept"]))
      .mockResolvedValueOnce({ error: { detail: "Invalid filter" } })
      .mockResolvedValueOnce({ data: { items: [], meta: { limit: 10, has_more: false } } });
    const { api } = mountComposable(() => usePaginatedList<string>(fetch, { autoLoad: false }));
    await api.loadPage();
    await api.loadPage();
    expect(api.items.value).toEqual(["kept"]);
    expect(api.error.value?.message).toBe("Invalid filter");
    expect(api.loading.value).toBe(false);
    await api.loadPage(4);
    expect(api.error.value).toBeNull();
    expect(api.page.value).toBe(4);
    expect(api.total.value).toBe(0);
  });
});
