import { describe, expect, it } from "vite-plus/test";
import { http, HttpResponse } from "msw";
import { useModels } from "@/composables/useModels";
import { server } from "@/mocks/server";
import { mountComposable } from "@/test/helpers";

describe("model list filter requests", () => {
  it("combines filters, preserves false status and restarts at page one", async () => {
    const queries: Record<string, string>[] = [];
    server.use(
      http.get("/api/models", ({ request }) => {
        queries.push(Object.fromEntries(new URL(request.url).searchParams));
        return HttpResponse.json({ items: [], meta: { has_more: false, total: 0 } });
      }),
    );
    const { api } = mountComposable(() =>
      useModels({
        autoLoad: false,
        pageSize: 5,
        initialPage: 3,
        initialFilters: { provider_id: "prov-openrouter" },
      }),
    );
    await api.search("meta/muse");
    await api.filterByStatus(false);
    await api.filterByFamily("family-meta");
    expect(queries.at(-1)).toEqual({
      page: "1",
      limit: "5",
      name__ilike: "meta/muse",
      provider_id: "prov-openrouter",
      model_family_id: "family-meta",
      enabled: "false",
    });
    await api.search("");
    await api.filterByProvider(undefined);
    await api.filterByStatus(undefined);
    await api.filterByFamily(undefined);
    expect(queries.at(-1)).toEqual({ page: "1", limit: "5" });
  });
});
