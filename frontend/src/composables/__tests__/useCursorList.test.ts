import { defineComponent, h } from "vue";
import { describe, it, expect, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { useCursorList } from "@/composables/useCursorList";

// The cursor/infinite-scroll machinery's concurrency guards: the
// monotonic `requestSeq` last-request-wins discard, `reset()` invalidating an
// in-flight load, and `loadMore` gating on hasMore/cursor. `fetchPage` is a
// caller-supplied closure, so these drive the composable directly with mock
// closures — no fetch/MSW involved.

interface Item {
  id: string;
}
type Page = { items: Item[]; meta: { has_more: boolean; cursor: string | null } };
type FetchResult = { data?: Page; error?: unknown };

interface ListOptions {
  fetchPage: (cursor: string | undefined, pageSize: number) => Promise<FetchResult> | null;
  merge: (existing: Item[], batch: Item[], isInitial: boolean) => Item[];
  pageSize?: number;
  hasMoreInitial?: boolean;
  autoLoad?: boolean;
  errorContext?: string;
}

// A promise whose resolution is controlled externally, so a test can settle two
// concurrent loads out of order.
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function page(items: Item[], hasMore = false, cursor: string | null = null): FetchResult {
  return { data: { items, meta: { has_more: hasMore, cursor } } };
}

const mergeAppend = (existing: Item[], batch: Item[], isInitial: boolean): Item[] =>
  isInitial ? batch : [...existing, ...batch];

// useCursorList registers an onMounted (autoLoad) hook, so instantiate it inside
// a mounted host — a bare call would warn "onMounted is called when there is no
// active component instance" and skip the lifecycle entirely.
function mountList(options: ListOptions) {
  let api!: ReturnType<typeof useCursorList<Item>>;
  const wrapper = mount(
    defineComponent({
      setup() {
        api = useCursorList<Item>(options);
        return () => h("div");
      },
    }),
  );
  return { api, wrapper };
}

describe("useCursorList", () => {
  it("last-request-wins: a stale earlier response can't clobber the newest query", async () => {
    const gates: Array<ReturnType<typeof deferred<FetchResult>>> = [];
    const fetchPage = vi.fn(() => {
      const gate = deferred<FetchResult>();
      gates.push(gate);
      return gate.promise;
    });

    const { api } = mountList({ fetchPage, merge: mergeAppend });

    const first = api.load(); // request seq 1 (e.g. filter "a")
    const second = api.load(); // request seq 2 (e.g. filter "ab") — supersedes seq 1
    expect(fetchPage).toHaveBeenCalledTimes(2);

    // Newest request resolves first and renders.
    gates[1].resolve(page([{ id: "fresh" }], false, null));
    await second;
    expect(api.items.value.map((i) => i.id)).toEqual(["fresh"]);

    // The FIRST request resolves LAST — its stale batch must be discarded whole.
    gates[0].resolve(page([{ id: "stale" }], true, "stale-cursor"));
    await first;
    expect(api.items.value.map((i) => i.id)).toEqual(["fresh"]);
    expect(api.hasMore.value).toBe(false); // from the winner, not the stale `true`
    expect(api.cursor.value).toBeNull(); // not the stale cursor
  });

  it("reset() invalidates an in-flight load so its late response is dropped", async () => {
    const gate = deferred<FetchResult>();
    const fetchPage = vi.fn(() => gate.promise);

    const { api } = mountList({ fetchPage, merge: mergeAppend, hasMoreInitial: true });

    const inflight = api.load();
    expect(api.loading.value).toBe(true);

    api.reset();
    expect(api.items.value).toEqual([]);
    expect(api.loading.value).toBe(false);

    gate.resolve(page([{ id: "late" }], true, "c1"));
    await inflight;

    // reset() bumped requestSeq, so the resolved load is discarded — the late
    // batch, its cursor, and its hasMore never land.
    expect(api.items.value).toEqual([]);
    expect(api.hasMore.value).toBe(true); // back to hasMoreInitial
    expect(api.cursor.value).toBeNull(); // not the late "c1"
  });

  it("loadMore() no-ops when hasMore is false", async () => {
    const fetchPage = vi.fn(() => Promise.resolve(page([], false, null)));
    const { api } = mountList({ fetchPage, merge: mergeAppend }); // hasMore=false by default
    await api.loadMore();
    expect(fetchPage).not.toHaveBeenCalled();
  });

  it("loadMore() no-ops when hasMore is true but there's no cursor yet", async () => {
    const fetchPage = vi.fn(() => Promise.resolve(page([], true, "c1")));
    const { api } = mountList({ fetchPage, merge: mergeAppend, hasMoreInitial: true });
    await api.loadMore(); // cursor still null → gated off
    expect(fetchPage).not.toHaveBeenCalled();
  });

  it("loadMore() fetches and appends the next page once a cursor exists", async () => {
    const fetchPage = vi
      .fn()
      .mockResolvedValueOnce(page([{ id: "a" }], true, "c1"))
      .mockResolvedValueOnce(page([{ id: "b" }], false, null));

    const { api } = mountList({ fetchPage, merge: mergeAppend });

    await api.load();
    expect(api.items.value.map((i) => i.id)).toEqual(["a"]);
    expect(api.hasMore.value).toBe(true);
    expect(api.cursor.value).toBe("c1");

    await api.loadMore();
    expect(fetchPage).toHaveBeenLastCalledWith("c1", 20); // default pageSize
    expect(api.items.value.map((i) => i.id)).toEqual(["a", "b"]);
    expect(api.hasMore.value).toBe(false);
    expect(api.cursor.value).toBeNull();
  });

  it("load() is a no-op when fetchPage returns null (no context yet)", async () => {
    const fetchPage = vi.fn(() => null);
    const { api } = mountList({ fetchPage, merge: mergeAppend });
    await api.load();
    expect(api.loading.value).toBe(false);
    expect(api.items.value).toEqual([]);
  });

  it("autoLoad triggers an initial load on mount", async () => {
    const fetchPage = vi.fn(() => Promise.resolve(page([{ id: "x" }], false, null)));
    const { api } = mountList({ fetchPage, merge: mergeAppend, autoLoad: true });
    await flushPromises();
    expect(fetchPage).toHaveBeenCalledTimes(1);
    expect(api.items.value.map((i) => i.id)).toEqual(["x"]);
  });
});
