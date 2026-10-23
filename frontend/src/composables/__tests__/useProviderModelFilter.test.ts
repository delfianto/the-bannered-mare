import { afterEach, beforeEach, describe, expect, it, vi } from "vite-plus/test";
import { ref } from "vue";
import { flushPromises } from "@vue/test-utils";
import { useProviderModelFilter } from "@/composables/useProviderModelFilter";
import { useToastState } from "@/composables/useToast";
import { providers } from "@/mocks/data/providers";
import { deferred, mountComposable } from "@/test/helpers";

beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  vi.useRealTimers();
  useToastState().value = [];
});
function setup() {
  const provider = ref({ ...providers[0], allowed_models: ["existing"] });
  const ops = {
    searchModels: vi.fn(async (_id: string, _q: string) => []),
    clearSearch: vi.fn(),
    setModelFilter: vi.fn(async (_id: string, _models: string[]) => {}),
  };
  return { ...mountComposable(() => useProviderModelFilter(provider, ops)), ops, provider };
}
describe("provider allow-list controls", () => {
  it("debounces search and sends trimmed query text", async () => {
    const { api, ops, provider } = setup();
    api.modelSearchQuery.value = " m ";
    api.onSearchInput();
    vi.advanceTimersByTime(100);
    api.modelSearchQuery.value = " meta/muse ";
    api.onSearchInput();
    await vi.advanceTimersByTimeAsync(250);
    expect(ops.searchModels).toHaveBeenCalledTimes(1);
    expect(ops.searchModels).toHaveBeenCalledWith(provider.value.id, "meta/muse");
  });

  it("clearing search before the debounce fires cancels the stale query", async () => {
    const { api, ops } = setup();
    api.modelSearchQuery.value = "old";
    api.onSearchInput();
    api.modelSearchQuery.value = "";
    api.onSearchInput();
    await vi.advanceTimersByTimeAsync(250);
    expect(ops.searchModels).not.toHaveBeenCalled();
    expect(api.showSearchResults.value).toBe(false);
  });

  it("clearing search while the HTTP call is pending does not reopen the dropdown", async () => {
    const { api, ops } = setup();
    const gate = deferred<never[]>();
    ops.searchModels.mockReturnValueOnce(gate.promise);
    api.modelSearchQuery.value = "old";
    api.onSearchInput();
    await vi.advanceTimersByTimeAsync(250);
    api.modelSearchQuery.value = "";
    api.onSearchInput();
    gate.resolve([]);
    await flushPromises();
    expect(api.showSearchResults.value).toBe(false);
  });

  it("ignores duplicate additions, persists edits and clears the selection search", async () => {
    const { api, ops, provider } = setup();
    expect(api.isFiltered("existing")).toBe(true);
    await api.addToFilter("existing");
    expect(ops.setModelFilter).not.toHaveBeenCalled();
    await api.addToFilter("new");
    expect(ops.setModelFilter).toHaveBeenLastCalledWith(provider.value.id, ["existing", "new"]);
    expect(api.modelSearchQuery.value).toBe("");
    await api.removeFromFilter("existing");
    expect(ops.setModelFilter).toHaveBeenLastCalledWith(provider.value.id, []);
    await api.clearFilter();
    expect(ops.clearSearch).toHaveBeenCalled();
  });

  it("failed saves show an error toast and leave the persisted allow-list intact", async () => {
    const { api, ops, provider } = setup();
    ops.setModelFilter.mockRejectedValueOnce(new Error("offline"));
    await api.removeFromFilter("existing");
    expect(provider.value.allowed_models).toEqual(["existing"]);
    expect(useToastState().value.at(-1)?.type).toBe("error");
  });
});
