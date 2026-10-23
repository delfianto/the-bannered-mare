import { describe, expect, it } from "vite-plus/test";
import { createMemoryHistory, createRouter } from "vue-router";
import { flushPromises } from "@vue/test-utils";
import { useQueryState } from "@/composables/useQueryState";
import { mountComposable } from "@/test/helpers";

async function setup(query: Record<string, string | null | string[]>) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/models", component: { template: "<div/>" } }],
  });
  await router.push({ path: "/models", query });
  await router.isReady();
  return { ...mountComposable(useQueryState, { global: { plugins: [router] } }), router };
}
describe("URL-backed filter state", () => {
  it("reads only nonempty scalar query values", async () => {
    const { api } = await setup({ q: "dragon", empty: "", flag: null, repeated: ["a", "b"] });
    expect(api.readQuery("q")).toBe("dragon");
    for (const key of ["empty", "flag", "repeated", "missing"])
      expect(api.readQuery(key)).toBeUndefined();
  });
  it("merges into current query, stringifies zero and drops cleared keys", async () => {
    const { api, router } = await setup({ tab: "models", q: "old", page: "4" });
    api.patchQuery({ q: "", page: 0, family: "meta/muse", unused: undefined });
    await flushPromises();
    expect(router.currentRoute.value.query).toEqual({
      tab: "models",
      page: "0",
      family: "meta/muse",
    });
    await router.replace({ query: { tab: "families", fresh: "kept" } });
    api.patchQuery({ page: 2 });
    await flushPromises();
    expect(router.currentRoute.value.query).toEqual({ tab: "families", fresh: "kept", page: "2" });
  });
});
