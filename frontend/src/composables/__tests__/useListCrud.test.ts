import { describe, expect, it, vi } from "vite-plus/test";
import { flushPromises } from "@vue/test-utils";
import { useListCrud } from "@/composables/useListCrud";
import { mountComposable } from "@/test/helpers";

type Item = { id: string; is_default?: boolean; name: string };
type Result = { data?: Item; error?: unknown; response?: Response };
function setup(autoLoad = false) {
  const rows: Item[] = [
    { id: "a", name: "A", is_default: true },
    { id: "b", name: "B" },
  ];
  const ops = {
    label: "persona",
    singleDefault: true,
    autoLoad,
    list: vi.fn(
      async (_scope?: string): Promise<{ data?: { items: Item[] }; error?: unknown }> => ({
        data: { items: rows },
      }),
    ),
    create: vi.fn(async (body: Item): Promise<Result> => ({ data: body })),
    update: vi.fn(async (_id: string, body: Item): Promise<Result> => ({ data: body })),
    remove: vi.fn(async (_id: string): Promise<Result> => ({})),
    setDefault: vi.fn(async (_id: string): Promise<Result> => ({})),
  };
  const { api } = mountComposable(() => useListCrud<Item, [string?], Item, Item>(ops));
  return { api, ops };
}

describe("per-view CRUD lists", () => {
  it("auto-loads on mount and forwards refresh filters", async () => {
    const { api, ops } = setup(true);
    await flushPromises();
    expect(api.items.value).toHaveLength(2);
    expect(ops.list).toHaveBeenCalledTimes(1);
    api.refresh("global");
    await flushPromises();
    expect(ops.list).toHaveBeenLastCalledWith("global");
  });

  it("reconciles creates, updates, defaults and deletes in the displayed list", async () => {
    const { api } = setup();
    await api.fetchList();
    const created = { id: "c", name: "C", is_default: true };
    expect(await api.createItem(created)).toEqual(created);
    expect(api.items.value[1].is_default).toBe(false);
    await api.updateItem("b", { id: "b", name: "Updated", is_default: true });
    expect(api.items.value.filter((i) => i.is_default).map((i) => i.id)).toEqual(["b"]);
    await api.setDefaultItem("a");
    expect(api.items.value.filter((i) => i.is_default).map((i) => i.id)).toEqual(["a"]);
    await api.removeItem("b");
    expect(api.items.value.map((i) => i.id)).toEqual(["c", "a"]);
  });

  it.each(["create", "update", "remove", "setDefault"] as const)(
    "failed %s preserves rows and exposes the error",
    async (op) => {
      const { api, ops } = setup();
      await api.fetchList();
      const before = JSON.parse(JSON.stringify(api.items.value));
      ops[op].mockResolvedValueOnce({
        error: { detail: "Conflict" },
        response: new Response(null, { status: 409 }),
      });
      const result =
        op === "create"
          ? await api.createItem({ id: "c", name: "C" })
          : op === "update"
            ? await api.updateItem("a", { id: "a", name: "New" })
            : op === "remove"
              ? await api.removeItem("a")
              : await api.setDefaultItem("b");
      expect(result).toBe(op === "create" || op === "update" ? null : false);
      expect(api.items.value).toEqual(before);
      expect(api.error.value).toMatchObject({ message: "Conflict", statusCode: 409 });
    },
  );

  it("failed fetch retains the previous rows and a retry clears the error", async () => {
    const { api, ops } = setup();
    await api.fetchList();
    ops.list.mockRejectedValueOnce(new Error("offline"));
    await api.fetchList();
    expect(api.loading.value).toBe(false);
    expect(api.items.value).toHaveLength(2);
    expect(api.error.value?.message).toBe("offline");
    await api.fetchList();
    expect(api.error.value).toBeNull();
  });
});
