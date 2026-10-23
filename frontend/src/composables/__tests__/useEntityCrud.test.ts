import { describe, expect, it, vi } from "vite-plus/test";
import { useEntityCrud } from "@/composables/useEntityCrud";
import { deferred } from "@/test/helpers";

type Item = { id: string; name: string };
type Result = { data?: Item; error?: unknown; response?: Response };
const original = { id: "a", name: "Original" };
function setup() {
  const ops = {
    label: "model",
    fetchOne: vi.fn(async (_id: string): Promise<Result> => ({ data: original })),
    create: vi.fn(async (body: Item): Promise<Result> => ({ data: body })),
    update: vi.fn(async (_id: string, body: Item): Promise<Result> => ({ data: body })),
    remove: vi.fn(async (_id: string): Promise<Result> => ({})),
  };
  return { api: useEntityCrud<Item, Item, Item>(ops), ops };
}

describe("entity CRUD", () => {
  it("tracks pending reads and replaces the entity after success", async () => {
    const { api, ops } = setup();
    const gate = deferred<Result>();
    ops.fetchOne.mockReturnValueOnce(gate.promise);
    const pending = api.fetchItem("a");
    expect(api.loading.value).toBe(true);
    expect(api.item.value).toBeNull();
    gate.resolve({ data: original });
    await pending;
    expect(api.loading.value).toBe(false);
    expect(api.item.value).toEqual(original);
  });

  it("records read errors without destroying an already-loaded entity, then recovers", async () => {
    const { api, ops } = setup();
    await api.fetchItem("a");
    ops.fetchOne.mockResolvedValueOnce({
      error: { detail: "Not found" },
      response: new Response(null, { status: 404 }),
    });
    await api.fetchItem("missing");
    expect(api.item.value).toEqual(original);
    expect(api.error.value).toMatchObject({ message: "Not found", statusCode: 404 });
    await api.fetchItem("a");
    expect(api.error.value).toBeNull();
  });

  it("treats a missing read body as a failure and always resets loading", async () => {
    const { api, ops } = setup();
    ops.fetchOne.mockResolvedValueOnce({});
    await api.fetchItem("a");
    expect(api.error.value?.message).toBe("Failed to load model");
    expect(api.loading.value).toBe(false);
  });

  it.each(["create", "update", "remove"] as const)(
    "rethrows %s failures for the view and resets its busy flag",
    async (op) => {
      const { api, ops } = setup();
      await api.fetchItem("a");
      ops[op].mockRejectedValueOnce(new Error("offline"));
      const pending =
        op === "create"
          ? api.createItem(original)
          : op === "update"
            ? api.updateItem("a", original)
            : api.removeItem("a");
      expect(op === "remove" ? api.deleting.value : api.saving.value).toBe(true);
      await expect(pending).rejects.toThrow("offline");
      expect(api.error.value?.message).toBe("offline");
      expect(api.item.value).toEqual(original);
      expect(api.saving.value).toBe(false);
      expect(api.deleting.value).toBe(false);
    },
  );

  it("successful create returns the row; update replaces detail; delete accepts 204", async () => {
    const { api } = setup();
    expect(await api.createItem(original)).toEqual(original);
    const updated = { ...original, name: "Edited" };
    expect(await api.updateItem("a", updated)).toEqual(updated);
    expect(api.item.value).toEqual(updated);
    await expect(api.removeItem("a")).resolves.toBeUndefined();
  });

  it("custom mutations share error/status handling and recover on retry", async () => {
    const { api } = setup();
    await expect(
      api.runSaving(
        async () => ({
          error: { detail: [{ msg: "Invalid route" }] },
          response: new Response(null, { status: 422 }),
        }),
        "Failed to activate",
      ),
    ).rejects.toThrow("Invalid route");
    expect(api.error.value).toMatchObject({ statusCode: 422 });
    expect(api.saving.value).toBe(false);
    expect(await api.runSaving(async () => ({ data: false }), "Failed")).toBe(false);
    expect(api.error.value).toBeNull();
  });

  it("rejects an empty custom mutation body", async () => {
    const { api } = setup();
    await expect(api.runSaving(async () => ({}), "Missing result")).rejects.toThrow(
      "Missing result",
    );
  });
});

it("navigating between detail records discards the earlier request's late response", async () => {
  const { api, ops } = setup();
  const old = deferred<Result>(),
    fresh = deferred<Result>();
  ops.fetchOne.mockReturnValueOnce(old.promise).mockReturnValueOnce(fresh.promise);
  const p1 = api.fetchItem("old"),
    p2 = api.fetchItem("new");
  old.resolve({ data: { id: "old", name: "Stale" } });
  await p1;
  expect(api.loading.value).toBe(true);
  expect(api.item.value).toBeNull();
  fresh.resolve({ data: { id: "new", name: "Current" } });
  await p2;
  expect(api.item.value?.id).toBe("new");
  expect(api.loading.value).toBe(false);
});
