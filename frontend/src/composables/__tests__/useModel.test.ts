import { describe, expect, it } from "vite-plus/test";
import { http, HttpResponse } from "msw";
import { server } from "@/mocks/server";
import { useModel } from "@/composables/useModel";
import { allModelsMock } from "@/mocks/data/models-data";
import { allModelFamiliesMock } from "@/mocks/data/model-families-data";

function setup() {
  const row = structuredClone(allModelsMock[0]);
  const family = structuredClone(allModelFamiliesMock.find((f) => f.id === row.model_family_id)!);
  server.use(
    http.get("/api/models/:id", () => HttpResponse.json({ ...row, model_family: family })),
  );
  return { api: useModel(), row, family };
}

describe("model detail and routes over HTTP", () => {
  it("saves parameter overrides without losing embedded family metadata", async () => {
    const { api, row, family } = setup();
    await api.fetchModel(row.id);
    let received: unknown;
    server.use(
      http.put("/api/models/:id", async ({ request, params }) => {
        expect(params.id).toBe(row.id);
        received = await request.json();
        return HttpResponse.json({
          ...row,
          display_name: "My model",
          parameters: { temperature: 0.7 },
        });
      }),
    );
    await api.saveModel(row.id, { display_name: "My model", parameters: { temperature: 0.7 } });
    expect(received).toEqual({ display_name: "My model", parameters: { temperature: 0.7 } });
    expect(api.model.value).toMatchObject({
      display_name: "My model",
      parameters: { temperature: 0.7 },
      model_family: family,
    });
  });

  it("adds an enabled route and preserves the loaded family", async () => {
    const { api, row, family } = setup();
    await api.fetchModel(row.id);
    let received: unknown;
    server.use(
      http.post("/api/models/:id/routes", async ({ request }) => {
        received = await request.json();
        return HttpResponse.json({ ...row, active_route_id: "new-route" });
      }),
    );
    await api.addRoute(row.id, {
      provider_id: "prov-openrouter",
      model_identifier: "openai/gpt-6-sol",
    });
    expect(received).toEqual({
      provider_id: "prov-openrouter",
      model_identifier: "openai/gpt-6-sol",
      enabled: true,
    });
    expect(api.model.value?.active_route_id).toBe("new-route");
    expect(api.model.value?.model_family).toEqual(family);
  });

  it("changes the active route and applies a returned replacement after deletion", async () => {
    const { api, row, family } = setup();
    await api.fetchModel(row.id);
    server.use(
      http.put("/api/models/:id/active-route", async ({ request }) => {
        expect(await request.json()).toEqual({ route_id: "alternate" });
        return HttpResponse.json({ ...row, active_route_id: "alternate" });
      }),
      http.delete("/api/models/:id/routes/:routeId", ({ params }) => {
        expect(params.routeId).toBe("alternate");
        return HttpResponse.json(row);
      }),
    );
    await api.setActiveRoute(row.id, "alternate");
    expect(api.model.value?.active_route_id).toBe("alternate");
    await api.deleteRoute(row.id, "alternate");
    expect(api.model.value?.active_route_id).toBe(row.active_route_id);
    expect(api.model.value?.model_family).toEqual(family);
  });

  it("failed route writes preserve detail and expose HTTP conflicts to the view", async () => {
    const { api, row } = setup();
    await api.fetchModel(row.id);
    const before = JSON.parse(JSON.stringify(api.model.value));
    server.use(
      http.put("/api/models/:id/active-route", () =>
        HttpResponse.json({ detail: "Route is disabled" }, { status: 409 }),
      ),
    );
    await expect(api.setActiveRoute(row.id, "disabled")).rejects.toMatchObject({
      message: "Route is disabled",
      statusCode: 409,
    });
    expect(api.model.value).toEqual(before);
    expect(api.saving.value).toBe(false);
  });

  it("creates a registry and toggles flags through their distinct API contracts", async () => {
    const { api, row } = setup();
    server.use(
      http.post("/api/models", async ({ request }) => {
        expect(await request.json()).toMatchObject({ display_name: "New" });
        return HttpResponse.json(row, { status: 201 });
      }),
      http.patch("/api/models/:id/flags", async ({ request }) => {
        expect(await request.json()).toEqual({ enabled: false });
        return HttpResponse.json({ ...row, enabled: false });
      }),
    );
    expect(
      await api.createModel({
        display_name: "New",
        model_family_id: row.model_family_id,
        enabled: true,
        routes: [],
      }),
    ).toEqual(row);
    expect((await api.toggleFlags(row.id, { enabled: false })).enabled).toBe(false);
  });
});
