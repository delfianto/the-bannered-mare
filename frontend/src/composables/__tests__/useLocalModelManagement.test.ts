import { afterEach, beforeEach, describe, expect, it, vi } from "vite-plus/test";
import { ref } from "vue";
import { createPinia, setActivePinia } from "pinia";
import { http, HttpResponse } from "msw";
import { useLocalModelManagement } from "@/composables/useLocalModelManagement";
import { useProvider } from "@/composables/useProvider";
import { useConfirmState } from "@/composables/useConfirm";
import { useToastState } from "@/composables/useToast";
import { providers } from "@/mocks/data/providers";
import { server } from "@/mocks/server";
import { mountComposable } from "@/test/helpers";

beforeEach(() => {
  setActivePinia(createPinia());
  vi.useFakeTimers();
});
afterEach(() => {
  useConfirmState().onCancel();
  useToastState().value = [];
  vi.useRealTimers();
});
function setup() {
  const ops = {
    syncNow: vi.fn(async () => {}),
    loadModel: vi.fn(async () => {}),
    unloadModel: vi.fn(async () => {}),
    deleteModel: vi.fn(async () => {}),
    reloadPersisted: vi.fn(),
  };
  return { ...mountComposable(() => useLocalModelManagement(ref(providers[0]), ops)), ops };
}
describe("local model operations", () => {
  it.each([
    ["handleLoadModel", "loadModel"],
    ["handleUnloadModel", "unloadModel"],
    ["handleDeleteModel", "deleteModel"],
  ] as const)("%s waits for confirmation and cancellation makes no change", async (action, op) => {
    const { api, ops } = setup();
    const pending = api[action]("model:Q4");
    expect(ops[op]).not.toHaveBeenCalled();
    useConfirmState().onCancel();
    await pending;
    expect(ops[op]).not.toHaveBeenCalled();
    expect(ops.reloadPersisted).not.toHaveBeenCalled();
  });

  it("confirmed deletion targets the requested identifier and refreshes persisted models", async () => {
    const { api, ops } = setup();
    const pending = api.handleDeleteModel("model:Q4");
    expect(useConfirmState().state.value.danger).toBe(true);
    useConfirmState().onConfirm();
    await pending;
    expect(ops.deleteModel).toHaveBeenCalledWith(providers[0].id, "model:Q4");
    expect(ops.reloadPersisted).toHaveBeenCalledTimes(1);
    expect(useToastState().value.at(-1)?.type).toBe("success");
  });

  it("failed deletion reports the provider error and does not refresh the list", async () => {
    const { api, ops } = setup();
    ops.deleteModel.mockRejectedValueOnce(new Error("File is locked"));
    const pending = api.handleDeleteModel("model");
    useConfirmState().onConfirm();
    await pending;
    expect(ops.reloadPersisted).not.toHaveBeenCalled();
    expect(useToastState().value.at(-1)).toMatchObject({ type: "error", title: "File is locked" });
  });

  it("a failed real provider sync shows an error, not a success toast", async () => {
    const providerApi = useProvider();
    providerApi.provider.value = { ...providers[0] };
    server.use(
      http.post("/api/providers/:id/models/sync", () =>
        HttpResponse.json({ detail: "Offline" }, { status: 503 }),
      ),
    );
    const { api } = mountComposable(() =>
      useLocalModelManagement(providerApi.provider, { ...providerApi, reloadPersisted: () => {} }),
    );
    await api.handleSyncNow();
    expect(providerApi.modelsError.value).toBeInstanceOf(Error);
    expect(useToastState().value.at(-1)?.type).toBe("error");
  });
});
