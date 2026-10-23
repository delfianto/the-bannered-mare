import { beforeEach, describe, expect, it, vi } from "vite-plus/test";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises } from "@vue/test-utils";
import { defineListStore } from "@/stores/listStore";
import { APIError } from "@/api/client";
import { deferred } from "@/test/helpers";

type Item = { id: string; name: string; is_default?: boolean };
const first: Item = { id: "a", name: "First", is_default: true };
const second: Item = { id: "b", name: "Second", is_default: false };
function setup(singleDefault = true) {
  const ops = {
    label: "preset",
    singleDefault,
    list: vi.fn(async () => ({ data: { items: [{ ...first }, { ...second }] } })),
    create: vi.fn(async (body: Item) => ({ data: body })),
    update: vi.fn(async (_id: string, body: Item) => ({ data: body })),
    remove: vi.fn(async (_id: string): Promise<{ error?: unknown; response?: Response }> => ({})),
    setDefault: vi.fn(
      async (_id: string): Promise<{ error?: unknown; response?: Response }> => ({}),
    ),
  };
  const useStore = defineListStore<Item, Item, Item>("test-list", ops);
  return { store: useStore(), useStore, ops };
}
beforeEach(() => setActivePinia(createPinia()));

describe("shared resource cache", () => {
  it("shares one fetch between consumers and serves warm reads without refetching", async () => {
    const { store, useStore, ops } = setup();
    const gate = deferred<{ data: { items: Item[] } }>();
    ops.list.mockReturnValueOnce(gate.promise);
    const other = useStore();
    store.ensureLoaded();
    other.ensureLoaded();
    expect(store.loading).toBe(true);
    expect(ops.list).toHaveBeenCalledTimes(1);
    gate.resolve({ data: { items: [first] } });
    await flushPromises();
    expect(other.items).toEqual([first]);
    expect(other.hasLoaded).toBe(true);
    store.ensureLoaded();
    expect(ops.list).toHaveBeenCalledTimes(1);
  });

  it("retries a failed cold fetch and preserves a warm cache when refresh fails", async () => {
    const { store, ops } = setup();
    ops.list.mockRejectedValueOnce(new Error("offline"));
    store.ensureLoaded();
    await flushPromises();
    expect(store.hasLoaded).toBe(false);
    expect(store.loading).toBe(false);
    expect(store.error?.message).toBe("offline");
    store.ensureLoaded();
    await flushPromises();
    expect(store.items).toHaveLength(2);
    expect(store.error).toBeNull();
    ops.list.mockRejectedValueOnce(new Error("offline again"));
    await store.refresh();
    expect(store.items).toHaveLength(2);
    expect(store.error?.message).toBe("offline again");
  });

  it("refresh invalidates a warm cache for every consumer", async () => {
    const { store, useStore, ops } = setup();
    await store.refresh();
    ops.list.mockResolvedValueOnce({ data: { items: [{ ...first, name: "Edited elsewhere" }] } });
    await useStore().refresh();
    expect(store.items[0].name).toBe("Edited elsewhere");
    expect(store.items).toHaveLength(1);
  });

  it("upsert replaces an existing row, prepends a new row, and reconciles defaults", () => {
    const { store } = setup();
    store.upsert({ ...first });
    store.upsert({ ...second });
    store.upsert({ ...second, name: "Edited", is_default: true });
    expect(store.items).toEqual([
      { ...second, name: "Edited", is_default: true },
      { ...first, is_default: false },
    ]);
  });

  it("does not unset flags on resources without the single-default policy", () => {
    const { store } = setup(false);
    store.upsert({ ...first });
    store.upsert({ ...second, is_default: true });
    expect(store.items.every((item) => item.is_default)).toBe(true);
  });

  it("successful writes keep all list consumers coherent without an extra GET", async () => {
    const { store, useStore, ops } = setup();
    await store.refresh();
    const created = { id: "c", name: "New", is_default: true };
    expect(await store.createItem(created)).toEqual(created);
    expect(store.items.find((i) => i.id === "a")?.is_default).toBe(false);
    await store.updateItem("b", { ...second, name: "Changed" });
    expect(useStore().items.find((i) => i.id === "b")?.name).toBe("Changed");
    expect(await store.setDefaultItem("b")).toBe(true);
    expect(store.items.filter((i) => i.is_default).map((i) => i.id)).toEqual(["b"]);
    expect(await store.removeItem("a")).toBe(true);
    expect(store.items.map((i) => i.id)).toEqual(["c", "b"]);
    expect(ops.list).toHaveBeenCalledTimes(1);
  });

  it.each(["create", "update", "remove", "setDefault"] as const)(
    "failed %s leaves cached rows and defaults intact",
    async (op) => {
      const { store, ops } = setup();
      await store.refresh();
      const before = JSON.parse(JSON.stringify(store.items));
      ops[op].mockRejectedValueOnce(new Error("write rejected"));
      const result =
        op === "create"
          ? await store.createItem(second)
          : op === "update"
            ? await store.updateItem("a", { ...first, name: "Lost" })
            : op === "remove"
              ? await store.removeItem("a")
              : await store.setDefaultItem("b");
      expect(result).toBe(op === "create" || op === "update" ? null : false);
      expect(store.items).toEqual(before);
      expect(store.error?.message).toBe("write rejected");
      store.clearError();
      expect(store.error).toBeNull();
    },
  );

  it("keeps HTTP status and validation detail on failed deletes", async () => {
    const { store, ops } = setup();
    await store.refresh();
    ops.remove.mockResolvedValueOnce({
      error: { detail: "Preset is in use" },
      response: new Response(null, { status: 409 }),
    });
    expect(await store.removeItem("a")).toBe(false);
    expect(store.error).toBeInstanceOf(APIError);
    expect(store.error).toMatchObject({ message: "Preset is in use", statusCode: 409 });
    expect(store.items).toHaveLength(2);
  });
});

it("late refresh responses cannot replace a newer cache snapshot", async () => {
  const { store, ops } = setup();
  const old = deferred<{ data: { items: Item[] } }>(),
    fresh = deferred<{ data: { items: Item[] } }>();
  ops.list.mockReturnValueOnce(old.promise).mockReturnValueOnce(fresh.promise);
  const p1 = store.refresh(),
    p2 = store.refresh();
  fresh.resolve({ data: { items: [{ ...first, name: "Current" }] } });
  await p2;
  old.resolve({ data: { items: [{ ...first, name: "Stale" }] } });
  await p1;
  expect(store.items[0].name).toBe("Current");
  expect(store.loading).toBe(false);
});
